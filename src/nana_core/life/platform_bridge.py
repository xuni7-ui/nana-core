"""Explicit OneBot observation and original-Kernel delivery adapters.

The platform provides observations/receipts, never a second Subject or memory.
No ambient token lookup, social retry, or authority inferred from message text.
The ordinary Core must be explicitly bound to this trusted host adapter.
"""

import http.client
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from types import MappingProxyType

from ..contracts import CoreError, Invocation, Receipt, Verification
from ..storage import digest
from ..continuity.open_agency.world import ContactArgs, bounded_data
from ..continuity.records import RecordService
from ..continuity.privacy import _json_object


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def message_text(value):
    """Only actual text segments become language; images remain typed metadata."""
    if isinstance(value, str):
        return value[:2048]
    if type(value) is not list or len(value) > 64:
        raise CoreError("ONEBOT_MESSAGE_INVALID")
    parts = []
    for item in value:
        if type(item) is not dict or type(item.get("data")) is not dict:
            raise CoreError("ONEBOT_MESSAGE_INVALID")
        if item.get("type") == "text" and isinstance(item["data"].get("text"), str):
            parts.append(item["data"]["text"])
        elif item.get("type") in {"image", "record", "video", "file"}:
            parts.append("[" + item["type"] + ": content not inspected]")
    return "".join(parts)[:2048]


