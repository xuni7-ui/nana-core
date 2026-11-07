"""One real source remains one encounter across derived interpretation aliases."""
import pytest

from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.world_loop.cognition import CognitionSession, StructuredProposal, InterestProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from nana_core.continuity.subject.growth import Growth
from nana_core.contracts import CoreError
from nana_core.clock import ManualClock
from nana_core.life.inspector import inspect
from tests.world_loop.helpers import fresh, capture, policy, HOUR, SECOND


def proposer(request):
    return StructuredProposal(interpretation='SYNTHETIC curiosity proposal; no authority',
        source_refs=request.primary_source_refs, interests=(InterestProposal(
            topic='independent-curiosity', motivation_source='CURIOSITY',
            source_memory_ids=request.primary_source_refs,
            interpretation='A sourced question worth considering, not an event we performed'),))


def alias(r, root, key):
    memory = MemoryService(r.store)
    eid = memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.concern-alias',
        source_reference=key, source_kind='MODEL_DERIVATION'), text='SYNTHETIC interpretation '+key,
        privacy_class='PUBLIC', observed_time_us=r.clock.utc_now_us()))
    return memory.add(MemoryCandidate(entity_id='observer', scope='world', memory_type=MemoryType.EPISODIC,
        epistemic_kind='BELIEF', source_evidence_id=eid, text='SYNTHETIC interpretation '+key, derived_from=(root,)))


def offer(session, concerns, key, source):
    result = session.execute(session.prepare(key, 'INTERPRET', (source,)))
    assert result['state']=='PROPOSED'
    return concerns.offer(result['record_id'])


def test_interpretation_aliases_do_not_inflate_interest_but_independent_source_can(tmp_path):
    path = tmp_path/'subject/self.db'; clock=ManualClock()
    with fresh(path, clock) as r, provider_harness(proposer=proposer) as (transport, _):
        session = CognitionSession(r, transport, policy())
        concerns = ConcernService(r, resources=('synthetic://watch',), cognition=session)
        root = capture(r, 'original', {'data':'SYNTHETIC one public discovery'})
        cid = offer(session, concerns, 'first', root)[0]
        visible=inspect(tmp_path,scope='world',entity_id='observer',privacy=('PUBLIC',)).sections['concerns']
        assert len(visible)==1 and visible[0].state=='TRANSIENT'
        identity = r.identity_id
        for n in range(3):
            derived = alias(r, root, str(n))
            assert offer(session, concerns, 'alias-'+str(n), derived)==()
            row = r.store.one('open_concerns', cid)
            assert row['encounters']==1 and row['state']=='TRANSIENT'
            assert concerns.opportunity() is None
        assert not r.store.all('goals') and not r.store.all('actions') and not r.store.all('grants')
    with fresh(path, clock) as r, provider_harness(proposer=proposer) as (transport, _):
        session = CognitionSession(r, transport, policy()); concerns = ConcernService(r, resources=('synthetic://watch',), cognition=session)
        assert r.identity_id==identity and r.store.one('open_concerns', cid)['encounters']==1
        second = capture(r, 'new-source', {'data':'SYNTHETIC different independent discovery'})
        assert offer(session, concerns, 'second', second)==(cid,)
        assert r.store.one('open_concerns', cid)['encounters']==2
        assert r.store.one('open_concerns', cid)['state']=='INTEREST'
        visible=inspect(tmp_path,scope='world',entity_id='observer',privacy=('PUBLIC',)).sections['concerns']
        assert len(visible)==1 and visible[0].state=='INTEREST'
        event=concerns.opportunity()
        assert event is not None
        cycle=r.subject.run(event.input)
        assert cycle.intention.behavior=='EXPLORE' and cycle.intention.self_generated
        concerns.after_cycle(cycle,event.input,None)
        assert r.store.one('open_concerns',cid)['state']=='PROPOSED'
        assert inspect(tmp_path,scope='world',entity_id='observer',privacy=('PUBLIC',)).sections['concerns'][0].state=='PROPOSED'
        assert concerns.opportunity() is None  # no repeated C cycle without new support
        assert not r.store.all('actions') and not r.store.all('grants')
    clock.advance(3*24*HOUR+SECOND)
    with fresh(path, clock) as r:
        concerns=ConcernService(r, resources=('synthetic://watch',))
        assert concerns.opportunity() is None
        assert r.store.one('open_concerns', cid)['state']=='EXPIRED'
        assert r.identity_id==identity and MemoryService(r.store).read(root)
    with fresh(path, clock) as r, provider_harness(proposer=proposer) as (transport, _):
        session=CognitionSession(r, transport, policy()); concerns=ConcernService(r, resources=('synthetic://watch',), cognition=session)
        assert offer(session, concerns, 'old-alias-after-expiry', alias(r, root, 'late'))==()
        later=capture(r, 'later-independent', {'data':'SYNTHETIC renewed discovery after rest'})
        assert offer(session, concerns, 'revisit-later', later)==(cid,)
        current=r.store.one('open_concerns', cid)
        assert current['state']=='TRANSIENT' and current['encounters']==1
        assert concerns.opportunity() is None
        # Past model context remains traceable, never cut to bypass withdrawal.
        MemoryService(r.store, r.authority).forget(root, r.authority)
        assert concerns.view()==()
        assert not r.store.all('actions') and not r.store.all('grants')


def test_shared_root_resolution_can_be_bounded_without_changing_old_assertion_counting(tmp_path):
    with fresh(tmp_path/'subject.db') as r:
        root=capture(r, 'root', {'data':'SYNTHETIC original'})
        child=alias(r, root, 'child')
        growth=Growth(r.store)
        assert growth._roots(root)==growth._roots(child)
        assert growth.source_roots((root, child), max_nodes=4)==growth._roots(root)
        with pytest.raises(CoreError, match='SOURCE_ROOT_HORIZON'):
            growth.source_roots((child,), max_nodes=1)
