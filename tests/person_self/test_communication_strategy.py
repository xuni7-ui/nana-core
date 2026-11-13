"""Bounded own methods persist through original Records, without becoming tasks."""
import json
import pytest
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_inner_communication import seed


def methods(request):
    return [json.loads(b['data_json']) for b in json.loads(request['context_json'])['blocks'] if b['kind']=='COMMUNICATION_STRATEGY']


def meaning(request):
    text=request['role_input']['dialogue']['text'];prior=methods(request)
    properties=request['expected_schema']['$defs']['CommunicationProposal']['properties']
    if 'begin-listening' in text:
        result={'kind':'VENT','communication_proposal':{'approach':'LISTEN','detail':'BRIEF','follow_up':'NONE'}}
        if 'strategy_duration_seconds' in properties:result['communication_proposal']['strategy_duration_seconds']=600
        return result
    if prior:
        proposal={**prior[0]['choice'],'strategy_duration_seconds':600}
        if 'new-direction' in text:proposal={'approach':'CHAT','detail':'BRIEF','follow_up':'NONE','end_previous_strategy':True}
        if 'no-longer-this-method' in text:
            return {'kind':'DECLINE_DEPTH','communication_proposal':{'approach':'CHAT','detail':'BRIEF','end_previous_strategy':True}}
        return {'communication_proposal':proposal}
    return {}


def render(request):
    choice=request['role_input']['dialogue']['communication_purpose'].get('choice')
    return 'SYNTHETIC: keep listening without turning this into a project.' if choice and choice['approach']=='LISTEN' else 'SYNTHETIC: hello.'


def strategy_rows(app):
    return app.runtime.store.db.execute("SELECT * FROM continuity_records WHERE record_kind='INTENTION' AND target_id LIKE 'communication-strategy.%' ORDER BY rowid").fetchall()


def test_bounded_own_method_survives_restart_without_private_history_injection_or_repeated_strategy_writes(tmp_path,monkeypatch):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();root,rid=seed(app);identity=app.runtime.identity_id
            first=app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT',message_id='first')
            assert first['render_state']=='UNVERIFIED_MODEL_WORDING' and 'keep listening' in first['text']
        clock.advance(30*SECOND)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();monkeypatch.setattr(app.runtime.subject,'dialogue_private_refs',lambda **kwargs:(),raising=False)
            later=app.chat('SYNTHETIC related followup',topic='own-curiosity',privacy='PROJECT',message_id='later')
            assert 'keep listening' in later['text'] and app.runtime.identity_id==identity
            assert len(strategy_rows(app))==1
            prior=methods(requests[-2]);assert len(prior)==1 and prior[0]['effect_status']=='NOT_EVALUATED_NO_EFFECT_INFERRED'
            assert prior[0]['expires_at_us']-prior[0]['created_at_us']==600*SECOND
            assert not any(b['kind']=='PRIVATE_INTERNAL_STATE' for b in json.loads(requests[-2]['context_json'])['blocks'])
            assert not methods(requests[-1]) and len(requests)==4
            assert not app.runtime.subject.pending('project-work') and not app.runtime.store.all('goals')
            assert not app.runtime.store.all('experiences') and not app.runtime.store.all('lessons')
            assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC begin-listening')>0").fetchone()


def test_new_explicit_direction_stops_old_method_but_not_private_interest(tmp_path):
    from nana_core.continuity.autonomy.private_intent import candidates
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();root,rid=seed(app)
        app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT',message_id='begin')
        result=app.chat('SYNTHETIC new-direction',topic='own-curiosity',privacy='PROJECT',message_id='change')
        assert result['text']=='SYNTHETIC: hello.'
        after=app.chat('SYNTHETIC another context',topic='own-curiosity',privacy='PROJECT',message_id='after')
        assert after['text']=='SYNTHETIC: hello.' and not methods(requests[-2])
        assert any(key==rid and value.activity_state=='ACTIVE' for key,value in candidates(app.runtime.store,'project-work',('PROJECT',)))
        assert len(strategy_rows(app))==2


def test_method_expiry_does_not_wake_model_or_delete_interest(tmp_path):
    from nana_core.continuity.subject.context_fit import communication_strategy_projection
    from nana_core.continuity.autonomy.private_intent import candidates
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();root,rid=seed(app)
            app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT')
            assert len(strategy_rows(app))==1
            count=len(app.runtime.store.all('cognitive_requests'));identity=app.runtime.identity_id
        # A stopped old writer does not pretend its lease survived the delay.
        clock.advance(601*SECOND)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause()
            for _ in range(4):app.runtime.step()
            assert len(app.runtime.store.all('cognitive_requests'))==count and len(requests)==2
            assert communication_strategy_projection(app.runtime.store,scope='project-work',entity_id='project-user',topic='own-curiosity',recipient_context=None,privacy_classes=('PROJECT',)) is None
            assert len(strategy_rows(app))==1 and app.runtime.identity_id==identity
            assert any(key==rid and value.activity_state=='ACTIVE' for key,value in candidates(app.runtime.store,'project-work',('PROJECT',)))


