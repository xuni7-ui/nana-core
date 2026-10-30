"""Explicit QQ host binding on the existing owner, not another platform brain.

The inbound transport independently fetches account/message identity. Core alone
interprets/judges/renders; original Manager/Grant/Kernel/Verify deliver at most
once. Lost wording and ambiguous effects are parked, never regenerated/replayed.
No credential discovery, new Subject, Store, scheduler or automatic Grant.
"""

from typing import Literal
from pydantic import Field

from ..contracts import CoreError, DTO
from ..storage import digest
from ..continuity.autonomy.contracts import RealizationTarget
from ..continuity.open_agency.delivery import DeliveryAdmission, DeliveryPolicy, ReplyWindowBinding
from .platform_authority import PlatformActivation
from .platform_bridge import OneBotHTTPTransport, QQIngress, QQCapabilityPort, QQGovernedDelivery


def reserve_inbound_read(kernel, requests, channel, channel_id, reservation):
    """Spend the original external/cost ceilings before trusted connector I/O.

    Input observation does not invent an action/goal or Grant. Its explicitly
    permitted reads still consume the same resource ledger as the ActionKernel.
    Ambiguous/failed reads retain the conservative reservation, including crash.
    """
    with kernel.store.transaction(
        "platform." + channel + ".ingress_reserved",
        {"channel_id": channel_id, "request_ceiling": requests},
        source_namespace="platform." + channel + ".ingress",
        source_key=reservation,
    ) as tx:
        amounts = {"external_requests": requests, "cost_micro_units": requests}
        # These are source observations, not action attempts. Spend atomically
        # in the original budget rows; do not invent an attempts/FK identity.
        for dimension, amount in amounts.items():
            budget = kernel.store.one("budgets", dimension)
            if not budget or budget["spent"] + budget["held"] + amount > budget["limit_value"]:
                raise CoreError("BUDGET_EXHAUSTED")
            tx.update("budgets", dimension, spent=budget["spent"] + amount)


class QQChannelBinding(DTO):
    channel_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    binding_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    endpoint: str = Field(min_length=1, max_length=256)
    account_id: str = Field(pattern=r"^[0-9]{1,20}$")
    sender_id: str = Field(pattern=r"^[0-9]{1,20}$")
    target_kind: Literal["private", "group"] = "private"
    target_id: str = Field(pattern=r"^[0-9]{1,20}$")
    credential_ref: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    enabled: bool = False
    read_authorized: bool = False
    send_authorized: bool = False
    private_read_authorized: bool = False
    privacy_class: Literal["PUBLIC", "PROJECT", "PERSONAL"] = "PROJECT"
    activation: PlatformActivation | None = None
    max_events_per_hour: int = Field(default=24, ge=0, le=128)


