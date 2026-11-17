import shutil
import ssl
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import threading

import pytest
from pydantic import ValidationError

from nana_core.contracts import CoreError
from nana_core.continuity.provider_config import ProviderProfile
from nana_core.continuity.provider_routing import RuntimeProviderFactory,RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget
from tests.provider_routing.helpers import model
from tests.world_loop.helpers import fresh,policy,capture
from tools.nana_next_experience.experiments.keyless_tls_fixture import keyless_tls_fixture
from tools.nana_next_experience.experiments.keyless_loopback_prototype import KeylessLoopbackPrototype
from nana_core.continuity.world_loop.harness import provider_harness


pytestmark=pytest.mark.skipif(not shutil.which('openssl'),reason='optional local OpenSSL unavailable')


def test_existing_provider_config_rejects_keyless_before_dispatch():
    with pytest.raises(ValidationError):
        ProviderProfile(provider_profile_id='local.test',display_name='local',protocol='OPENAI_COMPATIBLE_CHAT',
                        locality='REMOTE',base_url='http://127.0.0.1:12345/v1')
    with pytest.raises(ValidationError):
        ProviderProfile(provider_profile_id='local.test',display_name='local',protocol='OPENAI_COMPATIBLE_CHAT',
                        locality='REMOTE',base_url='https://127.0.0.1:12345/v1')
    profile=ProviderProfile(provider_profile_id='local.test',display_name='local',protocol='OPENAI_COMPATIBLE_CHAT',
                            locality='REMOTE',base_url='https://local.example/v1')
    factory=RuntimeProviderFactory(ProviderRegistry(),None,
        RoutingPolicy(allow_remote=True,allowed_remote_hosts=('local.example',)))
    assert factory.secret_state(profile)=='UNCONFIGURED'
    with pytest.raises(CoreError,match='SECRET_UNAVAILABLE'):
        factory.available(profile,model('model.local','local.test'),'COGNITION')
    with pytest.raises(ValidationError):
        ProviderProfile.model_validate({**profile.model_dump(),'authentication':'NONE'})


def test_original_tls_transport_can_use_no_key_and_preserves_subject_and_ledger(tmp_path):
    with fresh(tmp_path/'subject.db') as runtime,keyless_tls_fixture() as (port,synthetic,metrics,upstream):
        identity=runtime.identity_id;mid=capture(runtime,'fixture-source',{'data':'synthetic context'})
        first=CognitionSession(runtime,synthetic,policy());first_id=first.prepare('fixture','INTERPRET',(mid,))
        assert first.execute(first_id)['state']=='PROPOSED'
        second=CognitionSession(runtime,port,policy())
        request=second.prepare('local-tls','INTERPRET',(mid,),budget=CognitionBudget(cost_ceiling_micro=1))
        assert second.execute(request)['state']=='PROPOSED'
        assert second.execute(request)['replayed'] and metrics['requests']==1 and upstream['calls']==2
        assert not metrics['authorization_header_present'] and runtime.identity_id==identity
        row=runtime.store.one('cognitive_requests',request)
        assert row['state']=='PROPOSED' and row['actual_cost_micro'] is None
        assert row['input_bytes']>0 and row['output_bytes']>0
        assert not runtime.store.all('actions') and not runtime.store.all('grants')


def test_timeout_does_not_repeat_keyless_tls_request(tmp_path):
    with fresh(tmp_path/'subject.db') as runtime,keyless_tls_fixture(delay=.25) as (port,_,metrics,upstream):
        mid=capture(runtime,'fixture-source',{'data':'synthetic context'})
        session=CognitionSession(runtime,port,policy())
        request=session.prepare('local-timeout','INTERPRET',(mid,),
            budget=CognitionBudget(timeout_ms=100,cost_ceiling_micro=1))
        assert session.execute(request)['state']=='UNKNOWN'
        time.sleep(.3)
        assert session.execute(request)['state']=='UNKNOWN'
        assert metrics['requests']==1 and upstream['calls']==1
        assert not metrics['authorization_header_present']


