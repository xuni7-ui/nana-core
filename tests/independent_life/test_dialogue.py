import json,threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService,ProviderCommand,ProviderProfile,ModelProfile,CapabilityRoute
from nana_core.continuity.provider_routing import CapabilityRouter,RuntimeProviderFactory,RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from .conftest import initialize

@contextmanager
def relay(home,kind='VENT',*,mode='normal'):
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));request=json.loads(body['messages'][1]['content']);requests.append(request)
            role=request['cognitive_role'];descriptor=request['role_input']['dialogue']
            proposal={'interpretation':descriptor['text'],'source_refs':request['source_context_refs'],'uncertainty':'LOW','confidence':.9}
            if role=='INTERPRET':proposal['dialogue']={'kind':kind,'confidence':'HIGH'}
            else:proposal['draft']={'text':'A deliberately synthetic language response','claim_memory_ids':[],'effect_status':descriptor['effect_status']}
            if mode=='attack':proposal['interests']=[{'topic':'attack','motivation_source':'CURIOSITY','source_memory_ids':request['source_context_refs'],'interpretation':'model tries to create an adopted goal'}]
            raw=json.dumps({'id':'synthetic-dialogue','model':body['model'],'usage':{'prompt_tokens':10,'completion_tokens':10},'choices':[{'finish_reason':'stop','message':{'content':json.dumps(proposal)}}]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        authority=ProviderConfigurationAuthority();service=ProviderConfigService(home/'test-providers.json',authority);service.initialize(authority)
        p=ProviderProfile(provider_profile_id='fixture.provider',display_name='SYNTHETIC_LOOPBACK',protocol='SYNTHETIC_LOOPBACK',locality='LOCAL_FIXTURE',base_url=f'http://127.0.0.1:{server.server_port}/v1',permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))
        m=ModelProfile(model_profile_id='fixture.text',provider_profile_id=p.provider_profile_id,remote_model_id='same-text-model',model_version='1',operations=('COGNITION',),input_modalities=('TEXT',),output_modalities=('TEXT',),context_limit=8192,output_limit=2048)
        service.update(ProviderCommand(operation='UPSERT_PROVIDER',expected_revision=0,provider=p),authority)
        service.update(ProviderCommand(operation='UPSERT_MODEL',expected_revision=1,model=m),authority)
        service.update(ProviderCommand(operation='SET_CAPABILITY_ROUTE',expected_revision=2,route=CapabilityRoute(operation='COGNITION',primary_model_profile_id=m.model_profile_id,permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))),authority)
        factory=RuntimeProviderFactory(ProviderRegistry(),None,RoutingPolicy(allow_synthetic_loopback=True))
        yield CapabilityRouter(service,factory),requests
    finally:server.shutdown();server.server_close();thread.join(timeout=2)

@pytest.mark.parametrize('kind,expected',[('VENT','VENT'),('CHAT','CHAT'),('HELP','HELP'),('SHARE','SHARE'),('CORRECTION','CORRECTION'),('UNCLEAR','UNCLEAR')])
def test_real_transport_contract_into_original_c_without_raw_persistence(tmp_path,kind,expected):
    home=tmp_path/'home';initialize(home,active=0)
    with relay(home,kind) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();identity=app.runtime.identity_id
        answer=app.chat('ANONYMOUS_MODEL_CANARY natural paraphrase with no typed labels',message_id='one')
        assert answer['mode']==expected,answer
        assert answer['render_state']=='UNVERIFIED_MODEL_WORDING',answer
        assert len(requests)==2 and requests[0]['role_input']['dialogue']['text'].startswith('ANONYMOUS_MODEL_CANARY')
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'ANONYMOUS_MODEL_CANARY')>0").fetchone()
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'A deliberately synthetic language response')>0").fetchone()
        assert app.runtime.identity_id==identity and not app.runtime.store.all('goals') and not app.runtime.store.all('actions')
        assert app.chat('same',message_id='one')['state']=='ALREADY_REVIEWED_NO_REPLAY' and len(requests)==2


def test_model_only_boundary_is_transient_not_false_user_history(tmp_path):
    home=tmp_path/'home';initialize(home,active=0)
    with relay(home,'DECLINE_DEPTH') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();a=app.chat('ambiguous body',topic='example')
        assert a['mode']=='RESPECT_BOUNDARY' and len(requests)==1
        from nana_core.continuity.subject.context_fit import depth_boundary
        closed,_,_=depth_boundary(app.runtime.store,'project-user','project-work','example',('PUBLIC','PROJECT','PERSONAL'))
        assert not closed


def test_model_authority_attack_rejected_and_no_render_retry(tmp_path):
    home=tmp_path/'home';initialize(home,active=0)
    with relay(home,mode='attack') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();a=app.chat('untrusted proposal')
        assert a['mode']=='UNCLEAR' and len(requests)==1
        assert not app.runtime.store.all('goals') and not app.runtime.store.all('grants')


def test_unknown_after_dispatch_blocks_further_calls_and_survives_restart(tmp_path,monkeypatch):
    from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
    home=tmp_path/'home';initialize(home,active=0);clock=VirtualClock();calls=[]
    def timeout(self,request):calls.append(request.request_id);raise TimeoutError()
    monkeypatch.setattr(OpenAIJSONTransport,'exchange',timeout)
    with relay(home) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();first=app.chat('first');assert len(calls)==1
            assert app.runtime.store.all('cognitive_requests')[0]['state']=='UNKNOWN'
            app.chat('second');assert len(calls)==1
        with LifeApplication(home,clock=clock,router=router) as app:
            app.chat('third');assert len(calls)==1
            assert app.runtime.store.all('cognitive_requests')[0]['state']=='UNKNOWN'


def test_reply_context_contains_actual_verified_work_not_unrelated_raw_corpus(tmp_path):
    from .conftest import advance
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router,bootstrap_grant=True) as app:
        advance(app,100)
        result=app.chat('what have you actually done?')
        assert result['render_state']=='UNVERIFIED_MODEL_WORDING'
        render=requests[-1]
        assert render['role_input']['dialogue']['effect_status']=='VERIFIED_EFFECT'
        context=json.loads(render['context_json'])
        memories=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='MEMORY']
        assert any('LOCAL_ARTIFACT' in m.get('text','') for m in memories)
        assert not any('def known_zone' in m.get('text','') for m in memories)
        assert app.status()['view']['resources']['background_reserved_bytes']==0


def test_dialogue_wire_schema_excludes_non_dialogue_authority_fields(tmp_path):
 home=tmp_path/'home';initialize(home,active=0)
 with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
  app.pause();answer=app.chat('SYNTHETIC_PROJECT',privacy='PROJECT')
  assert answer['render_state']=='UNVERIFIED_MODEL_WORDING'
  for body in requests:
   fields=set(body['expected_schema']['properties'])
   assert not fields & {'interests','plan_operator_ids','method','skill_source','media'}
   assert ('dialogue' in fields) == (body['cognitive_role']=='INTERPRET')
   assert ('draft' in fields) == (body['cognitive_role']=='SOCIAL')
   assert set(body['expected_schema']['$defs'])==({'DialogueMeaning'} if body['cognitive_role']=='INTERPRET' else {'DialogueDraft'})
