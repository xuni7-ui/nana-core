"""Current permission affects attention eligibility, never existence of a wish."""
import json
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.continuity.autonomy.private_intent import candidates,internal_projection
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_private_tendency import form


def test_sixty_four_processing_closed_thoughts_do_not_displace_a_legal_new_method_opportunity(tmp_path):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[];refs=[]
    def meaning(request):return {'communication_proposal':{'approach':'LISTEN','detail':'BRIEF','follow_up':'NONE','strategy_duration_seconds':3600}}
    def inner(request):
        seen.append(request);context=json.loads(request['context_json']);manifest=context['manifest']
        methods=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='COMMUNICATION_STRATEGY']
        assert len(methods)==1 and methods[0]['choice']['approach']=='LISTEN'
        assert 'PRIVATE_CLOSED_SOURCE_CANARY' not in request['context_json']
        return {'interpretation':'SYNTHETIC a legal current method can still become an internal question',
            'subject_cognition':{'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],
                'interpretation':'SYNTHETIC consider own method, without processing the separately closed topics',
                'preferred_behavior':'REFLECT','proposed_operations':['DRAFT'],
                'private_question':{'topic':'open-method','question':'SYNTHETIC I wonder whether my current listening method has another option.'}}}
    with relay(home,'CHAT',meaning_builder=meaning,subject_builder=inner,context_limit=65536) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();identity=app.runtime.identity_id
            for index in range(64):
                topic='closed-topic-'+str(index)
                form(app,key='closed-'+str(index),topic=topic,text='PRIVATE_CLOSED_SOURCE_CANARY '+str(index)+': an own unresolved thought, not a world fact.')
                rid,item=next((r,v) for r,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')) if v.topic==topic)
                refs.append(rid)
                result=app.chat('不要研究这个话题',topic=topic,privacy='PERSONAL',message_id='close-'+str(index))
                assert result['mode']=='RESPECT_BOUNDARY'
            assert not requests and len(refs)==64
            opening=app.chat('SYNTHETIC a different explicitly retained interaction',topic='open-method',privacy='PERSONAL',retain_shared_life=True,message_id='open-method')
            assert opening['exchange_record_id'] and len(requests)==2
        clock.advance(601*SECOND);config=load_config(home)
        update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_context_tokens':32768,'provider_background_cognition':True}),expected_revision=config.revision)
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity
            app.pause(False);app.runtime.refresh_attention()
            snapshot=app.runtime.store.snapshot();writes=app.runtime.store.db.total_changes
            opportunities=app.runtime.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=0,quiet_window_us=SECOND)
            offered=any(v.communication_method_record_id is not None for v in opportunities)
            assert app.runtime.store.snapshot()==snapshot and app.runtime.store.db.total_changes==writes
            for _ in range(8):app.tick()
            clock.advance(2*SECOND);app.runtime.lease.heartbeat();app.runtime.refresh_attention()
            for _ in range(8):app.tick()
            measure=app.runtime.store.one('cognitive_requests',seen[0]['request_id']) if seen else None
            print(json.dumps({'measurement':'synthetic_mixed_attention_eligibility','closed_thoughts':64,
                'collector_opportunities':len(opportunities),'open_method_offered':offered,'self_http_calls':len(seen),'total_http_calls':len(requests),
                'input_bytes':measure['input_bytes'] if measure else None,'reserved_bytes':measure['reserved_bytes'] if measure else None,
                'latency_us':measure['latency_us'] if measure else None,'configured_input_tokens':load_config(home).provider_context_tokens},sort_keys=True))
            assert offered and len(seen)==1
            assert any(v.category=='PRIVATE_QUESTION' and v.topic=='open-method' for _,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')))
            retained=internal_projection(app.runtime.store,tuple(refs),scope='project-work',privacy_classes=('PROJECT','PERSONAL'),include_associations=False)
            assert len(retained)==64 and all(v['activity_state']=='ACTIVE' for v in retained)
            app.pause();calls=len(requests)
            reopened=app.chat('允许研究这个话题',topic='closed-topic-0',privacy='PERSONAL',message_id='reopen-one')
            assert len(requests)==calls
            available=app.runtime.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=0,quiet_window_us=SECOND)
            assert any(v.private_thought_ref and v.private_thought_ref.record_id==refs[0] for v in available)
            assert not app.runtime.store.all('goals') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_delivery_only_refusal_does_not_remove_internal_continuation(tmp_path):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app);rid,item=candidates(app.runtime.store,'project-work',('PROJECT',))[0]
        result=app.chat('别分析这个话题',topic=item.topic,privacy='PERSONAL',message_id='delivery-only')
        assert result['mode']=='RESPECT_BOUNDARY'
        clock.advance(2*SECOND);app.runtime.lease.heartbeat()
        opportunities=app.runtime.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=0,quiet_window_us=SECOND)
        assert any(v.private_thought_ref and v.private_thought_ref.record_id==rid for v in opportunities)
