"""Metadata-only actual receipt accounting, not real provider qualification."""
import pytest
from nana_core.presence.resources import resource_state,_reported_usage_pair
from tests.independent_life.test_dialogue import relay
from nana_core.life.application import LifeApplication


@pytest.mark.parametrize('usage,expected',[
    ({'prompt_tokens':10,'completion_tokens':7,'total_tokens':17},(10,7)),
    ({'input_tokens':4,'output_tokens':0},(4,0)),
    ({'input_tokens':4,'prompt_tokens':4,'output_tokens':1,'completion_tokens':1},(4,1)),
    ({'input_tokens':4,'prompt_tokens':5,'output_tokens':1},None),
    ({'input_tokens':True,'output_tokens':1},None),
    ({'input_tokens':4,'output_tokens':1,'total_tokens':9},None),
    ({'prompt_tokens':8},None),(None,None),({},None),
])
def test_usage_aliases_missing_invalid_and_zero(usage,expected):
    assert _reported_usage_pair(usage)==expected


def test_original_receipts_report_fixture_separately_and_unknown_is_not_free(app,monkeypatch):
    home=app.home;clock=app.clock;app.close()
    with relay(home,'CHAT') as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as current:
            current.pause();answer=current.chat('SYNTHETIC usage sample',message_id='usage')
            assert answer['render_state']=='UNVERIFIED_MODEL_WORDING' and len(requests)==2
            state=resource_state(current.runtime.store,current.runtime.config)
            assert state.provider_reported_input_tokens is None and state.real_usage_reported_calls==0
            assert state.fixture_reported_input_tokens==20 and state.fixture_reported_output_tokens==20
            assert state.fixture_usage_reported_calls==2 and state.usage_missing_or_invalid_calls==0
            from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
            def timeout(*args):raise TimeoutError()
            monkeypatch.setattr(OpenAIJSONTransport,'exchange',timeout)
            current.chat('SYNTHETIC unresolved sample',message_id='usage-unknown')
            after=resource_state(current.runtime.store,current.runtime.config)
            assert after.usage_missing_or_invalid_calls==1 and after.unresolved_calls==1
            assert after.fixture_reported_input_tokens==20
            assert after.reserved_estimated_cost_micro>=state.reserved_estimated_cost_micro


def test_body_free_usage_survives_source_erasure_restart_and_replay_without_refund(app):
    from nana_core.continuity.accounting import PREFIX,decode_usage_receipt
    home=app.home;clock=app.clock;app.close()
    with relay(home,'CHAT') as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as current:
            current.pause();reply=current.chat('SYNTHETIC ERASE_USAGE_BODY_ONLY',message_id='erased-usage',retain_shared_life=True)
            assert reply['render_state']=='UNVERIFIED_MODEL_WORDING' and len(requests)==2
            before=resource_state(current.runtime.store,current.runtime.config)
            request_ids=[r['request_id'] for r in current.runtime.store.all('cognitive_requests')]
            for request_id in request_ids:
                saved=current.runtime.store.one('core_meta',PREFIX+request_id)
                assert decode_usage_receipt(saved['key'],saved['value_json'])
                assert 'ERASE_USAGE_BODY_ONLY' not in saved['value_json'] and 'model' not in saved['value_json']
            current.forget(reply['message_memory_id'])
            assert not current.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'ERASE_USAGE_BODY_ONLY')>0").fetchone()
            after=resource_state(current.runtime.store,current.runtime.config)
            assert after.fixture_reported_input_tokens==before.fixture_reported_input_tokens==20
            assert after.fixture_usage_reported_calls==2 and after.usage_missing_or_invalid_calls==0
            assert after.reserved_estimated_cost_micro==before.reserved_estimated_cost_micro
        with LifeApplication(home,clock=clock,router=router) as current:
            current.chat('SYNTHETIC do not replay',message_id='erased-usage')
            assert len(requests)==2
            after=resource_state(current.runtime.store,current.runtime.config)
            assert after.fixture_reported_input_tokens==20 and after.fixture_usage_reported_calls==2


def test_portable_accounting_metadata_rejects_unbound_or_extra_content(app):
    from nana_core.continuity.accounting import PREFIX,decode_usage_receipt,portable_usage_metadata
    from nana_core.storage import canonical
    value={'version':1,'request_id':'not-a-request','origin':'SYNTHETIC','input_tokens':2,'output_tokens':3}
    key=PREFIX+value['request_id']
    assert not portable_usage_metadata(app.runtime.store,{'key':key,'value_json':canonical(value)})
    assert decode_usage_receipt(key,canonical({**value,'text':'UNRETAINED_TEXT_MUST_NOT_EXPORT'})) is None
    assert decode_usage_receipt(key,'{"version":1,"version":1}') is None


