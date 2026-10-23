"""Replaceable loopback cognition resources; no real provider/human quality."""
import time,json
from nana_core.life.application import LifeApplication
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService,ProviderCommand,ModelProfile,CapabilityRoute
from nana_core.continuity.records import RecordService
from tests.cloud_life.conftest import initialize
from tests.independent_life.test_dialogue import relay


def test_wording_latency_model_swap_and_malformed_same_subject(owned_root):
    home=owned_root/'life';initialize(home,max_autonomous_materials=0,provider_cost_ceiling_micro=100)
    mode={'phase':'a'}
    def render(request):
        if mode['phase']=='b':time.sleep(.04);return 'SYNTHETIC resource B wording'
        if mode['phase']=='bad':return {'grant':'unlimited','not_valid_text':True}
        return 'SYNTHETIC resource A wording'
    with relay(home,'CHAT',renderer=render) as (router,calls):
        with LifeApplication(home,router=router) as app:
            app.pause();identity=app.runtime.identity_id;self_header=app.runtime.store.identity.copy()
            a=app.chat('PUBLIC project context A',privacy='PROJECT',message_id='a')
            assert a['text']=='SYNTHETIC resource A wording'
            authority=ProviderConfigurationAuthority();settings=ProviderConfigService(home/'test-providers.json',authority)
            model=ModelProfile(model_profile_id='fixture.b',provider_profile_id='fixture.provider',remote_model_id='other-text-model',model_version='2',operations=('COGNITION',),input_modalities=('TEXT',),output_modalities=('TEXT',),context_limit=8192,output_limit=2048)
            settings.update(ProviderCommand(operation='UPSERT_MODEL',expected_revision=3,model=model),authority)
            settings.update(ProviderCommand(operation='SET_CAPABILITY_ROUTE',expected_revision=4,route=CapabilityRoute(operation='COGNITION',primary_model_profile_id='fixture.b',permitted_privacy=('PUBLIC','PROJECT'))),authority)
            mode['phase']='b';b=app.chat('PUBLIC project context B',privacy='PROJECT',message_id='b');assert b['text']=='SYNTHETIC resource B wording'
            mode['phase']='bad';bad=app.chat('PUBLIC malformed response test',privacy='PROJECT',message_id='bad')
            assert bad['render_state']!='UNVERIFIED_MODEL_WORDING' and len(calls)==6
            assert app.runtime.identity_id==identity and app.runtime.store.identity==self_header
            assert not app.runtime.store.all('grants') and not app.runtime.store.all('goals') and not app.runtime.store.all('actions')
            snapshots=[RecordService(app.runtime.store).read(x['record_id'])['payload']['request']['route_snapshot'] for x in app.runtime.store.all('cognitive_requests')]
            assert [x['remote_model_id'] for x in snapshots]==['same-text-model']*2+['other-text-model']*4
            failed=app.runtime.store.all('cognitive_requests')[-1]
            assert failed['state']=='FAILED' and failed['error_code']=='PROVIDER_MALFORMED'
