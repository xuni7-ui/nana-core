"""Offline qualification: current project facts are not personal memories."""
import json,shutil
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.life.config import write_config
from nana_core.life.application import LifeApplication
from nana_core.continuity.current_state import START,END,ProjectStateBinding,ProjectStateSource
from nana_core.continuity.context import ContextRequest,ContextPolicy,ContextAssembler
from nana_core.continuity.dialogue_shadow.bridge import LiteralSpanInterpreter
from nana_core.continuity.project_work.service import capture
from nana_core.presence.authority import VirtualClock
from tests.cloud_life.conftest import config,REPO
from tests.independent_life.test_dialogue import relay


def source(path,clock,revision=1,*,age=0):
 state={'schema_version':1,'project_id':'synthetic.project','scope':'project-work','privacy_class':'PROJECT',
  'revision':revision,'as_of_us':clock.utc_now_us()-age,'stage':'H','workstream':'FIRST_LIFE_REVIEW',
  'status':'CONTEXT_REPAIR_OFFLINE_ONLY','progress':['LATEST_STAGE_MARKER_'+str(revision),'External developers implemented the runtime; this is not a Subject personal experience.'],
  'open_gates':['Human review not run; production not changed.'],'evidence_refs':['docs/public-evidence.json']}
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(b'# SSOT\n'+START+b'\n'+json.dumps(state).encode()+b'\n'+END+b'\n'+b'OLD_HISTORICAL_SECRET_CANARY '*5000)
 return state


def initialize(tmp_path,clock):
 root=tmp_path/'project';root.mkdir();base=config(max_autonomous_materials=0,provider_cost_ceiling_micro=100,provider_context_tokens=16384)
 for m in (*base.materials,base.practice,base.heldout,base.transfer):
  p=root/m.relative_path;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/m.relative_path,p)
 binding=ProjectStateBinding(relative_path='PROJECT_BRAIN/09_STATE.md',source_id='test.current',scope='project-work')
 state=root/binding.relative_path;source(state,clock)
 home=tmp_path/'life';write_config(home,base.model_copy(update={'project_root':str(root),'current_project_state':binding}))
 return home,state


@pytest.mark.parametrize('question',[
 '今天折腾这个工程很久了，你还记得我们做到哪了吗？你自己怎么看现在这个阶段？',
 '当前阶段是什么？','现在进展怎样？','你怎么看目前状态？','请报告当前进度。',
 'What is the current project status?',
])
def test_clear_project_questions_are_not_unclear(question):
 result=LiteralSpanInterpreter().interpret(question)
 assert result.kind=='PROJECT_STATUS' and result.basis=='LITERAL_SPAN'
 assert question[result.support_start:result.support_end]


@pytest.mark.parametrize('text',['他说“当前阶段”这个词，我只是吐槽','如果有人问做到哪该怎么翻译','我们的关系目前状态怎么样？','饭做到哪了？','目前状态不错。'])
def test_status_words_are_not_automatically_project_requests(text):
 assert LiteralSpanInterpreter().interpret(text).kind!='PROJECT_STATUS'


def test_original_loop_and_assembler_get_current_bounded_state_not_episodes(tmp_path):
 clock=VirtualClock();home,path=initialize(tmp_path,clock)
 # Deliberately contrary model classification: observable explicit query wins.
 with relay(home,'UNCLEAR') as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
  app.pause();before=len(app.runtime.store.all('memories'));identity=app.runtime.identity_id
  answer=app.chat('你还记得这个工程做到哪了吗？',topic='first-life',privacy='PROJECT',message_id='project-status-one')
  assert answer['mode']=='PROJECT_STATUS' and answer['judgment']=='WATCH' and answer['intention']=='SOCIAL_INTERACTION'
  assert answer['render_state']=='UNVERIFIED_MODEL_WORDING' and len(requests)==2
  for request in requests:
   assert request['expected_schema']['properties']['source_refs']['items']['enum']==request['source_context_refs']
   if request['cognitive_role']=='SOCIAL':
    assert request['expected_schema']['$defs']['DialogueDraft']['properties']['claim_memory_ids']['items']['enum']==request['source_context_refs']
   data=json.loads(request['context_json']);blocks=[b for b in data['blocks'] if b['kind']=='PROJECT_CURRENT_STATE']
   assert len(blocks)==1
   projected=json.loads(blocks[0]['data_json'])
   assert projected['attribution']=='EXTERNAL_PROJECT_STATUS_NOT_SUBJECT_EXPERIENCE'
   assert projected['source']['relative_path']=='PROJECT_BRAIN/09_STATE.md'
   assert projected['state']['revision']==1 and len(blocks[0]['data_json'].encode())<4096
   assert 'LATEST_STAGE_MARKER_1' in blocks[0]['data_json'] and 'OLD_HISTORICAL_SECRET_CANARY' not in request['context_json']
   assert 'reviewed meaning: UNCLEAR' not in request['context_json']
   assert request['role_input']['dialogue']['project_status_query']
  assert len(app.runtime.store.all('memories'))==before+1 # receipt only, no current-state memory
  assert app.runtime.identity_id==identity and not app.runtime.store.all('actions') and not app.runtime.store.all('goals')
  source(path,clock,revision=2)
  app.chat('现在进展怎样？',topic='first-life',privacy='PROJECT',message_id='project-status-two')
  assert 'LATEST_STAGE_MARKER_2' in requests[-1]['context_json'] and 'LATEST_STAGE_MARKER_1' not in requests[-1]['context_json']