class OneBotHTTPTransport:
    """Finite account-bound API. ACK is not independent delivery verification."""

    def __init__(self, endpoint, account_id, *, credential=None, authorized=False, request_limit=32,
                 realm="ACCOUNT_API_UNATTESTED"):
        u = urllib.parse.urlsplit(endpoint)
        if (u.scheme not in {"https", "http"} or not u.hostname or u.username or u.password
                or u.query or u.fragment or u.path not in {"", "/"}
                or (u.scheme == "http" and u.hostname not in {"127.0.0.1", "::1"})
                or any(c in endpoint for c in "\\\r\n")):
            raise CoreError("ONEBOT_EXPLICIT_SAFE_ENDPOINT_REQUIRED")
        if not re.fullmatch(r"[0-9]{1,20}", str(account_id)):
            raise CoreError("ONEBOT_ACCOUNT_REQUIRED")
        self.endpoint = endpoint.rstrip("/")
        self.account_id = str(account_id)
        self.credential = credential
        self.authorized = authorized is True
        self.limit = min(max(request_limit, 0), 128)
        self.calls = 0
        if realm not in {"ACCOUNT_API_UNATTESTED", "SYNTHETIC_LOOPBACK", "AUTHENTICATED_PLATFORM"}:
            raise CoreError("ONEBOT_REALM_INVALID")
        self.realm = realm
        # Loopback account APIs must not inherit an Internet credential proxy.
        handlers = [NoRedirect()]
        if u.scheme == "http":
            handlers.insert(0, urllib.request.ProxyHandler({}))
        self.opener = urllib.request.build_opener(*handlers)

    def __repr__(self):
        return "<OneBotHTTPTransport explicit-bound; credential redacted>"

    def _call(self, operation, params):
        if not self.authorized:
            raise CoreError("ONEBOT_CHANNEL_NOT_AUTHORIZED")
        if self.calls >= self.limit:
            raise CoreError("ONEBOT_REQUEST_BUDGET")
        if operation not in {"get_login_info", "get_msg", "send_private_msg", "send_group_msg"}:
            raise CoreError("ONEBOT_OPERATION_DENIED")
        raw = json.dumps(params, ensure_ascii=False, allow_nan=False).encode()
        if len(raw) > 16384:
            raise CoreError("ONEBOT_REQUEST_BOUND")
        headers = {"Content-Type": "application/json"}
        if self.credential is not None:
            headers["Authorization"] = "Bearer " + self.credential.reveal_for_header()
        request = urllib.request.Request(self.endpoint + "/" + operation, data=raw, headers=headers, method="POST")
        self.calls += 1
        try:
            with self.opener.open(request, timeout=5) as response:
                body = response.read(262145)
        except urllib.error.HTTPError:
            raise CoreError("ONEBOT_HTTP_REJECTED_NO_RETRY") from None
        except (OSError, http.client.HTTPException):
            raise CoreError("ONEBOT_COMPLETION_UNKNOWN_NO_RETRY") from None
        if len(body) > 262144:
            raise CoreError("ONEBOT_RESPONSE_BOUND")
        try:
            value = json.loads(body, object_pairs_hook=_json_object)
        except (ValueError, UnicodeError):
            raise CoreError("ONEBOT_MALFORMED_RESPONSE_NO_RETRY") from None
        if type(value) is not dict or value.get("status") != "ok" or value.get("retcode") != 0:
            raise CoreError("ONEBOT_REJECTED_NO_RETRY")
        if type(value.get("data")) is not dict:
            raise CoreError("ONEBOT_MALFORMED_RESPONSE_NO_RETRY")
        return value["data"]

    def account(self):
        row = self._call("get_login_info", {})
        if str(row.get("user_id")) != self.account_id:
            raise CoreError("ONEBOT_ACCOUNT_BINDING_CHANGED")
        return {"account_id": self.account_id}

    def get_message(self, message_id):
        if not re.fullmatch(r"-?[0-9]{1,20}", str(message_id)):
            raise CoreError("ONEBOT_MESSAGE_ID_INVALID")
        row = self._call("get_msg", {"message_id": int(message_id)})
        if str(row.get("message_id")) != str(message_id):
            raise CoreError("ONEBOT_MESSAGE_CORRELATION_MISMATCH")
        return row

    def send(self, target_kind, target_id, text, echo):
        if target_kind not in {"private", "group"} or not re.fullmatch(r"[0-9]{1,20}", str(target_id)):
            raise CoreError("ONEBOT_TARGET_INVALID")
        if type(text) is not str or not 1 <= len(text) <= 2048:
            raise CoreError("ONEBOT_MESSAGE_BOUND")
        self.account()  # A changed account cannot inherit old delivery authority.
        params = {target_kind + ("_id" if target_kind == "group" else "_id"): int(target_id),
                  "message": [{"type": "text", "data": {"text": text}}], "echo": echo}
        if target_kind == "private":
            params["user_id"] = params.pop("private_id")
        row = self._call("send_" + target_kind + "_msg", params)
        message_id = row.get("message_id")
        if not re.fullmatch(r"-?[0-9]{1,20}", str(message_id)):
            raise CoreError("ONEBOT_ACK_UNKNOWN_NO_RETRY")
        return {"message_id": str(message_id), "target_kind": target_kind, "target_id": str(target_id),
                "account_id": self.account_id, "text_digest": digest(text), "echo": echo}

    def verify_receipt(self, receipt):
        row = self.get_message(receipt["message_id"])
        sender = row.get("sender") or {}
        peer = row.get("group_id") if receipt["target_kind"] == "group" else row.get("target_id")
        if peer is None:
            return Verification(verdict="INCONCLUSIVE", evidence={"reason": "ONEBOT_PEER_NOT_ATTESTED_NO_RETRY"})
        matches = (str(peer) == receipt["target_id"] and str(sender.get("user_id")) == self.account_id
                   and row.get("message_type") == receipt["target_kind"]
                   and digest(message_text(row.get("message"))) == receipt["text_digest"])
        return Verification(verdict="MATCH" if matches else "EFFECT_MISMATCH", evidence={
            "message_id": receipt["message_id"], "account_id": self.account_id,
            "target_id": str(peer), "independent_readback": True})


