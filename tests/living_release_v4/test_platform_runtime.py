"""Actual original chat/C -> original Kernel -> owned HTTP counterpart.

No prewritten C cycle or real account; synthetic model wording and owned effects
are explicitly independent from real-platform/provider/human qualification.
"""

import pytest

from nana_core.contracts import GrantSpec, CoreError
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config, update_config
from nana_core.life.platform_runtime import QQChannelBinding, QQReplyWorkflow
from nana_core.life.surfaces import SurfaceBinding, SurfaceObservation
from nana_core.presence.authority import VirtualClock
from tests.person_self.conftest import initialize
from tests.independent_life.test_dialogue import relay
from tests.living_release_v4.test_platform_bridge import counterpart, transport


def initialize_channel(home, url):
    initialize(home)
    cfg = load_config(home)
    binding = SurfaceBinding(
        binding_id="qq.primary",
        platform="qq.onebot",
        surface="chat.direct",
        adapter="qq.onebot",
        mode="PLATFORM_ADAPTER_NO_SEND",
        permitted_privacy=("PROJECT",),
    )
    update_config(
        home,
        cfg.model_copy(update={"revision": cfg.revision + 1, "surface_bindings": (binding,)}),
        expected_revision=cfg.revision,
    )
    return QQChannelBinding(
        channel_id="primary",
        binding_id=binding.binding_id,
        endpoint=url,
        account_id="42",
        sender_id="43",
        target_id="43",
        enabled=True,
        read_authorized=True,
        send_authorized=True,
    )


def equip(app, channel, url, *, with_grant=True):
    flow = QQReplyWorkflow(app, channel, transport(url))
    GovernanceController(app.runtime.store, app.runtime.authority).initialize(app.runtime.authority)
    flow.realization.kernel.set_budgets(
        {"external_requests": 16, "write_attempts": 4, "cost_micro_units": 16}, app.runtime.authority
    )
    if with_grant:
        flow.realization.kernel.grant(
            GrantSpec(
                capabilities=("world.contact", "world.action.verify"),
                resources=(flow.resource,),
                not_before_us=app.runtime.clock.utc_now_us(),
                expires_at_us=app.runtime.clock.utc_now_us() + 100_000000,
            ),
            app.runtime.authority,
        )
    return flow


def test_original_natural_reply_completes_actual_owned_send_and_duplicate_is_receipt_only(tmp_path):
    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        with (
            relay(home, "CHAT") as (router, requests),
            LifeApplication(home, clock=VirtualClock(), router=router) as app,
        ):
            app.pause()
            flow = equip(app, channel, url)
            result = flow.receive("1")
            assert result["delivery"] == "SUCCEEDED" and result["external_delivery"]
            assert len(requests) == 2 and len(platform["sent"]) == 1
            assert platform["sent"][0]["message"] == [
                {"type": "text", "data": {"text": "A deliberately synthetic language response"}}
            ]
            calls = len(platform["calls"])
            assert flow.receive("1")["delivery"] == "SUCCEEDED"
            assert len(platform["calls"]) == calls and len(requests) == 2


def test_unknown_restart_does_not_refetch_reinterpret_or_resend(tmp_path):
    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        clock = VirtualClock()
        with relay(home, "CHAT") as (router, requests):
            with LifeApplication(home, clock=clock, router=router) as app:
                app.pause()
                flow = equip(app, channel, url)
                platform["lose_ack"] = True
                result = flow.receive("1")
                assert result["delivery"] == "UNKNOWN" and not result["external_delivery"]
                calls = len(platform["calls"])
                identity = app.runtime.identity_id
            with LifeApplication(home, clock=clock, router=router) as app:
                app.pause()
                flow = QQReplyWorkflow(app, channel, transport(url))
                later = flow.receive("1")
                assert later["delivery"] == "UNKNOWN"
                assert len(platform["calls"]) == calls and len(platform["sent"]) == 1 and len(requests) == 2
                assert app.runtime.identity_id == identity


def test_direct_reply_window_is_not_a_grant_or_proactive_permission(tmp_path):
    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        with relay(home, "CHAT") as (router, _), LifeApplication(home, clock=VirtualClock(), router=router) as app:
            app.pause()
            flow = equip(app, channel, url, with_grant=False)
            with pytest.raises(CoreError, match="AUTH_REQUIRED"):
                flow.receive("1")
            assert platform["sent"] == []
            assert not app.runtime.store.all("grants")