@pytest.mark.parametrize('mismatch',['topic','contact','recipient','privacy'])
def test_method_projection_is_bound_to_contact_topic_recipient_and_privacy(tmp_path,mismatch):
    from nana_core.continuity.subject.context_fit import communication_strategy_projection
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();seed(app);app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT')
        arguments=dict(scope='project-work',entity_id='project-user',topic='own-curiosity',recipient_context=None,privacy_classes=('PROJECT',))
        assert communication_strategy_projection(app.runtime.store,**arguments)
        arguments.update({'topic':'other'} if mismatch=='topic' else {'entity_id':'other-contact'} if mismatch=='contact' else {'recipient_context':{'platform':'synthetic','binding_id':'other','conversation_id':'other'}} if mismatch=='recipient' else {'privacy_classes':('PUBLIC',)})
        assert communication_strategy_projection(app.runtime.store,**arguments) is None


def test_source_withdrawal_removes_ongoing_method_and_prevents_old_method_fallback(tmp_path):
    from nana_core.continuity.subject.context_fit import communication_strategy_projection
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();root,rid=seed(app)
        first=app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT',message_id='begin')
        assert 'keep listening' in first['text'] and len(strategy_rows(app))==1
        app.forget(root)
        assert communication_strategy_projection(app.runtime.store,scope='project-work',entity_id='project-user',topic='own-curiosity',recipient_context=None,privacy_classes=('PROJECT',)) is None
        after=app.chat('SYNTHETIC fresh context',topic='own-curiosity',privacy='PROJECT',message_id='after')
        assert after['text']=='SYNTHETIC: hello.' and not methods(requests[-2])


def test_explicit_receiver_boundary_stops_method_without_withdrawing_own_question(tmp_path):
    from nana_core.continuity.subject.context_fit import communication_strategy_projection
    from nana_core.continuity.autonomy.private_intent import candidates
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();root,rid=seed(app)
        app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT',message_id='begin')
        before=len(requests)
        stopped=app.chat('先别分析这个话题',topic='own-curiosity',privacy='PROJECT',message_id='boundary')
        assert stopped['mode']=='RESPECT_BOUNDARY' and len(requests)==before
        assert communication_strategy_projection(app.runtime.store,scope='project-work',entity_id='project-user',topic='own-curiosity',recipient_context=None,privacy_classes=('PROJECT',)) is None
        assert any(key==rid and value.activity_state=='ACTIVE' for key,value in candidates(app.runtime.store,'project-work',('PROJECT',)))


def test_current_model_refusal_can_end_own_method_without_installing_permanent_user_boundary(tmp_path):
    from nana_core.continuity.subject.context_fit import communication_strategy_projection,depth_boundary
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();seed(app);app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT',message_id='begin')
        result=app.chat('SYNTHETIC no-longer-this-method',topic='own-curiosity',privacy='PROJECT',message_id='refusal')
        assert result['mode']=='RESPECT_BOUNDARY'
        assert communication_strategy_projection(app.runtime.store,scope='project-work',entity_id='project-user',topic='own-curiosity',recipient_context=None,privacy_classes=('PROJECT',)) is None
        assert not depth_boundary(app.runtime.store,'project-user','project-work','own-curiosity',('PROJECT',))[0]


def test_abandoned_private_basis_invalidates_method_without_forgetting_the_source(tmp_path):
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity.subject.opportunities import ConcernCue,PrivateIntentRef
    from nana_core.continuity.autonomy.private_intent import candidates
    from nana_core.continuity.project_work.service import capture
    from nana_core.continuity.subject.context_fit import communication_strategy_projection
    home=tmp_path/'home';initialize(home)
    def grounded(request):
        proposal=meaning(request)
        if 'begin-listening' in request['role_input']['dialogue']['text']:
            proposal['communication_proposal']['basis_private_record_ids']=[rid]
        return proposal
    with relay(home,'CHAT',meaning_builder=grounded,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();root,rid=seed(app);r=app.runtime
        app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT')
        assert len(strategy_rows(app))==1
        item=next(value for key,value in candidates(r.store,'project-work',('PROJECT',)) if key==rid)
        cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key=item.topic,motivation_source='CURIOSITY',possible_behaviors=('WITHDRAW',),
            private_intent_ref=PrivateIntentRef(record_id=rid,intent_id=item.intent_id,revision=item.revision))
        mid=capture(r,'abandon-strategy-basis',cue.model_dump(mode='json'),predicate='concern.abandon-strategy-basis')
        r.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.abandon-strategy-basis',kind='WAKE',origin='SELF_WAKE',
            entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,)))
        assert r.store.one('memories',root)
        assert communication_strategy_projection(r.store,scope='project-work',entity_id='project-user',topic=item.topic,recipient_context=None,privacy_classes=('PROJECT',)) is None


