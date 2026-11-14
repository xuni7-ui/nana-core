"""Normal D must not turn C's tentative default into a fixed living priority."""
import json
import pytest
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.continuity.commitments import CommitmentService,CommitmentCandidate
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_private_tendency import form,current
from .test_private_feedback_continuation import wording


@pytest.mark.parametrize('basis',['initial-method','own-tendency'])
@pytest.mark.parametrize('blocked',[False,True])
def test_normal_d_can_offer_c_private_reflection_against_due_promise_but_preserves_norm_and_promise(tmp_path,basis,blocked):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    private='PRIVATE_CHOICE: I would like to reconsider my own concern while recognizing that my promise is still due.'
    topic='initial-choice' if basis=='initial-method' else 'own-concern'
    def meaning(request):return {'communication_proposal':{'approach':'LISTEN','detail':'BRIEF','follow_up':'NONE','strategy_duration_seconds':3600}}
    def inner(request):
        seen.append(request);context=json.loads(request['context_json']);manifest=context['manifest']
        frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert any(m['source']=='COMMITMENT' and m['strength']=='PRESSING' for m in frame['motivations'])
        assert 'REFLECT' in frame['behavior_options']
        own=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY']
        assert bool(own)==(basis=='own-tendency')
        return {'interpretation':'SYNTHETIC normal D offers a choice; source promise is neither erased nor executed',
            'subject_cognition':{'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],
                'interpretation':'SYNTHETIC explicitly select own reflection rather than silently overriding the promise',
                'preferred_behavior':'REFLECT','proposed_operations':['DRAFT'],
                'private_tendency':{'topic':topic,'tendency':private,**({'revises_record_id':own[0]['record_id']} if own else {})}}}
    with relay(home,'CHAT',meaning_builder=meaning,renderer=wording,subject_builder=inner,context_limit=65536) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();r=app.runtime;identity=r.identity_id
            if basis=='initial-method':
                app.chat('SYNTHETIC an actual retained occurrence',topic=topic,privacy='PERSONAL',retain_shared_life=True,message_id='initial')
            else:form(app)
            source=capture(r,'private-choice-due',{'source':'SYNTHETIC independently adopted promise'})
            promises=CommitmentService(r.store,r.authority)
            cid=promises.propose(CommitmentCandidate(entity_id='project-user',scope='project-work',description='SYNTHETIC due promise still matters',support_memory_ids=(source,),due_at_us=clock.utc_now_us()-1))
            promises.transition(cid,'ADOPTED',expected_revision=1,authority=r.authority);promise=dict(r.store.one('commitments',cid))
            if blocked:
                norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key=topic,prohibited_behaviors=('REFLECT',))
                capture(r,'private-choice-norm',norm.model_dump(mode='json'),predicate='concern.constraint.private-choice')
        clock.advance(601*SECOND);config=load_config(home)
        update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_context_tokens':32768,'provider_background_cognition':True}),expected_revision=config.revision)
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity
            app.pause(False);app.runtime.refresh_attention()
            from nana_core.continuity.subject import SubjectInput
            opportunity=next(v for v in app.runtime.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=0,quiet_window_us=SECOND)
                if (v.communication_method_record_id is not None if basis=='initial-method' else v.private_thought_ref is not None))
            preview_event=SubjectInput(source_key='synthetic.private-admission-preview',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PERSONAL',
                observed_at_us=clock.utc_now_us(),source_memory_ids=opportunity.memory_ids,task_class=opportunity.task_class,
                communication_method_record_id=opportunity.communication_method_record_id,private_thought_ref=opportunity.private_thought_ref)
            snapshot=app.runtime.store.snapshot();writes=app.runtime.store.db.total_changes;calls=len(requests)
            preview=app.runtime.cognition.preview_private(preview_event,app.runtime.subject)
            assert app.runtime.store.snapshot()==snapshot and app.runtime.store.db.total_changes==writes and len(requests)==calls
            for _ in range(8):app.tick()
            clock.advance(2*SECOND);app.runtime.lease.heartbeat();app.runtime.refresh_attention()
            for _ in range(8):app.tick()
            measure=app.runtime.store.one('cognitive_requests',seen[0]['request_id']) if seen else None
            print(json.dumps({'measurement':'synthetic_private_admission','basis':basis,'blocked':blocked,'self_http_calls':len(seen),'preview_mode':preview[0],'preview_reason':preview[1],
                'input_bytes':measure['input_bytes'] if measure else None,'reserved_bytes':measure['reserved_bytes'] if measure else None,
                'latency_us':measure['latency_us'] if measure else None,'budget':seen[0]['budget'] if seen else None},sort_keys=True))
            assert len(seen)==(0 if blocked else 1)
            assert preview[0]==('LIGHT_COGNITION' if blocked else 'FULL_COGNITION')
            if not blocked:assert preview[1]=='PRIVATE_CONSIDERATION_AVAILABLE'
            assert dict(app.runtime.store.one('commitments',cid))==promise and CommitmentService(app.runtime.store,app.runtime.authority).get(cid).overdue
            if not blocked:
                assert current(app)[0][1].content_summary==private
                assert len(app.runtime.store.all('cognitive_requests'))==len(requests)
            assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants') and not app.runtime.store.all('runtime_cognition_calls')