def test_changed_or_withdrawn_current_state_stales_before_dispatch(tmp_path):
 clock=VirtualClock();home,path=initialize(tmp_path,clock)
 with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
  app.pause();mid=capture(app.runtime,'fixture-source','SYNTHETIC PROJECT input')
  session=app._session('PROJECT');cid=session.prepare('state-version','INTERPRET',(mid,))
  source(path,clock,revision=2)
  assert session.execute(cid)['state']=='STALE' and len(requests)==0
  cid=session.prepare('state-withdraw','INTERPRET',(mid,));path.unlink()
  assert session.execute(cid)['state']=='STALE' and len(requests)==0


def test_privacy_before_open_and_expiry_fail_closed(tmp_path):
 clock=VirtualClock();home,path=initialize(tmp_path,clock)
 with LifeApplication(home,clock=clock) as app:
  assembler=ContextAssembler(app.runtime.store,app.runtime.authority,project_state_source=app.current_project_state)
  req=ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='test.current',task='status',task_privacy_class='PUBLIC',destination='DEVELOPMENT_REMOTE')
  policy=ContextPolicy(policy_id='public-only',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'),remote_privacy=('PUBLIC',))
  path.unlink() # Denied classification must not attempt opening a missing file.
  package=assembler.assemble(req,policy)
  assert not any(b.kind=='PROJECT_CURRENT_STATE' for b in package.blocks)
  with pytest.raises(CoreError,match='NOT_BOUND_OR_DENIED'):assembler.assemble(req,policy,require_current_state=True)
  source(path,clock,age=86400_000_001)
  with pytest.raises(CoreError,match='PROJECT_CURRENT_STATE_STALE'):
   app.current_project_state.projection(scopes=('project-work',),privacy_classes=('PROJECT',),now_us=clock.utc_now_us())


def test_refusal_remains_stronger_than_status_question(tmp_path):
 clock=VirtualClock();home,path=initialize(tmp_path,clock)
 with relay(home,'UNCLEAR') as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
  a=app.chat('不要研究这个话题。',topic='closed',privacy='PROJECT',message_id='closed')
  b=app.chat('这个工程做到哪了？',topic='closed',privacy='PROJECT',message_id='status-closed')
  assert a['mode']==b['mode']=='RESPECT_BOUNDARY' and not requests


def test_projection_does_not_mutate_store_and_late_source_change_is_stale(tmp_path):
 clock=VirtualClock();home,path=initialize(tmp_path,clock)
 with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
  mid=capture(app.runtime,'fixture-required','Public project data')
  session=app._session('PROJECT')
  req=ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='test.current',task='current project status',task_privacy_class='PROJECT',max_input_tokens=16000)
  before=app.runtime.store.snapshot();package=session.assembler.assemble(req,app.policy,require_current_state=True)
  assert before==app.runtime.store.snapshot()
  assert any(b.kind=='PROJECT_CURRENT_STATE' for b in package.blocks)
  from nana_core.life.dialogue_contracts import DialogueContext
  descriptor=DialogueContext(message_memory_id=mid,topic='first-life',privacy_class='PROJECT',phase='INTERPRET',project_status_query=True)
  cid=session.prepare('late-source-change','INTERPRET',(mid,),role_input={'dialogue':descriptor.model_dump(mode='json')},volatile_input={'dialogue':descriptor.model_copy(update={'text':'当前阶段是什么？'}).model_dump(mode='json')});original=session.transport.exchange
  def changed(request):
   reply=original(request);source(path,clock,revision=2);return reply
  session.transport.exchange=changed
  assert session.execute(cid)['state']=='STALE' and len(requests)==1 # synthetic loopback only


@pytest.mark.parametrize('bad',['invalid-json','duplicate','symlink','secret-class'])
def test_source_corruption_is_not_forwarded(tmp_path,bad):
 clock=VirtualClock();home,path=initialize(tmp_path,clock)
 if bad=='invalid-json':path.write_bytes(START+b'\n{\n'+END)
 elif bad=='duplicate':path.write_bytes(START+b'\n{"schema_version":1,"schema_version":1}\n'+END)
 elif bad=='symlink':
  target=path.with_suffix('.target');path.rename(target);path.symlink_to(target.name)
 else:path.write_text(path.read_text().replace('"privacy_class": "PROJECT"','"privacy_class": "SECRET"',1))
 with relay(home,'PROJECT_STATUS') as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
  response=app.chat('当前阶段是什么？',privacy='PROJECT',message_id='bad-current-source')
  assert response['mode']=='PROJECT_STATUS' and len(requests)==0
  assert response['provider_state']=='PROJECT_CURRENT_STATE_UNAVAILABLE'


