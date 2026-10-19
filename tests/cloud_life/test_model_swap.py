"""Synthetic loopback provider swap: no real provider or credential used."""
import json
from nana_core.life.application import LifeApplication
from nana_core.continuity.records import RecordService
from nana_core.life.surfaces import SurfaceBinding,SurfaceObservation
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService,ProviderCommand,ModelProfile,CapabilityRoute
from tests.independent_life.test_dialogue import relay
from .conftest import initialize


def test_model_swap_keeps_subject_sources_and_original_context_path(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,provider_cost_ceiling_micro=100,
  surface_bindings=(SurfaceBinding(binding_id='cloud.shadow',platform='cloud.cli',surface='chat.direct',adapter='shadow.local'),))
 with relay(home,'CHAT') as (router,calls):
  with LifeApplication(home,router=router) as app:
   app.pause();identity=app.runtime.identity_id
   first=app.surfaces.receive(SurfaceObservation(binding_id='cloud.shadow',event_id='one',topic='project',text='public project question',approved_summary='Synthetic project has a verified open question.',summary_authorization='EXPLICIT_PROJECT_SUMMARY'))
   assert first['render_state']=='UNVERIFIED_MODEL_WORDING'
   summary=first['summary_memory_ids'][0]
   before=app.runtime.store.identity.copy();memories={m['memory_id'] for m in app.runtime.store.all('memories')}
   # Trusted host construction, not a model or frontend identity authority.
   auth=ProviderConfigurationAuthority();settings=ProviderConfigService(home/'test-providers.json',auth)
   new=ModelProfile(model_profile_id='fixture.replacement',provider_profile_id='fixture.provider',remote_model_id='other-text-model',model_version='2',operations=('COGNITION',),input_modalities=('TEXT',),output_modalities=('TEXT',),context_limit=8192,output_limit=2048)
   settings.update(ProviderCommand(operation='UPSERT_MODEL',expected_revision=3,model=new),auth)
   settings.update(ProviderCommand(operation='SET_CAPABILITY_ROUTE',expected_revision=4,route=CapabilityRoute(operation='COGNITION',primary_model_profile_id=new.model_profile_id,permitted_privacy=('PUBLIC','PROJECT'))),auth)
   assert app.runtime.store.identity==before and {m['memory_id'] for m in app.runtime.store.all('memories')}==memories
   reply=app.chat('continue project',privacy='PROJECT',topic='project',message_id='two')
   assert reply['render_state']=='UNVERIFIED_MODEL_WORDING' and app.runtime.identity_id==identity,reply
   assert summary in calls[-1]['source_context_refs']
   assert app.session.route_snapshot.model_profile_id=='fixture.replacement'
   requests=[RecordService(app.runtime.store).read(r['record_id'])['payload']['request']['route_snapshot'] for r in app.runtime.store.all('cognitive_requests')]
   assert [r['remote_model_id'] for r in requests]==['same-text-model']*2+['other-text-model']*2
   assert not app.runtime.store.all('grants') and not app.runtime.store.all('goals')
  with LifeApplication(home,router=router) as app:
   assert app.runtime.identity_id==identity
   reply=app.chat('still the same public project',privacy='PROJECT',topic='project',message_id='three')
   assert reply['render_state']=='UNVERIFIED_MODEL_WORDING'
   assert summary in calls[-1]['source_context_refs'] and app.session.route_snapshot.model_profile_id=='fixture.replacement'
  assert len(calls)==6
