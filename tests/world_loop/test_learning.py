import pytest
from nana_core.contracts import CoreError
from nana_core.storage import canonical
from nana_core.continuity.open_agency.fixtures import numeric_learning
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.subject import SubjectInput
from nana_core.presence.contracts import RuntimeEvent,Cause
from nana_core.continuity.memory import MemoryService
from .helpers import *

@pytest.mark.parametrize('counter_data,expected,inapplicable', [
    ([.1, .2], .3, False),
    ('3.25 + 2.5', 5.75, True),
])
def test_episode_reuse_counterexample_and_independent_revalidation(tmp_path,monkeypatch,counter_data,expected,inapplicable):
    with fresh(tmp_path/'s'/'self.db') as r:
        r.work.configure_open_learning((numeric_learning(),))
        cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='SELF_DEVELOPMENT',topic_key='numbers',program_id='learn.numbers',possible_behaviors=('LEARN',))
        mid=capture(r,'learn',{'data':'numeric precision concern'})
        m=MemoryService(r.store);e=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.learn-cue',source_reference='cue',source_kind='DIRECT_OBSERVATION'),text=cue.model_dump_json(),privacy_class='PUBLIC',observed_time_us=r.clock.utc_now_us()));c=m.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.PROSPECTIVE,epistemic_kind='OBSERVATION',source_evidence_id=e,text=cue.model_dump_json(),predicate_key='concern.numbers'))
        inp=SubjectInput(source_key='synthetic.learn',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(c,),observed_at_us=r.clock.utc_now_us())
        r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='MEMORY',reference_id=c),),due_at_us=r.clock.utc_now_us()));r.drain(32)
        lesson=r.store.all('lessons')[0];assert lesson['state']=='ACTIVE'
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
        def assess(key,data,expected,*,kind='DIRECT_OBSERVATION'):
            body={'strategy_episode':{'episode_key':key,'lesson_id':lesson['lesson_id'],'case':LearningCase(case_id=key,context=key,data=data,expected=expected).model_dump(mode='json')}}
            mid=capture(r,key,body,kind=kind);aid=review.assess(lesson['lesson_id'],mid,authority=r.authority);return mid,aid
        assess('reuse',[3.5,2],5.5);view=review.view(lesson['lesson_id']);assert view['supports']==1 and view['state']=='ACTIVE'
        if inapplicable:
            with pytest.raises(CoreError,match='WORLD_NUMERIC_INPUT_REQUIRED'):
                assess('unverified-format',counter_data,expected,kind='USER_STATEMENT')
            assert review.view(lesson['lesson_id'])['state']=='ACTIVE'
            assert review.view(lesson['lesson_id'])['counterexamples']==0
        # A process can die after the independent verdict is durable but before
        # the caller resumes. Suspension must share that very same transaction.
        from contextlib import contextmanager
        original=r.store.transaction
        @contextmanager
        def after_commit(kind,*args,**kwargs):
            with original(kind,*args,**kwargs) as tx:yield tx
            if kind=='world.strategy_episode_checked':
                assert r.store.one('lessons',lesson['lesson_id'])['state']=='SUSPENDED'
        with monkeypatch.context() as patch:
            patch.setattr(r.store,'transaction',after_commit)
            counter,aid=assess('independent-counter',counter_data,expected,kind='SYSTEM_VERIFICATION')
        if inapplicable:
            rid=r.store.one('strategy_assessments',aid)['record_id']
            result=review.records.read(rid)['payload']['result']
            assert result['checked']==1 and result['passed']==0
            assert result['cases'][0]['reason']=='WORLD_NUMERIC_INPUT_REQUIRED'
            assert 'actual' not in result['cases'][0]
        assert review.view(lesson['lesson_id'])['counterexamples']==1 and not r.work.open_learning.strategy('numbers','world')
        assert review.assess(lesson['lesson_id'],counter,authority=r.authority)==aid
        assess('recheck-a',[2,3],5);assess('recheck-b',[1.25,2.5],3.75)
        with pytest.raises(CoreError,match='UNRESOLVED_COUNTEREXAMPLE'):review.revalidate(lesson['lesson_id'],authority=r.authority)
        MemoryService(r.store,r.authority).set_lifecycle(counter,'SUPPRESSED',r.authority)
        assert review.revalidate(lesson['lesson_id'],authority=r.authority)['state']=='ACTIVE'
        assert review.competition('numbers')[0]['state']=='ACTIVE'
        assert not r.store.all('cognitive_requests')


