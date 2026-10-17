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

def test_episode_reuse_counterexample_and_independent_revalidation(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        r.work.configure_open_learning((numeric_learning(),))
        cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='SELF_DEVELOPMENT',topic_key='numbers',program_id='learn.numbers',possible_behaviors=('LEARN',))
        mid=capture(r,'learn',{'data':'numeric precision concern'})
        m=MemoryService(r.store);e=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.learn-cue',source_reference='cue',source_kind='DIRECT_OBSERVATION'),text=cue.model_dump_json(),privacy_class='PUBLIC',observed_time_us=r.clock.utc_now_us()));c=m.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.PROSPECTIVE,epistemic_kind='OBSERVATION',source_evidence_id=e,text=cue.model_dump_json(),predicate_key='concern.numbers'))
        inp=SubjectInput(source_key='synthetic.learn',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(c,),observed_at_us=r.clock.utc_now_us())
        r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='MEMORY',reference_id=c),),due_at_us=r.clock.utc_now_us()));r.drain(32)
        lesson=r.store.all('lessons')[0];assert lesson['state']=='ACTIVE'
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
        def assess(key,data,expected):
            body={'strategy_episode':{'episode_key':key,'lesson_id':lesson['lesson_id'],'case':LearningCase(case_id=key,context=key,data=data,expected=expected).model_dump(mode='json')}}
            mid=capture(r,key,body);aid=review.assess(lesson['lesson_id'],mid,authority=r.authority);return mid,aid
        assess('reuse',[3.5,2],5.5);view=review.view(lesson['lesson_id']);assert view['supports']==1 and view['state']=='ACTIVE'
        counter,aid=assess('precision-counter',[.1,.2],.3);assert review.view(lesson['lesson_id'])['counterexamples']==1 and not r.work.open_learning.strategy('numbers','world')
        assert review.assess(lesson['lesson_id'],counter,authority=r.authority)==aid
        assess('recheck-a',[2,3],5);assess('recheck-b',[1.25,2.5],3.75)
        with pytest.raises(CoreError,match='UNRESOLVED_COUNTEREXAMPLE'):review.revalidate(lesson['lesson_id'],authority=r.authority)
        MemoryService(r.store,r.authority).set_lifecycle(counter,'SUPPRESSED',r.authority)
        assert review.revalidate(lesson['lesson_id'],authority=r.authority)['state']=='ACTIVE'
        assert review.competition('numbers')[0]['state']=='ACTIVE'


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
