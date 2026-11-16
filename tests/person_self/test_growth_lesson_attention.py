"""A busy learned method must not erase another checked capability from C."""
import json
import pytest
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.open_agency.fixtures import numeric_learning,language_learning
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.records import RecordService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject import growth_life
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.reference import context_policy
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tools.nana_vision_first.demo import source,cue,post,advance
from .test_growth_inner_choice import grown
from .test_private_method_continuation import bind


@pytest.mark.parametrize('newer_checks,withdrawn',[(0,False),(32,False),(32,True)])
def test_normal_c_can_still_consider_a_different_checked_skill(tmp_path,newer_checks,withdrawn):
    clock=VirtualClock();seen=[];language_id=None;checked_sources={}
    def propose(request):
        context=json.loads(request.context_json);identity=context['manifest']
        growth=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='GROWTH_CHANGE')
        seen.append(growth['lesson_id']);use=growth['lesson_id']==language_id
        return StructuredProposal(interpretation='SYNTHETIC original C may use a different skill',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],
            interpretation='SYNTHETIC own language curiosity' if use else 'SYNTHETIC leave numeric outcome alone',
            preferred_behavior='REFLECT' if use else 'WATCH',proposed_operations=('DRAFT',) if use else ('WAIT',),
            private_question={'topic':'own-language-play','question':'SYNTHETIC Could this checked text method support my own wordplay?'} if use else None))
    with grown(tmp_path/'life',clock) as (r,first,origin,reuse,math_id),provider_harness(proposer=propose) as (transport,state):
        r.work.configure_open_learning((numeric_learning(),language_learning()))
        request=cue(r,'language-gap',ConcernCue(cue_kind='DISCOVERY',motivation_source='CURIOSITY',
            topic_key='own-language-gap',program_id='learn.language',possible_behaviors=('LEARN',)))
        post(r,'language-study',(request,),task_class='language');advance(r,clock,30)
        jobs=[row for row in r.store.all('jobs') if row['work_kind']=='LEARNING' and row['state']=='DONE']
        assert len(jobs)==2
        language_id=next(RecordService(r.store).read(row['record_id'])['payload']['lesson_id'] for row in jobs
            if RecordService(r.store).read(row['record_id'])['payload']['lesson_id']!=math_id)
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
        def check(key,lesson,case):
            mid=source(r,key,{'strategy_episode':{'episode_key':key,'lesson_id':lesson,'case':case.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
            checked_sources[key]=mid
            aid=review.assess(lesson,mid,authority=r.authority)
            assert growth_life.project(r.store,aid,scope='world',privacy_classes=('PUBLIC',))
            return aid
        check('language-unseen',language_id,LearningCase(case_id='language-unseen',context='own-wordplay',data='Ｓky\tblue',expected=['Sky','blue']))
        for i in range(newer_checks):
            clock.advance(SECOND);r.lease.heartbeat()
            check('numeric-unseen-'+str(i),math_id,LearningCase(case_id='numeric-unseen-'+str(i),context='mathematical-check-'+str(i),data=[100+i,.25],expected=100.25+i))
        if withdrawn:MemoryService(r.store,r.authority).forget(checked_sources['language-unseen'],r.authority)
        before=r.store.db.total_changes
        views=growth_life.opportunities(r.store,scope='world',privacy_classes=('PUBLIC',))
        print(json.dumps({'math':math_id,'language':language_id,'views':[v.lesson_id for v in views], 'states':[(row['lesson_id'],row['state']) for row in r.store.all('lessons')]}))
        assert {v.lesson_id for v in views}==({math_id} if withdrawn else {math_id,language_id})
        assert r.store.db.total_changes==before
        bind(r,transport,context_policy());counts={t:len(r.store.all(t)) for t in ('goals','actions','grants')}
        clock.advance(3*SECOND);r.lease.heartbeat();r.refresh_attention()
        for _ in range(20):
            clock.advance(r.config.cognition_cooldown_us+SECOND);r.lease.heartbeat();r.step()
        assert (language_id in seen) is (not withdrawn)
        own=[(rid,v) for rid,v in candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL')) if v.category=='PRIVATE_QUESTION' and v.topic=='own-language-play']
        assert len(own)==(0 if withdrawn else 1) and counts=={t:len(r.store.all(t)) for t in counts}
        calls=state['calls']
        for _ in range(3):r.refresh_attention();r.step()
        assert state['calls']==calls
        if not withdrawn:
            MemoryService(r.store,r.authority).forget(checked_sources['language-unseen'],r.authority)
            assert not RecordService(r.store).current_support(own[0][0])
        assert r.store.one('lessons',language_id)['state']=='ACTIVE'
        assert language_id not in {v.lesson_id for v in growth_life.opportunities(r.store,scope='world',privacy_classes=('PUBLIC',))}
        print(json.dumps({'other_method_checks':newer_checks,'source_withdrawn_before_c':withdrawn,'original_learning_jobs':2,
            'language_considered':language_id in seen,'own_questions':len(own),'self_calls':calls,'real_provider_calls':0,'new_actions_or_grants':False,
            'input_bytes':[row['input_bytes'] for row in r.store.all('cognitive_requests')]}))
