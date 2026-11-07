"""Real HTTP → UDS → original owner/C → SSE provider fixture → live HTTP.

The test supervisor only supplies existing DEV coordinates; the actual Store,
owner, control socket, original C and network transports all execute.
"""

import http.client, json, threading, shutil, time
from types import SimpleNamespace
from nana_core.life.application import LifeApplication
from nana_core.life.control import ControlServer
from nana_core.life.live_api.auth import AuthService
from nana_core.life.live_api.bridge import GatewayService
from nana_core.life.live_api.contracts import Role
from nana_core.life.live_api.server import ApiServer, PREFIX
from tests.first_life_android_v2.test_supervisor import owned
from tests.first_life_android_v2.test_http_integration import login, ORIGIN, PW
from tests.independent_life.test_dialogue import relay


def test_complete_network_path_streams_before_provider_done_without_replacing_original_subject(tmp_path):
    home, binding, _ = owned(tmp_path)
    from nana_core.life.config import load_config, update_config

    cfg = load_config(home)
    update_config(
        home,
        cfg.model_copy(
            update={
                "revision": cfg.revision + 1,
                "provider_calls_per_day": 4,
                "provider_calls_per_hour": 4,
                "per_provider_calls_per_day": 4,
                "provider_total_calls_limit": 4,
            }
        ),
        expected_revision=cfg.revision,
    )
    release = threading.Event()
    finished = threading.Event()
    ready = threading.Event()
    stop = threading.Event()
    state = {}
    errors = []
    with relay(home, "CHAT", stream_fixture={"release": release, "finished": finished}) as (router, requests):
        shutil.copy2(home / "test-providers.json", home / "providers.json")

        def owner():
            try:
                with LifeApplication(home, router=router) as app, ControlServer(app) as control:
                    app.pause()
                    state.update(epoch=app.runtime.lease.epoch, identity=app.runtime.identity_id)
                    ready.set()
                    while not stop.is_set():
                        control.poll()
                        app.runtime.step()
                        stop.wait(0.005)
            except Exception as exc:
                errors.append(type(exc).__name__)
                ready.set()

        thread = threading.Thread(target=owner, daemon=True)
        thread.start()
        assert ready.wait(5) and not errors
        supervisor = SimpleNamespace(
            home=home,
            binding=binding,
            status=lambda: {"owner_epoch": state["epoch"], "process_ready": True},
            verify_binding=lambda: None,
        )
        service = GatewayService(
            supervisor, AuthService(tmp_path / "auth.json", password=PW, roles=tuple(Role)), tmp_path / "gateway"
        )
        server = ApiServer(("127.0.0.1", 0), service, public_origin=ORIGIN)
        http_thread = threading.Thread(target=server.serve_forever, daemon=True)
        http_thread.start()
        try:
            headers = login(server, service)
            body = {
                "client_request_id": "real-stream",
                "idempotency_key": "real-stream",
                "expected_revision": service.ledger.revision,
                "run_generation": service.generation,
                "owner_epoch": state["epoch"],
                "text": "SYNTHETIC live stream fixture",
                "privacy_class": "PROJECT",
                "require_model": True,
            }
            connection = http.client.HTTPConnection(*server.server_address, timeout=10)
            connection.request(
                "POST",
                PREFIX + "/messages/stream",
                json.dumps(body),
                {"Host": "space.test", "Content-Type": "application/json", **headers},
            )
            response = connection.getresponse()
            assert response.status == 200
            frames = []
            while True:
                raw = response.readline()
                assert raw, "missing final receipt"
                frame = json.loads(raw)
                frames.append(frame)
                if frame["event"] == "progress" and frame["data"]["data"].get("text"):
                    if not release.is_set():
                        assert not finished.is_set(), "must receive actual prefix before provider termination"
                        from tests.first_life_android_v2.test_http_integration import http as http_call, base
                        from nana_core.life.control import request

                        started = time.monotonic()
                        for op in ("PAUSE", "REVOKE"):
                            code, receipt, _ = http_call(
                                server, "commands", "POST", {**base(service, "during-" + op), "operation": op}, headers
                            )
                            assert code == 200 and receipt["data"]["state"] == "VERIFIED"
                            assert receipt["data"]["result"]["subject_desire_rewritten"] is False
                        refused = request(home, {"operation": "control", "command": "resume"}, timeout=2)
                        assert refused == {"ok": False, "code": "CLOUD_BUSY_PRE_DISPATCH"}
                        assert time.monotonic() - started < 2.5
                        assert not finished.is_set(), "controls must not wait for provider completion"
                        release.set()
                if frame["event"] == "receipt":
                    break
            connection.close()
            assert release.is_set()
            assert any(f["event"] == "progress" and f["data"]["data"].get("text") for f in frames)
            final = frames[-1]["data"]["data"]
            assert (
                final["state"] == "VERIFIED" and final["result"]["text"] == "A deliberately synthetic language response"
            )
            assert state["identity"] == binding.subject_id and len(requests) == 2
            assert all(f["data"]["subject_id"] == binding.subject_id for f in frames)
        finally:
            release.set()
            stop.set()
            thread.join(timeout=4)
            server.shutdown()
            server.server_close()
            http_thread.join(timeout=2)
    assert not errors
