"""External installed DEV probe. Only installed Core imports, loopback models."""
import argparse,json,sys,hashlib,importlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--keep-source',action='store_true');a=p.parse_args()
bundle=a.bundle.resolve();home=a.work.resolve()
assert __debug__ and Path(sys.prefix).resolve()==bundle/'.venv'
assert not home.exists() and not a.output.exists()
sys.dont_write_bytecode=True;sys.path.insert(0,str(bundle/'src'))
from nana_core.life.application import LifeApplication
from nana_core.life.config import LifeConfig,write_config,load_config,update_config
from nana_core.continuity.project_work.service import material_for
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.cognition import AnalyticalFixturePort,CognitiveProposal
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService,ProviderCommand,ProviderProfile,ModelProfile,CapabilityRoute
from nana_core.continuity.provider_routing import CapabilityRouter,RuntimeProviderFactory,RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
# The missing shipped module is now imported from the sealed runtime itself.
importlib.import_module('nana_core.continuity.world_loop.anthropic')
materials=lambda path:material_for(bundle,'src/nana_core/continuity/'+path)
write_config(home,LifeConfig(project_root=str(bundle),materials=(materials('recurrence.py'),),practice=materials('identity.py'),heldout=materials('autonomy/requests.py'),transfer=materials('subject/social.py'),max_autonomous_materials=0,provider_calls_per_hour=24,provider_calls_per_day=24,per_provider_calls_per_day=24,provider_context_tokens=16384,provider_output_tokens=2048))
def save(enabled):
 c=load_config(home);update_config(home,c.model_copy(update={'revision':c.revision+1,'provider_background_cognition':enabled}),expected_revision=c.revision)
class Seed:
 descriptor='synthetic-installed-own-curiosity'
 def propose(self,request):
  value=json.loads(AnalyticalFixturePort().propose(request));value['private_tendency']={'topic':'own-curiosity','tendency':'SYNTHETIC I feel curious and hesitant about contrasting shapes, without having decided on a plan.'};return json.dumps(value)
def reply(request):
 identity=json.loads(request.context_json)['manifest']
 assert request.cognitive_role=='SELF'
 return StructuredProposal(interpretation='SYNTHETIC installed continuation',subject_cognition=CognitiveProposal(identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='SYNTHETIC own continuation',proposed_operations=('DRAFT',),private_question={'topic':'own-curiosity','question':'SYNTHETIC Startup resource continues the installed private concern.'}))
clock=VirtualClock()
with provider_harness(proposer=reply) as (transport,state):
 authority=ProviderConfigurationAuthority();service=ProviderConfigService(home/'synthetic-providers.json',authority);service.initialize(authority)
 provider=ProviderProfile(provider_profile_id='fixture.installed',display_name='SYNTHETIC_LOOPBACK',protocol='SYNTHETIC_LOOPBACK',locality='LOCAL_FIXTURE',base_url=transport.endpoint.removesuffix('/chat/completions'),permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))
 model=ModelProfile(model_profile_id='fixture.text',provider_profile_id=provider.provider_profile_id,remote_model_id='harness-v1',model_version='1',operations=('COGNITION',),input_modalities=('TEXT',),output_modalities=('TEXT',),context_limit=32768,output_limit=2048)
 for operation,value in [('UPSERT_PROVIDER',{'provider':provider}),('UPSERT_MODEL',{'model':model}),('SET_CAPABILITY_ROUTE',{'route':CapabilityRoute(operation='COGNITION',primary_model_profile_id=model.model_profile_id,permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))})]:
  service.update(ProviderCommand(operation=operation,expected_revision=service.load().revision,**value),authority)
 router=CapabilityRouter(service,RuntimeProviderFactory(ProviderRegistry(),None,RoutingPolicy(allow_synthetic_loopback=True)))
 with LifeApplication(home,clock=clock,router=router) as app:
  app.pause();r=app.runtime;identity=r.identity_id
  assert r.cognition.provider_factory is None and state['calls']==0
  r.subject.cognize(SubjectInput(source_key='synthetic.installed-startup-seed',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=clock.utc_now_us(),topic='own-curiosity'),model=Seed(),authority=r.authority,policy=app.policy)
  original=next(v.source_memory_ids[0] for _,v in candidates(r.store,'project-work',('PROJECT',)))
  assert any(v.category=='PRIVATE_TENDENCY' and v.contract=='PRIVATE_TENDENCY_V4' for _,v in candidates(r.store,'project-work',('PROJECT',)))
  save(True)
  assert app.runtime.cognition.provider_factory is None and state['calls']==0
 with LifeApplication(home,clock=clock,router=router) as app:
  assert app.runtime.identity_id==identity and app.runtime.cognition.provider_factory is not None and state['calls']==0
  app.pause(False);clock.advance(2*SECOND);app.runtime.refresh_attention()
  for _ in range(5):app.tick()
  assert state['calls']==1
  assert any('Startup resource' in v.content_summary for _,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')))
  assert len(app.runtime.store.all('cognitive_requests'))==1 and not app.runtime.store.all('runtime_cognition_calls') and not app.runtime.store.all('actions')
  for _ in range(5):app.tick()
  assert state['calls']==1
  save(False)
 with LifeApplication(home,clock=clock,router=router) as app:
  app.pause();assert app.runtime.identity_id==identity and app.runtime.cognition.provider_factory is None
  assert 'provider_background_cognition' not in json.loads((home/'life.json').read_text())
  assert state['calls']==1 and len(app.runtime.store.all('cognitive_requests'))==1
  if not a.keep_source:
   app.forget(original)
   assert not candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL'))
  else:assert {v.category for _,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL'))}=={'PRIVATE_TENDENCY','PRIVATE_QUESTION'}
for name,module in sys.modules.items():
 if name=='nana_core' or name.startswith('nana_core.'):
  assert Path(module.__file__).resolve().is_relative_to(bundle/'src'),name
result={'source_commit':json.loads((bundle/'runtime.json').read_text())['source_commit'],'execution':'ACTUAL_INSTALLED_DEV_STARTUP_ORIGINAL_RUNTIME_LOOPBACK','same_identity':True,'default_off':True,'save_without_apply_or_model':True,'restart_binds_original_provider':True,'original_c_private_continuation':True,'same_condition_no_repeat':True,'disable_restart_and_legacy_field_omission':True,'withdrawal_closes_private_projection':not a.keep_source,'active_tendency_and_question_retained':a.keep_source,'root_source_memory_id':original,'subject_id':identity,'synthetic_http_calls':state['calls'],'real_provider_calls':0,'actions':0,'private_python_only':True,'native_anthropic_module_import':'PASS','production_changed':False}
from nana_core.life.live_api.supervisor import existing_identity
result['lineage_binding']=existing_identity(home)[1]
(home/'nana-space-development.json').write_text(json.dumps({'realm':'OWNED_DEVELOPMENT_ONLY','identity_id':identity}))
(home/'nana-space-development.json').chmod(0o600)
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
