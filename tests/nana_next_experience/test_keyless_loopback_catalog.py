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
