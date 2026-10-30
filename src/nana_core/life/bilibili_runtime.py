"""Account events -> the original Surface/C -> governed Bilibili reply.

This is a finite account/peer binding, not a Bilibili brain. Private read and
retention are distinct opt-ins. Reads are bounded API pages; absence never means
old history did not exist. Original Store admissions/actions own restart state.
"""

from typing import Literal
from pydantic import Field, model_validator

from ..contracts import DTO, CoreError
from ..storage import digest
from ..continuity.autonomy.contracts import RealizationTarget
from ..continuity.open_agency.delivery import DeliveryAdmission, DeliveryPolicy, ReplyWindowBinding
from .platform_authority import PlatformActivation, require_platform_authority
from .bilibili_account import BilibiliAccountPolicy, BilibiliAccountTransport, BilibiliAccountRealization
from .surfaces import SurfaceObservation


class BilibiliChannelBinding(DTO):
    channel_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    binding_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    kind: Literal["dm", "comment"] = "dm"
    account_id: int = Field(ge=1)
    target_id: int = Field(ge=1)
    sender_id: int = Field(ge=1)
    cookie_ref: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    csrf_ref: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    enabled: bool = False
    read_authorized: bool = False
    send_authorized: bool = False
    private_read_authorized: bool = False
    retain_shared_life: bool = False
    max_events_per_hour: int = Field(default=12, ge=0, le=64)
    activation: PlatformActivation | None = None

    @model_validator(mode="after")
    def same_private_peer(self):
        if self.kind == "dm" and self.sender_id != self.target_id:
            raise ValueError("DM sender must be the bound recipient")
        return self


