"""One original owner, two actual owned HTTP transports, no real account/LLM."""

from nana_core.contracts import GrantSpec
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config, update_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.platform_runtime import QQChannelBinding
from nana_core.life.bilibili_runtime import BilibiliChannelBinding
from nana_core.presence.authority import VirtualClock
from tests.person_self.conftest import initialize
from tests.independent_life.test_dialogue import relay
from tests.living_release_v4.test_platform_bridge import counterpart as qq_counterpart
from tests.living_release_v4.test_platform_runtime import equip
from nana_core.life.platform_runtime import QQReplyWorkflow
from nana_core.life.bilibili_runtime import BilibiliReplyWorkflow
from tests.living_release_v4.bilibili_loopback import counterpart as bili_counterpart
from tests.living_release_v4.test_bilibili_runtime import equipped


def test_same_original_subject_dispatches_two_platforms_and_restart_reads_only_receipts(tmp_path):
    home = tmp_path / "home"
    initialize(home)
    cfg = load_config(home)
    clock = VirtualClock()
    qq = SurfaceBinding(
        binding_id="qq.primary",
        platform="qq.onebot",
        surface="chat.direct",
        adapter="qq.onebot",
        mode="PLATFORM_ADAPTER_NO_SEND",
        permitted_privacy=("PROJECT",),
    )
    bili = SurfaceBinding(
        binding_id="bilibili.primary",
        platform="bilibili.account",
        surface="chat.direct",
        adapter="bilibili.account",
        mode="PLATFORM_ADAPTER_NO_SEND",
        permitted_privacy=("PUBLIC",),
    )
    update_config(
        home,
        cfg.model_copy(update={"revision": cfg.revision + 1, "surface_bindings": (qq, bili)}),
        expected_revision=cfg.revision,
    )
    with (
        qq_counterpart() as (url, qq_state),
        bili_counterpart() as (opener, bili_state),
        relay(home, "CHAT") as (router, calls),
    ):
        qc = QQChannelBinding(
            channel_id="primary",
            binding_id=qq.binding_id,
            endpoint=url,
            account_id="42",
            sender_id="43",
            target_id="43",
            enabled=True,
            read_authorized=True,
            send_authorized=True,
        )
        bc = BilibiliChannelBinding(
            channel_id="primary",
            binding_id=bili.binding_id,
            kind="comment",
            account_id=42,
            sender_id=43,
            target_id=7,
            cookie_ref="test.cookie",
            csrf_ref="test.csrf",
            enabled=True,
            read_authorized=True,
            send_authorized=True,
        )
        bili_state["comments"] = [
            {"rpid": 9, "root": 0, "member": {"mid": 43}, "content": {"message": "Independent public project message"}}
        ]

        def flows(app):
            q = equip(app, qc, url)
            b = equipped(app, bc, opener.endpoint, grant=False)
            b.realization.kernel.grant(
                GrantSpec(
                    capabilities=("bilibili.comment.send", "bilibili.action.verify"),
                    resources=(b.resource,),
                    not_before_us=clock.utc_now_us(),
                    expires_at_us=clock.utc_now_us() + 100_000000,
                ),
                app.runtime.authority,
            )
            return q, b

        with LifeApplication(home, clock=clock, router=router) as app:
            app.pause()
            q, b = flows(app)
            identity = app.runtime.identity_id
            assert q.receive("1")["delivery"] == "SUCCEEDED"
            assert b.receive("9")["delivery"] == "SUCCEEDED"
            assert len(calls) == 4 and len(qq_state["sent"]) == bili_state["posts"] == 1
            assert app.runtime.store.db.execute("SELECT count(*) FROM subject_cycles").fetchone()[0] == 2
            assert not app.runtime.store.db.execute("PRAGMA foreign_key_check").fetchall()
        counts = (len(qq_state["calls"]), len(bili_state["requests"]))
        qq_transport, bili_transport = q.transport, b.transport
        with LifeApplication(home, clock=clock, router=router) as app:
            app.pause()
            q, b = QQReplyWorkflow(app, qc, qq_transport), BilibiliReplyWorkflow(app, bc, bili_transport)
            assert app.runtime.identity_id == identity
            assert q.receive("1")["delivery"] == b.receive("9")["delivery"] == "SUCCEEDED"
            assert counts == (len(qq_state["calls"]), len(bili_state["requests"])) and len(calls) == 4
