"""One execution owner for a closed synthetic CapabilityPort registry."""
import json
from ..actions import ActionKernel
from ..contracts import CAPABILITIES, CoreError, Receipt, Verification, VERIFY_CAPABILITY
from ..storage import canonical, digest

OWNER_KEY = "migration.execution_owner"
OWNERS = {"legacy_simulator", "core_simulator"}
TERMINAL = {"SUCCEEDED", "NOT_APPLIED", "FAILED_EFFECT", "CANCELLED"}


class BoundCapabilityPort:
    """Implements existing CapabilityPort; never handed to a model or shadow."""
    def __init__(self, router, actor, epoch):
        self._router, self._actor, self._epoch = router, actor, epoch

    def execute(self, invocation):
        return self._router.execute(self._actor, self._epoch, invocation)

    def verify(self, invocation):
        return self._router.verify(self._actor, self._epoch, invocation)


class CapabilityRouter:
    def __init__(self, store, ports, authority, *, resource_scope="synthetic_only", registry=None):
        self.registry = registry
        expected_capabilities = set(registry.definitions) if registry else CAPABILITIES
        if set(ports) != expected_capabilities:
            raise CoreError("CLOSED_SYNTHETIC_REGISTRY_REQUIRED")
        if registry and resource_scope != "isolated_development":
            raise CoreError("DEV_REGISTRY_SCOPE_REQUIRED")
        if not registry and resource_scope == "isolated_development":
            raise CoreError("DEV_REGISTRY_REQUIRED")
        if any(getattr(p, "path", None) and p.path.resolve() == store.path.resolve() for p in ports.values()):
            raise CoreError("CAPABILITY_DATABASE_MUST_BE_SEPARATE")
        if resource_scope not in {"synthetic_only", "development_public", "isolated_development"}:
            raise CoreError("INVALID_DEVELOPMENT_RESOURCE_SCOPE")
        self.store, self._ports, self._authority = store, dict(ports), authority
        self._resource_scope = resource_scope
        if self.owner and self.owner["scope"] != resource_scope:
            raise CoreError("ROUTER_SCOPE_MISMATCH")
        # Reuse existing grant/time validation; this object never dispatches.
        self._grant_gate = ActionKernel(store, None, authority, registry=registry)

    def _operator(self, authority):
        if authority is not self._authority:
            raise CoreError("UNAUTHENTICATED_MIGRATION_OPERATOR")

    @property
    def owner(self):
        row = self.store.one("core_meta", OWNER_KEY)
        return json.loads(row["value_json"]) if row else None

    def select_owner(self, actor, authority):
        self._operator(authority)
        if actor not in OWNERS:
            raise CoreError("SYNTHETIC_EXECUTION_OWNER_REQUIRED")
        with self.store.transaction("migration.owner_selected", {"actor": actor}) as tx:
            if json.loads(self.store.one("core_meta", "recovery_quarantine")["value_json"]):
                raise CoreError("RESTORE_QUARANTINE")
            previous = self.owner
            if previous and previous["actor"] == actor:
                return previous
            if (any(a["state"] not in TERMINAL for a in self.store.all("actions"))
                or any(g["state"] in {"PROPOSED", "ACTIVE", "BLOCKED"} for g in self.store.all("goals"))):
                raise CoreError("UNRESOLVED_WORK_PREVENTS_HANDOFF")
            owner = {"actor": actor, "epoch": previous["epoch"] + 1 if previous else 1,
                     "scope": self._resource_scope}
            tx.put("core_meta", {"key": OWNER_KEY, "value_json": canonical(owner)})
        return owner

    def bind(self, actor, authority):
        self._operator(authority)
        if actor not in OWNERS | {"shadow"}:
            raise CoreError("UNKNOWN_MIGRATION_ACTOR")
        return BoundCapabilityPort(self, actor, self.owner["epoch"] if self.owner else 0)

    def _guard(self, actor, epoch, invocation, states):
        if actor == "shadow":
            raise CoreError("SHADOW_HAS_NO_EXECUTION_RIGHT")
        owner = self.owner
        if not owner or owner["actor"] != actor or owner["epoch"] != epoch:
            raise CoreError("EXECUTION_OWNER_MISMATCH")
        if json.loads(self.store.one("core_meta", "recovery_quarantine")["value_json"]):
            raise CoreError("RESTORE_QUARANTINE")
        protocol = self.store.one("core_meta", "cloud.execution_protocol")
        if protocol:
            phase = json.loads(protocol["value_json"])
            if phase["epoch"] != owner["epoch"]:
                raise CoreError("HANDOFF_EPOCH_UNRECONCILED")
            allowed = ({"CORE_ACTIVE"} if actor == "core_simulator" else
                {"LEGACY_ACTIVE", "SHADOW_CORE", "CORE_READY", "LEGACY_RESTORED"})
            if states == {"DISPATCHING"} and phase["state"] not in allowed:
                raise CoreError("HANDOFF_EXECUTION_FENCED")
        action = self.store.one("actions", invocation.action_id)
        if not action or action["state"] not in states:
            raise CoreError("CORE_ACTION_REQUIRED")
        if (action["attempt_id"] != invocation.attempt_id or action["capability"] != invocation.capability
            or action["resource"] != invocation.resource or action["args_hash"] != invocation.args_hash
            or invocation.args_hash != digest(invocation.args) or action["idempotency_key"] != invocation.idempotency_key
            or invocation.capability not in self._ports):
            raise CoreError("ROUTE_INVOCATION_MISMATCH")
        prefixes = ("source://synthetic/", "notebook://synthetic/") if self._resource_scope == "synthetic_only" else (
            "source://public/", "notebook://synthetic/")
        if self.registry:
            prefixes = ("workspace://synthetic/",)
        if not invocation.resource.startswith(prefixes):
            raise CoreError("SYNTHETIC_RESOURCE_REQUIRED")
        return action

    def _attempt_gate(self, attempt, invocation, kind):
        if (not attempt or attempt["kind"] != kind or attempt["started_at_us"] is None
            or attempt["outcome"] is not None):
            raise CoreError("AUTHORIZED_ATTEMPT_REQUIRED")
        capability = self._grant_gate.verify_capability if kind == "VERIFY" else invocation.capability
        self._grant_gate._grant_for(capability, invocation.resource, attempt["grant_id"])
        holds = {h["dimension"]: h for h in self.store.all("budget_holds") if h["owner_id"] == attempt["attempt_id"]}
        expected = {"external_requests": "SPENT", "cost_micro_units": "HELD"}
        if kind == "EXECUTE" and (self.registry.is_write(capability) if self.registry else capability == "reading.card.create"):
            expected["write_attempts"] = "SPENT"
        if any(d not in holds or holds[d]["status"] != state or holds[d]["amount"] != 1 for d, state in expected.items()):
            raise CoreError("CONSUMED_ATTEMPT_BUDGET_REQUIRED")

    def execute(self, actor, epoch, invocation):
        action = self._guard(actor, epoch, invocation, {"DISPATCHING"})
        # Kernel already consumed request/write holds and persisted the authorized
        # dispatch. Require that proof; a proposal alone cannot call the backend.
        attempt = self.store.one("attempts", action["attempt_id"])
        self._attempt_gate(attempt, invocation, "EXECUTE")
        key = "migration.route_claim:" + invocation.action_id
        with self.store.transaction("migration.route_dispatched", {
            "action_id": invocation.action_id, "attempt_id": invocation.attempt_id, "actor": actor, "epoch": epoch}) as tx:
            if self.store.one("core_meta", key):
                raise CoreError("ROUTE_ALREADY_DISPATCHED")
            tx.put("core_meta", {"key": key, "value_json": canonical({"actor": actor, "epoch": epoch,
                "attempt_id": invocation.attempt_id, "args_hash": invocation.args_hash})})
        receipt = self._ports[invocation.capability].execute(invocation)
        if not isinstance(receipt, Receipt):
            raise CoreError("STRICT_RECEIPT_REQUIRED")
        return receipt

    def verify(self, actor, epoch, invocation):
        self._guard(actor, epoch, invocation, {"PENDING_VERIFY", "UNKNOWN"})
        live = [a for a in self.store.all("attempts") if a["action_id"] == invocation.action_id
                and a["kind"] == "VERIFY" and a["started_at_us"] is not None and a["outcome"] is None]
        if not live:
            raise CoreError("AUTHORIZED_VERIFICATION_ATTEMPT_REQUIRED")
        attempt = live[-1]
        self._attempt_gate(attempt, invocation, "VERIFY")
        key = "migration.verify_claim:" + attempt["attempt_id"]
        with self.store.transaction("migration.route_verification_dispatched", {
            "action_id": invocation.action_id, "attempt_id": attempt["attempt_id"], "actor": actor, "epoch": epoch}) as tx:
            if self.store.one("core_meta", key):
                raise CoreError("VERIFICATION_ALREADY_DISPATCHED")
            tx.put("core_meta", {"key": key, "value_json": canonical({"actor": actor, "epoch": epoch})})
        result = self._ports[invocation.capability].verify(invocation)
        if not isinstance(result, Verification):
            raise CoreError("STRICT_VERIFICATION_REQUIRED")
        return result