@pytest.mark.parametrize('choice',['REFLECT','REST','BLOCKED_REFLECT'])
def test_actual_runtime_can_choose_light_own_reflection_with_sourced_load_without_compulsory_rest(tmp_path,choice):
    from nana_core.continuity.subject import SubjectInput
    from nana_core.presence.contracts import RuntimeEvent,Cause
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    revised='PRIVATE_LIGHT_REFLECTION: I choose a brief reflection on my own concern while recognizing current load; rest remains available.'
    def inner(request):
        seen.append(request);context=json.loads(request['context_json']);manifest=context['manifest']
        frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert any(m['source']=='REST' and m['strength']=='RELEVANT' for m in frame['motivations'])
        own=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY'];assert len(own)==1
        proposal={'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],
            'interpretation':'SYNTHETIC compare rest with a bounded personally meaningful reflection',
            'preferred_behavior':'REST' if choice=='REST' else 'REFLECT','proposed_operations':['WAIT'] if choice=='REST' else ['DRAFT']}
        if choice!='REST':proposal['private_tendency']={'topic':'own-concern','tendency':revised,'revises_record_id':own[0]['record_id']}
        return {'interpretation':'SYNTHETIC sourced load is a motive, not compulsory fatigue behavior','subject_cognition':proposal}
    with relay(home,'CHAT',subject_builder=inner,context_limit=65536) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();form(app);old=current(app)[0][1].content_summary;identity=app.runtime.identity_id
            cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='PRIVATE_INTEREST',topic_key='own-concern',possible_behaviors=('REST','REFLECT'),cognitive_load='HIGH')
            mid=capture(app.runtime,'sourced-load',cue.model_dump(mode='json'),predicate='concern.current-private-load')
            if choice=='BLOCKED_REFLECT':
                norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key='own-concern',prohibited_behaviors=('REFLECT',))
                capture(app.runtime,'sourced-load-norm',norm.model_dump(mode='json'),predicate='concern.constraint.private-load')
        config=load_config(home);update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_context_tokens':32768,'provider_background_cognition':True}),expected_revision=config.revision)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause(False);r=app.runtime;assert r.identity_id==identity
            event=SubjectInput(source_key='synthetic.sourced-private-load-choice',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,),novelty='HIGH',uncertainty='RELEVANT')
            r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=event,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=clock.utc_now_us(),priority=3))
            result=r.step();assert len(seen)==len(requests)==1
            row=r.store.one('cognitive_requests',seen[0]['request_id'])
            print(json.dumps({'measurement':'synthetic_sourced_load_choice','choice':choice,'self_http_calls':len(seen),'input_bytes':row['input_bytes'],'reserved_bytes':row['reserved_bytes'],'latency_us':row['latency_us'],'budget':seen[0]['budget'],'chosen_behavior':result['cycle'].intention.behavior},sort_keys=True))
            assert result['cycle'].intention.behavior==('REFLECT' if choice=='REFLECT' else 'REST')
            assert current(app)[0][1].content_summary==(revised if choice=='REFLECT' else old)
            assert len(r.store.all('cognitive_requests'))==1 and not r.store.all('runtime_cognition_calls')
            assert not r.store.all('goals') and not r.store.all('actions') and not r.store.all('grants')


def test_six_pending_work_intentions_do_not_invent_fatigue_for_existing_private_thought(tmp_path):
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity.subject.opportunities import PrivateIntentRef
    from nana_core.presence.contracts import RuntimeEvent,Cause
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    revised='PRIVATE_PENDING_WORK: I can briefly reconsider my own concern without claiming that the pending queue means I feel tired.'
    def inner(request):
        seen.append(request);context=json.loads(request['context_json']);manifest=context['manifest']
        frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert not any(m['source']=='REST' for m in frame['motivations'])
        if 'REFLECT' not in frame['behavior_options']:
            return {'interpretation':'SYNTHETIC no explicit direction is offered; wait without inventing permission',
                'subject_cognition':{'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],
                    'interpretation':'SYNTHETIC keep the existing concern while waiting','proposed_operations':['WAIT']}}
        own=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY'];assert len(own)==1
        return {'interpretation':'SYNTHETIC pending work is a resource fact, not an emotional observation',
            'subject_cognition':{'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],'interpretation':'SYNTHETIC choose brief private reflection without executing any pending work',
                'preferred_behavior':'REFLECT','proposed_operations':['DRAFT'],'private_tendency':{'topic':'own-concern','tendency':revised,'revises_record_id':own[0]['record_id']}}}
    with relay(home,'CHAT',subject_builder=inner,context_limit=65536) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();form(app);r=app.runtime;rid,item=current(app)[0]
            for index in range(6):
                topic='pending-work-'+str(index)
                cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CREATIVE_INTEREST',topic_key=topic,possible_behaviors=('CREATE',),valid_until_us=clock.utc_now_us()+SECOND)
                mid=capture(r,topic,cue.model_dump(mode='json'),predicate='concern.'+topic)
                chosen=r.subject.run(SubjectInput(source_key='synthetic.'+topic,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,)))
                assert chosen.intention.kind=='GOAL_CANDIDATE'
            pending=[dict(v) for v in r.subject.pending('project-work')];assert len(pending)==6
            origin=r.store.one('subject_intentions',item.intent_id)
        clock.advance(2*SECOND);config=load_config(home)
        update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_context_tokens':32768,'provider_background_cognition':True}),expected_revision=config.revision)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause(False);r=app.runtime
            event=SubjectInput(source_key='synthetic.private-with-pending-work',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=item.source_memory_ids,private_thought_ref=PrivateIntentRef(record_id=rid,intent_id=item.intent_id,revision=item.revision))
            r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=event,causes=(Cause(kind='INTENTION',reference_id=item.intent_id,revision=origin['revision']),),due_at_us=clock.utc_now_us(),priority=3))
            result=r.step();assert len(seen)==len(requests)==1
            assert result['cycle'].intention.behavior=='REFLECT' and current(app)[0][1].content_summary==revised
            assert [dict(v) for v in r.subject.pending('project-work')]==pending
            assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('runtime_cognition_calls')