def test_untrusted_fixture_certificate_is_not_accepted():
    with keyless_tls_fixture() as (port,_,metrics,__):
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                          urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        with pytest.raises(urllib.error.URLError) as error:
            opener.open(port.endpoint,timeout=3)
        assert isinstance(error.value.reason,ssl.SSLCertVerificationError)
        assert metrics['requests']==0


def test_keyless_loopback_prototype_uses_original_session_and_rejects_untrusted_addresses(tmp_path):
    with fresh(tmp_path/'subject.db') as runtime,provider_harness() as (synthetic,metrics):
        base=synthetic.endpoint.removesuffix('/chat/completions')
        for candidate,authorized,allowed in [
            (base,False,(base,)),(base,'true',(base,)),(base,True,('http://127.0.0.1:1/v1',)),
            (base.replace('127.0.0.1','localhost'),True,(base.replace('127.0.0.1','localhost'),)),
            (base.replace('127.0.0.1','127.0.0.2'),True,(base.replace('127.0.0.1','127.0.0.2'),)),
            (base.replace('http:','https:'),True,(base.replace('http:','https:'),)),
            (base+'?secret=example',True,(base+'?secret=example',)),
            (base+'/../admin',True,(base+'/../admin',)),
            (base+'/x%2Fadmin',True,(base+'/x%2Fadmin',)),
        ]:
            with pytest.raises(ValueError):
                KeylessLoopbackPrototype(candidate,'harness-v1',provider_id='local.fixture',
                                         explicit_authorized=authorized,allowed_bases=allowed)
        port=KeylessLoopbackPrototype(base,'harness-v1',provider_id='local.fixture',
                                      explicit_authorized=True,allowed_bases=(base,))
        assert port.remote and not port.harness and 'Authorization' not in port.request_headers('fixture')
        identity=runtime.identity_id;mid=capture(runtime,'source',{'data':'synthetic context'})
        session=CognitionSession(runtime,port,policy())
        request=session.prepare('local-loopback','INTERPRET',(mid,),budget=CognitionBudget(cost_ceiling_micro=1))
        assert session.execute(request)['state']=='PROPOSED'
        assert session.execute(request)['replayed'] and metrics['calls']==1
        row=runtime.store.one('cognitive_requests',request)
        assert row['actual_cost_micro'] is None and row['input_bytes']>0 and runtime.identity_id==identity
        private=capture(runtime,'private',{'data':'synthetic private context'},privacy='PERSONAL')
        with pytest.raises(CoreError,match='DENIED'):
            session.prepare('local-private','INTERPRET',(private,),budget=CognitionBudget(cost_ceiling_micro=1))


def test_keyless_loopback_timeout_keeps_unknown_without_retry(tmp_path):
    with fresh(tmp_path/'subject.db') as runtime,provider_harness(delay=.25) as (synthetic,metrics):
        base=synthetic.endpoint.removesuffix('/chat/completions')
        port=KeylessLoopbackPrototype(base,'harness-v1',provider_id='local.fixture',
                                      explicit_authorized=True,allowed_bases=(base,))
        mid=capture(runtime,'source',{'data':'synthetic context'});session=CognitionSession(runtime,port,policy())
        request=session.prepare('local-timeout','INTERPRET',(mid,),
            budget=CognitionBudget(timeout_ms=100,cost_ceiling_micro=1))
        assert session.execute(request)['state']=='UNKNOWN'
        time.sleep(.3)
        assert session.execute(request)['state']=='UNKNOWN' and metrics['calls']==1


def test_keyless_loopback_never_follows_provider_redirect():
    visits=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            visits.append('post');self.send_response(302)
            self.send_header('Location',f'http://127.0.0.1:{self.server.server_port}/other')
            self.end_headers()
        def do_GET(self):visits.append('redirected');self.send_response(200);self.end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);worker.start()
    try:
        base=f'http://127.0.0.1:{server.server_port}/v1'
        port=KeylessLoopbackPrototype(base,'fixture',provider_id='local.fixture',
                                      explicit_authorized=True,allowed_bases=(base,))
        request=urllib.request.Request(port.endpoint,data=b'{}',method='POST')
        with pytest.raises(CoreError,match='PROVIDER_REDIRECT_DENIED'):port.opener.open(request,timeout=3)
        assert visits==['post']
    finally:server.shutdown();server.server_close();worker.join(2)