class QQRegistry:
    """Original world.contact taxonomy, exact resources, never an extra Grant."""
    definitions = MappingProxyType({"world.contact": ContactArgs})
    verify_capability = "world.action.verify"

    def __init__(self, resources):
        self.resources = frozenset(resources)

    @staticmethod
    def request_count(capability):
        if capability != "world.contact":
            raise CoreError("QQ_RESOURCE_SCOPE_DENIED")
        return 2  # account preflight + one send; independent Verify is one get_msg.

    @staticmethod
    def is_write(capability):
        return capability == "world.contact"

    @staticmethod
    def payload_privacy(payload):
        from ..continuity.open_agency.world import LocalWorldRegistry
        return LocalWorldRegistry.payload_privacy(payload)

    def validate(self, capability, resource, args):
        if capability != "world.contact" or resource not in self.resources:
            raise CoreError("QQ_RESOURCE_SCOPE_DENIED")
        value = ContactArgs.model_validate(args).model_dump()
        bounded_data(value)
        data = value["data"]
        if (value["data_privacy"] not in {"PUBLIC", "PROJECT", "PERSONAL"}
                or type(value["admission_id"]) is not str or not 1 <= len(value["admission_id"]) <= 128
                or type(data) is not dict or set(data) != {"candidate_digest", "cycle_record_id"}
                or type(data["candidate_digest"]) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", data["candidate_digest"])
                or type(data["cycle_record_id"]) is not str):
            raise CoreError("QQ_ORIGINAL_C_CANDIDATE_REQUIRED")
        return value


