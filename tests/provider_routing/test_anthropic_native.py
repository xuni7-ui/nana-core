"""Native Messages wire through original session, synthetic HTTP only."""
import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import pytest
from nana_core.continuity.provider_config import ProviderProfile
from nana_core.continuity.provider_routing import RuntimeProviderFactory,RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
from nana_core.continuity.world_loop.cognition import CognitionSession,StructuredProposal,CognitionRequest
from nana_core.storage import canonical
from tests.world_loop.helpers import fresh,capture,policy
from .helpers import Resolver,model


def test_native_factory_uses_messages_endpoint_and_existing_host_secret_gates():
    p=ProviderProfile(provider_profile_id='native.main',display_name='Native',protocol='ANTHROPIC',
        base_url='https://native.example/v1',locality='REMOTE',secret_ref='native.main')
    m=model('model.native',p.provider_profile_id).model_copy(update={'remote_model_id':'synthetic-native'})
    resolver=Resolver(('native.main',));factory=RuntimeProviderFactory(ProviderRegistry(),resolver,
        RoutingPolicy(allow_remote=True,allowed_remote_hosts=('native.example',)))
    port=factory.create(p,m,'COGNITION')
    assert port.endpoint=='https://native.example/v1/messages' and resolver.resolved==1
    assert port.request_headers('synthetic')['x-api-key']=='TEST_ONLY_NOT_SECRET'
    assert 'Authorization' not in port.request_headers('synthetic')
    assert port.request_headers('synthetic')['anthropic-version']=='2026-10-21'
    from nana_core.contracts import CoreError
    with pytest.raises(CoreError,match='OPERATION_UNSUPPORTED'):factory.create(p,m,'VISION')
    factory.policy=RoutingPolicy()
    with pytest.raises(CoreError,match='PRE_DISPATCH_UNAVAILABLE'):factory.create(p,m,'COGNITION')
    assert resolver.resolved==1


@contextmanager
def native_wire(mode):
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            assert self.path=='/v1/messages'
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert set(body)<= {'model','system','messages','max_tokens','stream','thinking'}
            assert body['stream'] is False and len(body['messages'])==1
            assert body['messages'][0]['role']=='user' and 'JSON' in body['system']
            assert self.headers['anthropic-version']=='2026-10-21'
            request=json.loads(body['messages'][0]['content']);calls.append(body)
            proposal=StructuredProposal(interpretation='SYNTHETIC native proposal',source_refs=tuple(request['primary_source_refs']))
            if mode=='dialogue':
                descriptor=request['role_input']['dialogue']
                payload={'interpretation':'SYNTHETIC native dialogue','source_refs':request['source_context_refs'],
                         'uncertainty':'LOW','confidence':.9}
                if request['cognitive_role']=='INTERPRET':payload['dialogue']={'kind':'CHAT','confidence':'HIGH'}
                else:payload['draft']={'text':'SYNTHETIC native response','claim_memory_ids':[],
                                      'effect_status':descriptor['effect_status']}
            else:payload=proposal.model_dump(mode='json')
            value={'id':'msg_synthetic','type':'message','role':'assistant','model':body['model'],
                   'content':[{'type':'text','text':json.dumps(payload)}],
                   'stop_reason':'end_turn','usage':{'input_tokens':10,'output_tokens':4,
                       'cache_creation_input_tokens':3,'cache_read_input_tokens':2}}
            if mode=='truncated':value['stop_reason']='max_tokens'
            if mode=='tool':value['content']=[{'type':'tool_use','name':'untrusted','input':{}}];value['stop_reason']='tool_use'
            if mode=='bad-usage':value['usage']['input_tokens']=True
            if mode=='refusal':value['stop_reason']='refusal'
            if mode=='thinking':value['content'].insert(0,{'type':'thinking','thinking':'SYNTHETIC transient private model reasoning','signature':'synthetic'})
            raw=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield 'http://127.0.0.1:'+str(server.server_port)+'/v1/messages',calls
    finally:server.shutdown();server.server_close();thread.join()