def test_original_portability_keeps_only_bound_numeric_usage_and_drops_routine_checkpoint(app,tmp_path):
    import json,sqlite3,zipfile
    from uuid import uuid4
    from nana_core.continuity import ContinuityStore
    from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority,verify_package
    from nana_core.continuity.accounting import PREFIX
    from nana_core.storage import canonical
    home=app.home;clock=app.clock;identity=app.runtime.identity_id;app.close()
    with relay(home,'CHAT') as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as current:
            current.pause();current.chat('SYNTHETIC portable usage',message_id='portable-usage')
            assert len(requests)==2
            # Same reconstructible operational metadata used by the runtime;
            # never a new Subject fact or an event containing a host path.
            current.runtime.store._put('core_meta',{'key':'runtime.routine_review','value_json':canonical({'pending':False,'checks':1,'as_of_us':current.runtime.clock.utc_now_us(),'authority':False})})
    authority=PortableTransferAuthority();target=str(uuid4());path=tmp_path/'usage-package.zip'
    with ContinuityStore(home/'subject'/'self.db',clock,schema_target=13) as store:
        result=SubjectPackageService(store,authority).export(path,destination_id=target,source_commit='a69cbf17b6227d3d33c89a8c6639ac93958b82ae',authority=authority)
    manifest,_=verify_package(path,expected_sha256=result['sha256'])
    assert manifest.identity_id==identity
    with zipfile.ZipFile(path) as archive:raw=archive.read('subject.sqlite')
    readback=tmp_path/'readback.sqlite';readback.write_bytes(raw);readback.chmod(0o600)
    db=sqlite3.connect(readback.as_uri()+'?mode=ro&immutable=1',uri=True)
    try:
        assert not db.execute("SELECT 1 FROM core_meta WHERE key='runtime.routine_review'").fetchone()
        saved=list(db.execute('SELECT key,value_json FROM core_meta WHERE substr(key,1,?)=?',(len(PREFIX),PREFIX)))
        assert len(saved)==2
        assert all('portable usage' not in row[1] and json.loads(row[1])['input_tokens']==10 for row in saved)
    finally:db.close()


@pytest.mark.parametrize('mode,reported',[('partial',True),('refusal',True),('malformed',True),('rate_limit',False)])
def test_rejected_provider_wording_keeps_bound_numeric_usage_without_success_or_refund(tmp_path,mode,reported):
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.world_loop.cognition import CognitionSession
    from nana_core.continuity.accounting import PREFIX
    from nana_core.continuity.memory import MemoryService
    from tests.world_loop.helpers import fresh,capture,policy
    import json
    home=tmp_path/'self.db'
    with provider_harness(mode=mode) as (port,wire):
        with fresh(home) as runtime:
            clock=runtime.clock;identity=runtime.identity_id
            session=CognitionSession(runtime,port,policy())
            mid=capture(runtime,'failed-usage-source',{'fact':'SYNTHETIC failed wording does not erase paid work'})
            cid=session.prepare('failed-usage-'+mode,'INTERPRET',(mid,))
            outcome=session.execute(cid)
            assert outcome['state']=='FAILED' and wire['calls']==1
            before=resource_state(runtime.store,runtime.config)
            saved=runtime.store.one('core_meta',PREFIX+cid)
            print(json.dumps({'measurement':'synthetic_failed_provider_usage','mode':mode,'state':outcome['state'],
                'reported_calls':before.fixture_usage_reported_calls,'input_tokens':before.fixture_reported_input_tokens,
                'output_tokens':before.fixture_reported_output_tokens,'calls':wire['calls']},sort_keys=True))
            assert bool(saved)==reported
            assert before.fixture_usage_reported_calls==int(reported)
            assert before.fixture_reported_input_tokens==(10 if reported else None)
            assert before.fixture_reported_output_tokens==(10 if reported else None)
            assert before.usage_missing_or_invalid_calls==int(not reported)
            assert before.provider_reported_input_tokens is None and before.real_usage_reported_calls==0
            assert before.unknown_cost_calls==1 and runtime.store.one('cognitive_requests',cid)['actual_cost_micro'] is None
            assert not runtime.store.db.execute("SELECT 1 FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL' AND target_id=?",(cid,)).fetchone()
            assert not runtime.store.all('actions') and not runtime.store.all('grants')
            assert session.execute(cid)['replayed'] and wire['calls']==1
            if reported:
                snapshot=saved['value_json']
                assert set(json.loads(snapshot))=={'version','request_id','origin','input_tokens','output_tokens'}
                assert 'wording' not in snapshot
            MemoryService(runtime.store,runtime.authority).forget(mid,runtime.authority)
            after=resource_state(runtime.store,runtime.config)
            assert after.fixture_reported_input_tokens==before.fixture_reported_input_tokens
            assert after.reserved_estimated_cost_micro==before.reserved_estimated_cost_micro and after.unknown_cost_calls==1
        with fresh(home,clock=clock) as runtime:
            assert runtime.identity_id==identity
            session=CognitionSession(runtime,port,policy());assert session.execute(cid)['replayed'] and wire['calls']==1
            after=resource_state(runtime.store,runtime.config)
            assert after.fixture_usage_reported_calls==int(reported) and after.unknown_cost_calls==1
            if reported:assert runtime.store.one('core_meta',PREFIX+cid)['value_json']==snapshot


