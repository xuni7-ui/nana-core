"""Offline response compatibility; never a live provider or model quality claim."""
import copy,json
import pytest
from nana_core.storage import canonical
from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport,CognitionSession,CognitionBudget,CognitionRequest,StructuredProposal
from tests.world_loop.helpers import fresh,capture,policy
from tests.h1_live_semantics.test_wire import Response,Opener


def make_request(r):
    mid=capture(r,'response-source',{'project':'public synthetic note'})
    port=OpenAIJSONTransport('https://api.deepseek.com/chat/completions','deepseek-flash',provider_id='synthetic.response-wire',credential='TEST_ONLY_NOT_SECRET')
    session=CognitionSession(r,port,policy())
    cid=session.prepare('response-once','INTERPRET',(mid,),budget=CognitionBudget(cost_ceiling_micro=50000))
    req=CognitionRequest.model_validate_json(canonical(session.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']))
    return port,session,req


def envelope():
    return {'id':'synthetic-response-id','object':'chat.completion','created':1792560000,'model':'deepseek-flash','choices':[{'index':0,'message':{'role':'assistant','content':canonical({'interpretation':'A synthetic sourced proposal, not a fact or permission','uncertainty':'UNKNOWN','confidence':.4})},'finish_reason':'stop'}],'usage':{'prompt_tokens':8,'completion_tokens':4}}


@pytest.mark.parametrize('variant',['canonical','deepseek','optional-omitted','nullable','vendor-extra','text-blocks','usage-absent'])
def test_valid_envelope_differences_do_not_relax_semantic_contract(tmp_path,variant):
    with fresh(tmp_path/'subject/self.db') as r:
        port,session,req=make_request(r);body=envelope();msg=body['choices'][0]['message']
        if variant=='deepseek':msg['reasoning_content']=None;body['usage'].update(prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=8)
        if variant=='optional-omitted':
            for key in ('id','object','created'):body.pop(key)
            msg.pop('role') # legacy single-choice compatible implicit assistant
        if variant=='nullable':msg['refusal']=None;body['usage']=None
        if variant=='vendor-extra':body['vendor_note']='TEST_ONLY_NOT_SECRET_VENDOR';msg['annotations']=[]
        if variant=='text-blocks':
            old=copy.deepcopy(body)
            msg['content']=[{'type':'text','text':msg['content']}]
            # Exact old code path reproduces a *synthetic* known incompatibility.
            from nana_core.continuity.world_loop.cognition import strict_json
            with pytest.raises(TypeError):strict_json(msg['content'])
        if variant=='usage-absent':body.pop('usage')
        port.opener=Opener(Response(canonical(body).encode()));out=session.execute(req.request_id)
        assert out['state']=='PROPOSED' and len(port.opener.requests)==1
        assert port.last_parse_diagnostic.stage=='COMPLETE'
        assert port.last_parse_diagnostic.json_valid and port.last_parse_diagnostic.strict_schema_valid
        assert not r.store.all('actions') and not r.store.all('grants')
        assert session.execute(req.request_id)['replayed'] and len(port.opener.requests)==1


@pytest.mark.parametrize('variant,stage,code',[
 ('top-array','ENVELOPE','PROVIDER_MALFORMED'),('missing-message','MESSAGE','PROVIDER_MALFORMED'),
 ('duplicate-json','OUTER_JSON','PROVIDER_MALFORMED'),('truncated-json','OUTER_JSON','PROVIDER_MALFORMED'),
 ('missing-semantic','SEMANTIC_SCHEMA','PROVIDER_MALFORMED'),
 ('choices-empty','CHOICES','PROVIDER_MALFORMED'),('choices-object','CHOICES','PROVIDER_MALFORMED'),
 ('role-user','MESSAGE','PROVIDER_MALFORMED'),('content-number','CONTENT','PROVIDER_MALFORMED'),
 ('content-null','CONTENT','PROVIDER_MALFORMED'),('bad-json','SEMANTIC_JSON','PROVIDER_MALFORMED'),
 ('wrong-enum','SEMANTIC_SCHEMA','PROVIDER_MALFORMED'),('extra-authority','SEMANTIC_SCHEMA','PROVIDER_MALFORMED'),
 ('numeric-string','SEMANTIC_SCHEMA','PROVIDER_MALFORMED'),('usage-string','USAGE','PROVIDER_MALFORMED'),
 ('tool-calls','FINISH','PROVIDER_PARTIAL_OUTPUT'),('length','FINISH','PROVIDER_PARTIAL_OUTPUT')])
def test_negative_diagnostics_are_structural_durable_and_no_replay(tmp_path,variant,stage,code):
    with fresh(tmp_path/'subject/self.db') as r:
        port,session,req=make_request(r);body=envelope();msg=body['choices'][0]['message'];secret='TEST_ONLY_NOT_SECRET_PRIVATE_PROSE'
        payload=json.loads(msg['content'])
        if variant=='missing-message':body['choices'][0].pop('message')
        if variant=='missing-semantic':payload.pop('interpretation');msg['content']=canonical(payload)
        if variant=='choices-empty':body['choices']=[]
        if variant=='choices-object':body['choices']={}
        if variant=='role-user':msg['role']='user'
        if variant=='content-number':msg['content']=12
        if variant=='content-null':msg['content']=None
        if variant=='bad-json':msg['content']='{'+secret
        if variant=='wrong-enum':payload['uncertainty']=secret
        if variant=='extra-authority':payload[secret]={'grant':True}
        if variant=='numeric-string':payload['confidence']='0.4'
        if variant in {'wrong-enum','extra-authority','numeric-string'}:msg['content']=canonical(payload)
        if variant=='usage-string':body['usage']['prompt_tokens']=secret
        if variant=='tool-calls':body['choices'][0]['finish_reason']='tool_calls';msg['content']=None
        if variant=='length':body['choices'][0]['finish_reason']='length'
        raw=canonical(body).encode()
        if variant=='top-array':raw=b'[]'
        if variant=='duplicate-json':raw=b'{"choices":[],"choices":[]}'
        if variant=='truncated-json':raw=raw[:-3]
        port.opener=Opener(Response(raw));out=session.execute(req.request_id)
        assert out['state']=='FAILED' and out['error_code']==code and len(port.opener.requests)==1
        diag=port.last_parse_diagnostic
        assert diag.stage==stage and diag.issues
        if variant=='extra-authority':assert diag.issues[0].actual_type=='OBJECT' and '$unknown' in diag.issues[0].path
        assert secret not in diag.model_dump_json() and '0.4' not in diag.model_dump_json()
        terminal=r.store.db.execute("SELECT data_json FROM events WHERE kind='world.cognition_terminal' ORDER BY seq DESC LIMIT 1").fetchone()[0]
        assert secret not in terminal and 'parser_diagnostic' in terminal and 'raw_response_body_sha256' in terminal
        assert session.execute(req.request_id)['replayed'] and len(port.opener.requests)==1
        if variant in {'length','tool-calls'}:assert diag.openai_shape_valid
        assert not r.store.all('actions') and not r.store.all('grants')


def test_model_mismatch_stays_core_correlation_rejection(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        port,session,req=make_request(r);body=envelope();body['model']='another-model'
        port.opener=Opener(Response(canonical(body).encode()));out=session.execute(req.request_id)
        assert out['state']=='REJECTED' and out['error_code']=='CORRELATION_MISMATCH'
        assert not port.last_parse_diagnostic.model_matches_request
        assert not r.store.all('actions') and not r.store.all('grants')


def test_outer_json_and_timeout_diagnostic_do_not_reuse_previous_result(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        port,session,req=make_request(r)
        port.opener=Opener(Response(b'{'))
        out=session.execute(req.request_id)
        assert out['state']=='FAILED' and port.last_parse_diagnostic.stage=='OUTER_JSON'
        assert port.last_parse_diagnostic.json_valid is False
        assert port.last_parse_diagnostic.issues[0].path=='$'
        # Independent request, not replay/retry of the failed attempt.
        mid=capture(r,'second-source',{'public':'independent test'})
        second=session.prepare('independent-timeout','INTERPRET',(mid,),budget=CognitionBudget(cost_ceiling_micro=50000))
        class Timeout:
            def open(self,*args,**kwargs):raise TimeoutError()
        port.opener=Timeout();out=session.execute(second)
        assert out['state']=='UNKNOWN' and out['error_code']=='PROVIDER_TIMEOUT_BILLING_UNKNOWN'
        assert port.last_parse_request_id==second and port.last_parse_diagnostic.stage=='HTTP'
        assert port.last_parse_diagnostic.json_valid is None and not port.last_parse_diagnostic.issues
        assert port.last_response_metadata is None
        assert session.execute(second)['replayed']


def test_new_iteration_keys_use_same_subject_and_never_replay_old_source(tmp_path):
    from uuid import uuid4
    from tools.nana_first_life_integration.dev import initialize
    from tools.nana_first_life_integration.live_review import semantic
    from nana_core.life.config import load_config,update_config
    from nana_core.life.application import LifeApplication
    from nana_core.continuity.world_loop.harness import provider_harness
    home=tmp_path/'life';initialize(home)
    cfg=load_config(home);update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'provider_cost_ceiling_micro':50000}),expected_revision=cfg.revision)
    first,second=str(uuid4()),str(uuid4())
    with provider_harness() as (transport,metrics),LifeApplication(home) as app:
        session=CognitionSession(app.runtime,transport,app.policy);app._session=lambda privacy:session
        a=semantic(app,attempt_id=first);b=semantic(app,attempt_id=second)
        assert metrics['calls']==2 and a['request_id']!=b['request_id']
        assert a['identity_id']==b['identity_id']==app.runtime.identity_id
        assert a['qualification']=='SYNTHETIC_SEMANTIC_INTEGRATION_PASS'
        # Topic retirement/dedup is Subject policy, not a parser defect. A fresh
        # request ID must not force a second motive for the same retired topic.
        assert b['state']=='PROPOSED' and b['qualification']=='PARTIAL_NO_ELIGIBLE_CONCERN_NO_SECOND_CALL'
        with pytest.raises(CoreError,match='SOURCE_ALREADY_EXISTS_NO_REPLAY'):semantic(app,attempt_id=first)
        assert metrics['calls']==2 and len(app.runtime.store.all('cognitive_requests'))==2
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_live_binding_accepts_memory_pipe_but_never_reads_disk_credential(tmp_path,monkeypatch):
    import os
    from tools.nana_first_life_live_response.attempt import resolver_from_fd
    from tools.nana_first_life_integration.live_review import REF
    disk=tmp_path/'synthetic-input';disk.write_text('TEST_ONLY_NOT_SECRET_FILE_DENIED')
    fd=os.open(disk,os.O_RDONLY)
    try:
        with monkeypatch.context() as m:
            m.setattr(os,'read',lambda *args:(_ for _ in ()).throw(AssertionError('DISK_CREDENTIAL_READ')))
            with pytest.raises(CoreError,match='MEMORY_PIPE_FD_REQUIRED'):resolver_from_fd(fd)
    finally:os.close(fd)
    left,right=os.pipe();os.write(right,b'TEST_ONLY_NOT_SECRET_MEMORY_PIPE');os.close(right)
    try:resolver=resolver_from_fd(left)
    finally:os.close(left)
    assert resolver.available(REF) and 'TEST_ONLY_NOT_SECRET_MEMORY_PIPE' not in repr(resolver)
    resolver.clear();assert not resolver.available(REF)
