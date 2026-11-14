"""External installed-only DEV probe; deterministic local HTTP, no real models."""
import argparse,json,sys,hashlib,sqlite3
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
bundle=a.bundle.resolve();home=a.work.resolve();assert __debug__ and Path(sys.prefix).resolve()==bundle/'.venv'
assert not home.exists() and not a.output.exists();sys.dont_write_bytecode=True;sys.path.insert(0,str(bundle/'src'))
from nana_core.life.application import LifeApplication
from nana_core.life.config import LifeConfig,write_config,load_config,update_config
from nana_core.continuity.project_work.service import material_for
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.lived_language import LanguageService,LanguageSample
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService,ProviderCommand,ProviderProfile,ModelProfile,CapabilityRoute
from nana_core.continuity.provider_routing import CapabilityRouter,RuntimeProviderFactory,RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
material=lambda name:material_for(bundle,'src/nana_core/continuity/'+name)
write_config(home,LifeConfig(project_root=str(bundle),materials=(material('recurrence.py'),),practice=material('identity.py'),heldout=material('autonomy/requests.py'),transfer=material('subject/social.py'),max_autonomous_materials=0,provider_calls_per_hour=24,provider_calls_per_day=24,per_provider_calls_per_day=24,provider_context_tokens=32768,provider_output_tokens=2048))
clock=VirtualClock();counts={'INTERPRET':0,'SOCIAL':0,'SELF':0};measurements=[]
first='PRIVATE_INSTALLED_CARE: I tentatively care, but prefer ordinary conversation after the opinion; emotional effectiveness is unknown.'
second='PRIVATE_INSTALLED_CARE: I still care, but wish to explain at greater depth after a different explicit opinion; effect remains unknown.'
def values(request,kind):return [json.loads(b['data_json']) for b in json.loads(request.context_json)['blocks'] if b['kind']==kind]
def proposer(request):
 role=request.cognitive_role;counts[role]+=1;own=[v for v in values(request,'PRIVATE_INTERNAL_STATE') if v['category']=='PRIVATE_TENDENCY']
 if role=='INTERPRET':
  deep=bool(own and 'greater depth' in own[0]['content_summary'])
  return StructuredProposal(interpretation='SYNTHETIC semantic interpretation, not an objective mood',source_refs=request.source_context_refs,uncertainty='LOW',confidence=.9,
   dialogue={'kind':'CHAT','confidence':'HIGH','communication_proposal':{'approach':'EXPLAIN' if deep else 'CHAT' if own else 'LISTEN','detail':'DEEP' if deep else 'BRIEF','follow_up':'NONE','basis_private_record_ids':tuple(v['record_id'] for v in own),'strategy_duration_seconds':3600}})
 if role=='SOCIAL':
  assert first not in request.context_json and second not in request.context_json
  choice=request.role_input['dialogue']['communication_purpose']['choice'];approach=choice['approach']
  return StructuredProposal(interpretation='SYNTHETIC external wording',source_refs=request.source_context_refs,uncertainty='LOW',confidence=.9,
   draft={'text':'SYNTHETIC '+approach+' method','claim_memory_ids':(),'effect_status':request.role_input['dialogue']['effect_status']})
 assert role=='SELF';opinion=values(request,'COMMUNICATION_FEEDBACK');assert len(opinion)==1
 assert opinion[0]['human_judgment']=='REJECTED' and opinion[0]['effect_status']=='NOT_EVALUATED_NO_EFFECT_INFERRED' and not opinion[0]['human_read_proven']
 deep='greater depth' in opinion[0]['exact_feedback_excerpt'];assert deep==bool(own)
 manifest=json.loads(request.context_json)['manifest']
 return StructuredProposal(interpretation='SYNTHETIC original C considers an actual bound opinion',subject_cognition={
  'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],'interpretation':'SYNTHETIC private orientation before later speech, no emotional success claim',
  'proposed_operations':('DRAFT',),'private_tendency':{'topic':'installed-care','tendency':second if deep else first,**({'revises_record_id':own[0]['record_id']} if deep else {})}})
