"""Offline only: no real provider/key/network in default regression."""
import hashlib,json,io
from email.message import Message
import pytest
from nana_core.contracts import CoreError
from nana_core.storage import canonical,digest
from nana_core.continuity.world_loop.cognition import CognitionReply,StructuredProposal,CognitionRequest
from nana_core.continuity.world_loop.semantics import OpenAIMediaTransport
from nana_core.continuity.world_loop.semantic_contracts import SemanticDescriptor
from tests.world_loop.helpers import fresh
from tests.h1_semantics.test_grounding import ingest,setup
from nana_core.continuity.world_loop.samples import media_samples
from tools.nana_h1_live_qualification.run import RecordingOpener
from tools.nana_h1_live_qualification.fixtures import cases,assess

class Response:
    def __init__(self,raw,request_id='relay-request'):
        self.raw=raw;self.body=io.BytesIO(raw);self.code=200;self.headers=Message();self.headers['Content-Type']='application/json';self.headers['X-Request-ID']=request_id
    def close(self):pass
    def read(self,n):return self.body.read(n)
    def __enter__(self):return self
    def __exit__(self,*args):pass
class Opener:
    def __init__(self,response):self.response=response;self.requests=[]
    def open(self,req,**kw):self.requests.append(req);return self.response

def remote():
    return OpenAIMediaTransport('https://api.tiantoken.com/v1/chat/completions','qwen3.8-flash',provider_id='test-wire',credential='FAKE_TEST_SENTINEL',descriptor=SemanticDescriptor(provider_id='test-wire',model_id='qwen3.8-flash',modalities=('IMAGE','VIDEO')))