class BilibiliReplyWorkflow:
    def __init__(self, app, channel, transport):
        self.app, self.runtime, self.store, self.channel, self.transport = (
            app,
            app.runtime,
            app.runtime.store,
            channel,
            transport,
        )
        self.privacy = "PERSONAL" if channel.kind == "dm" else "PUBLIC"
        b = app.surfaces._binding(channel.binding_id)
        if (
            b.mode != "PLATFORM_ADAPTER_NO_SEND"
            or b.platform != "bilibili.account"
            or self.privacy not in b.permitted_privacy
        ):
            raise CoreError("BILIBILI_SURFACE_OR_PRIVACY_UNBOUND")
        self.resource = "project://bilibili/" + channel.kind + "/" + str(channel.target_id)
        self.target = RealizationTarget(
            capability="bilibili." + channel.kind + ".send",
            resource=self.resource,
            operation="WRITE",
            resource_class="ORDINARY",
        )
        self.thread = "bili." + channel.kind + "." + str(channel.target_id)
        delivery = DeliveryAdmission(
            self.store,
            DeliveryPolicy(
                recipients=(self.resource,),
                privacy_classes=(self.privacy,),
                direct_reply_bindings=(
                    ReplyWindowBinding(
                        resource=self.resource,
                        binding_id=channel.binding_id,
                        platform="bilibili.account",
                        thread_id=self.thread,
                    ),
                ),
            ),
            scopes=app.runtime.config.scopes,
            privacy_classes=(self.privacy,),
        )
        self.realization = BilibiliAccountRealization(
            self.store, transport, app.runtime.authority, app=app, activation=channel.activation, delivery=delivery
        )

    def _authority(self):
        if self.transport.realm == "SYNTHETIC_LOOPBACK":
            return
        if self.channel.activation is None or self.channel.activation.binding_id != self.channel.binding_id:
            raise CoreError("BILIBILI_CANONICAL_ACTIVATION_REQUIRED")
        require_platform_authority(
            self.app,
            self.channel.activation,
            channel="bilibili",
            exclusive_writer=self.channel.send_authorized,
            account_id=self.channel.account_id,
        )

    def _fetch(self, message_id):
        if self.channel.kind == "dm" and not self.channel.private_read_authorized:
            raise CoreError("BILIBILI_PRIVATE_READ_NOT_AUTHORIZED")
        self.transport.account()
        if self.channel.kind == "dm":
            rows = self.transport.messages(self.channel.target_id)
            row = next((r for r in rows if r["message_key"] == message_id), None)
            if row is None:
                raise CoreError("BILIBILI_MESSAGE_NOT_IN_BOUNDED_PAGE")
            if row["sender_id"] != self.channel.sender_id or row["receiver_id"] != self.channel.account_id:
                raise CoreError("BILIBILI_INCOMING_PEER_MISMATCH")
            return row["text"], row["sequence"], 0
        rows = self.transport.comment_rows(self.channel.target_id)
        row = next((r for r in rows if str(r.get("rpid")) == message_id), None)
        if row is None:
            raise CoreError("BILIBILI_COMMENT_NOT_IN_BOUNDED_PAGE")
        if str((row.get("member") or {}).get("mid")) != str(self.channel.sender_id):
            raise CoreError("BILIBILI_INCOMING_PEER_MISMATCH")
        text = (row.get("content") or {}).get("message")
        if type(text) is not str or not 1 <= len(text) <= 2048:
            raise CoreError("BILIBILI_COMMENT_CONTENT_BOUND")
        root = int(row.get("root") or message_id)
        return text, 0, root

    def receive(self, message_id):
        c = self.channel
        if not c.enabled or not c.read_authorized:
            raise CoreError("BILIBILI_CHANNEL_DISABLED_OR_NOT_AUTHORIZED")
        if c.kind == "dm" and not c.private_read_authorized:
            raise CoreError("BILIBILI_PRIVATE_READ_NOT_AUTHORIZED")
        self._authority()
        b = self.app.surfaces._binding(c.binding_id)
        event_id = "bili." + c.kind + ":" + digest(message_id)
        key = "local.surface." + digest([b.platform, b.adapter, b.surface, digest([b.binding_id, event_id])])
        prior = self.store.db.execute(
            "SELECT cy.* FROM subject_cycles cy JOIN subject_events e ON e.subject_event_id=cy.subject_event_id WHERE e.source_key=?",
            (key,),
        ).fetchone()
        if prior:
            cycle = self.runtime.subject.result(dict(prior))
            action = self.store.db.execute(
                "SELECT action_id FROM actions WHERE effect_slot=?", ("subject:" + cycle.intention_id,)
            ).fetchone()
            if not action:
                return {
                    "platform": "bilibili",
                    "delivery": "NO_SOCIAL_DISPATCH_REPLY_NOT_REPLAYED",
                    "external_delivery": False,
                }
            state = self.realization.dispatch(cycle.intention_id, action[0], expected_revision=1)
            return {
                "platform": "bilibili",
                "delivery": state,
                "action_id": action[0],
                "external_delivery": state == "SUCCEEDED",
                "resent": False,
            }
        reservation = digest([c.channel_id, message_id])
        if self.store.db.execute(
            "SELECT 1 FROM events WHERE source_namespace='platform.bilibili.ingress' AND source_key=?", (reservation,)
        ).fetchone():
            return {
                "platform": "bilibili",
                "delivery": "UNKNOWN_INPUT_ADMISSION_NO_AUTORETRY",
                "external_delivery": False,
            }
        count = self.store.db.execute(
            "SELECT count(*) FROM events WHERE kind='platform.bilibili.ingress_reserved' AND recorded_at_us>=? "
            "AND json_extract(data_json,'$.data.channel_id')=?",
            (self.store.clock.utc_now_us() - 3600_000000, c.channel_id),
        ).fetchone()[0]
        if count >= c.max_events_per_hour:
            raise CoreError("BILIBILI_INBOUND_HOURLY_CEILING")
        from .platform_runtime import reserve_inbound_read

        reserve_inbound_read(self.realization.kernel, 2, "bilibili", c.channel_id, reservation)
        self.transport.calls = 0
        text, sequence, root = self._fetch(message_id)
        result = self.app.surfaces.receive(
            SurfaceObservation(
                binding_id=c.binding_id,
                event_id=event_id,
                thread_id=self.thread,
                text=text,
                privacy_class=self.privacy,
                origin=self.transport.realm,
                retain_shared_life=c.retain_shared_life,
            ),
            reply_target=self.target if c.send_authorized else None,
        )
        return self._reply(result, message_id, sequence, root)

    def _reply(self, result, message_id, sequence, root):
        c = self.channel
        row = self.store.db.execute("SELECT * FROM subject_cycles WHERE cycle_id=?", (result["cycle_id"],)).fetchone()
        cycle = self.runtime.subject.result(dict(row))
        eligible = (
            cycle.evaluation
            and cycle.evaluation.normative == "ENDORSED"
            and cycle.intention.kind in {"SOCIAL_INTERACTION", "DISAGREE", "ACTION_PROPOSAL"}
        )
        if (
            not c.send_authorized
            or result.get("render_state") != "UNVERIFIED_MODEL_WORDING"
            or not eligible
            or len(result["text"]) > 1024
        ):
            intention = self.store.one("subject_intentions", cycle.intention_id)
            if intention and intention["state"] == "PENDING":
                self.runtime.subject.transition_intention(
                    cycle.intention_id, expected_revision=intention["revision"], state="DEFERRED"
                )
            return {**result, "delivery": "C_SILENCE_OR_REPLY_UNAVAILABLE", "external_delivery": False}
        candidate = {
            "candidate_digest": digest([result["text"], cycle.record_id, self.privacy]),
            "cycle_record_id": cycle.record_id,
        }
        admission = self.realization.port.delivery.assess_reply(
            cycle, self.resource, payload=candidate, source_memory_ids=(result["message_memory_id"],)
        )
        intention = self.store.one("subject_intentions", cycle.intention_id)
        _, action = self.realization.propose(
            cycle.intention_id,
            expected_revision=intention["revision"],
            args={
                "target_id": c.target_id,
                "text": result["text"],
                "after_seqno": sequence,
                "root_reply_id": root,
                "parent_reply_id": int(message_id) if c.kind == "comment" else None,
                "data_privacy": self.privacy,
                "data": candidate,
                "admission_id": admission["record_id"],
            },
            input_memory_ids=(result["message_memory_id"],),
        )
        if not action:
            return {**result, "delivery": "BLOCKED_MANAGER", "external_delivery": False}
        state = self.realization.dispatch(cycle.intention_id, action, expected_revision=intention["revision"])
        if state == "SUCCEEDED":
            current = self.store.one("subject_intentions", cycle.intention_id)
            if current["state"] == "PENDING":
                self.runtime.subject.transition_intention(
                    cycle.intention_id, expected_revision=current["revision"], state="COMPLETED"
                )
        return {**result, "delivery": state, "action_id": action, "external_delivery": state == "SUCCEEDED"}


def account_message(app, resolver, channel_id, message_id):
    channels = [c for c in app.config.bilibili_channels if c.channel_id == channel_id]
    if len(channels) != 1:
        raise CoreError("BILIBILI_CHANNEL_UNBOUND")
    channel = channels[0]
    if not channel.enabled or not channel.read_authorized:
        raise CoreError("BILIBILI_CHANNEL_DISABLED_OR_NOT_AUTHORIZED")
    if resolver is None:
        raise CoreError("BILIBILI_EXPLICIT_RESOLVER_REQUIRED")
    transport = BilibiliAccountTransport(
        resolver,
        cookie_ref=channel.cookie_ref,
        csrf_ref=channel.csrf_ref,
        policy=BilibiliAccountPolicy(
            channel.account_id,
            read_authorized=channel.read_authorized,
            send_authorized=channel.send_authorized,
            exclusive_writer_confirmed=bool(channel.activation and channel.activation.exclusive_writer_confirmed),
            permitted_recipients=(channel.target_id,) if channel.kind == "dm" else (),
            request_limit=8,
        ),
        realm="AUTHENTICATED_PLATFORM",
    )
    return BilibiliReplyWorkflow(app, channel, transport).receive(message_id)