def test_public_boundary_does_not_downgrade_the_prior_private_method_revision(tmp_path):
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();seed(app)
        app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT',message_id='begin')
        assert strategy_rows(app)[-1]['privacy_class']=='PROJECT'
        app.chat('先别分析这个话题',topic='own-curiosity',privacy='PUBLIC',message_id='stop-public')
        assert len(strategy_rows(app))==2 and strategy_rows(app)[-1]['privacy_class']=='PROJECT'


def test_original_s8_expression_result_changes_later_method_and_unseen_topic_then_counterexample_reopens_choice(tmp_path):
    from .test_learning import record,activate
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    def informed(request):
        blocks=json.loads(request['context_json'])['blocks']
        active=any(b['kind']=='LIVED_LANGUAGE' and json.loads(b['data_json'])['policy']['state']=='ACTIVE_BOUNDED_HYPOTHESIS' for b in blocks)
        return {'communication_proposal':{'approach':'CHAT' if active else 'EXPLORE','detail':'BRIEF' if active else 'DEEP',
            'follow_up':'NONE','strategy_duration_seconds':600}}
    def wording(request):
        choice=request['role_input']['dialogue']['communication_purpose'].get('choice')
        return 'SYNTHETIC concise response' if choice and choice['detail']=='BRIEF' else 'SYNTHETIC expanded comparison'
    with relay(home,'CHAT',meaning_builder=informed,renderer=wording,context_limit=32768) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();root,rid=seed(app);identity=app.runtime.identity_id
            before=app.chat('SYNTHETIC first comparison',topic='own-curiosity',privacy='PROJECT',message_id='before-learning')
            assert before['text']=='SYNTHETIC expanded comparison'
            record(app,1);_,eid=record(app,2);activate(app,eid)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();assert app.runtime.identity_id==identity
            changed=app.chat('SYNTHETIC a different later situation',topic='own-curiosity',privacy='PROJECT',message_id='after-learning')
            assert changed['text']=='SYNTHETIC concise response'
            assert methods(requests[-2])[0]['choice']['detail']=='DEEP'  # Prior private method is available, not binding.
            assert requests[-1]['role_input']['dialogue']['communication_purpose']['choice']['detail']=='BRIEF'
            transferred=app.chat('SYNTHETIC unseen conversation topic',topic='unseen-transfer',privacy='PROJECT',message_id='transfer')
            assert transferred['text']=='SYNTHETIC concise response' and not methods(requests[-2])
            record(app,3,tags=('TOO_TERSE',))
            counter=app.chat('SYNTHETIC another independent context',topic='after-counterexample',privacy='PROJECT',message_id='counterexample')
            assert counter['text']=='SYNTHETIC expanded comparison'
            assert len(requests)==8 and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def reviews(request):
    return [json.loads(b['data_json']) for b in json.loads(request['context_json'])['blocks'] if b['kind']=='COMMUNICATION_FEEDBACK']


