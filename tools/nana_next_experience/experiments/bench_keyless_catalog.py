"""Reproducible same-response local catalog timing; no external model or billing."""
import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import statistics
import threading
import time
from types import SimpleNamespace

from nana_core.life.live_api.provider_models import read_catalog
from tools.nana_next_experience.experiments.keyless_loopback_catalog import read_keyless_loopback_catalog


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rounds',type=int,default=60)
    rounds=parser.parse_args().rounds
    if not 1<=rounds<=1000:raise ValueError('rounds must be 1..1000')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            body=b'{"data":[{"id":"model.a"},{"id":"model.b"}]}'
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}/v1'
    profile=SimpleNamespace(protocol='OPENAI_COMPATIBLE_CHAT',base_url=base)
    functions={'original':lambda:read_catalog(profile,'SYNTHETIC_FIXTURE_CREDENTIAL'),
               'candidate':lambda:read_keyless_loopback_catalog(base,explicit_authorized=True,allowed_bases=(base,))}
    samples={name:[] for name in functions};cpu=time.process_time()
    try:
        for turn in range(rounds):
            for name in (('original','candidate') if turn%2==0 else ('candidate','original')):
                start=time.perf_counter();result=functions[name]()
                samples[name].append((time.perf_counter()-start)*1000)
                if result['models']!=['model.a','model.b'] or result['truncated']:
                    raise RuntimeError('catalog output differs')
    finally:server.shutdown();server.server_close();thread.join(2)
    def metrics(values):
        ordered=sorted(values)
        return {'median_ms':statistics.median(ordered),'p95_ms':ordered[max(0,(95*len(ordered)+99)//100-1)]}
    print(json.dumps({'rounds_per_side':rounds,'original':metrics(samples['original']),
        'candidate':metrics(samples['candidate']),'process_and_fixture_cpu_seconds':time.process_time()-cpu,
        'scope':'tiny loopback synthetic response; no real provider, inference or token billing'},indent=2))


if __name__=='__main__':main()
