import json
import pytest

from nana_core.contracts import CoreError, GrantSpec
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config, update_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.bilibili_account import BilibiliAccountTransport, BilibiliAccountPolicy
from nana_core.life.bilibili_runtime import BilibiliChannelBinding, BilibiliReplyWorkflow
from nana_core.life.secret_binding import MemorySecretResolver
from nana_core.presence.authority import VirtualClock
from tests.person_self.conftest import initialize
from tests.independent_life.test_dialogue import relay
from tests.living_release_v4.bilibili_loopback import counterpart


def channel(home):
    initialize(home)
    cfg = load_config(home)
    b = SurfaceBinding(
        binding_id="bili.primary",
        platform="bilibili.account",
        surface="chat.direct",
        adapter="bili.account",
        mode="PLATFORM_ADAPTER_NO_SEND",
        permitted_privacy=("PERSONAL",),
    )
    update_config(
        home,
        cfg.model_copy(update={"revision": cfg.revision + 1, "surface_bindings": (b,)}),
        expected_revision=cfg.revision,
    )
    return BilibiliChannelBinding(
        channel_id="primary",
        binding_id=b.binding_id,
        account_id=42,
        target_id=43,
        sender_id=43,
        cookie_ref="test.cookie",
        csrf_ref="test.csrf",
        enabled=True,
        read_authorized=True,
        send_authorized=True,
        private_read_authorized=True,
    )


def equipped(app, c, url, *, grant=True):
    secrets = MemorySecretResolver()
    secrets.bind("test.cookie", "TEST_ONLY_NOT_SECRET_COOKIE")
    secrets.bind("test.csrf", "TESTONLYNOTSECRET0123456789")
    transport = BilibiliAccountTransport(
        secrets,
        cookie_ref=c.cookie_ref,
        csrf_ref=c.csrf_ref,
        policy=BilibiliAccountPolicy(
            42,
            read_authorized=True,
            send_authorized=True,
            exclusive_writer_confirmed=True,
            permitted_recipients=(43,),
            request_limit=12,
        ),
        realm="SYNTHETIC_LOOPBACK",
        loopback_endpoint=url,
    )
    flow = BilibiliReplyWorkflow(app, c, transport)
    GovernanceController(app.runtime.store, app.runtime.authority).initialize(app.runtime.authority)
    flow.realization.kernel.set_budgets(
        {"external_requests": 16, "write_attempts": 4, "cost_micro_units": 16}, app.runtime.authority
    )
    if grant:
        flow.realization.kernel.grant(
            GrantSpec(
                capabilities=("bilibili.dm.send", "bilibili.action.verify"),
                resources=(flow.resource,),
                not_before_us=app.runtime.clock.utc_now_us(),
                expires_at_us=app.runtime.clock.utc_now_us() + 100_000000,
            ),
            app.runtime.authority,
        )
    return flow


def incoming(platform):
    platform["messages"] = [
        {
            "msg_key": "incoming-1",
            "msg_seqno": 1,
            "sender_uid": 43,
            "receiver_id": 42,
            "content": json.dumps({"content": "Owned synthetic direct message"}),
            "timestamp": 1,
        }
    ]


def test_real_core_chat_to_account_dm_once_with_current_identity_verify_and_privacy(tmp_path):
    with counterpart() as (opener, platform):
        home = tmp_path / "home"
        c = channel(home)
        incoming(platform)
        with relay(home, "CHAT") as (router, calls), LifeApplication(home, clock=VirtualClock(), router=router) as app:
            app.pause()
            flow = equipped(app, c, opener.endpoint)
            result = flow.receive("incoming-1")
            assert result["delivery"] == "SUCCEEDED" and platform["posts"] == 1 and len(calls) == 2
            assert app.runtime.store.one("budgets", "external_requests")["spent"] == 7  # inbound2 + execute3 + verify2
            count = len(platform["requests"])
            assert flow.receive("incoming-1")["delivery"] == "SUCCEEDED"
            assert platform["posts"] == 1 and len(calls) == 2 and len(platform["requests"]) == count


def test_dm_ack_unknown_survives_owner_restart_without_new_send_or_model(tmp_path):
    with counterpart() as (opener, platform):
        home = tmp_path / "home"
        c = channel(home)
        incoming(platform)
        clock = VirtualClock()
        with relay(home, "CHAT") as (router, calls):
            with LifeApplication(home, clock=clock, router=router) as app:
                app.pause()
                flow = equipped(app, c, opener.endpoint)
                platform["lose_response"] = True
                result = flow.receive("incoming-1")
                assert result["delivery"] == "UNKNOWN" and platform["posts"] == 1
                identity = app.runtime.identity_id
            with LifeApplication(home, clock=clock, router=router) as app:
                app.pause()
                flow = equipped(app, c, opener.endpoint)
                assert flow.receive("incoming-1")["delivery"] == "UNKNOWN"
                assert platform["posts"] == 1 and len(calls) == 2 and app.runtime.identity_id == identity


def test_dm_private_read_and_grant_are_separate(tmp_path):
    with counterpart() as (opener, platform):
        home = tmp_path / "home"
        c = channel(home)
        incoming(platform)
        with relay(home, "CHAT") as (router, _), LifeApplication(home, clock=VirtualClock(), router=router) as app:
            app.pause()
            flow = equipped(app, c.model_copy(update={"private_read_authorized": False}), opener.endpoint)
            with pytest.raises(CoreError, match="BILIBILI_PRIVATE_READ_NOT_AUTHORIZED"):
                flow.receive("incoming-1")
            assert platform["posts"] == 0 and platform["requests"] == []


def test_public_comment_original_c_reply_uses_exact_thread_and_independent_verify(tmp_path):
    with counterpart() as (opener, platform):
        home = tmp_path / "home"
        c = channel(home)
        cfg = load_config(home)
        b = cfg.surface_bindings[0].model_copy(update={"permitted_privacy": ("PUBLIC",)})
        update_config(
            home,
            cfg.model_copy(update={"revision": cfg.revision + 1, "surface_bindings": (b,)}),
            expected_revision=cfg.revision,
        )
        c = c.model_copy(update={"kind": "comment", "target_id": 7, "private_read_authorized": False})
        platform["comments"] = [
            {"rpid": 9, "root": 0, "member": {"mid": 43}, "content": {"message": "Public project source question"}}
        ]
        with relay(home, "CHAT") as (router, calls), LifeApplication(home, clock=VirtualClock(), router=router) as app:
            app.pause()
            flow = equipped(app, c, opener.endpoint, grant=False)
            flow.realization.kernel.grant(
                GrantSpec(
                    capabilities=("bilibili.comment.send", "bilibili.action.verify"),
                    resources=(flow.resource,),
                    not_before_us=app.runtime.clock.utc_now_us(),
                    expires_at_us=app.runtime.clock.utc_now_us() + 100_000000,
                ),
                app.runtime.authority,
            )
            result = flow.receive("9")
            assert result["delivery"] == "SUCCEEDED" and platform["posts"] == 1 and len(calls) == 2
            sent = platform["comments"][-1]
            assert sent["root"] == sent["parent"] == 9
            assert any("/x/v2/reply/reply?" in path and "root=9" in path for method, path in platform["requests"])
