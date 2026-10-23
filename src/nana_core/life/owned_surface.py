"""Explicit owned localhost input transport. No C, Store or delivery authority.

Only the original owner drains ingress. HTTP202 is volatile admission, never a
judgment or durable receipt. The random per-process admission nonce is held only
in this handle and request headers; it is not a provider credential or Grant.
"""
import hmac
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from ..contracts import CoreError
from .surfaces import SurfaceObservation


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class OwnedSurfaceBridge:
    def __init__(self,app,*,bindings):
        # Binding and priority are trusted application construction, not payload.
        if not bindings or len(bindings)>8 or any(v not in {'USER','BACKGROUND'} for v in bindings.values()):raise CoreError('SURFACE_BRIDGE_BINDINGS')
        for key in bindings:app.surfaces._binding(key)
        priorities=dict(bindings);nonce=secrets.token_urlsafe(32);ingress=app.ingress
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def setup(self):
                super().setup();self.connection.settimeout(1)
            def reply(self,status,value):
                body=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def do_POST(self):
                if self.path!='/observe':return self.reply(404,{'error':'SURFACE_ENDPOINT'})
                supplied=self.headers.get('X-Nana-Owned-Session','')
                if not hmac.compare_digest(supplied.encode(),nonce.encode()):return self.reply(403,{'error':'SURFACE_SESSION_DENIED'})
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    if not 1<=n<=8192 or self.headers.get('Transfer-Encoding'):raise ValueError()
                    observation=SurfaceObservation.model_validate_json(self.rfile.read(n))
                    if observation.binding_id not in priorities:return self.reply(403,{'error':'SURFACE_BINDING_DENIED'})
                    result=ingress.offer(observation,urgency=priorities[observation.binding_id])
                except CoreError as exc:
                    return self.reply(409,{'error':str(exc)[:96]})
                except (ValueError,TimeoutError,OSError):return self.reply(400,{'error':'SURFACE_INPUT_INVALID'})
                return self.reply(202,result)
        class Server(ThreadingHTTPServer):
            # Bound concurrent HTTP handlers separately from bounded Core inbox.
            daemon_threads=True
            def __init__(self,*args,**kwargs):self.slots=threading.BoundedSemaphore(4);super().__init__(*args,**kwargs)
            def process_request(self,request,address):
                if not self.slots.acquire(False):self.shutdown_request(request);return
                try:super().process_request(request,address)
                except BaseException:self.slots.release();raise
            def process_request_thread(self,request,address):
                try:super().process_request_thread(request,address)
                finally:self.slots.release()
        self._server=Server(('127.0.0.1',0),Handler);self._nonce=nonce
        self.url='http://127.0.0.1:'+str(self._server.server_port)+'/observe'
        self._thread=threading.Thread(target=self._server.serve_forever,kwargs={'poll_interval':.1},daemon=True);self._thread.start()
    def __repr__(self):return '<OwnedSurfaceBridge localhost input-only>'
    def post(self,observation):
        if type(observation) is not SurfaceObservation:raise CoreError('SURFACE_TYPED_INPUT_REQUIRED')
        request=Request(self.url,data=observation.model_dump_json().encode(),headers={'Content-Type':'application/json','X-Nana-Owned-Session':self._nonce},method='POST')
        # One attempt; no inherited proxy, redirect or retry. Network ambiguity
        # is not an invitation to resend a volatile input with a new event ID.
        with build_opener(ProxyHandler({}),_NoRedirect()).open(request,timeout=2) as response:
            return json.loads(response.read(2048))
    def close(self):
        self._server.shutdown();self._server.server_close();self._thread.join(2);self._nonce=''
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def social_observations(payload,*,binding_id):
    """Bounded synthetic social service events; no role/authority promotion."""
    if not isinstance(payload,dict) or not isinstance(payload.get('messages'),list) or len(payload['messages'])>16:raise CoreError('SOCIAL_EVENT_BOUND')
    result=[]
    for message in payload['messages']:
        if not isinstance(message,dict) or set(message)-{'message_id','thread_id','text','occurred_at_us','sequence','duplicate_delivery','quiet_period'}:raise CoreError('SOCIAL_EVENT_INVALID')
        try:result.append(SurfaceObservation(binding_id=binding_id,event_id='owned-social:'+str(message['message_id']),thread_id=message['thread_id'],topic='lab-life',text=message['text'],occurred_at_us=message.get('occurred_at_us')))
        except (KeyError,ValueError) as exc:raise CoreError('SOCIAL_EVENT_INVALID') from None
    return tuple(result)
