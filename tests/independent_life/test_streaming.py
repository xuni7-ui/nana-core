"""Actual original C and loopback SSE, no real-provider semantic claim."""

import threading
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from .conftest import initialize
from .test_dialogue import relay


def test_actual_draft_arrives_before_upstream_finishes_and_original_c_still_decides(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    release = threading.Event()
    seen = []
    with (
        relay(home, "CHAT", stream_fixture={"release": release}) as (router, requests),
        LifeApplication(home, clock=VirtualClock(), router=router) as app,
    ):

        def observe(value):
            seen.append(value)
            if value["state"] == "PROVISIONAL_MODEL_DRAFT":
                release.set()

        app.response_sink = observe
        app.pause()
        identity = app.runtime.identity_id
        result = app.chat("SYNTHETIC real streamed fixture please", privacy="PROJECT", message_id="stream.one")
        assert release.is_set() and any(e.get("text") for e in seen)
        assert result["render_state"] == "UNVERIFIED_MODEL_WORDING"
        assert result["text"] == "A deliberately synthetic language response"
        assert requests[0].get("response_mode", "JSON") == "JSON" and requests[-1]["response_mode"] == "JSON_STREAM"
        assert [x["state"] for x in seen[:2]] == ["INTERPRETING", "RENDERING"]
        assert seen[-1]["text"] == result["text"]
        assert app.runtime.identity_id == identity and len(requests) == 2
        assert not app.runtime.store.all("actions")
        assert not app.runtime.store.db.execute(
            "SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'A deliberately synthetic language response')>0"
        ).fetchone()


def test_interrupted_stream_keeps_unknown_and_new_independent_message_does_not_retry_it(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    seen = []
    with (
        relay(home, "CHAT", stream_fixture={"interrupt": True}) as (router, requests),
        LifeApplication(home, clock=VirtualClock(), router=router) as app,
    ):
        app.response_sink = seen.append
        app.pause()
        result = app.chat("SYNTHETIC truncated stream", privacy="PROJECT", message_id="stream.unknown")
        assert result["render_state"] != "UNVERIFIED_MODEL_WORDING"
        row = app.runtime.store.db.execute("SELECT * FROM cognitive_requests WHERE state='UNKNOWN'").fetchone()
        assert row is not None and row["error_code"] == "PROVIDER_STREAM_INTERRUPTED_BILLING_UNKNOWN"
        before = len(requests)
        app.chat("SYNTHETIC truncated stream", privacy="PROJECT", message_id="stream.unknown")
        assert len(requests) == before
        app.chat("SYNTHETIC new independent question", privacy="PROJECT", message_id="stream.new")
        assert (
            len(requests) > before
            and app.runtime.store.one("cognitive_requests", row["request_id"])["state"] == "UNKNOWN"
        )


def test_runtime_stop_during_interpret_wait_is_unknown_and_never_dispatches_render(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    with relay(home, "CHAT") as (router, requests), LifeApplication(home, clock=VirtualClock(), router=router) as app:
        app.pause()
        app.runtime.control_progress = app.runtime.request_stop
        app.chat("SYNTHETIC stop before render", privacy="PROJECT", message_id="stop.during.interpret")
        rows = app.runtime.store.all("cognitive_requests")
        assert len(requests) == 1 and len(rows) == 1
        assert rows[0]["state"] == "UNKNOWN" and rows[0]["error_code"] == "STOPPED_PROVIDER_BILLING_UNKNOWN_NO_RETRY"
        assert app.runtime.stop_requested


def test_long_stream_keeps_bounded_provisional_prefix_and_complete_final_reply(tmp_path):
    import threading
    home = tmp_path / 'home'; initialize(home, active=0)
    release = threading.Event(); release.set()
    fixture = {'release': release, 'finished': threading.Event()}
    text = 'SYNTHETIC_LONG_STREAM_CANARY ' + 'complete explanation. ' * 260
    assert 4096 < len(text) < 8192
    values = []
    with relay(home, 'CHAT', renderer=lambda request: text, stream_fixture=fixture) as (router, requests), LifeApplication(home, clock=VirtualClock(), router=router) as app:
        app.pause(); app.response_sink = values.append
        result = app.chat('SYNTHETIC long discussion', privacy='PROJECT', message_id='long-stream')
        assert result['text'] == text and result['render_state'] == 'UNVERIFIED_MODEL_WORDING'
        partials = [v['text'] for v in values if v['state'] == 'PROVISIONAL_MODEL_DRAFT']
        assert partials and all(text.startswith(p) and len(p) <= 4096 for p in partials)
        assert len(requests) == 2 and fixture['finished'].is_set()
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC_LONG_STREAM_CANARY')>0").fetchone()
