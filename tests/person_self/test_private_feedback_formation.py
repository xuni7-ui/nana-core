"""A bound actual method opinion need not wait for a pre-seeded inner state."""
import json
import pytest
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.lived_language import LanguageService,LanguageSample
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_private_tendency import current
from .test_private_feedback_continuation import wording


@pytest.mark.parametrize('condition',['form','rest','hesitate','no-method','withdrawn','disabled','budget','declined','source-race'])
def test_bound_method_opinion_can_form_first_own_tendency_in_normal_d_without_another_loop(tmp_path,condition):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[];independent=[]
    private='PRIVATE_FIRST_CARE: I want to keep a tentative concern, while preferring ordinary conversation; I do not know whether their mood improved.'
    def meaning(request):
        states=[json.loads(b['data_json']) for b in json.loads(request['context_json'])['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY']
        proposal={'approach':'CHAT' if states else 'LISTEN','detail':'BRIEF','follow_up':'NONE','basis_private_record_ids':[v['record_id'] for v in states]}
        if states:proposal['end_previous_strategy']=True
        elif condition!='no-method':proposal['strategy_duration_seconds']=3600
        return {'communication_proposal':proposal}
    def inner(request):
        context=json.loads(request['context_json']);manifest=context['manifest']
        opinions=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='COMMUNICATION_FEEDBACK']
        if not opinions:
            # The withdrawn opinion cannot drive C, while the independently
            # retained original method may still offer its own consideration.
            assert condition in {'withdrawn','source-race'}
            assert any(b['kind']=='COMMUNICATION_STRATEGY' for b in context['blocks'])
            frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
            assert feedback not in frame['source_memory_ids'] and sample.exact_feedback not in request['context_json']
            independent.append(request)
            return {'interpretation':'SYNTHETIC independent method remains available; withdrawn opinion is not used',
                'subject_cognition':{'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],
                    'interpretation':'SYNTHETIC rest without inventing an opinion','preferred_behavior':'REST','proposed_operations':['WAIT']}}
        seen.append(request)
        assert any('ordinary conversation' in v.get('exact_feedback_excerpt','') and v['effect_status']=='NOT_EVALUATED_NO_EFFECT_INFERRED' for v in opinions)
        assert not any(b['kind']=='PRIVATE_INTERNAL_STATE' for b in context['blocks'])
        proposal={'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],'interpretation':'SYNTHETIC consider a new own orientation, not a verified mood or compulsory task',
            'preferred_behavior':'REST' if condition=='rest' else 'REFLECT','proposed_operations':['WAIT'] if condition=='rest' else ['ASK'] if condition=='hesitate' else ['DRAFT']}
        if condition in {'form','budget'}:proposal['private_tendency']={'topic':'fresh-care','tendency':private}
        return {'interpretation':'SYNTHETIC actual feedback can matter without an already formed private tendency','subject_cognition':proposal}
    with relay(home,'VENT',meaning_builder=meaning,renderer=wording,subject_builder=inner,context_limit=65536) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();assert not current(app);identity=app.runtime.identity_id
            turn=app.chat('SYNTHETIC user statement about a difficult day',topic='fresh-care',privacy='PROJECT',retain_shared_life=True,message_id='initial')
            assert turn['text']=='SYNTHETIC listening method' and len(requests)==2
            language=LanguageService(app.runtime.store,app.runtime.authority)
            sample=LanguageSample(sample_id='first-method-opinion',review_target=turn['exchange_record_id'],mode='CASUAL',context='SYNTHETIC retained actual local turn',candidate_response=turn['text'],human_judgment='REJECTED',exact_feedback='SYNTHETIC ordinary conversation suits me better; please do not keep asking.',reason_tags=('TOO_FORMAL',),provenance='PROJECT_SYNTHETIC',observed_at_us=clock.utc_now_us())
            rid=language.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
            eid=language.experience(rid,app.runtime.authority);feedback=app.runtime.store.one('experiences',eid)['result_memory_id']
            if condition=='withdrawn':app.forget(feedback)
            if condition=='declined':
                boundary=app.chat('不要研究这个话题',topic='fresh-care',privacy='PROJECT',message_id='decline')
                assert boundary['mode']=='RESPECT_BOUNDARY'
        clock.advance(601*SECOND);config=load_config(home)
        changes={'revision':config.revision+1,'provider_background_cognition':condition!='disabled','provider_context_tokens':32768}
        if condition=='budget':changes['provider_calls_per_day']=2
        update_config(home,config.model_copy(update=changes),expected_revision=config.revision)
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity
            app.pause(False);app.runtime.refresh_attention()
            if condition=='source-race':
                factory=app.runtime.cognition.provider_factory
                def withdraw_before_dispatch(event):
                    if event.task_class=='private.feedback.review':app.forget(feedback)
                    return factory(event)
                app.runtime.cognition.provider_factory=withdraw_before_dispatch
            for _ in range(8):app.tick()
            clock.advance(2*SECOND);app.runtime.lease.heartbeat();app.runtime.refresh_attention()
            for _ in range(8):app.tick()
            formed=current(app)
            observed=seen+independent
            measure=app.runtime.store.one('cognitive_requests',observed[0]['request_id']) if observed else None
            print(json.dumps({'measurement':'synthetic_first_tendency','condition':condition,'self_http_calls':len(observed),'bound_feedback_self_http_calls':len(seen),'independent_method_self_http_calls':len(independent),
                'http_calls_so_far':len(requests),'input_bytes':measure['input_bytes'] if measure else None,
                'reserved_bytes':measure['reserved_bytes'] if measure else None,'latency_us':measure['latency_us'] if measure else None,
                'fixture_cost_micro':measure['actual_cost_micro'] if measure else None,'budget':observed[0]['budget'] if observed else None,
                'formed':bool(formed),'continuity_records':len(app.runtime.store.all('continuity_records'))},sort_keys=True))
            assert len(seen)==(1 if condition in {'form','rest','hesitate'} else 0)
            assert bool(formed)==(condition=='form')
            if condition=='hesitate':assert not app.runtime.store.db.execute("SELECT 1 FROM subject_intentions WHERE state='PENDING' AND kind='WAIT'").fetchone()
            if condition=='form':
                _,item=formed[0];assert item.content_summary==private and item.epistemic_status=='OWN_TENDENCY_NOT_WORLD_FACT'
                assert feedback in item.source_memory_ids
                assert not app.runtime.store.all('world_beliefs')
                assert private not in seen[0]['context_json']
            calls=len(requests);clock.advance(3*SECOND);app.runtime.lease.heartbeat();app.runtime.refresh_attention()
            for _ in range(8):app.tick()
            assert len(requests)==calls
            assert not app.runtime.store.all('goals') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
            assert all(v['state']!='ACTIVE' for v in app.runtime.store.all('lessons'))
            app.pause()
            if condition in {'form','rest','hesitate'}:
                if condition=='form':
                    restricted=app.chat('SYNTHETIC a lower privacy context',topic='fresh-care',privacy='PROJECT',message_id='restricted')
                    assert restricted['text']=='SYNTHETIC listening method' and private not in requests[-2]['context_json']
                later=app.chat('SYNTHETIC a different later situation',topic='fresh-care',privacy='PERSONAL',message_id='later')
                assert later['text']==('SYNTHETIC ordinary-chat method' if condition=='form' else 'SYNTHETIC listening method')
                assert private not in requests[-1]['context_json'] and private not in later['text']
                app.forget(feedback);assert not current(app)
        if condition=='budget':
            # Insufficient resources do not consume the original opportunity.
            config=load_config(home)
            update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_calls_per_day':12}),expected_revision=config.revision)
            with LifeApplication(home,clock=clock,router=router) as app:
                assert app.runtime.identity_id==identity
                app.pause(False);app.runtime.refresh_attention()
                for _ in range(8):app.tick()
                assert len(seen)==1 and current(app)[0][1].content_summary==private
                app.forget(feedback);assert not current(app)
