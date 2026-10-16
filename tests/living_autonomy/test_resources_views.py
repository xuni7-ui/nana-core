import json
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.application import FrontendPolicy
from nana_core.continuity.providers import ProviderRegistry
from nana_core.continuity.extensions import SurfaceEnvelope
from nana_core.presence.resources import resource_state
from nana_core.presence.contracts import LivingRuntimeConfig,SECOND
from .helpers import fresh,event
from .test_agency import setup,start


def test_resource_subbudget_foreground_fallback_and_actual_estimated_separation(tmp_path):
    living=LivingRuntimeConfig(max_model_bytes_per_day=300000,background_fraction_percent=20)
    with fresh(tmp_path/'self.db',living=living,model='analytical',cognition_cooldown_us=0) as r:
        r.submit(event(r,'bg',background=True,novelty='HIGH',uncertainty='HIGH',significance='HIGH'))
        bg=r.step();assert bg['reason']=='BACKGROUND_SUB_BUDGET_PRESERVES_FOREGROUND'
        r.submit(event(r,'user',text='A fictional uncertain new issue',novelty='HIGH',uncertainty='HIGH',significance='HIGH'))
        assert r.step()['mode']=='FULL_COGNITION'
        state=resource_state(r.store,r.config)
        assert state.actual_input_bytes>0 and state.reserved_estimated_cost_micro>0 and state.actual_cost_micro==0
        r.submit(event(r,'user2',text='Another fictional uncertain issue',novelty='HIGH',uncertainty='HIGH',significance='HIGH'))
        assert r.step()['reason']=='MODEL_BYTE_RESERVATION_EXHAUSTED'
        assert len(r.store.all('runtime_cognition_calls'))==1
        assert state.max_observed_latency_us is not None


def test_frontend_same_runtime_surfaces_journal_and_private_filter(tmp_path):
    with fresh(tmp_path/'subject'/'self.db') as r:
        _,mid=setup(r,tmp_path/'world'/'world.fixture.json');start(r,mid);r.step()
        application=r.application(providers=ProviderRegistry())
        policy=ContextPolicy(policy_id='local',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        client=application.session(FrontendPolicy(context=policy,entity_id='synthetic-person',commands=('SEND_INPUT',)))
        for i,platform in enumerate(('fixture.desktop','fixture.mobile')):
            env=SurfaceEnvelope(subject_id=r.identity_id,platform=platform,surface=platform+'.chat',adapter='fixture.adapter',entity_id='synthetic-person',conversation_id='synthetic-conversation',session_id='synthetic-session',event_kind='message.input',observed_at_us=r.clock.utc_now_us(),correlation_id=str(i),privacy_class='PERSONAL',source_reference='synthetic.surface',source_event_key=str(i))
            receipt=client.send_input(env,event(r,'unused',text='A fictional cross-surface input',significance='RELEVANT').input)
            r.step();assert receipt.wait(.1)
        assert client.view('CONTINUITY',scope='lab').subject_id==r.identity_id
        assert len(client.view('CONTINUITY',scope='lab').surfaces)==2
        data=json.loads(client.view('LIVING_RUNTIME',scope='lab').data_json)
        assert data['goals'] and data['execution_authority']=='NONE_FROM_VIEW'
        journal=json.loads(client.view('LIVING_JOURNAL',scope='lab').data_json)
        assert any(e['phase']=='VERIFIED_EFFECT' for e in journal['entries'])
        public=application.session(FrontendPolicy(context=policy.model_copy(update={'readable_privacy':('PUBLIC',)}),entity_id='synthetic-person',commands=()))
        assert not json.loads(public.view('LIVING_JOURNAL',scope='lab').data_json)['entries']
