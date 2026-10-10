import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from urllib import request as http
import pytest
from pydantic import ValidationError
from nana_core.contracts import CoreError, ModelRequest
from nana_core.semantic.contracts import Endpoint, EvaluationCase, ModelBudget, RunConfig
from nana_core.semantic.model_port import CallLedger, CompatibleModelPort, HTTPTransport, NoRedirect
from nana_core.storage import canonical
from .helpers import ScriptedTransport

pytestmark = pytest.mark.s5


def local_endpoint(**changes):
    return Endpoint(alias="a", base_url="http://127.0.0.1:9999/v1", model="development-model",
                    account_scope="local_offline", funding="local_offline", **changes)


@pytest.mark.parametrize("change", [
    {"base_url": "https://user:pass@example.invalid/v1"},
    {"base_url": "http://remote.invalid/v1"},
    {"base_url": "https://example.invalid/v1?key=hidden"},
    {"credential_env": "OPENAI_API_KEY"},
    {"account_scope": "production"},
    {"funding": "new_purchase"},
    {"base_url": "https://remote.invalid/v1", "account_scope": "local_offline"},
])
def test_operator_endpoint_boundaries(change):
    data = local_endpoint().model_dump()
    data.update(change)
    with pytest.raises(ValidationError):
        Endpoint.model_validate(data)


def test_duplicate_model_is_not_migration():
    a = local_endpoint()
    with pytest.raises(ValidationError):
        RunConfig(endpoints=(a, a.model_copy(update={"alias": "b"})))


def test_attempt_budget_survives_failure_and_reopen(tmp_path):
    path, budget, scope = tmp_path / "calls.db", ModelBudget(max_calls=1), {"frozen": "same"}
    ledger = CallLedger(path, budget, scope)
    call = ledger.begin(local_endpoint(), b"synthetic", {"provenance": "transport_fixture"})
    ledger.finish(call, "FAILED", 1, {"error": "synthetic rejection", "provenance": "transport_fixture"})
    ledger.close()
    ledger = CallLedger(path, budget, scope)
    try:
        with pytest.raises(CoreError, match="MODEL_BUDGET_EXHAUSTED"):
            ledger.begin(local_endpoint(), b"synthetic", {})
        assert ledger.summary()["attempts"] == 1
        assert ledger.summary()["reserved_output_tokens"] == 1200
    finally:
        ledger.close()


@pytest.mark.parametrize("budget", [ModelBudget(max_reserved_input_bytes=1),
    ModelBudget(max_reserved_output_tokens=1), ModelBudget(max_reserved_cost_micro=0)])
def test_all_budget_dimensions_are_pre_dispatch(tmp_path, budget):
    ledger = CallLedger(tmp_path / "calls.db", budget, {})
    try:
        endpoint = local_endpoint(input_rate_micro=1)
        with pytest.raises(CoreError, match="MODEL_BUDGET_EXHAUSTED"):
            ledger.begin(endpoint, b"synthetic request", {})
        assert ledger.summary()["attempts"] == 0
    finally:
        ledger.close()


def test_ledger_scope_cannot_be_changed(tmp_path):
    path = tmp_path / "calls.db"
    ledger = CallLedger(path, ModelBudget(), {"identity": "frozen"})
    ledger.close()
    with pytest.raises(CoreError, match="MODEL_LEDGER_SCOPE_CHANGED"):
        CallLedger(path, ModelBudget(), {"identity": "replacement"})


def test_model_ledger_refuses_core_database_without_mutation(tmp_path):
    from nana_core.storage import Store, digest
    path = tmp_path / "core.db"
    with Store(path):
        pass
    before = digest(path.read_bytes())
    with pytest.raises(CoreError, match="MODEL_LEDGER_MUST_BE_SEPARATE"):
        CallLedger(path, ModelBudget(), {})
    assert digest(path.read_bytes()) == before


def test_model_ledger_excludes_second_writer(tmp_path):
    path = tmp_path / "calls.db"
    ledger = CallLedger(path, ModelBudget(), {})
    try:
        with pytest.raises(CoreError, match="MODEL_LEDGER_BUSY"):
            CallLedger(path, ModelBudget(), {})
    finally:
        ledger.close()


def test_real_sigkill_leaves_call_unresolved_without_retry(tmp_path):
    path = tmp_path / "calls.db"
    script = """
import os, signal, sys
from nana_core.semantic.contracts import Endpoint, ModelBudget
from nana_core.semantic.model_port import CallLedger
ledger=CallLedger(sys.argv[1],ModelBudget(),{})
e=Endpoint(alias='a',base_url='http://127.0.0.1:9999/v1',model='local',account_scope='local_offline',funding='local_offline')
ledger.begin(e,b'synthetic',{'provenance':'transport_fixture'})
os.kill(os.getpid(),signal.SIGKILL)
"""
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    child = subprocess.run([sys.executable, "-c", script, str(path)], env=env, capture_output=True, timeout=10)
    assert child.returncode == -signal.SIGKILL
    ledger = CallLedger(path, ModelBudget(), {})
    try:
        assert ledger.summary()["calls"][0]["state"] == "DISPATCHING"
        with pytest.raises(CoreError, match="MODEL_CALL_UNRESOLVED"):
            ledger.begin(local_endpoint(), b"new request", {})
        assert ledger.summary()["attempts"] == 1
    finally:
        ledger.close()


