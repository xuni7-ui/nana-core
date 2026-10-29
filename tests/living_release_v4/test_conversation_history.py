from nana_core.life.application import LifeApplication
from nana_core.life.conversation import history
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_dialogue import relay
from tests.person_self.conftest import initialize
from tests.first_life_android_v2.test_http_integration import running as running, http, login, base


def test_source_supported_history_survives_restart_but_not_withdrawal(tmp_path):
    home = tmp_path / "home"
    initialize(home)
    clock = VirtualClock()
    with relay(home, "CHAT") as (router, _):
        with LifeApplication(home, clock=clock, router=router) as app:
            app.pause()
            turn = app.chat("PROJECT retained common experience", privacy="PROJECT", retain_shared_life=True)
            app.chat("PROJECT unretained transient wording", privacy="PROJECT")
            first = history(app, privacy=("PUBLIC", "PROJECT"))
            assert len(first["items"]) == 1
            assert first["items"][0]["exchange_record_id"] == turn["exchange_record_id"]
            assert first["items"][0]["user_text"] == "PROJECT retained common experience"
            assert history(app, privacy=("PUBLIC",))["items"] == []
        with LifeApplication(home, clock=clock, router=router) as app:
            assert history(app, privacy=("PROJECT",))["items"] == first["items"]
            app.forget(turn["message_memory_id"])
            assert history(app, privacy=("PROJECT",))["items"] == []


def test_actual_bff_history_is_role_scoped_and_receipts_never_replay(running):  # noqa:F811
    from nana_core.life.live_api.contracts import Completion, Role
    from nana_core.life.live_api.auth import Principal
    from nana_core.life.live_api.server import COOKIE
    server, service = running
    headers = login(server, service)
    receipt = http(server, "messages", "POST", {**base(service, "retained-turn"),
        "text": "先不聊这个话题", "retain_shared_life": True, "require_model": True}, headers)[1]
    assert receipt["data"]["state"] == "VERIFIED"
    source = receipt["data"]["result"]["message_memory_id"]
    first = http(server, "conversation/history", headers=headers)[1]
    assert len(first["data"]["items"]) == 1
    assert first["data"]["items"][0]["exchange_record_id"] == receipt["data"]["result"]["exchange_record_id"]
    bound = service.binding
    for field in ("scope", "entity_id"):
        service.binding = bound.model_copy(update={field: "another-bound-coordinate"})
        assert http(server, "conversation/history", headers=headers)[1]["data"]["items"] == []
    service.binding = bound
    assert http(server, "life/shares", headers=headers)[1]["data"]["external_delivery"] is False
    assert http(server, "platform/bilibili", headers=headers)[1]["data"]["items"] == []
    principal = Principal("reader.test", (Role.READER,), "WEB", None, service.auth.generation)
    token, _ = service.auth._session(principal)
    assert http(server, "conversation/history", headers={"Cookie": COOKIE+"="+token})[0] == 403
    service.ledger.reserve("pending-one", "host.web", {}, "MESSAGE", service.ledger.revision, "pending-one")
    service.ledger.transition("pending-one", Completion.UNKNOWN, dispatched=True)
    later = http(server, "conversation/history", headers=headers)[1]
    assert later["data"]["pending_receipts"] == [{"receipt_id": "pending-one", "state": "UNKNOWN"}]
    withdrawn = http(server, "privacy/withdrawal", "POST", {
        **base(service, "withdraw-source"), "operation": "WITHDRAW", "target_id": source}, headers)[1]
    assert withdrawn["data"]["state"] == "VERIFIED"
    assert http(server, "conversation/history", headers=headers)[1]["data"]["items"] == []