def test_bound_method_review_changes_next_choice_without_claiming_effect_then_withdraws(tmp_path):
    from nana_core.continuity.lived_language import LanguageSample,LanguageService
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    def informed(request):
        if reviews(request):
            return {'communication_proposal':{'approach':'CHAT','detail':'BRIEF','follow_up':'NONE','end_previous_strategy':True}}
        return meaning(request)
    with relay(home,'CHAT',meaning_builder=informed,renderer=render,context_limit=32768) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();seed(app);identity=app.runtime.identity_id
            turn=app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT',retain_shared_life=True,message_id='reviewed-turn')
            service=LanguageService(app.runtime.store,app.runtime.authority)
            sample=LanguageSample(sample_id='method-review',review_target=turn['exchange_record_id'],mode='CASUAL',
                context='SYNTHETIC explicit method opinion',candidate_response=turn['text'],human_judgment='REJECTED',
                exact_feedback='SYNTHETIC_PRIVATE_REVIEW_DO_NOT_REPLAY',reason_tags=('TOO_FORMAL',),
                provenance='USER_PROVIDED_REVIEW',observed_at_us=clock.utc_now_us())
            rid=service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority,
                exchange_record_id=turn['exchange_record_id'])
            assert service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority,
                exchange_record_id=turn['exchange_record_id'])==rid
            from nana_core.continuity.lived_language import communication_feedback
            for changes in ({'scope':'other-scope'},{'entity_id':'another-contact'},{'topic':'another-topic'},
                    {'recipient_context':{'platform':'qq.onebot','binding_id':'qq.primary','conversation_id':'qq.private.43'}},
                    {'privacy':('PUBLIC',)}):
                assert communication_feedback(app.runtime.store,**(dict(scope='project-work',entity_id='project-user',topic='own-curiosity',recipient_context=None,privacy=('PROJECT',))|changes)) is None
            eid=service.experience(rid,app.runtime.authority)
            assert eid and not app.runtime.store.all('lessons')  # An opinion is not an adopted method.
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();assert app.runtime.identity_id==identity
            later=app.chat('SYNTHETIC related later message',topic='own-curiosity',privacy='PROJECT',message_id='review-later')
            assert later['text']=='SYNTHETIC: hello.'
            projected=reviews(requests[-2]);assert len(projected)==1
            assert projected[0]['reviewed_choice']['approach']=='LISTEN'
            assert projected[0]['human_judgment']=='REJECTED' and projected[0]['effect_status']=='NOT_EVALUATED_NO_EFFECT_INFERRED'
            assert projected[0]['delivery_state']=='NOT_PROVEN' and projected[0]['human_read_proven'] is False
            assert 'SYNTHETIC_PRIVATE_REVIEW_DO_NOT_REPLAY' not in json.dumps(projected)
            assert not reviews(requests[-1])  # Public RENDER receives only C's current choice.
            assert communication_feedback(app.runtime.store,scope='project-work',entity_id='project-user',topic='own-curiosity',recipient_context=None,privacy=('PROJECT',)) is None
            app.chat('SYNTHETIC different topic',topic='unrelated-review-topic',privacy='PROJECT',message_id='review-other')
            assert not reviews(requests[-2])
            service=LanguageService(app.runtime.store,app.runtime.authority)
            report=next(mid for mid in service.records.support(rid) if service.records.memory.read(mid)['source_provenance']['source_reference']=='method-review')
            app.forget(report)
            app.chat('SYNTHETIC related after withdrawal',topic='own-curiosity',privacy='PROJECT',message_id='review-withdrawn')
            assert not reviews(requests[-2]) and not service.records.current_support(rid)
            assert len(requests)==8 and not app.runtime.store.all('actions')


def test_unreviewed_does_not_update_method_and_withdrawn_latest_opinion_does_not_resurrect_older_one(tmp_path):
    from nana_core.continuity.lived_language import LanguageSample,LanguageService,communication_feedback
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();seed(app)
        turn=app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT',retain_shared_life=True)
        service=LanguageService(app.runtime.store,app.runtime.authority)
        args=dict(scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
        projection=dict(scope='project-work',entity_id='project-user',topic='own-curiosity',recipient_context=None,privacy=('PROJECT',))
        sample=LanguageSample(sample_id='unreviewed-method',review_target=turn['exchange_record_id'],mode='CASUAL',context='SYNTHETIC',
            candidate_response=turn['text'],human_judgment='UNREVIEWED',provenance='USER_PROVIDED_REVIEW',observed_at_us=app.clock.utc_now_us())
        unreviewed=service.record(sample,**args)
        assert 'communication_attribution' not in service.records.read(unreviewed)['payload']
        assert communication_feedback(app.runtime.store,**projection) is None
        older=service.record(sample.model_copy(update={'sample_id':'older-method','human_judgment':'PARTIAL'}),**args)
        latest=service.record(sample.model_copy(update={'sample_id':'latest-method','human_judgment':'REJECTED'}),**args)
        assert communication_feedback(app.runtime.store,**projection)['review_record_id']==latest
        source=next(mid for mid in service.records.support(latest) if service.records.memory.read(mid)['source_provenance']['source_reference']=='latest-method')
        app.forget(source)
        assert service.records.current_support(older) and communication_feedback(app.runtime.store,**projection) is None
        assert len(requests)==2


def test_method_opinion_expires_with_own_review_window_without_erasing_review_or_calling_model(tmp_path):
    from nana_core.continuity.lived_language import LanguageSample,LanguageService,communication_feedback
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    args=dict(scope='project-work',entity_id='project-user',topic='own-curiosity',recipient_context=None,privacy=('PROJECT',))
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=32768) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();seed(app)
            turn=app.chat('SYNTHETIC begin-listening',topic='own-curiosity',privacy='PROJECT',retain_shared_life=True)
            service=LanguageService(app.runtime.store,app.runtime.authority)
            sample=LanguageSample(sample_id='expiring-method-opinion',review_target=turn['exchange_record_id'],mode='CASUAL',context='SYNTHETIC',
                candidate_response=turn['text'],human_judgment='PARTIAL',provenance='USER_PROVIDED_REVIEW',observed_at_us=clock.utc_now_us())
            rid=service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
            assert communication_feedback(app.runtime.store,**args)
        clock.advance(601*SECOND)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();service=LanguageService(app.runtime.store,app.runtime.authority)
            assert communication_feedback(app.runtime.store,**args) is None
            assert service.records.current_support(rid) and len(requests)==2
