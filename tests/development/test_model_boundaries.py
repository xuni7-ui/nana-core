from http.client import IncompleteRead
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.semantic.contracts import load_run_config
from nana_core.semantic.model_port import CompatibleModelPort
from semantic_migration.helpers import ScriptedTransport
from semantic_migration.test_model_port import make_port


def test_truncated_provider_body_is_unresolved_not_definitive_failure(tmp_path):
    class Truncated:
        is_real_transport=False
        calls=0
        def send(self,*args):
            self.calls+=1
            raise IncompleteRead(b'synthetic-partial',100)
    transport=Truncated();port,req=make_port(tmp_path,transport)
    try:
        with pytest.raises(CoreError,match='MODEL_TRANSPORT_UNCERTAIN'):port.propose(req)
        with pytest.raises(CoreError,match='MODEL_CALL_UNRESOLVED'):port.propose(req)
        assert transport.calls==1
        assert port.ledger.summary()['calls'][0]['state']=='UNKNOWN'
    finally:port.ledger.close()


def test_development_binding_echo_never_enters_call_evidence(tmp_path,monkeypatch):
    marker='synthetic-development-echo-marker'
    monkeypatch.setenv('NANA_S5_DEV_ECHO',marker)
    transport=ScriptedTransport(mutate=lambda reply:reply.update(rationale=marker))
    port,req=make_port(tmp_path,transport,credential_env='NANA_S5_DEV_ECHO')
    try:
        with pytest.raises(CoreError,match='MODEL_RESPONSE_REJECTED'):port.propose(req)
        summary=port.ledger.summary()
        assert marker not in json.dumps(summary)
        assert 'raw_content' not in summary['calls'][0]['evidence']
        assert summary['calls'][0]['state']=='FAILED'
    finally:port.ledger.close()


def test_malformed_config_cannot_echo_credential_input(tmp_path):
    path=tmp_path/'bad.json';marker='synthetic-config-value-not-real'
    path.write_text(json.dumps({'api_key':marker}))
    with pytest.raises(CoreError,match='MODEL_CONFIG_REJECTED') as error:load_run_config(path)
    assert marker not in str(error.value)
    link=tmp_path/'link.json';link.symlink_to(path)
    with pytest.raises(CoreError,match='MODEL_CONFIG_REJECTED'):load_run_config(link)


def test_mutated_endpoint_cannot_bypass_scope_validation(tmp_path):
    port,req=make_port(tmp_path,ScriptedTransport())
    try:
        endpoint=port.endpoint.model_copy(update={'account_scope':'production'})
        with pytest.raises(CoreError,match='MODEL_ENDPOINT_REJECTED'):
            CompatibleModelPort(endpoint,port.ledger,port.continuity,port.case,port.arm)
        assert port.ledger.summary()['attempts']==0
    finally:port.ledger.close()
