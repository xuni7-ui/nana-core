"""Explicit QQ host binding on the existing owner, not another platform brain.

The inbound transport independently fetches account/message identity. Core alone
interprets/judges/renders; original Manager/Grant/Kernel/Verify deliver at most
once. Lost wording and ambiguous effects are parked, never regenerated/replayed.
No credential discovery, new Subject, Store, scheduler or automatic Grant.
"""

from typing import Literal
from pydantic import Field, model_validator, model_serializer

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
    backend: Literal["onebot", "official"] = "onebot"
    sender_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    target_kind: Literal["private", "group"] = "private"
    target_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    credential_ref: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    enabled: bool = False
    read_authorized: bool = False
    send_authorized: bool = False
    private_read_authorized: bool = False
    privacy_class: Literal["PUBLIC", "PROJECT", "PERSONAL"] = "PROJECT"
    activation: PlatformActivation | None = None
    max_events_per_hour: int = Field(default=24, ge=0, le=128)

    @model_validator(mode='after')
    def backend_ids(self):
        import re
        if self.backend == 'onebot' and any(not re.fullmatch(r'[0-9]{1,20}', value) for value in (self.sender_id, self.target_id)):
            raise ValueError('OneBot numeric IDs required')
        return self

    @model_serializer(mode='wrap')
    def old_config_compatible(self, handler):
        value = handler(self)
        if self.backend == 'onebot':
            value.pop('backend', None)
        return value