def test_transport_hypothesis_reuses_original_nine_stages_and_reflection_stays_proposal(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionSession
    from nana_core.continuity.world_loop.ports import CognitionLearningProposer
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.records import RecordService
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness() as (transport,metrics):
        source=capture(r,'source',{'data':'Independent numeric precision problem'})
        session=CognitionSession(r,transport,policy());port=CognitionLearningProposer(session,(source,))
        r.work.configure_open_learning((numeric_learning(),),proposer=port)
        cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='SELF_DEVELOPMENT',topic_key='numbers',program_id='learn.numbers',possible_behaviors=('LEARN',))
        e=MemoryService(r.store).capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.learning-cognition',source_reference='cue',source_kind='DIRECT_OBSERVATION'),text=cue.model_dump_json(),privacy_class='PUBLIC',observed_time_us=r.clock.utc_now_us()))
        mid=MemoryService(r.store).add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.PROSPECTIVE,epistemic_kind='OBSERVATION',source_evidence_id=e,text=cue.model_dump_json(),predicate_key='concern.numbers'))
        inp=SubjectInput(source_key='synthetic.learning-http',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(mid,),observed_at_us=r.clock.utc_now_us())
        r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=r.clock.utc_now_us()));r.drain(32)
        assert metrics['calls']==1
        lesson=r.store.all('lessons')[0];assert lesson['state']=='ACTIVE'
        records=RecordService(r.store);assert source in records.support(lesson['record_id'])
        work=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone()
        assert work['state']=='DONE' and work['cursor']==9
        assert records.read(work['record_id'])['payload']['hypothesis_source']==port.last_record_id
        before=(len(r.store.all('experiences')),len(r.store.all('lessons')))
        request=session.prepare('reflect-proposal','REFLECT',(source,));assert session.execute(request)['state']=='PROPOSED'
        assert (len(r.store.all('experiences')),len(r.store.all('lessons')))==before


@pytest.mark.parametrize('counter_privacy',['PUBLIC','PERSONAL'])
def test_later_success_population_cannot_hide_a_persisted_counterexample_on_restart(tmp_path,counter_privacy):
    """Recent good episodes cannot certify a method whose older defect remains."""
    from nana_core.presence.runtime import NanaRuntime
    from nana_core.continuity.records import RecordService
    import json,time
    path=tmp_path/'long'/'self.db'
    with fresh(path) as r:
        r.work.configure_open_learning((numeric_learning(),))
        cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='SELF_DEVELOPMENT',topic_key='numbers',
            program_id='learn.numbers',possible_behaviors=('LEARN',))
        m=MemoryService(r.store);e=m.capture(EvidenceInput(provenance=Provenance(
            source_namespace='synthetic.long-learning',source_reference='cue',source_kind='DIRECT_OBSERVATION'),
            text=cue.model_dump_json(),privacy_class='PUBLIC',observed_time_us=r.clock.utc_now_us()))
        mid=m.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.PROSPECTIVE,
            epistemic_kind='OBSERVATION',source_evidence_id=e,text=cue.model_dump_json(),predicate_key='concern.numbers'))
        inp=SubjectInput(source_key='synthetic.long-learning',kind='WAKE',origin='SELF_WAKE',entity_id='observer',
            scope='world',source_memory_ids=(mid,),observed_at_us=r.clock.utc_now_us())
        r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,
            causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=r.clock.utc_now_us()));r.drain(32)
        lesson=r.store.all('lessons')[0];lesson_id=lesson['lesson_id'];assert lesson['state']=='ACTIVE'
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC','PERSONAL'))
        def assess(key,data,expected):
            body={'strategy_episode':{'episode_key':key,'lesson_id':lesson_id,'case':LearningCase(
                case_id=key,context=key,data=data,expected=expected).model_dump(mode='json')}}
            source=capture(r,key,body,privacy=counter_privacy if key=='old-precision-counter' else 'PUBLIC');return source,review.assess(lesson_id,source,authority=r.authority)
        counter,aid=assess('old-precision-counter',[.1,.2],.3)
        for i in range(64):assess('later-success-'+str(i),[i,.5],i+.5)
        assert r.store.one('lessons',lesson_id)['state']=='SUSPENDED'
        config,clock,identity=r.config,r.clock,r.identity_id
    with NanaRuntime(path,config,clock=clock) as r:
        assert r.identity_id==identity
        r.work.configure_open_learning((numeric_learning(),))
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC','PERSONAL'))
        records=RecordService(r.store)
        assert records.current_support(r.store.one('strategy_assessments',aid)['record_id'])
        started=time.perf_counter();cpu=time.process_time();writes=r.store.db.total_changes;error=None
        try:review.revalidate(lesson_id,authority=r.authority)
        except CoreError as exc:error=exc.code
        print(json.dumps({'measurement':'persisted_counterexample_after64_successes','counter_privacy':counter_privacy,
            'result':error,'state':r.store.one('lessons',lesson_id)['state'],
            'method_available':bool(r.work.open_learning.strategy('numbers','world')),
            'elapsed_seconds':time.perf_counter()-started,'cpu_seconds':time.process_time()-cpu,
            'write_rows':r.store.db.total_changes-writes,'model_calls':len(r.store.all('cognitive_requests'))}))
        assert error=='UNRESOLVED_COUNTEREXAMPLE'
        assert r.store.db.total_changes==writes
        if counter_privacy=='PERSONAL':
            restricted=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
            with pytest.raises(CoreError,match='INDEPENDENT_REVALIDATION_REQUIRED'):
                restricted.revalidate(lesson_id,authority=r.authority)
        assert r.store.one('lessons',lesson_id)['state']=='SUSPENDED'
        assert r.work.open_learning.strategy('numbers','world') is None
        # Withdrawal still removes this evidence's influence; no permanent ban.
        MemoryService(r.store,r.authority).set_lifecycle(counter,'SUPPRESSED',r.authority)
        assert review.revalidate(lesson_id,authority=r.authority)['state']=='ACTIVE'
        assert r.work.open_learning.strategy('numbers','world')
        assert not r.store.all('cognitive_requests')