def test_reply_source_window_and_peer_cannot_authorize_other_or_later_delivery(tmp_path):
    from nana_core.continuity.open_agency.delivery import DeliveryAdmission, DeliveryPolicy, ReplyWindowBinding

    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        clock = VirtualClock()
        with relay(home, "CHAT") as (router, _), LifeApplication(home, clock=clock, router=router) as app:
            app.pause()
            flow = equip(app, channel, url)
            result = app.surfaces.receive(
                SurfaceObservation(
                    binding_id=channel.binding_id,
                    event_id="test:window",
                    thread_id="qq.private.43",
                    text="PROJECT reply window",
                    privacy_class="PROJECT",
                    origin="SYNTHETIC_LOOPBACK",
                ),
                reply_target=flow.target,
            )
            row = app.runtime.store.db.execute(
                "SELECT * FROM subject_cycles WHERE cycle_id=?", (result["cycle_id"],)
            ).fetchone()
            cycle = app.runtime.subject.result(dict(row))
            admission = flow.port.delivery
            assert admission.assess(cycle, flow.resource)["result"] == "UNKNOWN_AVAILABILITY"
            wrong = DeliveryAdmission(
                app.runtime.store,
                DeliveryPolicy(
                    recipients=(flow.resource,),
                    privacy_classes=("PROJECT",),
                    direct_reply_bindings=(
                        ReplyWindowBinding(
                            resource=flow.resource,
                            binding_id=channel.binding_id,
                            platform="qq.onebot",
                            thread_id="qq.private.44",
                        ),
                    ),
                ),
                scopes=app.runtime.config.scopes,
                privacy_classes=("PROJECT",),
            )
            with pytest.raises(CoreError, match="DIRECT_REPLY_PEER_UNBOUND"):
                wrong.assess_reply(cycle, flow.resource)
            clock.advance(61_000000)
            with pytest.raises(CoreError, match="DIRECT_REPLY_WINDOW_EXPIRED"):
                admission.assess_reply(cycle, flow.resource)
            assert not platform["sent"]


def test_source_read_uses_original_budget_and_cannot_dispatch_when_exhausted(tmp_path):
    with counterpart() as (url, platform):
        home = tmp_path / "home"
        channel = initialize_channel(home, url)
        with LifeApplication(home, clock=VirtualClock()) as app:
            app.pause()
            flow = equip(app, channel, url)
            flow.realization.kernel.set_budgets(
                {"external_requests": 1, "cost_micro_units": 1, "write_attempts": 4}, app.runtime.authority
            )
            with pytest.raises(CoreError, match="BUDGET_EXHAUSTED"):
                flow.receive("1")
            assert platform["calls"] == [] and not platform["sent"]
            assert not app.runtime.store.db.execute("SELECT 1 FROM events WHERE kind='platform.qq.ingress_reserved'").fetchone()


def test_channel_bound_is_given_before_rendering_not_mechanical_post_split(tmp_path):
    with counterpart() as (url, platform):
        home=tmp_path/'home';channel=initialize_channel(home,url)
        def render(request):
            limit=request['role_input']['dialogue'].get('reply_character_limit',16384)
            return 'SYNTHETIC bounded channel reply' if limit==2048 else 'SYNTHETIC long channel wording '*100
        with relay(home,'CHAT',renderer=render) as (router,requests), LifeApplication(home,clock=VirtualClock(),router=router) as app:
            app.pause();flow=equip(app,channel,url)
            result=flow.receive('1')
            assert result['delivery']=='SUCCEEDED' and len(platform['sent'])==1
            assert requests[-1]['role_input']['dialogue']['reply_character_limit']==2048
            assert requests[-1]['expected_schema']['$defs']['DialogueDraft']['properties']['text']['anyOf'][0]['maxLength']==2048
            assert platform['sent'][0]['message']==[{'type':'text','data':{'text':'SYNTHETIC bounded channel reply'}}]
            assert len(requests)==2


def test_oversized_channel_reply_is_rejected_before_sending_without_split_or_retry(tmp_path):
    with counterpart() as (url, platform):
        home=tmp_path/'home';channel=initialize_channel(home,url)
        with relay(home,'CHAT',renderer=lambda request:'SYNTHETIC oversized channel reply '*100) as (router,requests), LifeApplication(home,clock=VirtualClock(),router=router) as app:
            app.pause();flow=equip(app,channel,url)
            result=flow.receive('1')
            assert result['render_state']=='DIALOGUE_REPLY_BOUND'
            assert result['delivery']=='NOT_AUTHORIZED_OR_NO_MODEL_WORDING'
            assert not platform['sent'] and len(requests)==2
            assert not app.runtime.store.all('actions')
            flow.receive('1')
            assert not platform['sent'] and len(requests)==2