class QQCapabilityPort:
    """ActionKernel-only execution; original Store owns all durable attempts.

    Text candidates stay in RAM. A restart with a lost ACK remains UNKNOWN;
    it never regenerates or resends an old reply. No separate social ledger.
    """
    evidence_namespace = "recorded.platform.qq.delivery"

    def __init__(self, store, transport, targets, *, host_enabled=False, app=None, activation=None, delivery=None):
        if host_enabled is not True or type(transport) is not OneBotHTTPTransport:
            raise CoreError("QQ_HOST_BINDING_REQUIRED")
        self.store, self.transport = store, transport
        self.identity_id = store.identity["identity_id"]
        self.app, self.activation = app, activation
        from ..continuity.open_agency.delivery import DeliveryAdmission
        if delivery is not None and (type(delivery) is not DeliveryAdmission or delivery.store is not store):
            raise CoreError("QQ_ORIGINAL_DELIVERY_ADMISSION_REQUIRED")
        self.delivery = delivery
        self.targets = dict(targets)
        if not 1 <= len(self.targets) <= 16:
            raise CoreError("QQ_FINITE_TARGET_BINDING_REQUIRED")
        for resource, target in self.targets.items():
            if (not re.fullmatch(r"^project://qq/[A-Za-z0-9/._:-]{1,120}$", resource)
                    or type(target) not in {tuple, list} or len(target) != 2
                    or target[0] not in {"private", "group"}
                    or not re.fullmatch(r"[0-9]{1,20}", str(target[1]))):
                raise CoreError("QQ_FINITE_TARGET_BINDING_REQUIRED")
        self.registry = QQRegistry(self.targets)
        self.candidates = {}

    def assert_owned(self):
        """A local fixture or canonical activation can enter the original Core."""
        endpoint = urllib.parse.urlsplit(self.transport.endpoint)
        if self.transport.realm == "SYNTHETIC_LOOPBACK":
            if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "::1"}:
                raise CoreError("QQ_SYNTHETIC_LOOPBACK_REQUIRED")
            return
        if self.app is None or self.app.runtime.store is not self.store or self.app.runtime.identity_id != self.identity_id:
            raise CoreError("QQ_CANONICAL_ACTIVATION_REQUIRED")
        from .platform_authority import require_platform_authority
        require_platform_authority(self.app, self.activation, channel="qq", exclusive_writer=True,
                                   account_id=self.transport.account_id)

    def bind_candidate(self, text, cycle_record_id, *, privacy):
        if privacy not in {"PUBLIC", "PROJECT", "PERSONAL"}:
            raise CoreError("QQ_PRIVACY_DENIED")
        if type(text) is not str or not 1 <= len(text) <= 2048:
            raise CoreError("QQ_MESSAGE_BOUND")
        record = RecordService(self.store).read(cycle_record_id)
        if record["record_kind"] != "SUBJECT_CYCLE" or not RecordService(self.store).current_support(cycle_record_id):
            raise CoreError("QQ_ORIGINAL_C_CANDIDATE_REQUIRED")
        payload = record["payload"]
        if payload["intention"]["kind"] not in {"SOCIAL_INTERACTION", "DISAGREE", "ACTION_PROPOSAL"}:
            raise CoreError("QQ_C_DID_NOT_SELECT_EXPRESSION")
        from ..continuity.memory import PRIVACY_RANK
        if PRIVACY_RANK[privacy] < PRIVACY_RANK[record["privacy_class"]]:
            raise CoreError("QQ_SOURCE_PRIVACY_DOWNGRADE_DENIED")
        target = payload.get("realization_target") or {}
        if (target.get("capability") != "world.contact" or target.get("operation") != "CONTACT"
                or target.get("resource_class") != "ORDINARY" or target.get("resource") not in self.targets
                or (payload.get("evaluation") or {}).get("normative") != "ENDORSED"):
            raise CoreError("QQ_C_CONTACT_TARGET_REQUIRED")
        key = digest([text, cycle_record_id, privacy])
        if len(self.candidates) >= 32 and key not in self.candidates:
            raise CoreError("QQ_VOLATILE_CANDIDATE_BOUND")
        self.candidates[key] = (text, cycle_record_id, privacy)
        return {"candidate_digest": key, "cycle_record_id": cycle_record_id}

    def _proof(self, inv, *, verify=False):
        if type(inv) is not Invocation:
            raise CoreError("QQ_KERNEL_ACTION_REQUIRED")
        action = self.store.one("actions", inv.action_id)
        if (not action or action["capability"] != inv.capability or action["resource"] != inv.resource
                or action["args_hash"] != inv.args_hash or inv.args_hash != digest(inv.args)
                or action["idempotency_key"] != inv.idempotency_key or action["attempt_id"] != inv.attempt_id):
            raise CoreError("QQ_KERNEL_ACTION_REQUIRED")
        if action["state"] not in ({"UNKNOWN", "PENDING_VERIFY"} if verify else {"DISPATCHING"}):
            raise CoreError("QQ_KERNEL_DISPATCH_REQUIRED")
        if self.store.schema_target < 13:
            raise CoreError("QQ_ORIGINAL_GOVERNANCE_REQUIRED")
        if not verify:
            guard = getattr(self.store, "_governed_action_guard", None)
            if not callable(guard):
                raise CoreError("QQ_ORIGINAL_GOVERNANCE_REQUIRED")
            guard()
        args = self.registry.validate(inv.capability, inv.resource, inv.args)
        records = RecordService(self.store)
        if not records.current_support(args["data"]["cycle_record_id"]):
            raise CoreError("QQ_C_SOURCE_RETIRED")
        cycle = records.read(args["data"]["cycle_record_id"])
        target = cycle["payload"].get("realization_target") or {}
        if target.get("resource") != inv.resource or target.get("capability") != inv.capability:
            raise CoreError("QQ_C_CONTACT_TARGET_REQUIRED")
        if not verify:
            support = getattr(self.store, "_governed_payload_support", None)
            outcome = records.read(support) if support else {}
            body = outcome.get("payload", {})
            if (outcome.get("record_kind") != "CONSTRAINT_OUTCOME" or body.get("result") != "PASS"
                    or body.get("cycle_id") != cycle["payload"]["cycle_id"]
                    or action["effect_slot"] != "subject:" + body.get("intention_id", "")):
                raise CoreError("QQ_EXACT_C_GOVERNANCE_REQUIRED")
        attempts = [a for a in self.store.all("attempts") if a["action_id"] == inv.action_id
                    and a["kind"] == ("VERIFY" if verify else "EXECUTE")
                    and a["started_at_us"] is not None and a["outcome"] is None]
        if not attempts:
            raise CoreError("QQ_AUTHORIZED_ATTEMPT_REQUIRED")
        attempt = attempts[-1]
        grant = self.store.one("grants", attempt["grant_id"])
        scope = json.loads(grant["body_json"]) if grant else {}
        now = self.store.clock.utc_now_us()
        cap = self.registry.verify_capability if verify else inv.capability
        if (not grant or grant["identity_id"] != self.store.identity["identity_id"]
                or grant["revoked"] or not grant["not_before_us"] <= now < grant["expires_at_us"]
                or cap not in scope["capabilities"] or inv.resource not in scope["resources"]):
            raise CoreError("QQ_CURRENT_GRANT_REQUIRED")
        holds = {h["dimension"]: h for h in self.store.all("budget_holds") if h["owner_id"] == attempt["attempt_id"]}
        required = {"external_requests": "SPENT", "cost_micro_units": "HELD"}
        if not verify:
            required["write_attempts"] = "SPENT"
        if any(d not in holds or holds[d]["status"] != state for d, state in required.items()):
            raise CoreError("QQ_RESERVED_ORIGINAL_BUDGET_REQUIRED")
        if not verify and holds["external_requests"]["amount"] < 2:
            raise CoreError("QQ_TWO_PHASE_REQUEST_BUDGET_REQUIRED")
        if not verify:
            if self.delivery is None:
                raise CoreError("QQ_ORIGINAL_DELIVERY_ADMISSION_REQUIRED")
            self.delivery.require(args["admission_id"], inv.resource, invocation=inv)
        return action, args

    def execute(self, inv):
        _, args = self._proof(inv)
        candidate = self.candidates.pop(args["data"]["candidate_digest"], None)
        if candidate is None or candidate[1:] != (args["data"]["cycle_record_id"], args["data_privacy"]):
            raise CoreError("QQ_CANDIDATE_NOT_AVAILABLE_NO_REGENERATION")
        target_kind, target_id = self.targets[inv.resource]
        result = self.transport.send(target_kind, target_id, candidate[0], inv.idempotency_key)
        return Receipt(external_id=result["message_id"], result=result)

    def verify(self, inv):
        action, _ = self._proof(inv, verify=True)
        attempt = self.store.one("attempts", action["attempt_id"])
        if not attempt["receipt_event_id"]:
            return Verification(verdict="INCONCLUSIVE", evidence={"reason": "QQ_ACK_LOST_UNKNOWN_NO_RETRY"})
        event = self.store.event(attempt["receipt_event_id"])
        receipt = Receipt.model_validate_json(self.store.artifact(event["artifact_id"]))
        return self.transport.verify_receipt(receipt.result)


