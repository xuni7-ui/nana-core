"""Actual HTTPTransport/socket integration. Servers are explicit simulators, not LLMs."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import pytest
from nana_core.contracts import CoreError, ModelRequest
from nana_core.development.lab import run
from nana_core.semantic.contracts import Endpoint, EvaluationCase, ModelBudget
from nana_core.semantic.evaluation import aggregate
from nana_core.semantic.model_port import CallLedger, CompatibleModelPort
from nana_core.storage import canonical
from semantic_migration.helpers import ScriptedTransport
from .proof import record


@contextmanager
def protocol_server(mode='valid'):
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            payload=self.rfile.read(int(self.headers['Content-Length']))
            calls.append({'path':self.path,'bytes':len(payload)})
            if mode=='redirect':
                self.send_response(307);self.send_header('Location','http://127.0.0.1:1/never');self.end_headers();return
            if mode=='disconnect':self.close_connection=True;return
            mutate=(lambda reply:reply.update(success=True)) if mode=='claims_success' else None
            raw=ScriptedTransport(mutate=mutate).send(None,payload)
            if mode=='oversize':raw=b'x'*65_537
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=HTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=0.02),daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}/v1',calls
    finally:server.shutdown();thread.join(timeout=2);server.server_close()


def port_for(url,tmp_path,service_kind='protocol_simulator'):
    endpoint=Endpoint(alias='simulator',base_url=url,model='fixture-protocol-model',service_kind=service_kind,
        account_scope='local_offline',funding='local_offline')
    ledger=CallLedger(tmp_path/'calls.db',ModelBudget(max_calls=1),{'mode':'loopback_protocol_simulator'})
    case=EvaluationCase(case_id='synthetic',kind='reading',raw_text='Synthetic request.',source_id='source://synthetic/a',
        card_resource='notebook://synthetic/a',occurred_at='2026-09-01T00:00:00Z')
    req=ModelRequest(identity_id='synthetic-stable-id',identity_revision=1,identity_snapshot={'charter':['evidence before success']},
        event_id='synthetic-current',event_text=case.raw_text,source_id=case.source_id,card_resource=case.card_resource)
    context={'memories':[{'created_event_id':'synthetic-prior'}],'active_experiences':[]}
    return CompatibleModelPort(endpoint,ledger,context,case,'with'),req


def test_real_wire_protocol_and_read_only_tool_end_to_end(tmp_path,monkeypatch):
    monkeypatch.setenv('NO_PROXY','127.0.0.1');monkeypatch.setenv('no_proxy','127.0.0.1')
    with protocol_server() as (url,calls):
        config={'endpoints':[{'alias':'protocol','base_url':url,'model':'fixture-protocol-model',
            'account_scope':'local_offline','funding':'local_offline','service_kind':'protocol_simulator'}],
            'budget':{'max_calls':2}}
        path=tmp_path/'config.json';path.write_text(canonical(config))
        report=run(tmp_path/'lab',path)
    assert len(calls)==2 and all(call['path']=='/v1/chat/completions' for call in calls)
    assert report['engineering_gate']=='PASS' and all(report['checks'].values())
    assert report['file_reads']=={'execute_reads':3,'verify_reads':3}
    assert report['real_model_attempts']==0 and report['E12']=='NOT_RUN'
    assert report['model_ledger']['attempts']==2
    assert all(c['state']=='COMPLETED' and c['evidence']['provenance']=='real_http' and
        c['evidence']['service_kind']=='protocol_simulator' for c in report['model_ledger']['calls'])
    record('actual_loopback_protocol',{'http_requests':len(calls),'calls':calls,'file_reads':report['file_reads'],
        'identity_equal':all(p['identity_equal'] for p in report['phases']),
        'grants_unchanged':all(p['grants_unchanged'] for p in report['phases']),
        'effects':report['phases'][-1]['world_counts']['effects'],'provenance':'protocol_simulator',
        'real_model_calls':0,'E12':'NOT_RUN','model_attempts':report['model_ledger']['attempts']})


@pytest.mark.parametrize('service_kind',['protocol_simulator','unverified'])
def test_successful_real_http_cannot_be_promoted_to_real_model(tmp_path,monkeypatch,service_kind):
    monkeypatch.setenv('NO_PROXY','127.0.0.1');monkeypatch.setenv('no_proxy','127.0.0.1')
    with protocol_server() as (url,calls):
        port,req=port_for(url,tmp_path,service_kind)
        try:
            assert port.propose(req)
            assert len(calls)==1
            summary=port.ledger.summary()
            result={'provenance':'real_http','call_id':port.last_call_id,'provider_model':'fixture-protocol-model',
                'alias':'simulator','case_id':'synthetic','arm':'with','semantic':{'passed':True},'behavior':{'passed':True}}
            report=aggregate([result],summary,[],'synthetic',1,2)
            assert report['E12']=='NOT_RUN' and report['real_model_attempts']==0
            assert report['protocol_simulator_attempts']==int(service_kind=='protocol_simulator')
            assert report['unverified_http_attempts']==int(service_kind=='unverified')
            with pytest.raises(CoreError,match='MODEL_BUDGET_EXHAUSTED'):port.propose(req)
            assert len(calls)==1
        finally:port.ledger.close()


@pytest.mark.parametrize('mode,state,error',[('redirect','FAILED','MODEL_RESPONSE_REJECTED'),
    ('claims_success','FAILED','MODEL_RESPONSE_REJECTED'),('oversize','FAILED','MODEL_RESPONSE_REJECTED'),
    ('disconnect','UNKNOWN','MODEL_TRANSPORT_UNCERTAIN')])
def test_actual_http_failures_have_no_retry_or_authority(tmp_path,monkeypatch,mode,state,error):
    monkeypatch.setenv('NO_PROXY','127.0.0.1');monkeypatch.setenv('no_proxy','127.0.0.1')
    with protocol_server(mode) as (url,calls):
        port,req=port_for(url,tmp_path)
        try:
            with pytest.raises(CoreError,match=error):port.propose(req)
            assert len(calls)==1 and port.last_reply is None
            assert port.ledger.summary()['calls'][0]['state']==state
            with pytest.raises(CoreError,match='MODEL_CALL_UNRESOLVED' if state=='UNKNOWN' else 'MODEL_BUDGET_EXHAUSTED'):
                port.propose(req)
            assert len(calls)==1
        finally:port.ledger.close()