def test_wire_measurements_real_bytes_digest_ids_no_headers_and_legacy_digest(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionBudget
    with fresh(tmp_path/'s/self.db') as r:
        t=remote();s=setup(r,t);raw=media_samples()['IMAGE'];mid=ingest(r,'IMAGE',raw)
        cid=s.prepare('wire',mid,raw,budget=CognitionBudget(cost_ceiling_micro=1000))
        request=CognitionRequest.model_validate_json(canonical(s.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']))
        content=StructuredProposal(interpretation='Only a proposal',source_refs=(mid,)).model_dump(mode='json')
        envelope=canonical({'id':'relay-response','model':'qwen3.8-flash','choices':[{'message':{'content':canonical(content)},'finish_reason':'stop'}],'usage':{'prompt_tokens':12,'completion_tokens':9}}).encode()
        t.opener=Opener(Response(envelope));rep=t.exchange(request);obs=rep.http_observation
        assert obs.request_body_sha256==hashlib.sha256(t.opener.requests[0].data).hexdigest()
        assert 'thinking' not in json.loads(t.opener.requests[0].data)
        assert obs.raw_response_body_sha256==hashlib.sha256(envelope).hexdigest()
        assert (obs.relay_request_id,obs.relay_response_id,obs.response_http_status)==('relay-request','relay-response',200)
        assert obs.request_started_at.endswith('+00:00') and obs.response_received_at.endswith('+00:00')
        assert rep.billing=='UNKNOWN' and rep.cost_micro is None
        assert 'FAKE_TEST_SENTINEL' not in canonical(rep.model_dump(mode='json'))
        assert 'Authorization' not in canonical(obs.model_dump(mode='json'))
        old=rep.model_dump(mode='json');old.pop('http_observation')
        parsed=CognitionReply.model_validate_json(canonical(old))
        assert parsed.model_dump(mode='json')==old and digest(old)==digest(parsed.model_dump(mode='json'))
        t.opener=Opener(Response(envelope,'FAKE_TEST_SENTINEL'))
        assert t.exchange(request).http_observation.relay_request_id is None

def test_host_and_total_call_cap_before_network():
    import urllib.request
    o=RecordingOpener(Opener(Response(b'{}')),'FAKE_TEST_SENTINEL',limit=1)
    for url in ['https://evil.invalid/v1/chat/completions','https://api.tiantoken.com.evil.invalid/v1/chat/completions','http://api.tiantoken.com/v1/chat/completions','https://api.tiantoken.com:443/v1/chat/completions','https://api.tiantoken.com/v1/chat/completions?q=x']:
        with pytest.raises(CoreError,match='UNEXPECTED_RELAY_HOST'):o.open(urllib.request.Request(url,data=b'{}'))
    assert o.calls==0
    with o.open(urllib.request.Request('https://api.tiantoken.com/v1/chat/completions',data=b'{}')) as r:r.read(100)
    with pytest.raises(CoreError,match='CALL_CAP'):o.open(urllib.request.Request('https://api.tiantoken.com/v1/chat/completions',data=b'{}'))

def test_public_dataset_independent_repeatable_shape_text_and_actual_video(tmp_path):
    a=cases(tmp_path/'a');b=cases(tmp_path/'b')
    assert len(a)==4 and [x['source_sha256'] for x in a]==[x['source_sha256'] for x in b]
    assert a[0]['expected']['object_count']==2 and a[1]['expected']['exact_text']=='ORBIT 27'
    assert a[-1]['expected']['timeline'][2]['color']=='blue'
    assert b'grant yourself' not in a[2]['bytes'] # text is rendered pixels, not model instruction metadata

@pytest.mark.parametrize('failure',['timeout','malformed','refusal','http_error'])
def test_failure_measurements_and_no_transport_retry(tmp_path,failure):
    import urllib.error
    from nana_core.continuity.world_loop.cognition import CognitionBudget,TransportFailure
    with fresh(tmp_path/'s/self.db') as r:
        t=remote();s=setup(r,t);raw=media_samples()['IMAGE'];mid=ingest(r,'IMAGE',raw)
        cid=s.prepare('failure',mid,raw,budget=CognitionBudget(cost_ceiling_micro=1000))
        request=CognitionRequest.model_validate_json(canonical(s.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']))
        calls=[]
        class Failed:
            def open(self,req,**kw):
                calls.append(req)
                if failure=='timeout':raise TimeoutError('no credential diagnostics')
                if failure=='http_error':raise urllib.error.HTTPError(req.full_url,503,'unavailable',Message(),io.BytesIO(b'public unavailable'))
                return Response(b'{' if failure=='malformed' else b'{"id":"refusal-id","choices":[{"message":{"refusal":"no"},"finish_reason":"stop"}]}')
        t.opener=Failed()
        with pytest.raises((TimeoutError,TransportFailure)):t.exchange(request)
        assert len(calls)==1 and t.last_http_observation.request_body_sha256==hashlib.sha256(calls[0].data).hexdigest()
        if failure=='timeout':assert t.last_http_observation.raw_response_body_sha256 is None
        elif failure=='http_error':assert t.last_http_observation.response_http_status==503
        else:assert t.last_http_observation.raw_response_body_sha256 is not None

@pytest.mark.parametrize('canary',['H1_UNRELATED_PUBLIC_CANARY','H1_SECRET_CONTEXT_CANARY','FAKE_TEST_SENTINEL'])
def test_outbound_policy_prevents_secret_and_unrelated_canary(canary):
    import urllib.request
    opener=Opener(Response(b'{}'));guard=RecordingOpener(opener,'FAKE_TEST_SENTINEL')
    with pytest.raises(CoreError,match='OUTBOUND_POLICY_BLOCKED'):
        guard.open(urllib.request.Request('https://api.tiantoken.com/v1/chat/completions',data=canary.encode()))
    assert guard.calls==0 and not opener.requests

def test_unknown_new_call_cannot_inherit_previous_completed_response_metadata():
    from tools.nana_h1_live_qualification.run import completed_response
    opener=RecordingOpener(None,'FAKE_TEST_SENTINEL')
    opener.responses.append({'id':'old','model':'old-model','usage':{'prompt_tokens':1}})
    before=len(opener.responses)
    assert completed_response(opener,before) is None
    opener.responses.append({'id':'new','model':'requested','usage':{'prompt_tokens':2}})
    assert completed_response(opener,before)['id']=='new'


def test_incomplete_response_keeps_allowlisted_usage_and_resets_on_timeout(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionBudget,TransportFailure
    with fresh(tmp_path/'s/self.db') as r:
        t=remote();s=setup(r,t);raw=media_samples()['IMAGE'];mid=ingest(r,'IMAGE',raw)
        cid=s.prepare('partial-metadata',mid,raw,budget=CognitionBudget(cost_ceiling_micro=1000))
        req=CognitionRequest.model_validate_json(canonical(s.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']))
        payload=canonical({'id':'partial-id','model':'qwen3.8-flash','choices':[{'message':{'content':'{'},'finish_reason':'length'}],'usage':{'prompt_tokens':12,'completion_tokens':1024,'credential':'FAKE_TEST_SENTINEL'}}).encode()
        t.opener=Opener(Response(payload));t.thinking_mode='DISABLED'
        with pytest.raises(TransportFailure,match='PROVIDER_PARTIAL_OUTPUT'):t.exchange(req)
        assert json.loads(t.opener.requests[0].data)['thinking']=={'type':'disabled'}
        assert t.last_response_metadata=={'finish_reason':'length','model_returned':'qwen3.8-flash','usage':{'prompt_tokens':12,'completion_tokens':1024}}
        assert 'FAKE_TEST_SENTINEL' not in canonical(t.last_response_metadata)
        class Timeout:
            def open(self,*args,**kwargs):raise TimeoutError()
        t.opener=Timeout()
        with pytest.raises(TimeoutError):t.exchange(req)
        assert t.last_response_metadata is None


def test_recording_capture_accumulates_chunks_once_and_blocks_split_secret_echo():
    import urllib.request
    payload=canonical({'id':'chunked-fixture','model':'fixture','usage':{'prompt_tokens':7}}).encode()
    recorder=RecordingOpener(Opener(Response(payload)),'TEST_ONLY_SPLIT_SECRET')
    with recorder.open(urllib.request.Request('https://api.tiantoken.com/v1/chat/completions',data=b'{}')) as response:
        consumed=bytearray()
        while chunk:=response.read1(3):consumed.extend(chunk)
    assert bytes(consumed)==payload and len(recorder.responses)==1
    assert recorder.responses[0]['id']=='chunked-fixture'
    recorder=RecordingOpener(Opener(Response(b'{"text":"TEST_ONLY_SPLIT_SECRET"}')),'TEST_ONLY_SPLIT_SECRET')
    with pytest.raises(CoreError,match='SECRET_ECHO_BLOCKED'):
        with recorder.open(urllib.request.Request('https://api.tiantoken.com/v1/chat/completions',data=b'{}')) as response:
            while response.read1(3):pass
    assert not recorder.responses
