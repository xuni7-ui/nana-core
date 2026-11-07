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
    eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.life',source_reference=key,source_kind='DIRECT_OBSERVATION'),text=text,event_time_us=r.clock.utc_now_us(),observed_time_us=r.clock.utc_now_us(),privacy_class='PERSONAL'))
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


def test_corrected_validity_source_cannot_remain_current_authority(tmp_path):
    with fresh(tmp_path/'self.db') as r:
        mid=capture(r,'fact-source','A fictional changing fact')
        declaration=FactValidity(memory_id=mid,valid_from_us=10,valid_until_us=20)
        source=capture(r,'source-v1',declaration.model_dump_json(),predicate_key='validity.source')
        service=TemporalMemoryService(r.store,r.authority)
        service.declare(declaration,support_memory_id=source,expected_revision=0,authority=r.authority)
        known_before=r.clock.utc_now_us()
        r.clock.source.advance(SECOND)
        corrected=FactValidity(memory_id=mid,valid_from_us=30,valid_until_us=40)
        capture(r,'source-v2',corrected.model_dump_json(),predicate_key='validity.source',correction_of=source)
        kwargs=dict(scopes=('lab',),privacy_classes=('PERSONAL',),as_of_valid_us=15)
        assert service.view(mid,as_of_known_us=r.clock.utc_now_us(),**kwargs).validity=='UNKNOWN'
        assert service.view(mid,as_of_known_us=known_before,**kwargs).validity=='WITHIN'


def test_optional_consolidation_can_rest_then_resume_only_after_changed_original_attention(tmp_path):
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity.subject.opportunities import ConcernCue
    path=tmp_path/'self.db'
    with fresh(path) as r:
        clock=r.clock.source;identity=r.identity_id
        for n in range(6):
            cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CURIOSITY',topic_key='pending-'+str(n),possible_behaviors=('EXPLORE',))
            mid=capture(r,'pending-'+str(n),cue.model_dump_json(),predicate_key='concern.opportunity.'+str(n))
            cycle=r.subject.run(SubjectInput(kind='WAKE',origin='SELF_WAKE',source_key='synthetic.pending.'+str(n),entity_id='synthetic-person',scope='lab',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,)))
            assert cycle.intention.kind=='EXPLORE'
        assert len(r.subject.pending('lab'))==6
        capture(r,'meaningful','A SYNTHETIC significant project observation',importance=.9)
        maintenance=r.work.maintenance;maintenance.interval=SECOND;maintenance.discover()
        clock.advance(SECOND);r.lease.heartbeat()
        for _ in range(16):
            clock.advance(100_000);r.step()
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='MEMORY_REVIEW' AND state='PAUSED'").fetchone()
        assert job and not [m for m in r.store.all('memories') if m['epistemic_kind']=='SUMMARY']
        count=len(r.store.all('subject_cycles'))
        for _ in range(10):r.step()
        assert len(r.store.all('subject_cycles'))==count
        rid=job['record_id']
    with fresh(path,clock=clock) as r:
        assert r.identity_id==identity
        r.step();assert len(r.store.all('subject_cycles'))==count
        pending=r.subject.pending('lab')[0]
        r.subject.transition_intention(pending['intention_id'],expected_revision=pending['revision'],state='DROPPED')
        r.drain(16)
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='MEMORY_REVIEW' AND record_id=?",(rid,)).fetchone()
        assert job['state']=='DONE'
        assert any(m['epistemic_kind']=='SUMMARY' for m in r.store.all('memories'))
        assert not r.store.all('runtime_cognition_calls') and not r.store.all('actions')


def test_weekly_review_is_bounded_resumable_and_does_not_reinvent_unchanged_summary(tmp_path):
    import json
    path=tmp_path/'self.db'
    with fresh(path) as r:
        clock=r.clock.source;identity=r.identity_id
        for n in range(9):capture(r,'weekly-'+str(n),'SYNTHETIC weekly source '+str(n))
        maintenance=r.work.maintenance;maintenance.interval=SECOND;maintenance.discover()
        for _ in range(24):clock.advance(100_000);r.step()
        assert r.store.db.execute("SELECT 1 FROM events WHERE source_namespace='living.consolidation-adopted'").fetchone()
    clock.advance(7*86_400_000_000)
    with fresh(path,clock=clock) as r:
        maintenance=r.work.maintenance
        original=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='SCAN'").fetchone()
        before=r.store.db.execute("SELECT count(*) FROM events WHERE source_namespace='living.consolidation'").fetchone()[0]
        activity=maintenance.slice()
        assert activity['mode']=='WEEKLY_REVIEW' and activity['read_count']<=4
        job=r.store.one('jobs',original['job_id']);metadata=json.loads(job['body_json'])
        assert job['cursor']==original['cursor'] and metadata['deep_cursor']>0
        cursor=metadata['deep_cursor']
    with fresh(path,clock=clock) as r:
        assert r.identity_id==identity
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='SCAN'").fetchone()
        assert json.loads(job['body_json'])['deep_cursor']==cursor
        for _ in range(24):clock.advance(100_000);r.lease.heartbeat();r.work.maintenance.slice()
        assert r.store.db.execute("SELECT count(*) FROM events WHERE source_namespace='living.consolidation'").fetchone()[0]==before
        metadata=json.loads(r.store.one('jobs',job['job_id'])['body_json'])
        assert metadata['deep_cursor']==0 and metadata['last_deep_review_us']>=clock.utc_now_us()-3_000_000
        assert not r.store.all('runtime_cognition_calls')