@pytest.mark.parametrize('mode,expected',[('ok','PROPOSED'),('thinking','PROPOSED'),('truncated','FAILED'),('tool','FAILED'),('bad-usage','FAILED'),('refusal','FAILED')])
def test_native_wire_original_cognition_usage_and_no_automatic_replay(tmp_path,mode,expected):
    from nana_core.continuity.world_loop.anthropic import AnthropicJSONTransport
    with native_wire(mode) as (endpoint,calls),fresh(tmp_path/'self.db') as r:
        port=AnthropicJSONTransport(endpoint,'synthetic-native',harness=True)
        session=CognitionSession(r,port,policy());mid=capture(r,'native-source',{'fact':'SYNTHETIC retained source'})
        cid=session.prepare('native-'+mode,'INTERPRET',(mid,));assert session.execute(cid)['state']==expected
        assert len(calls)==1 and not r.store.all('actions') and not r.store.all('grants')
        assert session.execute(cid)['replayed'] and len(calls)==1
        saved=r.store.one('core_meta','cognition.usage.'+cid)
        if mode!='bad-usage':
            receipt=json.loads(saved['value_json'])
            assert receipt['input_tokens']==15 and receipt['output_tokens']==4 and receipt['origin']=='SYNTHETIC'
            from nana_core.presence.resources import resource_state
            state=resource_state(r.store,r.config)
            assert state.fixture_reported_input_tokens==15 and state.fixture_reported_output_tokens==4
            assert state.provider_reported_input_tokens is None and state.real_usage_reported_calls==0
            assert port.last_response_metadata['usage']['cache_creation_input_tokens']==3
            assert port.last_response_metadata['usage']['cache_read_input_tokens']==2
            print(json.dumps({'measurement':'synthetic_native_response_usage','mode':mode,'state':expected,
                'input_tokens':receipt['input_tokens'],'output_tokens':receipt['output_tokens'],'http_calls':len(calls)},sort_keys=True))
        else:assert saved is None
        if mode in {'ok','thinking'}:
            assert port.last_response_metadata['finish_reason']=='end_turn'
            assert port.last_parse_diagnostic.openai_shape_valid is None
            assert 'SYNTHETIC transient private model reasoning' not in json.dumps(session.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload'])
        else:
            assert not r.store.db.execute("SELECT 1 FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL' AND target_id=?",(cid,)).fetchone()
            assert r.store.one('cognitive_requests',cid)['actual_cost_micro'] is None


def test_native_social_does_not_request_an_openai_sse_stream(tmp_path):
    from nana_core.continuity.world_loop.anthropic import AnthropicJSONTransport
    with fresh(tmp_path/'self.db') as r:
        port=AnthropicJSONTransport('http://127.0.0.1:1/v1/messages','synthetic-native',harness=True)
        session=CognitionSession(r,port,policy());session.draft_sink=lambda value:None
        mid=capture(r,'social-native',{'fact':'SYNTHETIC'})
        cid=session.prepare('native-social','SOCIAL',(mid,))
        data=session.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']
        assert CognitionRequest.model_validate_json(canonical(data)).response_mode=='JSON' and not r.store.all('actions')


def test_native_messages_reach_original_c_render_and_same_subject_restart(tmp_path):
    from nana_core.continuity.world_loop.anthropic import AnthropicJSONTransport
    from nana_core.continuity.provider_routing import CapabilityRouter
    from nana_core.continuity.provider_config import CapabilityRoute
    from nana_core.life.application import LifeApplication
    from nana_core.life.config import update_config
    from nana_core.presence.authority import VirtualClock
    from tests.independent_life.conftest import initialize
    from .helpers import config_service,update
    home=tmp_path/'home';config=initialize(home,active=0);clock=VirtualClock()
    update_config(home,config.model_copy(update={'revision':config.revision+1,
        'remote_privacy':('PUBLIC','PROJECT'),'provider_cost_ceiling_micro':1000}),expected_revision=config.revision)
    with native_wire('dialogue') as (endpoint,calls):
        cfg,authority=config_service(home/'synthetic-native-providers.json')
        p=ProviderProfile(provider_profile_id='native.fixture',display_name='SYNTHETIC native codec only',
            protocol='ANTHROPIC',locality='REMOTE',base_url='https://native.example/v1',secret_ref='native.fixture',
            permitted_privacy=('PUBLIC','PROJECT'))
        m=model('model.native',p.provider_profile_id).model_copy(update={'remote_model_id':'synthetic-native'})
        update(cfg,authority,'UPSERT_PROVIDER',provider=p);update(cfg,authority,'UPSERT_MODEL',model=m)
        update(cfg,authority,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='COGNITION',primary_model_profile_id=m.model_profile_id,
               permitted_privacy=('PUBLIC','PROJECT')))
        class SyntheticNativeFactory(RuntimeProviderFactory):
            # Explicit fixture injection, never mislabel localhost as a real provider.
            def create(self,provider,model,operation):
                self.available(provider,model,operation)
                return AnthropicJSONTransport(endpoint,model.remote_model_id,provider_id=provider.provider_profile_id,harness=True)
        factory=SyntheticNativeFactory(ProviderRegistry(),Resolver(('native.fixture',)),
            RoutingPolicy(allow_remote=True,allowed_remote_hosts=('native.example',)))
        router=CapabilityRouter(cfg,factory)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();identity=app.runtime.identity_id
            answer=app.chat('SYNTHETIC native greeting',privacy='PROJECT',message_id='native-one')
            assert answer['mode']=='CHAT' and answer['text']=='SYNTHETIC native response'
            cycles=len(app.runtime.store.all('subject_cycles'))
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity
            answer=app.chat('SYNTHETIC native followup',privacy='PROJECT',message_id='native-two')
            assert answer['mode']=='CHAT' and answer['text']=='SYNTHETIC native response'
            assert len(app.runtime.store.all('subject_cycles'))==cycles+1
            assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        assert len(calls)==4 and all(body['stream'] is False for body in calls)