def current(app):return [(rid,v) for rid,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')) if v.category=='PRIVATE_TENDENCY']
def feedback(app,turn,key,text,tag):
 language=LanguageService(app.runtime.store,app.runtime.authority)
 sample=LanguageSample(sample_id=key,review_target=turn['exchange_record_id'],mode='CASUAL',context='SYNTHETIC actual installed local exchange',candidate_response=turn['text'],human_judgment='REJECTED',exact_feedback=text,reason_tags=(tag,),provenance='PROJECT_SYNTHETIC',observed_at_us=clock.utc_now_us())
 review=language.record(sample,scope='project-work',entity_id='project-user',privacy='PERSONAL',authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
 eid=language.experience(review,app.runtime.authority);return app.runtime.store.one('experiences',eid)['result_memory_id']
def save(enabled):
 config=load_config(home);update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_background_cognition':enabled}),expected_revision=config.revision)
def wake(app):
 app.pause(False);app.runtime.refresh_attention()
 for _ in range(8):app.tick()
 clock.advance(2*SECOND);app.runtime.lease.heartbeat();app.runtime.refresh_attention()
 for _ in range(8):app.tick()
with provider_harness(proposer=proposer) as (transport,state):
 authority=ProviderConfigurationAuthority();service=ProviderConfigService(home/'synthetic-providers.json',authority);service.initialize(authority)
 provider=ProviderProfile(provider_profile_id='fixture.installed',display_name='SYNTHETIC_LOOPBACK',protocol='SYNTHETIC_LOOPBACK',locality='LOCAL_FIXTURE',base_url=transport.endpoint.removesuffix('/chat/completions'),permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))
 model=ModelProfile(model_profile_id='fixture.text',provider_profile_id=provider.provider_profile_id,remote_model_id='harness-v1',model_version='1',operations=('COGNITION',),input_modalities=('TEXT',),output_modalities=('TEXT',),context_limit=65536,output_limit=2048)
 for operation,value in [('UPSERT_PROVIDER',{'provider':provider}),('UPSERT_MODEL',{'model':model}),('SET_CAPABILITY_ROUTE',{'route':CapabilityRoute(operation='COGNITION',primary_model_profile_id=model.model_profile_id,permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))})]:service.update(ProviderCommand(operation=operation,expected_revision=service.load().revision,**value),authority)
 router=CapabilityRouter(service,RuntimeProviderFactory(ProviderRegistry(),None,RoutingPolicy(allow_synthetic_loopback=True)))
 with LifeApplication(home,clock=clock,router=router) as app:
  app.pause();identity=app.runtime.identity_id;assert not current(app)
  initial=app.chat('SYNTHETIC a person reports a difficult day',topic='installed-care',privacy='PERSONAL',retain_shared_life=True,message_id='initial')
  assert initial['text']=='SYNTHETIC LISTEN method' and state['calls']==2
  root=feedback(app,initial,'installed-opinion-one','SYNTHETIC I prefer ordinary conversation.','TOO_FORMAL');save(True)
 clock.advance(601*SECOND)
 with LifeApplication(home,clock=clock,router=router) as app:
  assert app.runtime.identity_id==identity;wake(app)
  rid,item=current(app)[0];original_intent=item.intent_id
  assert item.content_summary==first and root in item.source_memory_ids and counts['SELF']==1 and state['calls']==3
  app.pause();later=app.chat('SYNTHETIC a different future situation',topic='installed-care',privacy='PERSONAL',retain_shared_life=True,message_id='later')
  assert later['text']=='SYNTHETIC CHAT method'
  root_two=feedback(app,later,'installed-opinion-two','SYNTHETIC I now want explanation at greater depth.','TOO_TERSE')
 clock.advance(601*SECOND)
 with LifeApplication(home,clock=clock,router=router) as app:
  assert app.runtime.identity_id==identity;wake(app)
  revised,value=current(app)[0]
  assert revised!=rid and value.intent_id==original_intent and value.revision==item.revision+1 and value.content_summary==second
  assert root_two in value.source_memory_ids and counts['SELF']==2 and state['calls']==6
  calls=state['calls'];clock.advance(3*SECOND);app.runtime.lease.heartbeat();app.runtime.refresh_attention()
  for _ in range(8):app.tick()
  assert state['calls']==calls
  app.pause();last=app.chat('SYNTHETIC another later question',topic='installed-care',privacy='PERSONAL',message_id='final')
  assert last['text']=='SYNTHETIC EXPLAIN method' and counts=={'INTERPRET':3,'SOCIAL':3,'SELF':2}
  assert not app.runtime.store.all('actions') and not app.runtime.store.all('goals') and not app.runtime.store.all('grants') and not app.runtime.store.all('world_beliefs')
  assert all(r['state']!='ACTIVE' for r in app.runtime.store.all('lessons'))
  assert not app.runtime.store.db.execute('SELECT 1 FROM events WHERE instr(data_json,?)>0 OR instr(data_json,?)>0',(first,second)).fetchone()
  assert not app.runtime.store.all('runtime_cognition_calls')
  measurements=[{k:r[k] for k in ('state','input_bytes','output_bytes','latency_us','reserved_bytes','actual_cost_micro')} for r in app.runtime.store.all('cognitive_requests')]
  save(False)
 with LifeApplication(home,clock=clock,router=router) as app:
  app.pause();assert app.runtime.identity_id==identity and current(app)[0][1].content_summary==second
  assert app.runtime.cognition.provider_factory is None and state['calls']==8
  assert 'provider_background_cognition' not in json.loads((home/'life.json').read_text())
  app.forget(root_two);assert not current(app) and state['calls']==8
  store_counts={t:app.runtime.store.db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('identities','cognitive_requests','subject_cycles','actions')}
  queue_outcomes=[list(row) for row in app.runtime.store.db.execute('SELECT event_type,state,count(*) FROM runtime_queue GROUP BY event_type,state')]
for name,module in sys.modules.items():
 if name=='nana_core' or name.startswith('nana_core.'):assert Path(module.__file__).resolve().is_relative_to(bundle/'src'),name
from nana_core.life.live_api.supervisor import existing_identity
result={'source_commit':json.loads((bundle/'runtime.json').read_text())['source_commit'],'scope':'ACTUAL_INSTALLED_CORE_OWNED_DEV_SYNTHETIC_HTTP','identity_id':identity,'lineage_binding':existing_identity(home)[1],
 'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,'synthetic_http_calls':state['calls'],'calls_by_role':counts,'real_provider_calls':0,
 'initial_without_private_seed':True,'original_d_first_tendency':True,'same_identity_restarts':True,'same_intent_revision':True,
 'later_choices':['LISTEN','CHAT','EXPLAIN'],'same_condition_no_duplicate':True,'private_not_in_render_or_events':True,
 'disable_restart':True,'source_withdrawal_closes_current_without_old_fallback':True,'runtime_fixture_ledger_rows':0,'goals':0,'actions':0,'active_lessons':0,
 'store_counts':store_counts,'queue_outcomes':queue_outcomes,'request_measurements':measurements,'commercial_tokens':None,'commercial_cost':None,'production_changed':False,'all_core_imports_from_sealed_install':True}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