@pytest.mark.parametrize('invalid',[
    {'prompt_tokens':10,'input_tokens':True,'completion_tokens':4},
    {'prompt_tokens':10,'completion_tokens':4,'total_tokens':'PRIVATE_INVALID_USAGE_CANARY'},
])
def test_invalid_usage_alias_is_not_silently_removed_to_create_a_valid_failure_receipt(tmp_path,invalid,monkeypatch):
    import io,json
    from email.message import Message
    from urllib.response import addinfourl
    from nana_core.continuity.world_loop.cognition import CognitionSession,OpenAIJSONTransport
    from tests.world_loop.helpers import fresh,capture,policy
    with fresh(tmp_path/'self.db') as runtime:
        port=OpenAIJSONTransport('http://127.0.0.1:1/v1/chat/completions','synthetic-invalid-usage',harness=True)
        envelope={'model':port.model_id,'usage':invalid,'choices':[{'finish_reason':'length','message':{'content':'not an accepted proposal'}}]}
        raw=json.dumps(envelope).encode();headers=Message();headers['Content-Type']='application/json'
        calls=[]
        def response(request,**kwargs):
            calls.append(request);return addinfourl(io.BytesIO(raw),headers,port.endpoint,200)
        monkeypatch.setattr(port.opener,'open',response)
        session=CognitionSession(runtime,port,policy());mid=capture(runtime,'invalid-usage',{'fact':'SYNTHETIC codec only'})
        cid=session.prepare('invalid-usage','INTERPRET',(mid,));assert session.execute(cid)['state']=='FAILED'
        assert len(calls)==1 and port.last_response_metadata['usage'] is None
        assert not runtime.store.one('core_meta','cognition.usage.'+cid)
        assert 'PRIVATE_INVALID_USAGE_CANARY' not in json.dumps(port.last_response_metadata)
        state=resource_state(runtime.store,runtime.config)
        assert state.fixture_usage_reported_calls==0 and state.usage_missing_or_invalid_calls==1 and state.unknown_cost_calls==1


def test_previous_usage_does_not_leak_into_unknown_request_and_independent_request_can_continue(tmp_path,monkeypatch):
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget
    from tests.world_loop.helpers import fresh,capture,policy
    with provider_harness(mode='partial') as (port,wire),fresh(tmp_path/'self.db') as runtime:
        budget=CognitionBudget(cost_ceiling_micro=1000)
        session=CognitionSession(runtime,port,policy());mid=capture(runtime,'separate-requests',{'fact':'SYNTHETIC independent requests'})
        first=session.prepare('partial-response','INTERPRET',(mid,),budget=budget);assert session.execute(first)['state']=='FAILED'
        before=resource_state(runtime.store,runtime.config)
        def no_response(*args,**kwargs):raise TimeoutError('SYNTHETIC no provider response')
        original=port.opener.open;monkeypatch.setattr(port.opener,'open',no_response)
        second=session.prepare('no-response','INTERPRET',(mid,),budget=budget);assert session.execute(second)['state']=='UNKNOWN'
        after=resource_state(runtime.store,runtime.config)
        assert after.fixture_usage_reported_calls==1 and after.fixture_reported_input_tokens==10
        assert after.usage_missing_or_invalid_calls==1 and after.unresolved_terminal_calls==1 and after.unknown_cost_calls==2
        assert after.reserved_estimated_cost_micro>before.reserved_estimated_cost_micro
        assert not runtime.store.one('core_meta','cognition.usage.'+second)
        monkeypatch.setattr(port.opener,'open',original);wire['mode']='ok'
        third=session.prepare('new-independent','INTERPRET',(mid,),budget=budget);assert session.execute(third)['state']=='PROPOSED'
        assert session.execute(second)['replayed'] and wire['calls']==2
        state=resource_state(runtime.store,runtime.config)
        assert state.fixture_usage_reported_calls==2 and state.fixture_reported_input_tokens==20
        assert state.usage_missing_or_invalid_calls==1 and state.unknown_cost_calls==2
        assert not runtime.store.all('actions') and not runtime.store.all('grants')