class QQReplyWorkflow:
    def __init__(self, app, channel, transport):
        self.app, self.runtime, self.channel, self.transport = app, app.runtime, channel, transport
        self.store = app.runtime.store
        self.resource = "project://qq/" + channel.channel_id
        self.target = RealizationTarget(
            capability="world.contact", resource=self.resource, operation="CONTACT", resource_class="ORDINARY"
        )
        self.ingress = QQIngress(
            app,
            transport,
            channel.binding_id,
            channel.sender_id,
            privacy=channel.privacy_class,
            private_read_authorized=channel.private_read_authorized,
            target_kind=channel.target_kind,
            target_id=channel.target_id,
            activation=channel.activation,
        )
        delivery = DeliveryAdmission(
            self.store,
            DeliveryPolicy(
                recipients=(self.resource,),
                privacy_classes=(channel.privacy_class,),
                direct_reply_bindings=(
                    ReplyWindowBinding(
                        resource=self.resource,
                        binding_id=channel.binding_id,
                        platform="qq.onebot",
                        thread_id="qq." + channel.target_kind + "." + channel.target_id,
                    ),
                ),
            ),
            scopes=app.runtime.config.scopes,
            privacy_classes=(channel.privacy_class,),
        )
        self.port = QQCapabilityPort(
            self.store,
            transport,
            {self.resource: (channel.target_kind, channel.target_id)},
            host_enabled=True,
            app=app,
            activation=channel.activation,
            delivery=delivery,
        )
        self.realization = QQGovernedDelivery(self.port, app.runtime.authority, host_enabled=True)

    def receive(self, message_id):
        if not self.channel.enabled or not self.channel.read_authorized:
            raise CoreError("QQ_CHANNEL_DISABLED_OR_NOT_AUTHORIZED")
        binding = self.app.surfaces._binding(self.channel.binding_id)
        event_key = "local.surface." + digest(
            [binding.platform, binding.adapter, binding.surface, digest([binding.binding_id, "qq:" + str(message_id)])]
        )
        prior = self.store.db.execute(
            "SELECT c.* FROM subject_cycles c JOIN subject_events e ON e.subject_event_id=c.subject_event_id "
            "WHERE e.source_key=?",
            (event_key,),
        ).fetchone()
        if prior:
            cycle = self.runtime.subject.result(dict(prior))
            action = self.store.db.execute(
                "SELECT action_id FROM actions WHERE effect_slot=?", ("subject:" + cycle.intention_id,)
            ).fetchone()
            if not action:
                return {
                    "platform": "qq",
                    "delivery": "NO_SOCIAL_DISPATCH_REPLY_NOT_REPLAYED",
                    "external_delivery": False,
                }
            state = self.realization.dispatch(cycle.intention_id, action[0], expected_revision=1)
            return {
                "platform": "qq",
                "action_id": action[0],
                "delivery": state,
                "replayed_semantics": False,
                "resent": False,
                "external_delivery": state == "SUCCEEDED",
            }
        now = self.store.clock.utc_now_us()
        # Body-free original admission journal survives source erasure; deletion
        # is not a quota refund and a crash is not permission to replay input.
        reservation = digest([self.channel.channel_id, str(message_id)])
        if self.store.db.execute(
            "SELECT 1 FROM events WHERE source_namespace='platform.qq.ingress' AND source_key=?", (reservation,)
        ).fetchone():
            return {"platform": "qq", "delivery": "UNKNOWN_INPUT_ADMISSION_NO_AUTORETRY", "external_delivery": False}
        count = self.store.db.execute(
            "SELECT count(*) FROM events WHERE kind='platform.qq.ingress_reserved' AND recorded_at_us>=? "
            "AND json_extract(data_json,'$.data.channel_id')=?",
            (now - 3600_000000, self.channel.channel_id),
        ).fetchone()[0]
        if count >= self.channel.max_events_per_hour:
            raise CoreError("QQ_INBOUND_HOURLY_CEILING")
        reserve_inbound_read(self.realization.kernel, 2, "qq", self.channel.channel_id, reservation)
        self.transport.calls = 0
        result = self.ingress.receive(message_id, reply_target=self.target if self.channel.send_authorized else None)
        return self._reply(result, message_id)

    def _reply(self, result, message_id):
        """C-approved wording is necessary, never sufficient to dispatch."""
        rid = result.get("cycle_record_id")
        if not rid:
            return {**result, "delivery": "NO_ORIGINAL_C_CYCLE"}
        row = self.store.db.execute("SELECT * FROM subject_cycles WHERE record_id=?", (rid,)).fetchone()
        if not row:
            raise CoreError("QQ_ORIGINAL_C_CANDIDATE_REQUIRED")
        cycle = self.runtime.subject.result(dict(row))
        action = self.store.db.execute(
            "SELECT action_id,state FROM actions WHERE effect_slot=?", ("subject:" + cycle.intention_id,)
        ).fetchone()
        if action:
            state = self.realization.dispatch(cycle.intention_id, action["action_id"], expected_revision=1)
            return {
                "platform": "qq",
                "platform_message_id": str(message_id),
                "action_id": action["action_id"],
                "delivery": state,
                "replayed_semantics": False,
                "resent": False,
                "external_delivery": state == "SUCCEEDED",
            }
        eligible = (
            cycle.evaluation
            and cycle.evaluation.normative == "ENDORSED"
            and cycle.intention.kind in {"SOCIAL_INTERACTION", "DISAGREE", "ACTION_PROPOSAL"}
        )
        if not self.channel.send_authorized or result.get("render_state") != "UNVERIFIED_MODEL_WORDING" or not eligible:
            intention = self.store.one("subject_intentions", cycle.intention_id)
            if intention and intention["state"] == "PENDING":
                self.runtime.subject.transition_intention(
                    cycle.intention_id, expected_revision=intention["revision"], state="DEFERRED"
                )
            return {**result, "delivery": "NOT_AUTHORIZED_OR_NO_MODEL_WORDING", "external_delivery": False}
        candidate = self.port.bind_candidate(result["text"], rid, privacy=self.channel.privacy_class)
        admission = self.port.delivery.assess_reply(
            cycle, self.resource, payload=candidate, source_memory_ids=(result["message_memory_id"],)
        )
        intention = self.store.one("subject_intentions", cycle.intention_id)
        _, action_id = self.realization.propose(
            cycle.intention_id,
            expected_revision=intention["revision"],
            args={
                "data": candidate,
                "data_privacy": self.channel.privacy_class,
                "admission_id": admission["record_id"],
            },
            input_memory_ids=(result["message_memory_id"],),
        )
        if action_id is None:
            return {**result, "delivery": "BLOCKED_MANAGER", "external_delivery": False}
        state = self.realization.dispatch(cycle.intention_id, action_id, expected_revision=intention["revision"])
        if state == "SUCCEEDED":
            current = self.store.one("subject_intentions", cycle.intention_id)
            if current["state"] == "PENDING":
                self.runtime.subject.transition_intention(
                    cycle.intention_id, expected_revision=current["revision"], state="COMPLETED"
                )
        return {**result, "action_id": action_id, "delivery": state, "external_delivery": state == "SUCCEEDED"}


