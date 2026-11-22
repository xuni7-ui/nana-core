import hashlib
import json
import sys
from pathlib import Path

from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.semantic_harness import semantic_harness, semantic_proposer
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import RuntimeConfig
from nana_core.presence.runtime import NanaRuntime
from tests.h1_semantics.test_grounding import ingest, setup
from tests.world_loop.helpers import fresh
from tests.world_loop.test_media_stream_binding import _write_irregular_video

phase, root = sys.argv[1], Path(sys.argv[2])
db, path, previous = root / 'subject/self.db', root / 'irregular.mkv', root / 'old.json'
clock = VirtualClock()

def propose(request):
    candidate = semantic_proposer(request)
    index = next(i for i, frame in enumerate(request.role_input['parts']) if frame['start_s'] == 6.)
    is_point = len(seen) == 2
    seen.append(index)
    observation = candidate.media.observations[0].model_copy(update={
        'part_indices': (index,), 'start_s': 6. if is_point else 6.3,
        'end_s': 6. if is_point else 6.5,
    })
    return candidate.model_copy(update={'media': candidate.media.model_copy(update={'observations': (observation,)})})

def source_hash(r, mid):
    return hashlib.sha256(MemoryService(r.store).read(mid)['text'].encode()).hexdigest()

if phase == 'old':
    _write_irregular_video(path, True)
    raw, seen = path.read_bytes(), []
    with fresh(db, clock) as runtime, semantic_harness(proposer=propose) as (transport, state):
        mid = ingest(runtime, 'VIDEO', raw, 'history-original')
        service = setup(runtime, transport)
        result = {}
        for key in ('already-grounded', 'yet-unsupported', 'yet-observed'):
            cid = service.prepare(key, mid, raw)
            assert service.execute(cid)['state'] == 'PROPOSED'
            result[key] = cid
            if key == 'already-grounded':
                result['original_result'] = service.ground(cid, entity_id='device')
                assert [6., 7.] in result['original_result']['covered_intervals']
        result.update(
            source_commit='0cb5cab7358a3b101811d566122aaa265fc499fe',
            source=mid, identity=runtime.identity_id, config=runtime.config.model_dump(mode='json'),
            source_sha256=source_hash(runtime, mid), calls=state['calls'],
        )
        assert len(seen) == state['calls'] == 3
        previous.write_text(json.dumps(result))
        print(json.dumps({'old_calls': state['calls'], 'old_interval': [6., 7.], 'unsupported_proposal_previously_accepted': True}))
else:
    old = json.loads(previous.read_text())
    config = RuntimeConfig.model_validate_json(json.dumps(old['config']))
    raw = path.read_bytes()
    with NanaRuntime(db, config, clock=clock) as runtime, semantic_harness() as (transport, state):
        assert old['identity'] == runtime.identity_id
        mid = old['source']
        service = setup(runtime, transport)
        for key in ('already-grounded', 'yet-unsupported', 'yet-observed'):
            assert service.prepare(key, mid, raw) == old[key]
            assert service.execute(old[key])['replayed']
        assert service.ground(old['already-grounded'], entity_id='device') == old['original_result']
        count = len(runtime.store.all('world_beliefs'))
        try:
            service.ground(old['yet-unsupported'], entity_id='gapped')
        except CoreError as error:
            assert error.code == 'SEMANTIC_VIDEO_COVERAGE_UNVERIFIED'
        else:
            raise AssertionError('old gap proposal was newly grounded')
        assert len(runtime.store.all('world_beliefs')) == count
        result = service.ground(old['yet-observed'], entity_id='observed')
        assert [6.,6.] in result['covered_intervals']
        assert [6.,7.] not in result['covered_intervals']
        assert len(runtime.store.all('world_beliefs')) == count + 1
        assert old['source_sha256'] == source_hash(runtime, mid)
        assert not runtime.store.all('actions') and not runtime.store.all('goals')
        assert state['calls'] == 0
        MemoryService(runtime.store,runtime.authority).forget(mid,runtime.authority)
        try:
            service.ground(old['already-grounded'], entity_id='device')
        except CoreError:
            pass
        else:
            raise AssertionError('withdrawn old observation still replayable')
        print(json.dumps({'same_subject': True, 'historical_result_exact': True, 'original_source_exact': True,
            'old_gap_ungrounded': True, 'old_point_grounded': True, 'after_upgrade_calls': state['calls'],
            'replayed_keys': 3, 'withdrawal_prevents_replay': True, 'real_provider_calls': 0}))