class QQReplyWorkflow:
    def __init__(self, app, channel, transport, *, media_cache=None):
        self.app, self.runtime, self.channel, self.transport = app, app.runtime, channel, transport
        self.store = app.runtime.store
        from .platform_bridge import qq_platform
        if qq_platform(transport) != 'qq.' + channel.backend:
            raise CoreError('QQ_BACKEND_TRANSPORT_MISMATCH')
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
        from .platform_bridge import qq_platform
        delivery = DeliveryAdmission(
            self.store,
            DeliveryPolicy(
                recipients=(self.resource,),
                privacy_classes=(channel.privacy_class,),
                direct_reply_bindings=(
                    ReplyWindowBinding(
                        resource=self.resource,
                        binding_id=channel.binding_id,
                        platform=qq_platform(transport),
                        thread_id="qq." + channel.target_kind + "." + (digest(channel.target_id)[:32] if channel.backend=="official" else channel.target_id),
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
            media_cache=media_cache,
        )
        self.realization = QQGovernedDelivery(self.port, app.runtime.authority, host_enabled=True)

    def receive(self, message_id):
        if not self.channel.enabled or not self.channel.read_authorized:
            raise CoreError("QQ_CHANNEL_DISABLED_OR_NOT_AUTHORIZED")
        binding = self.app.surfaces._binding(self.channel.binding_id)
        from .official_transport import qq_event_id
        event_key = "local.surface." + digest(
            [binding.platform, binding.adapter, binding.surface, digest([binding.binding_id, qq_event_id(self.transport, message_id)])]
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
        # Never silently drop a C-selected attachment and send text alone.
        media = cycle.realization_target.media if cycle.realization_target else None
        if media is not None and (media.kind != 'image' or self.port.media_cache is None
                                  or type(self.transport) is not OneBotHTTPTransport):
            return {**result, "delivery":"MEDIA_ACTION_UNSUPPORTED", "external_delivery":False}
        candidate = self.port.bind_candidate(result["text"], rid, privacy=self.channel.privacy_class)
        sources = tuple(dict.fromkeys((result["message_memory_id"],) + ((media.source_memory_id,) if media else ())))
        admission = self.port.delivery.assess_reply(
            cycle, self.resource, payload=candidate, source_memory_ids=sources
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
            input_memory_ids=sources,
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
        self._qq_media_caches = {}
        self._owned_qq_media_caches = {}
        self._nanalink_bili_sources = {}
        from ..nanalink.private_source import reconcile_revoked_sources
        reconcile_revoked_sources(app,app.config)
        self._source_guard_busy = False
        self._source_config_version = self._config_version()
        app.runtime.store._nanalink_source_guard = self._guard_platform_sources

    def _config_version(self):
        try:
            st = (self.app.home / 'life.json').stat()
            return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns
        except OSError:
            raise CoreError('PLATFORM_SOURCE_CONFIG_UNAVAILABLE') from None

    def _guard_platform_sources(self):
        if self._source_guard_busy or self._config_version() == self._source_config_version:
            return
        if self.app.runtime.store.db.in_transaction:
            raise CoreError('PLATFORM_SOURCE_REVOCATION_PENDING_SAFE_POINT')
        from .config import load_config
        from ..nanalink.private_source import reconcile_revoked_sources
        self._source_guard_busy = True
        try:
            for _ in range(3):
                before = self._config_version()
                current = load_config(self.app.home)
                reconcile_revoked_sources(self.app, current)
                self._retire_stale_notification_sources(current)
                after = self._config_version()
                if before == after:
                    self._source_config_version = after
                    return
            raise CoreError('PLATFORM_SOURCE_CONFIG_CHANGED_RETRY_READ')
        finally:
            self._source_guard_busy = False

    def _retire_stale_notification_sources(self, config):
        channels = {item.channel_id: item for item in config.bilibili_channels}
        bindings = {item.binding_id: item for item in config.surface_bindings}
        for channel_id, (_, adapter) in tuple(self._nanalink_bili_sources.items()):
            old = adapter.workflow.channel
            try:
                old_binding = self.app.surfaces._binding(old.binding_id)
            except CoreError:
                old_binding = None
            if channels.get(channel_id) != old or bindings.get(old.binding_id) != old_binding:
                adapter.pending.clear()
                adapter.enabled = False
                self._nanalink_bili_sources.pop(channel_id, None)

    def _discard_qq_media_cache(self, channel_id):
        self._qq_media_caches.pop(channel_id, None)
        owned = self._owned_qq_media_caches.pop(channel_id, None)
        if owned is not None:
            try:
                owned[0].close()
            finally:
                owned[1].cleanup()

    def bind_qq_media_cache(self, channel_id, cache):
        """Bind a caller-owned volatile cache to one exact configured account.

        This owner-only adapter hook neither reads bytes nor grants any action.
        The caller retains cache lifecycle; bindings disappear on restart.
        """
        from ..nanalink.media import MediaCache
        self.app.runtime.cadence.assert_owner()
        channels = [c for c in self.app.config.qq_channels if c.channel_id == channel_id]
        if len(channels) != 1 or channels[0].backend != 'onebot':
            raise CoreError('QQ_CHANNEL_UNBOUND')
        if cache is None:
            self._discard_qq_media_cache(channel_id)
            return
        owned = self._owned_qq_media_caches.get(channel_id)
        if owned is not None and owned[0] is not cache:
            raise CoreError('QQ_MEDIA_CACHE_ALREADY_BOUND')
        if type(cache) is not MediaCache or any(k != channel_id and v[1] is cache for k, v in self._qq_media_caches.items()):
            raise CoreError('QQ_MEDIA_ACCOUNT_ISOLATION_REQUIRED')
        channel = channels[0]
        binding = (channel.binding_id, channel.backend, channel.account_id, channel.endpoint)
        owner = (channel_id, *binding)
        if getattr(cache, '_nanalink_qq_owner', owner) != owner:
            raise CoreError('QQ_MEDIA_ACCOUNT_ISOLATION_REQUIRED')
        cache._nanalink_qq_owner = owner
        self._qq_media_caches[channel_id] = (binding, cache)

    def open_qq_media_cache(self, channel_id):
        """Create an explicitly requested, session-scoped private cache."""
        import tempfile
        from ..continuity.memory import MemoryService
        from ..nanalink.media import MediaCache
        self.app.runtime.cadence.assert_owner()
        if channel_id in self._qq_media_caches or channel_id in self._owned_qq_media_caches:
            raise CoreError('QQ_MEDIA_CACHE_ALREADY_BOUND')
        directory = tempfile.TemporaryDirectory(prefix='nanalink-media-')
        def current(memory_id):
            try:
                MemoryService(self.app.runtime.store).read(memory_id)
                return True
            except CoreError:
                return False
        try:
            cache = MediaCache(directory.name, source_current=current,
                               max_bytes=8 * 1024 * 1024, item_bytes=8192, max_items=64)
            self.bind_qq_media_cache(channel_id, cache)
        except BaseException:
            directory.cleanup()
            raise
        self._owned_qq_media_caches[channel_id] = (cache, directory)
        return {'state': 'CACHE_BOUND_NO_AUTHORITY', 'persistent': False}

    def close(self):
        """Dispose only caches this owner created; external caches stay caller-owned."""
        for channel_id in tuple(self._owned_qq_media_caches):
            self._discard_qq_media_cache(channel_id)
        self._qq_media_caches.clear()
        for _, adapter in self._nanalink_bili_sources.values():
            adapter.pending.clear()
            adapter.enabled = False
        self._nanalink_bili_sources.clear()

    def cache_qq_observed_image(self, channel_id, source_memory_id, data):
        """Cache bytes of an existing original public perception; no fetch or Grant."""
        import hashlib
        from ..continuity.memory import MemoryService
        from ..continuity.records import RecordService
        from ..nanalink.media_candidates import candidate, resolve_image
        self.app.runtime.cadence.assert_owner()
        channels = [c for c in self.app.config.qq_channels if c.channel_id == channel_id]
        if len(channels) != 1:
            raise CoreError('QQ_CHANNEL_UNBOUND')
        channel = channels[0]
        entry = self._qq_media_caches.get(channel_id)
        binding = (channel.binding_id, channel.backend, channel.account_id, channel.endpoint)
        if not entry or entry[0] != binding:
            self._discard_qq_media_cache(channel_id)
            raise CoreError('QQ_MEDIA_CACHE_UNBOUND')
        surface = self.app.surfaces._binding(channel.binding_id)
        row = MemoryService(self.app.runtime.store).read(source_memory_id)
        selection = candidate(row)
        observation = self.app.runtime.store.db.execute(
            "SELECT record_id FROM continuity_records WHERE record_kind='MEDIA_OBSERVATION' AND target_id=?", (source_memory_id,)).fetchone()
        if (selection is None or row['scope'] != surface.scope
                or row['entity_id'] not in {surface.entity_id, self.app.runtime.identity_id}
                or not observation or not RecordService(self.app.runtime.store).current_support(observation[0])):
            raise CoreError('QQ_MEDIA_ORIGINAL_SOURCE_REQUIRED')
        if type(data) is not bytes or not 1 <= len(data) <= 8192 or hashlib.sha256(data).hexdigest() != selection.content_sha256:
            raise CoreError('QQ_MEDIA_SOURCE_BYTES_MISMATCH')
        entry[1].put((data,), source_ref=source_memory_id, media_type='image')
        resolve_image(self.app.runtime.store, entry[1], selection)
        return {'source_memory_id': source_memory_id, 'content_sha256': selection.content_sha256,
                'bytes_cached': len(data), 'execution_authority': False}

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
            from .official_transport import OfficialQQHTTPTransport
            transport_type = OfficialQQHTTPTransport if channel.backend == "official" else OneBotHTTPTransport
            transport = transport_type(
                channel.endpoint,
                channel.account_id,
                credential=credential,
                authorized=channel.read_authorized,
                request_limit=8,
                realm="AUTHENTICATED_PLATFORM",
            )
            binding = (channel.binding_id, channel.backend, channel.account_id, channel.endpoint)
            entry = self._qq_media_caches.get(channel_id)
            if entry and entry[0] != binding:
                self._discard_qq_media_cache(channel_id)
                entry = None
            result = QQReplyWorkflow(self.app, channel, transport, media_cache=entry[1] if entry else None).receive(message_id)
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
        from ..nanalink.private_source import reconcile_revoked_sources
        reconcile_revoked_sources(self.app,current)
        self._nanalink_bili_sources.clear()
        self.app.config = self.app.config.model_copy(
            update={
                "revision": current.revision,
                "qq_channels": current.qq_channels,
                "bilibili_channels": current.bilibili_channels,
            }
        )
        return self.view()

    def bilibili_dynamics(self, channel_id):
        from .bilibili_runtime import account_workflow
        from ..nanalink.private_source import poll_dynamics
        return poll_dynamics(account_workflow(self.app,self.resolver,channel_id))

    def bilibili_notifications(self, channel_id):
        """Explicit infrastructure poll on the ORIGINAL owner; defaults deny.

        Reuses original account policy/credentials, C.4 normalization and the
        same reply workflow. No new Runtime, timer, Store, model or Grant.
        """
        import asyncio
        from .bilibili_runtime import account_workflow
        from ..nanalink.adapters import BilibiliEventsAdapter
        self._guard_platform_sources()
        workflow = account_workflow(self.app, self.resolver, channel_id)
        revision = digest(workflow.channel.model_dump(mode='json'))
        previous = self._nanalink_bili_sources.get(channel_id)
        if previous is None or previous[0] != revision:
            adapter = BilibiliEventsAdapter(workflow)
            asyncio.run(adapter.connect())
            self._nanalink_bili_sources[channel_id] = (revision, adapter)
        else:
            adapter = previous[1]
            # Use the current resolver/channel/activation, never stale rights.
            adapter.workflow = workflow
        event = asyncio.run(adapter.receive())
        if event is None:
            return {'platform': 'bilibili', 'delivery': 'NO_NEW_BOUND_NOTIFICATION',
                    'external_delivery': False, 'pending_notifications': 0}
        receipt = adapter.receive_event(event)
        delivery = 'SUCCEEDED' if receipt.external_delivery else receipt.reason
        self.health['bilibili.' + channel_id] = delivery
        return {'platform': 'bilibili', 'delivery': delivery,
                'outcome': receipt.outcome.value, 'action_id': receipt.action_id,
                'external_delivery': receipt.external_delivery, 'no_retry': True,
                'pending_notifications': len(adapter.pending)}

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
