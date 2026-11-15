"""A governed Bilibili watch keeps the exact source's withdrawal lineage."""
import json
import pytest

from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.world_loop.cognition import CognitionSession
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.life.bilibili import BilibiliPublicTransport
from tests.living_release_v4.bilibili_loopback import counterpart
from tests.living_release_v4.test_bilibili_reads import grant, proposal, setup
from tests.world_loop.helpers import fresh, policy


def test_original_source_withdrawal_removes_watch_and_frame_experiences(tmp_path):
    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (model, _), \
            fresh(tmp_path/'subject.db', Clock()) as runtime:
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9)
        read, source = setup(runtime, opener, transport)
        session = CognitionSession(runtime, model, policy())
        concerns = ConcernService(runtime, resources=(read.port.registry.resource,))
        interpreted = session.execute(session.prepare('lineage-interest', 'INTERPRET', (source,)))
        concerns.offer(interpreted['record_id'])
        event = read.port.bind_event(concerns.opportunity().input, source, discover=False, visual=True)
        cycle = runtime.subject.run(event)
        grant(runtime, read, limit=10)
        _, action = read.propose(cycle.intention_id, expected_revision=1,
                                 args=read.port.args_for_cycle(cycle.cycle_id, source), input_memory_ids=(source,))
        assert read.dispatch(cycle.intention_id, action, expected_revision=1) == 'SUCCEEDED'
        receipt = json.loads(read.kernel.payload(runtime.store.one('actions', action), 'result_json'))
        video, frames = receipt['source_memory_id'], receipt['frame_memory_ids']
        assert len(frames) == 3 and not platform['posts']
        memory = MemoryService(runtime.store, runtime.authority)
        memory.forget(source, runtime.authority)
        for mid in (video, *frames):
            with pytest.raises(CoreError):
                memory.read(mid)


def test_source_withdrawn_during_fetch_is_not_retained_or_replayed(tmp_path):
    with counterpart() as (opener, platform), provider_harness(proposer=proposal) as (model, _), \
            fresh(tmp_path/'subject.db', Clock()) as runtime:
        transport = BilibiliPublicTransport(authorized=True, origin='SYNTHETIC_FIXTURE', request_limit=9)
        read, source = setup(runtime, opener, transport)
        session = CognitionSession(runtime, model, policy())
        concerns = ConcernService(runtime, resources=(read.port.registry.resource,))
        interpreted = session.execute(session.prepare('race-interest', 'INTERPRET', (source,)))
        concerns.offer(interpreted['record_id'])
        event = read.port.bind_event(concerns.opportunity().input, source, discover=False, visual=True)
        cycle = runtime.subject.run(event)
        grant(runtime, read, limit=10)
        _, action = read.propose(cycle.intention_id, expected_revision=1,
                                 args=read.port.args_for_cycle(cycle.cycle_id, source), input_memory_ids=(source,))
        original = transport.read_video
        def fetch_and_withdraw(*args, **kwargs):
            result = original(*args, **kwargs)
            MemoryService(runtime.store, runtime.authority).forget(source, runtime.authority)
            return result
        transport.read_video = fetch_and_withdraw
        with pytest.raises(CoreError, match='ACTION_PAYLOAD_SOURCE_NOT_CURRENT'):
            read.dispatch(cycle.intention_id, action, expected_revision=1)
        request_count = len(platform['requests'])
        assert request_count > 0 and not platform['posts']
        rows = runtime.store.db.execute("SELECT COUNT(*) FROM continuity_evidence WHERE source_namespace='recorded.project.bilibili.frames'").fetchone()[0]
        assert rows == 0
        active = runtime.store.db.execute("SELECT COUNT(*) FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='recorded.project.bilibili' AND m.lifecycle='ACTIVE'").fetchone()[0]
        assert active == 0
        assert runtime.store.one('actions', action)['state'] == 'UNKNOWN'
        try:
            read.dispatch(cycle.intention_id, action, expected_revision=1)
        except CoreError:
            pass
        assert len(platform['requests']) == request_count


def test_same_video_with_distinct_source_lineage_withdraws_independently(tmp_path):
    from types import SimpleNamespace
    from nana_core.life.bilibili import BilibiliSourceAdapter, PublicReading
    from tests.world_loop.helpers import capture
    with fresh(tmp_path/'subject.db', Clock()) as runtime:
        a = capture(runtime, 'source-a', {'synthetic': 'independent source A'})
        b = capture(runtime, 'source-b', {'synthetic': 'independent source B'})
        adapter = BilibiliSourceAdapter(SimpleNamespace(runtime=runtime, policy=policy()))
        reading = PublicReading('same-video', 'VIDEO_READING', runtime.clock.utc_now_us(),
            {'bvid':'BV1t55v6DE2v', 'cid':8, 'coverage':'METADATA_ONLY_NOT_WATCHED'}, 'SYNTHETIC_FIXTURE')
        first = adapter.ingest(reading, parents=(a,))
        second = adapter.ingest(reading, parents=(b,))
        assert first != second
        memory = MemoryService(runtime.store, runtime.authority)
        memory.forget(a, runtime.authority)
        with pytest.raises(CoreError):
            memory.read(first)
        assert memory.read(second)['memory_id'] == second
