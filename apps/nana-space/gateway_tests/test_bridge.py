import http.client, json, os, signal, subprocess, sys, threading, time
from pathlib import Path
import pytest

APP = Path(__file__).resolve().parents[1]
REPO = APP.parents[1]
sys.path[:0] = [str(APP), str(REPO / "src")]
from gateway.dev_instance import initialize
from gateway.server import Bridge, Server
from nana_core.life.control import request

ACCESS = (
    "qualification-only-access"  # test fixture, never a provider/service credential
)


def wait_owner(home, identity):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            value = request(home, {"operation": "view", "view": "status"}, timeout=2)
            if value.get("ok") and value["result"]["identity_id"] == identity:
                return
        except Exception:
            pass
        time.sleep(0.1)
    raise AssertionError("original Core owner did not become ready")


def start_owner(home, identity):
    process = subprocess.Popen(
        [
            sys.executable,
            str(APP / "gateway/dev_instance.py"),
            "run",
            "--home",
            str(home),
            "--subject-id",
            identity,
            "--seconds",
            "180",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_owner(home, identity)
    return process


@pytest.fixture()
def system(tmp_path):
    home = tmp_path / "life"
    identity = initialize(home)["identity_id"]
    process = start_owner(home, identity)
    bridge = Bridge(home, identity, ACCESS)
    server = Server(0, bridge, APP / "dist")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state = {
        "home": home,
        "identity": identity,
        "process": process,
        "bridge": bridge,
        "server": server,
        "cookie": "",
    }

    def call(path, body=None, origin=None, host=None, cookie=True, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=12)
        headers = {"Host": host or f"127.0.0.1:{server.server_port}"}
        if cookie:
            headers["Cookie"] = state["cookie"]
        if body is not None or raw is not None:
            headers.update(
                {"Origin": origin or server.origin, "Content-Type": "application/json"}
            )
        payload = (
            raw if raw is not None else json.dumps(body) if body is not None else None
        )
        conn.request(
            "POST" if payload is not None else "GET",
            path,
            body=payload,
            headers=headers,
        )
        response = conn.getresponse()
        data = response.read()
        result = (
            json.loads(data)
            if response.getheader("Content-Type", "").startswith("application/json")
            else data
        )
        if response.getheader("Set-Cookie"):
            state["cookie"] = response.getheader("Set-Cookie").split(";")[0]
        code = response.status
        headers = dict(response.getheaders())
        conn.close()
        return code, result, headers

    state["call"] = call
    yield state
    server.shutdown()
    server.server_close()
    process = state["process"]
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=10)


def login(system):
    code, data, headers = system["call"](
        "/api/nana-space/v1/session",
        {"password": ACCESS, "subject_id": system["identity"]},
    )
    assert code == 200
    assert (
        "HttpOnly" in headers["Set-Cookie"]
        and "SameSite=Strict" in headers["Set-Cookie"]
    )
    return data


def test_real_owner_projection_and_non_demo_message(system):
    call = system["call"]
    assert call("/api/nana-space/v1/snapshot", cookie=False)[0] == 401
    session = login(system)
    code, snapshot, _ = call("/api/nana-space/v1/snapshot")
    assert code == 200
    assert (
        snapshot["subject_id"] == system["identity"]
        and snapshot["execution_authority"] is False
    )
    assert snapshot["data"]["inspector"]["read_only"] is True
    raw = json.dumps(snapshot)
    assert (
        "self_view" not in raw
        and "private_intents" not in raw
        and str(system["home"]) not in raw
    )
    assert snapshot["data"]["runtime"]["provider"] == "OFFLINE_NO_PROVIDER"
    message = {
        "message_id": "verified-input",
        "text": "先别分析这个话题",
        "run_id": session["run_id"],
    }
    code, receipt, _ = call("/api/nana-space/v1/messages", message)
    assert code == 200
    assert receipt["data"]["state"] == "REVIEWED", receipt
    assert (
        receipt["data"]["raw_body_persisted"] is False
        and receipt["data"]["message_memory_id"]
    )
    assert "演示回复" not in receipt["data"]["text"]
    assert call("/api/nana-space/v1/messages", message)[1]["data"] == receipt["data"]
    assert len(system["bridge"].receipts) == 1
    collision = {**message, "text": "different"}
    assert call("/api/nana-space/v1/messages", collision)[0] == 409


def test_authority_scope_origin_and_schema_denials(system):
    call = system["call"]
    assert (
        call("/api/nana-space/v1/session", {"password": ACCESS, "subject_id": "wrong"})[
            0
        ]
        == 403
    )
    assert (
        call(
            "/api/nana-space/v1/session",
            {"password": ACCESS, "subject_id": system["identity"]},
            origin="https://untrusted.example",
        )[0]
        == 403
    )
    assert call("/", host="rebind.example")[0] == 403
    login(system)
    assert call("/api/nana-space/v1/control", {"command": "resume"})[0] == 404
    assert (
        call(
            "/api/nana-space/v1/messages",
            {
                "message_id": "x",
                "text": "test",
                "run_id": system["bridge"].run_id,
                "home": "/private",
            },
        )[0]
        == 400
    )
    assert (
        call(
            "/api/nana-space/v1/messages",
            {"message_id": "x", "text": "a" * 2049, "run_id": system["bridge"].run_id},
        )[0]
        == 400
    )
    assert (
        call("/api/nana-space/v1/messages", raw='{"message_id":"x","message_id":"y"}')[
            0
        ]
        == 400
    )
    assert (
        call(
            "/api/nana-space/v1/messages",
            {"message_id": "x", "text": "test", "run_id": "old-run"},
        )[0]
        == 409
    )
    assert len(system["bridge"].receipts) == 0


def test_unknown_never_replays_and_owner_recovery_preserves_identity(system):
    call = system["call"]
    login(system)
    bridge = system["bridge"]
    original = bridge.core
    dispatches = []

    def lost(req):
        if req["operation"] == "surface":
            dispatches.append(req)
            original(req)
            raise TimeoutError("lost after dispatch")
        return original(req)

    bridge.core = lost
    body = {"message_id": "unknown-input", "text": "先别分析", "run_id": bridge.run_id}
    assert call("/api/nana-space/v1/messages", body)[1]["data"]["state"] == "UNKNOWN"
    assert call("/api/nana-space/v1/messages", body)[1]["data"]["state"] == "UNKNOWN"
    assert len(dispatches) == 1
    assert (
        call("/api/nana-space/v1/receipts/unknown-input")[1]["data"]["no_retry"] is True
    )
    bridge.core = original
    system["process"].kill()
    system["process"].wait(timeout=10)
    assert call("/api/nana-space/v1/snapshot")[0] == 503
    system["process"] = start_owner(system["home"], system["identity"])
    code, snapshot, _ = call("/api/nana-space/v1/snapshot")
    assert code == 200 and snapshot["subject_id"] == system["identity"]
    assert len(dispatches) == 1


def test_read_only_session_does_not_dispatch(system):
    system["bridge"].read_only = True
    login(system)
    assert (
        system["call"](
            "/api/nana-space/v1/messages",
            {"message_id": "x", "text": "hello", "run_id": system["bridge"].run_id},
        )[0]
        == 403
    )
    assert len(system["bridge"].receipts) == 0
