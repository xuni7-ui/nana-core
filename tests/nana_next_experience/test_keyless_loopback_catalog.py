"""Real local HTTP fixture only: no real provider, inference, or host configuration."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import threading

import pytest

from nana_core.contracts import CoreError
from nana_core.life.live_api.contracts import ApiError
from tools.nana_next_experience.experiments.keyless_loopback_catalog import read_keyless_loopback_catalog


@pytest.fixture
def catalog_server():
    state={'body':b'{"data":[{"id":"model.b"},{"id":"model.a"},{"id":"model.a"}]}',
           'visits':[],'status':200,'content_type':'application/json'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            state['visits'].append((self.path,'Authorization' in self.headers))
            self.send_response(state['status'])
            self.send_header('Content-Type',state['content_type'])
            if state['status']==302:self.send_header('Location','/unexpected')
            self.end_headers()
            try:self.wfile.write(state['body'])
            except (BrokenPipeError,ConnectionResetError):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);worker.start()
    try:yield f'http://127.0.0.1:{server.server_port}/v1',state
    finally:server.shutdown();server.server_close();worker.join(2)


def read(base):return read_keyless_loopback_catalog(base,explicit_authorized=True,allowed_bases=(base,))


def test_local_catalog_is_explicit_bounded_and_does_not_infer(catalog_server,monkeypatch):
    base,state=catalog_server
    monkeypatch.setenv('http_proxy','http://127.0.0.1:1')
    monkeypatch.setenv('NO_PROXY','')
    assert read(base)=={'models':['model.a','model.b'],'truncated':False,
                        'qualification':'NOT_ESTABLISHED','inference_calls':0}
    assert state['visits']==[('/v1/models',False)]
    state['body']=json.dumps({'data':[{'id':f'model.{i:03d}'} for i in range(300)]}).encode()
    result=read(base)
    assert len(result['models'])==256 and result['truncated']
    for options in ({'explicit_authorized':False,'allowed_bases':(base,)},
                    {'explicit_authorized':True,'allowed_bases':('http://127.0.0.1:1/v1',)}):
        with pytest.raises(ValueError):read_keyless_loopback_catalog(base,**options)
    assert len(state['visits'])==2


@pytest.mark.parametrize('body,code',[
    (b'{"data":[],"data":[]}','PROVIDER_CATALOG_UNAVAILABLE'),
    (b'{"data":[{"id":"bad id"}]}','PROVIDER_CATALOG_MODEL_INVALID'),
    (b'x'*262145,'PROVIDER_CATALOG_BOUND'),
])
def test_local_catalog_rejects_invalid_or_oversized_data(catalog_server,body,code):
    base,state=catalog_server;state['body']=body
    with pytest.raises(ApiError,match=code):read(base)
    assert len(state['visits'])==1


def test_local_catalog_never_follows_redirect(catalog_server):
    base,state=catalog_server;state['status']=302
    with pytest.raises(CoreError,match='PROVIDER_REDIRECT_DENIED'):read(base)
    assert state['visits']==[('/v1/models',False)]


def test_keyless_catalog_matches_original_compatible_parser_for_same_response(catalog_server):
    from types import SimpleNamespace
    from nana_core.life.live_api.provider_models import read_catalog
    base,state=catalog_server
    profile=SimpleNamespace(protocol='OPENAI_COMPATIBLE_CHAT',base_url=base)
    original=read_catalog(profile,'SYNTHETIC_FIXTURE_CREDENTIAL')
    candidate=read(base)
    assert {'models':candidate['models'],'truncated':candidate['truncated']}==original
    assert state['visits']==[('/v1/models',True),('/v1/models',False)]
    assert candidate['inference_calls']==0 and candidate['qualification']=='NOT_ESTABLISHED'


def test_keyless_catalog_and_original_session_share_one_authorized_endpoint(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionBudget,CognitionSession
    from nana_core.continuity.world_loop.harness import provider_harness
    from tests.world_loop.helpers import capture,fresh,policy
    from tools.nana_next_experience.experiments.keyless_loopback_prototype import KeylessLoopbackPrototype
    import urllib.request

    with provider_harness() as (upstream,upstream_metrics),fresh(tmp_path/'subject.db') as runtime:
        seen=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,body):
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def do_GET(self):
                seen.append((self.path,'Authorization' in self.headers))
                assert self.path=='/v1/models'
                self.reply(b'{"data":[{"id":"harness-v1"}]}')
            def do_POST(self):
                seen.append((self.path,'Authorization' in self.headers))
                assert self.path=='/v1/chat/completions'
                length=int(self.headers['Content-Length'])
                request=urllib.request.Request(upstream.endpoint,data=self.rfile.read(length),
                    headers={'Content-Type':'application/json'},method='POST')
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=5) as response:
                    self.reply(response.read(131073))
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);worker.start()
        try:
            base=f'http://127.0.0.1:{server.server_port}/v1'
            catalog=read(base);assert catalog['models']==['harness-v1'] and catalog['inference_calls']==0
            port=KeylessLoopbackPrototype(base,catalog['models'][0],provider_id='local.fixture',
                                         explicit_authorized=True,allowed_bases=(base,))
            identity=runtime.identity_id;mid=capture(runtime,'source',{'data':'synthetic context'})
            session=CognitionSession(runtime,port,policy())
            request=session.prepare('local-catalog','INTERPRET',(mid,),budget=CognitionBudget(cost_ceiling_micro=1))
            assert session.execute(request)['state']=='PROPOSED'
            assert session.execute(request)['replayed'] and runtime.identity_id==identity
            assert runtime.store.one('cognitive_requests',request)['actual_cost_micro'] is None
            assert seen==[('/v1/models',False),('/v1/chat/completions',False)]
            assert upstream_metrics['calls']==1 and not runtime.store.all('actions') and not runtime.store.all('grants')
        finally:server.shutdown();server.server_close();worker.join(2)


def test_port_allowlist_does_not_authenticate_replacement_service():
    """An unchanged allowed URL can point at a replacement local service later."""
    def make_server(port,model):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                body=json.dumps({'data':[{'id':model}]}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
        worker=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True)
        worker.start();return server,worker
    first,worker=make_server(0,'original.fixture');port=first.server_port
    base=f'http://127.0.0.1:{port}/v1'
    try:assert read(base)['models']==['original.fixture']
    finally:first.shutdown();first.server_close();worker.join(2)
    replacement,worker=make_server(port,'replacement.fixture')
    try:
        assert read(base)['models']==['replacement.fixture']
        assert read(base)['qualification']=='NOT_ESTABLISHED'
    finally:replacement.shutdown();replacement.server_close();worker.join(2)
