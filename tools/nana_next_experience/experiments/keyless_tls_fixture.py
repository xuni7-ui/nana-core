"""Owned HTTPS loopback fixture for evaluating existing keyless Provider wire.

This is a research fixture, not a Provider factory or user-facing integration.
It uses a temporary test certificate and never accesses a real model or account.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import urllib.request

from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport,_NoRedirect
from nana_core.continuity.world_loop.harness import provider_harness


@contextmanager
def keyless_tls_fixture(*,delay=0):
    """Yield an original transport and local fixture metrics; verify TLS normally."""
    with tempfile.TemporaryDirectory(prefix='nana-keyless-tls-') as directory, provider_harness(delay=delay) as (upstream,upstream_metrics):
        root=Path(directory);certificate=root/'certificate.pem';key=root/'fixture-key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
            '-keyout',str(key),'-out',str(certificate),'-subj','/CN=127.0.0.1',
            '-addext','subjectAltName=IP:127.0.0.1'],stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=20)
        metrics={'requests':0,'authorization_header_present':False}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                try:
                    metrics['requests']+=1
                    if self.headers.get('Authorization') is not None:
                        metrics['authorization_header_present']=True;self.send_error(403);return
                    length=int(self.headers.get('Content-Length','0'))
                    if self.path!='/v1/chat/completions' or not 1<=length<=196608:
                        self.send_error(400);return
                    request=urllib.request.Request(upstream.endpoint,data=self.rfile.read(length),
                        headers={'Content-Type':'application/json'},method='POST')
                    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    with opener.open(request,timeout=5) as response:body=response.read(131073)
                    if len(body)>131072:self.send_error(502);return
                    self.send_response(200);self.send_header('Content-Type','application/json')
                    self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                except (BrokenPipeError,ConnectionResetError,TimeoutError):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(certificate,key)
        server.socket=context.wrap_socket(server.socket,server_side=True)
        worker=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);worker.start()
        endpoint=f'https://127.0.0.1:{server.server_port}/v1/chat/completions'
        port=OpenAIJSONTransport(endpoint,'harness-v1',provider_id='local.tls-fixture',credential=None)
        trust=ssl.create_default_context(cafile=str(certificate))
        port.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=trust),_NoRedirect())
        try:yield port,upstream,metrics,upstream_metrics
        finally:server.shutdown();server.server_close();worker.join(2)