def test_neutral_receipt_does_not_allow_raw_message_ingress(tmp_path):
 from nana_core.continuity.contracts import EvidenceInput,Provenance
 from nana_core.continuity.memory import MemoryService
 clock=VirtualClock();home,path=initialize(tmp_path,clock)
 with LifeApplication(home,clock=clock) as app:
  with pytest.raises(CoreError,match='LOCAL_METADATA_ONLY'):
   MemoryService(app.runtime.store).capture(EvidenceInput(provenance=Provenance(domain='LOCAL_INTERACTION_METADATA',source_namespace='recorded.local.message',source_reference='test.raw',source_kind='DIRECT_OBSERVATION'),text='This is an arbitrary raw user message, not receipt metadata.',privacy_class='PROJECT',observed_time_us=clock.utc_now_us()))


def test_project_status_through_actual_surface_retains_only_closed_metadata(tmp_path):
 from nana_core.life.surfaces import SurfaceObservation,SurfaceBinding
 from nana_core.life.config import load_config,update_config
 clock=VirtualClock();home,path=initialize(tmp_path,clock)
 cfg=load_config(home)
 update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(SurfaceBinding(binding_id='cloud.cli',platform='cloud.cli',surface='chat.direct',adapter='shadow.local'),)}),expected_revision=cfg.revision)
 text='这个工程现在进展怎样？' # synthetic project query; not the human opener
 with relay(home,'UNCLEAR') as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
  app.pause();before={t:len(app.runtime.store.all(t)) for t in ('actions','goals','grants')}
  result=app.surfaces.receive(SurfaceObservation(binding_id='cloud.cli',event_id='synthetic-status-surface',topic='first-life',privacy_class='PROJECT',text=text))
  assert result['mode']=='PROJECT_STATUS' and result['render_state']=='UNVERIFIED_MODEL_WORDING'
  assert len(requests)==2 and not result['delivered'] and not result['execution_authority']
  assert before=={t:len(app.runtime.store.all(t)) for t in before}
  record=app.runtime.store.db.execute('SELECT record_id FROM subject_events WHERE source_key=?',(result['source_key'],)).fetchone()[0]
  from nana_core.continuity.records import RecordService
  payload=RecordService(app.runtime.store).read(record)['payload']['input']
  assert payload['text']=='Local input reviewed meaning: PROJECT_STATUS'
  assert text not in str(app.runtime.store.snapshot())
  again=app.surfaces.receive(SurfaceObservation(binding_id='cloud.cli',event_id='synthetic-status-surface',topic='first-life',privacy_class='PROJECT',text=text))
  assert again['state']=='ALREADY_REVIEWED_NO_REPLAY' and len(requests)==2
  # The separate KEEP admission path uses the same finite vocabulary.
  from nana_core.continuity.contracts import EvidenceInput,Provenance
  from nana_core.continuity.memory import MemoryService
  service=MemoryService(app.runtime.store)
  p=Provenance(domain='LOCAL_INTERACTION_METADATA',source_namespace='recorded.local.subject',source_reference='synthetic-kept-status',source_kind='USER_STATEMENT')
  service.capture(EvidenceInput(provenance=p,text=payload['text'],privacy_class='PROJECT',observed_time_us=clock.utc_now_us()))
  with pytest.raises(CoreError,match='LOCAL_METADATA_ONLY'):
   service.capture(EvidenceInput(provenance=p.model_copy(update={'source_reference':'unsafe-suffix'}),text=payload['text']+' arbitrary prose',privacy_class='PROJECT',observed_time_us=clock.utc_now_us()))
  # A fresh rendering verification can reuse the already committed C judgment
  # without repeating INTERPRET or replaying its old RENDER request.
  from tools.nana_first_life_live_response.attempt import render_existing
  from uuid import uuid4
  counts={t:len(app.runtime.store.all(t)) for t in ('subject_cycles','actions','goals','grants')}
  info,wording=render_existing(app,result['source_key'],text,str(uuid4()))
  assert info['original_C_replayed_without_new_judgment'] and wording
  assert len(requests)==3 and requests[-1]['cognitive_role']=='SOCIAL'
  assert counts=={t:len(app.runtime.store.all(t)) for t in counts}
  assert text not in str(app.runtime.store.snapshot())
  # A provider can ignore the advertised enum. Core must still reject its
  # unbound reference, without dropping/normalizing it or calling again.
  session=app._session('PROJECT');original=session.transport.exchange
  def unbound(request):
   reply=original(request)
   return reply.model_copy(update={'proposal':reply.proposal.model_copy(update={'source_refs':('synthetic.unbound.project-state-label',)})})
  session.transport.exchange=unbound
  with pytest.raises(CoreError,match='UNSUPPORTED_CITATIONS'):
   render_existing(app,result['source_key'],text,str(uuid4()))
  assert len(requests)==4 and counts=={t:len(app.runtime.store.all(t)) for t in counts}