from ..continuity.autonomy.realization import GovernedRealization


class QQGovernedDelivery(GovernedRealization):
    """Explicit host binding reuses the original post-C handoff and Kernel.

    It does not generate a contact intention, candidate wording, Grant or retry.
    Ordinary ingress cycles have no contact target and cannot be sent.
    """

    def __init__(self, port, authority, *, host_enabled=False):
        from ..actions import ActionKernel
        from ..continuity.autonomy.governance import ManagerConstraintGate
        if host_enabled is not True or type(port) is not QQCapabilityPort or port.store.schema_target < 13:
            raise CoreError("QQ_HOST_BINDING_REQUIRED")
        self.store = port.store
        self.gate = ManagerConstraintGate(self.store)
        self.kernel = ActionKernel(self.store, port, authority, registry=port.registry)


class QQIngress:
    """Fetch from an authenticated fixed account, then original SurfaceSession/C."""

    def __init__(self, app, transport, binding_id, sender_id, *, privacy="PROJECT", private_read_authorized=False,
                 target_kind="private", target_id=None, activation=None):
        if type(transport) is not OneBotHTTPTransport:
            raise CoreError("ONEBOT_TYPED_TRANSPORT_REQUIRED")
        if privacy not in {"PUBLIC", "PROJECT", "PERSONAL"}:
            raise CoreError("QQ_PRIVACY_DENIED")
        if privacy == "PERSONAL" and private_read_authorized is not True:
            raise CoreError("QQ_PRIVATE_INGRESS_NOT_AUTHORIZED")
        binding = app.surfaces._binding(binding_id)
        if binding.mode != "PLATFORM_ADAPTER_NO_SEND" or binding.platform != "qq.onebot":
            raise CoreError("QQ_PLATFORM_BINDING_REQUIRED")
        if privacy not in binding.permitted_privacy:
            raise CoreError("SURFACE_PRIVACY_NOT_BOUND")
        if (not re.fullmatch(r"[0-9]{1,20}", str(sender_id)) or target_kind not in {"private", "group"}
                or (target_id is not None and not re.fullmatch(r"[0-9]{1,20}", str(target_id)))
                or (target_kind == "group" and target_id is None)):
            raise CoreError("QQ_TRUSTED_PEER_BINDING_REQUIRED")
        self.app, self.transport = app, transport
        self.binding_id, self.sender_id, self.privacy = binding_id, str(sender_id), privacy
        self.target_kind, self.target_id = target_kind, str(target_id) if target_id is not None else self.sender_id
        self.activation = activation
        self._authority()

    def _authority(self):
        if self.transport.realm == "SYNTHETIC_LOOPBACK":
            endpoint = urllib.parse.urlsplit(self.transport.endpoint)
            if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "::1"}:
                raise CoreError("QQ_SYNTHETIC_LOOPBACK_REQUIRED")
            return
        from .platform_authority import PlatformActivation, require_platform_authority
        if type(self.activation) is not PlatformActivation or self.activation.binding_id != self.binding_id:
            raise CoreError("QQ_CANONICAL_ACTIVATION_REQUIRED")
        require_platform_authority(self.app, self.activation, channel="qq", exclusive_writer=False,
                                   account_id=self.transport.account_id)

    def receive(self, message_id):
        from .surfaces import SurfaceObservation
        self._authority()
        self.transport.account()
        row = self.transport.get_message(message_id)
        if str((row.get("sender") or {}).get("user_id")) != self.sender_id:
            raise CoreError("QQ_SENDER_UNBOUND")
        kind = row.get("message_type")
        if kind not in {"private", "group"}:
            raise CoreError("QQ_EVENT_TYPE_UNSUPPORTED")
        peer = str(row.get("group_id")) if kind == "group" else self.sender_id
        if kind != self.target_kind or peer != self.target_id:
            raise CoreError("QQ_PEER_UNBOUND")
        if not re.fullmatch(r"[0-9]{1,20}", peer) or type(row.get("time")) is not int:
            raise CoreError("QQ_EVENT_METADATA_INVALID")
        result = self.app.surfaces.receive(SurfaceObservation(binding_id=self.binding_id,
            event_id="qq:" + str(message_id), thread_id="qq." + kind + "." + peer,
            occurred_at_us=row["time"] * 1_000_000, text=message_text(row.get("message")), privacy_class=self.privacy,
            origin=self.transport.realm))
        source = result.get("source_key")
        if source:
            cycle = self.app.runtime.store.db.execute(
                "SELECT c.record_id FROM subject_cycles c JOIN subject_events e ON e.subject_event_id=c.subject_event_id WHERE e.source_key=?",
                (source,)).fetchone()
            result["cycle_record_id"] = cycle[0] if cycle else None
        return {**result, "platform": "qq", "platform_message_id": str(message_id), "external_delivery": False}
