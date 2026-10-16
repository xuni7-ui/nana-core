import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.temporal import TemporalMemoryService,FactValidity
from nana_core.continuity.skills import OfflineLearningPolicy,OfflineSkillService
from nana_core.presence.contracts import SECOND
from .helpers import fresh,event
from .test_agency import setup,start


def capture(r,key,text,**kwargs):
    m=MemoryService(r.store)
    eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.life',source_reference=key,source_kind='DIRECT_OBSERVATION'),text=text,observed_time_us=r.clock.utc_now_us(),privacy_class='PERSONAL'))
    return m.add(MemoryCandidate(entity_id='synthetic-person',scope='lab',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,**kwargs))


def test_sliced_maintenance_yields_to_input_and_delete_invalidates_summary(tmp_path):
    with fresh(tmp_path/'self.db') as r:
        ids=[capture(r,str(i),'A fictional source '+str(i)) for i in range(6)]
        r.work.maintenance.interval=SECOND;r.work.maintenance.discover()
        r.clock.source.advance(SECOND)
        first=r.step();assert first['maintenance']['read_count']<=4
        cursor=r.store.all('jobs')[0]['cursor']
        r.submit(event(r,'user',text='A synthetic priority message',significance='RELEVANT'))
        assert r.step()['cycle'].intention.self_generated is False
        assert r.store.all('jobs')[0]['cursor']==cursor
        r.drain(10)
        summaries=[m for m in r.store.all('memories') if m['epistemic_kind']=='SUMMARY']
        assert summaries and all(m['authority']=='INFERRED' for m in summaries)
        MemoryService(r.store,r.authority).forget(ids[0],r.authority)
        assert r.store.one('memories',summaries[0]['memory_id'])['lifecycle']=='DELETED'


def test_time_validity_is_not_event_time_and_past_query_cannot_undo_delete(tmp_path):
    with fresh(tmp_path/'self.db') as r:
        mid=capture(r,'fact','A fictional service is available')
        service=TemporalMemoryService(r.store,r.authority);before=r.clock.utc_now_us()
        r.clock.source.advance(SECOND)
        validity=FactValidity(memory_id=mid,valid_from_us=10,valid_until_us=20,reference_time_us=15)
        support=capture(r,'validity',validity.model_dump_json())
        service.declare(validity,support_memory_id=support,expected_revision=0,authority=r.authority)
        kwargs=dict(scopes=('lab',),privacy_classes=('PERSONAL',))
        assert service.view(mid,as_of_valid_us=15,as_of_known_us=before,**kwargs).validity=='UNKNOWN'
        assert service.view(mid,as_of_valid_us=20,as_of_known_us=r.clock.utc_now_us(),**kwargs).validity=='OUTSIDE'
        assert service.view(mid,as_of_valid_us=15,as_of_known_us=r.clock.utc_now_us(),**kwargs).validity=='WITHIN'
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        with pytest.raises(CoreError,match='UNAVAILABLE'):service.view(mid,as_of_valid_us=15,as_of_known_us=before,**kwargs)


def test_verified_failure_reflection_changes_future_plan_and_offline_skill(tmp_path):
    with fresh(tmp_path/'subject'/'self.db',idle_recall_us=SECOND,review_interval_us=SECOND) as r:
        p,mid=setup(r,tmp_path/'world'/'world.fixture.json');r.work.learning_policy=OfflineLearningPolicy()
        start(r,mid);r.step();r.clock.source.advance(SECOND);r.step()
        assert r.store.all('goals')[0]['state']=='FAILED'
        r.clock.source.advance(2*SECOND);r.refresh_attention();r.drain(20)
        assert r.store.all('lessons') and r.store.all('lessons')[0]['state']=='ACTIVE'
        r.submit(event(r,'second-try',background=True,source_memory_ids=(mid,)))
        r.drain(5)
        plans=r.store.all('plans');record=r.store.one('goals',plans[-1]['goal_id'])
        import json
        body=r.work.agency.records.read(json.loads(record['body_json'])['plan_record_id'])['payload']
        assert [s['capability'] for s in body['steps']]==['reading.source.read','reading.source.locate','reading.card.create']
        for _ in range(4):r.clock.source.advance(SECOND);r.drain(8)
        assert r.store.all('goals')[-1]['state']=='COMPLETED'
        registry=r.work.agency.policy
        service=OfflineSkillService(r.store,r.authority,registry)
        proposal=service.propose(r.store.all('lessons')[0]['lesson_id'],p.model_copy(update={'program_id':'fixture.learned-reading'}))
        grants=r.store.all('grants')
        assert service.enable_offline(proposal,authority=r.authority)=='fixture.learned-reading'
        assert r.store.all('grants')==grants