class PlatformRuntime:
    def __init__(self, app, resolver=None):
        self.app, self.resolver = app, resolver
        self.health = {}

    def qq(self, channel_id, message_id):
        channels = [c for c in self.app.config.qq_channels if c.channel_id == channel_id]
        if len(channels) != 1:
            raise CoreError("QQ_CHANNEL_UNBOUND")
        channel = channels[0]
        if not channel.enabled or not channel.read_authorized:
            raise CoreError("QQ_CHANNEL_DISABLED_OR_NOT_AUTHORIZED")
        credential = None
        if channel.credential_ref:
            if self.resolver is None or not self.resolver.available(channel.credential_ref):
                raise CoreError("QQ_CREDENTIAL_UNAVAILABLE")
            credential = SecretReference(self.resolver, channel.credential_ref)
        try:
            transport = OneBotHTTPTransport(
                channel.endpoint,
                channel.account_id,
                credential=credential,
                authorized=channel.read_authorized,
                request_limit=8,
                realm="AUTHENTICATED_PLATFORM",
            )
            result = QQReplyWorkflow(self.app, channel, transport).receive(message_id)
            self.health["qq." + channel_id] = result.get("delivery", result.get("state", "UNKNOWN"))
            return result
        finally:
            if credential is not None:
                credential.clear()

    def view(self):
        channels = []
        for platform, items in (("qq", self.app.config.qq_channels), ("bilibili", self.app.config.bilibili_channels)):
            for c in items:
                references = (c.credential_ref,) if platform == "qq" else (c.cookie_ref, c.csrf_ref)
                present = all(
                    not ref or self.resolver is not None and self.resolver.available(ref) for ref in references
                )
                channels.append(
                    {
                        "platform": platform,
                        "channel_id": c.channel_id,
                        "enabled": c.enabled,
                        "read_authorized": c.read_authorized,
                        "send_configured": c.send_authorized,
                        "secret_state": "AVAILABLE" if present else "MISSING",
                        "activation_configured": c.activation is not None,
                        "state": self.health.get(platform + "." + c.channel_id, "NOT_OBSERVED"),
                        "grants_created": False,
                    }
                )
        return {
            "configuration_revision": self.app.config.revision,
            "channels": channels,
            "second_runtime": False,
            "social_qualification": "NOT_ATTESTED_BY_CONFIGURATION",
        }

    def refresh(self):
        from .config import load_config

        current = load_config(self.app.home)
        self.app.config = self.app.config.model_copy(
            update={
                "revision": current.revision,
                "qq_channels": current.qq_channels,
                "bilibili_channels": current.bilibili_channels,
            }
        )
        return self.view()

    def bilibili(self, channel_id, message_id):
        from .bilibili_runtime import account_message

        result = account_message(self.app, self.resolver, channel_id, message_id)
        self.health["bilibili." + channel_id] = result.get("delivery", "UNKNOWN")
        return result


class SecretReference:
    """Resolve/clear only at each Authorization header, including revocation."""

    def __init__(self, resolver, reference):
        self.resolver, self.reference = resolver, reference

    def available(self):
        return self.resolver.available(self.reference)

    def reveal_for_header(self):
        if not self.available():
            raise CoreError("QQ_CREDENTIAL_UNAVAILABLE")
        value = self.resolver.resolve(self.reference)
        try:
            return value.reveal_for_header()
        finally:
            value.clear()

    def clear(self):
        pass

    def __repr__(self):
        return "<SecretReference redacted>"
