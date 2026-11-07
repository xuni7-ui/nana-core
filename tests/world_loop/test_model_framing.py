"""Explicit SYNTHETIC character tokenizer; not a commercial BPE claim."""

import json
import pytest
from nana_core.continuity.context import ModelTokenCounter
from nana_core.continuity.world_loop.cognition import CognitionSession, CognitionRequest, CognitionBudget
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.contracts import CoreError
from nana_core.storage import canonical
from .helpers import fresh, capture, policy


def exact_fixture(body):
    # Independently specified fixture protocol: five role framing symbols per
    # message + character tokens, with explicit JSON response mode overhead.
    return 3 + sum(5 + len(m["role"]) + len(canonical(m["content"])) for m in body["messages"]) + 7


def bind(transport, counter=exact_fixture):
    transport.token_counter = ModelTokenCounter(
        provider_id=transport.provider_id,
        model_id=transport.model_id,
        revision="a" * 64,
        text_tokens=len,
        request_tokens=counter,
    )


def test_complete_actual_request_is_budgeted_and_rechecked_without_changing_source_or_authority(tmp_path):
    with fresh(tmp_path / "s" / "self.db") as runtime, provider_harness() as (transport, state):
        bind(transport)
        mid = capture(runtime, "framed.source", {"text": "SYNTHETIC 汉字🙂, punctuation and source"})
        session = CognitionSession(runtime, transport, policy())
        rid = session.prepare("model.frame", "INTERPRET", (mid,), budget=CognitionBudget(input_tokens=65536))
        payload = session.records.read(runtime.store.one("cognitive_requests", rid)["record_id"])["payload"]
        request = CognitionRequest.model_validate_json(canonical(payload["request"]))
        actual = exact_fixture(json.loads(transport.request_body(request)))
        assert payload["token_accounting"]["input_tokens"] == actual
        package = json.loads(request.context_json)
        assert actual <= package["manifest"]["input_tokens"]
        assert actual > len(request.context_json)
        assert payload["token_accounting"]["provider_reported_usage"] is False
        assert mid in request.source_context_refs and package["blocks"][0]["kind"] == "IDENTITY"
        assert actual + request.budget.output_tokens <= request.budget.input_tokens
        assert session.execute(rid)["state"] == "PROPOSED" and state["calls"] == 1


def test_request_framing_overflow_rejects_before_reservation_or_call(tmp_path):
    with fresh(tmp_path / "s" / "self.db") as runtime, provider_harness() as (transport, state):
        bind(transport, lambda body: 70000)
        mid = capture(runtime, "large.frame", {"text": "SYNTHETIC bounded"})
        session = CognitionSession(runtime, transport, policy())
        with pytest.raises(CoreError, match="INSUFFICIENT_CONTEXT_BUDGET"):
            session.prepare("too.big", "INTERPRET", (mid,), budget=CognitionBudget(input_tokens=65536))
        assert not runtime.store.all("cognitive_requests") and state["calls"] == 0


def test_changed_counter_model_or_revision_is_stopped_without_dispatch_or_refund(tmp_path):
    with fresh(tmp_path / "s" / "self.db") as runtime, provider_harness() as (transport, state):
        bind(transport)
        mid = capture(runtime, "bound.model", {"text": "SYNTHETIC counter binding"})
        session = CognitionSession(runtime, transport, policy())
        rid = session.prepare("frozen.counter", "INTERPRET", (mid,), budget=CognitionBudget(input_tokens=65536))
        before = runtime.store.one("cognitive_requests", rid)["reserved_bytes"]
        bind(transport, lambda body: 1)
        assert session.execute(rid)["state"] == "STALE" and state["calls"] == 0
        assert runtime.store.one("cognitive_requests", rid)["reserved_bytes"] == before


@pytest.mark.parametrize("result", [True, -1, 2.5, None, 3000000])
def test_invalid_counter_results_cannot_admit_a_request(result):
    counter = ModelTokenCounter(
        provider_id="p", model_id="m", revision="a" * 64, text_tokens=len, request_tokens=lambda body: result
    )
    with pytest.raises(CoreError, match="MODEL_TOKEN_COUNTER_RESULT_INVALID"):
        counter.count_request({}, provider_id="p", model_id="m")
    with pytest.raises(CoreError, match="MODEL_TOKEN_COUNTER_TARGET_MISMATCH"):
        counter.count_request({}, provider_id="p", model_id="different")


def test_actual_dialogue_uses_trusted_factory_binding_and_drops_raw_framing_closure(tmp_path):
    from tests.independent_life.conftest import initialize
    from tests.independent_life.test_dialogue import relay
    from nana_core.life.application import LifeApplication
    from nana_core.presence.authority import VirtualClock
    from nana_core.continuity.context import ConservativeCounter

    home = tmp_path / "home"
    initialize(home, active=0)
    observed = []

    def fixture_eight_character_protocol(body):
        observed.append(body)
        return (len(canonical(body)) + 7) // 8

    with relay(home, "CHAT") as (router, requests):
        model = router.config.load().models[0]
        router.factory.token_counters = {
            model.model_profile_id: ModelTokenCounter(
                provider_id=model.provider_profile_id,
                model_id=model.remote_model_id,
                revision="b" * 64,
                text_tokens=lambda text: (len(text) + 7) // 8,
                request_tokens=fixture_eight_character_protocol,
            )
        }
        with LifeApplication(home, clock=VirtualClock(), router=router) as app:
            app.pause()
            result = app.chat(
                "SYNTHETIC_EPHEMERAL_TOKEN_FRAME includes 原始字句", privacy="PROJECT", message_id="bound.dialogue"
            )
            assert result["render_state"] == "UNVERIFIED_MODEL_WORDING", result
            assert len(requests) == 2 and any("SYNTHETIC_EPHEMERAL_TOKEN_FRAME" in canonical(b) for b in observed)
            assert type(app.session.assembler.counter) is ConservativeCounter
            rows = app.runtime.store.all("cognitive_requests")
            assert all(
                app.session.records.read(row["record_id"])["payload"]["token_accounting"]["counter"].endswith("b" * 64)
                for row in rows
            )
            assert not app.runtime.store.db.execute(
                "SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC_EPHEMERAL_TOKEN_FRAME')>0"
            ).fetchone()
