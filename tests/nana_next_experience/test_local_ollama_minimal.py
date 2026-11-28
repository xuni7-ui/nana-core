"""Official Ollama SDK against a loopback protocol fixture; not real inference."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import threading

import pytest

pytest.importorskip('ollama')
from tools.nana_next_experience.experiments.local_ollama import LocalOllama


@pytest.fixture
def server():
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def send(self,body,content_type='application/json'):
            self.send_response(200);self.send_header('Content-Type',content_type)
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            requests.append((self.path,self.headers.get('Authorization'),None))
            self.send(json.dumps({'models':[{'name':'_fixture:latest','model':'_fixture:latest','size':1}]}).encode())
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append((self.path,self.headers.get('Authorization'),body))
            def event(text,done):return {'model':body['model'],'message':{'role':'assistant','content':text},'done':done}
            if body['stream']:
                self.send(('\n'.join(json.dumps(event(s,done)) for s,done in [('hello',False),(' world',False),('',True)])+'\n').encode(),'application/x-ndjson')
            else:self.send(json.dumps(event('fixture reply',True)).encode())
    http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{http.server_port}',requests
    finally:http.shutdown();http.server_close();thread.join()


def test_official_sdk_discovers_and_chats_without_leaking_environment_key(server,monkeypatch):
    host,requests=server;monkeypatch.setenv('OLLAMA_API_KEY','SYNTHETIC_NOT_A_SECRET')
    with LocalOllama(host) as client:
        assert client.models()==['_fixture:latest']
        response=client.chat('_fixture:latest','hello')
        assert response.message.content=='fixture reply' and response.done is True
        chunks=list(client.chat('_fixture:latest','hello',stream=True))
        assert ''.join(c.message.content or '' for c in chunks)=='hello world' and chunks[-1].done is True
    assert [p for p,_,_ in requests]==['/api/tags','/api/chat','/api/chat']
    assert all(auth is None for _,auth,_ in requests)
    assert [r[2]['stream'] for r in requests[1:]]==[False,True]


@pytest.mark.parametrize('host',['https://127.0.0.1:11434','http://example.com:11434',
    'http://127.0.0.1:11434/path','http://user:password@127.0.0.1:11434',
    'http://127.0.0.1:11434?x=1','http://127.0.0.1','http://127.0.0.1:bad'])
def test_remote_or_ambiguous_origins_are_rejected(host):
    with pytest.raises(ValueError):LocalOllama(host)