def make_port(tmp_path, transport, **endpoint_changes):
    case = EvaluationCase(case_id="synthetic", kind="reading", raw_text="Synthetic reading request.",
        source_id="source://synthetic/a", card_resource="notebook://synthetic/a", occurred_at="2026-09-02T00:00:00Z")
    identity = {"charter": ["retain independent judgement"]}
    req = ModelRequest(identity_id="same-identity", identity_revision=1, identity_snapshot=identity,
        event_id="synthetic-event", event_text=case.raw_text, source_id=case.source_id, card_resource=case.card_resource)
    continuity = {"memories": [{"created_event_id": "past-event"}], "active_experiences": []}
    ledger = CallLedger(tmp_path / "calls.db", ModelBudget(), {})
    return CompatibleModelPort(local_endpoint(**endpoint_changes), ledger, continuity, case, "with", transport), req


@pytest.mark.parametrize("mutate", [
    lambda reply: reply.update(success=True),
    lambda reply: reply["proposal"].update(receipt={"success": True}),
    lambda reply: reply["experience"].update(authorizes_new_permissions=True),
    lambda reply: reply["identity"].update(revision="1"),
])
def test_untrusted_response_cannot_claim_success_or_expand_authority(tmp_path, mutate):
    transport = ScriptedTransport(mutate=mutate)
    port, req = make_port(tmp_path, transport)
    try:
        with pytest.raises(CoreError, match="MODEL_RESPONSE_REJECTED"):
            port.propose(req)
        assert transport.calls == 1
        assert port.ledger.summary()["calls"][0]["state"] == "FAILED"
    finally:
        port.ledger.close()


def test_timeout_is_unknown_and_no_hidden_retry(tmp_path):
    class TimeoutTransport:
        is_real_transport = False
        calls = 0
        def send(self, endpoint, payload):
            self.calls += 1
            raise TimeoutError("synthetic")
    transport = TimeoutTransport()
    port, req = make_port(tmp_path, transport)
    try:
        with pytest.raises(CoreError, match="MODEL_TRANSPORT_UNCERTAIN"):
            port.propose(req)
        with pytest.raises(CoreError, match="MODEL_CALL_UNRESOLVED"):
            port.propose(req)
        assert transport.calls == 1
        assert port.ledger.summary()["calls"][0]["state"] == "UNKNOWN"
    finally:
        port.ledger.close()


def test_context_budget_preserves_raw_and_does_not_silently_trim(tmp_path):
    transport = ScriptedTransport()
    port, req = make_port(tmp_path, transport, max_input_bytes=1024)
    try:
        with pytest.raises(CoreError, match="MODEL_CONTEXT_TOO_LARGE"):
            port.propose(req)
        assert transport.calls == 0
        assert req.event_text == "Synthetic reading request."
        assert port.ledger.summary()["attempts"] == 0
    finally:
        port.ledger.close()


def test_redirect_is_never_followed():
    with pytest.raises(CoreError, match="MODEL_REDIRECT_REJECTED"):
        NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.invalid")


@pytest.mark.parametrize("change", [
    lambda e: e.update(model=None),
    lambda e: e["choices"][0].update(finish_reason="length"),
    lambda e: e["choices"][0]["message"].update(tool_calls=[{"name": "execute"}]),
])
def test_metadata_truncation_and_tool_calls_rejected(tmp_path, change):
    class Transport(ScriptedTransport):
        def send(self, endpoint, payload):
            result = json.loads(super().send(endpoint, payload))
            change(result)
            return canonical(result).encode()
    port, req = make_port(tmp_path, Transport())
    try:
        with pytest.raises(CoreError, match="MODEL_RESPONSE_REJECTED"):
            port.propose(req)
        assert port.ledger.summary()["attempts"] == 1
    finally:
        port.ledger.close()


def test_provider_usage_exceeding_reservation_is_reported(tmp_path):
    class Transport(ScriptedTransport):
        def send(self, endpoint, payload):
            result = json.loads(super().send(endpoint, payload))
            result["usage"]["completion_tokens"] = 9999
            return canonical(result).encode()
    port, req = make_port(tmp_path, Transport())
    try:
        with pytest.raises(CoreError, match="MODEL_PROVIDER_BUDGET_VIOLATION"):
            port.propose(req)
        call = port.ledger.summary()["calls"][0]
        assert call["state"] == "FAILED" and call["output_hold"] == 1200
        assert call["evidence"]["usage"]["completion_tokens"] == 9999
    finally:
        port.ledger.close()


def test_http_adapter_uses_development_binding_once_without_recording_secret(tmp_path, monkeypatch):
    calls = []
    synthetic_value = "synthetic-development-binding-only"
    monkeypatch.setenv("NANA_S5_DEV_TEST", synthetic_value)
    fixture = ScriptedTransport()
    class Response:
        def __init__(self, data): self.data = data
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return self.data[:limit]
    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, request.get_header("Authorization"), timeout))
            return Response(fixture.send(None, request.data))
    monkeypatch.setattr(http, "build_opener", lambda handler: Opener())
    # The mocked opener is engineering-only even though it exercises HTTPTransport.
    class FixtureHTTP(HTTPTransport): is_real_transport = False
    port, req = make_port(tmp_path, FixtureHTTP(), credential_env="NANA_S5_DEV_TEST")
    try:
        assert port.propose(req)
        assert len(calls) == 1 and calls[0][1] == "Bearer " + synthetic_value
        assert synthetic_value not in canonical(port.ledger.summary())
        assert port.ledger.summary()["calls"][0]["evidence"]["provenance"] == "transport_fixture"
    finally:
        port.ledger.close()
