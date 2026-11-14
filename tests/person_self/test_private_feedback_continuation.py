"""An attributed explicit opinion can reopen consideration of its own tendency."""
import json
import pytest
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.lived_language import LanguageService,LanguageSample
from nana_core.continuity.autonomy.private_intent import candidates
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_private_tendency import form,current,PRIVATE


def meaning(request):
    own=[json.loads(b['data_json']) for b in json.loads(request['context_json'])['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY']
    changed=any('ordinary-chat' in v['content_summary'] for v in own)
    proposal={'approach':'CHAT' if changed or not own else 'LISTEN','detail':'BRIEF','follow_up':'NONE','basis_private_record_ids':[v['record_id'] for v in own]}
    if own and not changed:proposal['strategy_duration_seconds']=3600
    if changed:proposal['end_previous_strategy']=True
    return {'communication_proposal':proposal}


def wording(request):
    choice=request['role_input']['dialogue']['communication_purpose'].get('choice')
    return 'SYNTHETIC listening method' if choice and choice['approach']=='LISTEN' else 'SYNTHETIC ordinary-chat method'


@pytest.mark.parametrize('choice',['revise','rest','source-race'])
def test_attributed_review_reaches_original_d_and_changes_tendency_then_later_choice(tmp_path,choice):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();feedback=[];self_requests=[]
    def inner(request):
        self_requests.append(request);context=json.loads(request['context_json']);manifest=context['manifest']
        frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        own=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY']
        grounded=bool(own and feedback and feedback[0] in frame['source_memory_ids'])
        if grounded and choice=='rest':
            return {'interpretation':'SYNTHETIC actual opinion considered; rest rather than compulsory learning','subject_cognition':{'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],'interpretation':'SYNTHETIC choose rest without declaring that the method worked','preferred_behavior':'REST','proposed_operations':['WAIT']}}
        return {'interpretation':'SYNTHETIC reconsider a bounded explicit opinion, not emotional effectiveness','subject_cognition':{'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],'interpretation':'SYNTHETIC own care can use a different method without claiming a changed mood','proposed_operations':['DRAFT'] if grounded else ['WAIT'],**({'private_tendency':{'topic':'own-concern','tendency':'SYNTHETIC I still care, but prefer ordinary-chat after this explicit opinion; the actual emotional effect is unknown.','revises_record_id':own[0]['record_id']}} if grounded else {})}}
    with relay(home,'CHAT',meaning_builder=meaning,renderer=wording,subject_builder=inner,context_limit=65536) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();form(app);identity=app.runtime.identity_id;first_id,first=current(app)[0]
            before=app.chat('SYNTHETIC initial related situation',topic='own-concern',privacy='PROJECT',retain_shared_life=True,message_id='before')
            assert before['text']=='SYNTHETIC listening method'
            service=LanguageService(app.runtime.store,app.runtime.authority)
            sample=LanguageSample(sample_id='explicit-own-method-opinion',review_target=before['exchange_record_id'],mode='CASUAL',context='SYNTHETIC exact retained local conversation',candidate_response=before['text'],human_judgment='REJECTED',exact_feedback='SYNTHETIC ordinary chat would suit this conversation better.',reason_tags=('TOO_FORMAL',),provenance='PROJECT_SYNTHETIC',observed_at_us=clock.utc_now_us())
            review=service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority,exchange_record_id=before['exchange_record_id'])
            eid=service.experience(review,app.runtime.authority);feedback.append(app.runtime.store.one('experiences',eid)['result_memory_id'])
            assert len(requests)==2 and not app.runtime.store.all('lessons')
        # Keep the original shared cooldown and method window, not a test-only
        # lowered threshold. A stopped writer is not a surviving 601s lease.
        clock.advance(601*SECOND)
        config=load_config(home);update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_background_cognition':True,'provider_context_tokens':32768}),expected_revision=config.revision)
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity
            app.pause(False);app.runtime.refresh_attention()
            if choice=='source-race':
                factory=app.runtime.cognition.provider_factory
                def withdraw_before_dispatch(event):
                    if event.task_class=='private.feedback.review':app.forget(feedback[0])
                    return factory(event)
                app.runtime.cognition.provider_factory=withdraw_before_dispatch
            for _ in range(8):app.tick()
            if choice=='source-race':
                assert not self_requests and current(app)[0][0]==first_id
                assert len(app.runtime.store.all('cognitive_requests'))==2
                assert app.runtime.store.db.execute("SELECT 1 FROM runtime_queue WHERE state='IGNORED' AND outcome_code='SOURCE_RETIRED_OR_INVALID'").fetchone()
                return
            # A light experience review may consume the first quiet window.
            # Let the original queue reach its real next due time as well.
            clock.advance(2*SECOND);app.runtime.lease.heartbeat();app.runtime.refresh_attention()
            for _ in range(8):app.tick()
            assert len(self_requests)==1
            new_id,tendency=current(app)[0]
            measure=app.runtime.store.one('cognitive_requests',self_requests[0]['request_id'])
            print(json.dumps({'measurement':'synthetic_private_feedback','variant':choice,
                'self_http_calls':len(self_requests),'http_calls_so_far':len(requests),
                'budget':self_requests[0]['budget'],'input_bytes':measure['input_bytes'],
                'reserved_bytes':measure['reserved_bytes'],'output_bytes':measure['output_bytes'],
                'latency_us':measure['latency_us'],'fixture_cost_micro':measure['actual_cost_micro'],
                'feedback_in_frame':feedback[0] in next(json.loads(b['data_json']) for b in json.loads(self_requests[0]['context_json'])['blocks'] if b['kind']=='SUBJECT_APPRAISAL')['source_memory_ids'],
                'tendency_revised':new_id!=first_id,'sqlite_allocated_bytes':sum(Path(str(app.runtime.store.path)+suffix).stat().st_size for suffix in ('','-wal','-shm') if Path(str(app.runtime.store.path)+suffix).exists()),
                'record_count':len(app.runtime.store.all('continuity_records'))},sort_keys=True))
            if choice=='revise':assert new_id!=first_id and 'ordinary-chat' in tendency.content_summary
            else:assert new_id==first_id and tendency.content_summary==PRIVATE
            assert tendency.intent_id==first.intent_id
            if choice=='rest':
                alias=sample.model_copy(update={'sample_id':'same-opinion-alias','observed_at_us':clock.utc_now_us()})
                language=LanguageService(app.runtime.store,app.runtime.authority)
                alias_id=language.record(alias,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority,exchange_record_id=before['exchange_record_id'])
                alias_experience=language.experience(alias_id,app.runtime.authority)
                snapshot=app.runtime.store.snapshot();writes=app.runtime.store.db.total_changes
                again=app.runtime.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=clock.utc_now_us(),quiet_window_us=SECOND)
                assert not any(v.private_thought_ref and v.reflection_experience_id in {eid,alias_experience} for v in again)
                assert app.runtime.store.snapshot()==snapshot and app.runtime.store.db.total_changes==writes
            app.pause()
            after=app.chat('SYNTHETIC a different later conversation',topic='own-concern',privacy='PROJECT',message_id='after')
            assert after['text']==('SYNTHETIC ordinary-chat method' if choice=='revise' else 'SYNTHETIC listening method')
            assert not app.runtime.store.all('goals') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
            assert all(v['state']!='ACTIVE' for v in app.runtime.store.all('lessons'))
            app.forget(feedback[0])
            assert (not current(app)) if choice=='revise' else current(app)[0][1].content_summary==PRIVATE


@pytest.mark.parametrize('condition',['unbound','withdrawn','paused','unreviewed'])
def test_only_a_current_attributed_opinion_can_reopen_its_tendency_read_only(tmp_path,condition):
    from .test_private_tendency import change
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with relay(home,'CHAT',meaning_builder=meaning,renderer=wording,context_limit=65536) as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
        app.pause();form(app)
        turn=app.chat('SYNTHETIC actual retained conversation',topic='own-concern',privacy='PROJECT',retain_shared_life=True,message_id='source')
        service=LanguageService(app.runtime.store,app.runtime.authority)
        sample=LanguageSample(sample_id='negative-'+condition,review_target=turn['exchange_record_id'] if condition!='unbound' else 'synthetic-unbound-report',mode='CASUAL',context='SYNTHETIC',candidate_response=turn['text'],human_judgment='UNREVIEWED' if condition=='unreviewed' else 'REJECTED',exact_feedback='SYNTHETIC explicit method opinion.',reason_tags=('TOO_FORMAL',),provenance='PROJECT_SYNTHETIC',observed_at_us=clock.utc_now_us())
        review=service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority,exchange_record_id=None if condition=='unbound' else turn['exchange_record_id'])
        eid=service.experience(review,app.runtime.authority)
        if condition=='withdrawn':app.forget(app.runtime.store.one('experiences',eid)['result_memory_id'])
        if condition=='paused':change(app,'REST','pause-before-review')
        snapshot=app.runtime.store.snapshot();writes=app.runtime.store.db.total_changes
        opportunities=app.runtime.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=clock.utc_now_us(),quiet_window_us=SECOND)
        assert not any(o.private_thought_ref and o.reflection_experience_id==eid for o in opportunities)
        assert app.runtime.store.snapshot()==snapshot and app.runtime.store.db.total_changes==writes
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
