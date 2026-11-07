"""Actual SSE parsing, never fake typewriter delivery of a buffered answer."""

import io, json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.streaming import DraftPrefix, receive


def stream(content, *, done=True, model="fixture-text", split=1):
    rows = []
    for i in range(0, len(content), split):
        value = {
            "model": model,
            "choices": [{"index": 0, "delta": {"content": content[i : i + split]}, "finish_reason": None}],
        }
        rows.append(("data: " + json.dumps(value) + "\n\n").encode())
    rows.append(
        (
            "data: "
            + json.dumps({"model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
            + "\n\n"
        ).encode()
    )
    if done:
        rows.append(b"data: [DONE]\n\n")
    return b"".join(rows)


@pytest.mark.parametrize("text", ["你好，奈奈 🌙", 'quoted "text" and \\ slash', "line\nnext\ttab", "𝄞 café"])
def test_split_unicode_escapes_emit_real_early_prefixes_without_interpretation_injection(text):
    draft = DraftPrefix()
    pieces = []
    raw = json.dumps(
        {
            "interpretation": 'a phrase "draft": {"text":"FAKE"}',
            "draft": {"text": text, "claim_memory_ids": [], "effect_status": "NO_EFFECT"},
        }
    )
    for ch in raw:
        piece = draft.feed(ch)
        if piece:
            pieces.append(piece)
    assert "".join(pieces) == text
    assert len(pieces) > 1


def test_sse_usage_and_final_payload_are_preserved_without_reasoning_or_tools_in_preview():
    content = json.dumps(
        {
            "interpretation": "fixture",
            "draft": {"text": "Early real text", "claim_memory_ids": [], "effect_status": "NO_EFFECT"},
        }
    )
    pieces = []
    body = stream(content, split=2)
    envelope, raw = receive(io.BytesIO(body), 1048576, pieces.append)
    assert raw == body and "".join(pieces) == "Early real text"
    assert json.loads(envelope["choices"][0]["message"]["content"]) == json.loads(content)
    assert envelope["model"] == "fixture-text"
    assert len(pieces) > 1


def test_missing_terminal_is_unknown_not_permission_to_retry():
    with pytest.raises(CoreError, match="PROVIDER_STREAM_INTERRUPTED_BILLING_UNKNOWN"):
        receive(io.BytesIO(stream('{"draft":{"text":"partial"}}', done=False)), 1048576, lambda _: None)


def test_bound_and_changed_model_reject_without_repair_or_fallback():
    body = stream('{"draft":{"text":"hello"}}')
    with pytest.raises(CoreError, match="PROVIDER_RESPONSE_BOUND"):
        receive(io.BytesIO(body), 30, lambda _: None)
    body = body.replace(b'"model": "fixture-text"', b'"model": "different"', 1)
    with pytest.raises(CoreError, match="PROVIDER_STREAM_MODEL_CHANGED"):
        receive(io.BytesIO(body), 1048576, lambda _: None)


def test_key_like_text_and_unfinished_escape_cannot_be_presented_as_a_draft():
    d = DraftPrefix()
    assert d.feed('{"interpretation":"draft text FAKE') == ""
    d = DraftPrefix()
    assert d.feed('{"draft":{"text":"x\\uD83C') == "x"


def test_confirmed_wire_allowance_is_separate_from_immutable_reservations_and_unknown_costs():
    from nana_core.presence.resources import accounted_bytes

    row = {"state": "PROPOSED", "reserved_bytes": 600000, "input_bytes": 20000, "output_bytes": 80000}
    assert accounted_bytes(row) == 100000 and row["reserved_bytes"] == 600000
    for state in ("PREPARED", "CALLING", "UNKNOWN", "FAILED", "REJECTED", "STALE"):
        assert accounted_bytes({**row, "state": state}) == 600000
    for changes in (
        {"input_bytes": None},
        {"output_bytes": None},
        {"input_bytes": 0},
        {"input_bytes": -1},
        {"output_bytes": 600000},
    ):
        assert accounted_bytes({**row, **changes}) == 600000


def test_trickled_bytes_do_not_reset_the_absolute_json_or_sse_deadline(monkeypatch):
    from nana_core.continuity.world_loop import streaming

    now = [0.0]
    monkeypatch.setattr(streaming.time, "monotonic", lambda: now[0])

    class Trickle:
        def read1(self, n):
            now[0] += 0.2
            return b"x"

        def readline(self, n):
            raise AssertionError("blocking readline must not be used")

    with pytest.raises(TimeoutError):
        streaming.read_body(Trickle(), 1000, 1.0)
    assert now[0] <= 1.01
    now[0] = 0.0
    with pytest.raises(TimeoutError):
        streaming.receive(Trickle(), 1000, lambda _: None, deadline=1.0)
    assert now[0] <= 1.01
