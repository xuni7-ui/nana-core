"""Original CapabilityPort decorator with durable per-action context evidence.

Constructed by the trusted host application, never by model text or the frontend.
The original Kernel still owns Grant, budget, dispatch state and recovery. This
port adds an exact resource/context/channel binding and delegates the unchanged
invocation; it does not implement shell commands or generic privileged repair.
"""

from ..actions import ActionKernel
from ..contracts import CoreError, Receipt, Verification
from ..storage import canonical, digest
from .routing import RouteSnapshot
from .contracts import PathObservation


PREFIX = "execution.context.action:"


class ContextBoundPort:
    def __init__(self, store, router, authority, *, registry=None):
        self.store, self.router = store, router
        # Reuse, rather than reimplement, the existing Grant/time checks.
        self._gate = ActionKernel(store, None, authority, registry=registry)
        self.registry = registry

    def reserve_context(self, tx, action, args):
        """Called inside original Kernel's authorized atomic preparation."""
        snapshot = self.router.select(action["resource"], action["capability"])
        metadata = self.router.observe_selected(snapshot)
        observation = PathObservation.model_validate_json(canonical(metadata["observation"]))
        if observation.status not in {"PRESENT", "MISSING"}:
            raise CoreError("EXECUTION_PATH_PREFLIGHT_UNAVAILABLE")
        is_write = (
            self.registry.is_write(action["capability"])
            if self.registry
            else action["capability"] == "reading.card.create"
        )
        # A new file has no filesystem identity yet. Creation adapters must bind
        # their existing owned directory as the anchor, not a missing pathname.
        if is_write and observation.status != "PRESENT":
            raise CoreError("EXECUTION_WRITE_ANCHOR_REQUIRED")
        snapshot = snapshot.model_copy(update={"path_observation": observation})
        channel, _, _ = self.router.channel_for(snapshot)
        preflight = getattr(channel.port, "preflight", None)
        if callable(preflight):
            preflight(action["capability"], action["resource"], args)
        key = PREFIX + action["action_id"]
        previous = self.store.one("core_meta", key)
        if previous:
            old = RouteSnapshot.model_validate_json(previous["value_json"])
            if (
                old.target_id,
                old.channel_id,
                old.binding_digest,
                old.source_context.context_id,
                old.target_context.context_id,
            ) != (
                snapshot.target_id,
                snapshot.channel_id,
                snapshot.binding_digest,
                snapshot.source_context.context_id,
                snapshot.target_context.context_id,
            ):
                raise CoreError("EXECUTION_ACTION_ROUTE_ALREADY_BOUND")
            snapshot = old
        tx.put("core_meta", {"key": key, "value_json": snapshot.model_dump_json()})

    def _proof(self, inv, *, verify=False):
        action = self.store.one("actions", inv.action_id)
        if (
            not action
            or action["state"] not in ({"PENDING_VERIFY", "UNKNOWN", "SUCCEEDED"} if verify else {"DISPATCHING"})
            or (
                action["attempt_id"],
                action["capability"],
                action["resource"],
                action["args_hash"],
                action["idempotency_key"],
            )
            != (inv.attempt_id, inv.capability, inv.resource, inv.args_hash, inv.idempotency_key)
            or inv.args_hash != digest(inv.args)
        ):
            raise CoreError("EXECUTION_KERNEL_INVOCATION_REQUIRED")
        attempts = [
            a
            for a in self.store.all("attempts")
            if a["action_id"] == inv.action_id
            and a["kind"] == ("VERIFY" if verify else "EXECUTE")
            and a["started_at_us"] is not None
            and a["outcome"] is None
        ]
        if not attempts:
            raise CoreError("EXECUTION_AUTHORIZED_ATTEMPT_REQUIRED")
        attempt = attempts[-1]
        capability = self._gate.verify_capability if verify else inv.capability
        self._gate._grant_for(capability, inv.resource, attempt["grant_id"])
        holds = {h["dimension"]: h for h in self.store.all("budget_holds") if h["owner_id"] == attempt["attempt_id"]}
        requirements = {"external_requests": "SPENT", "cost_micro_units": "HELD"}
        if not verify and (
            self.registry.is_write(inv.capability) if self.registry else inv.capability == "reading.card.create"
        ):
            requirements["write_attempts"] = "SPENT"
        if any(
            key not in holds or holds[key]["status"] != state or holds[key]["amount"] != 1
            for key, state in requirements.items()
        ):
            raise CoreError("EXECUTION_BUDGET_RESERVATION_REQUIRED")
        row = self.store.one("core_meta", PREFIX + inv.action_id)
        if row is None:
            raise CoreError("EXECUTION_ACTION_CONTEXT_REQUIRED")
        snapshot = RouteSnapshot.model_validate_json(row["value_json"])
        binding = self.router.resources.get(snapshot.resource)
        if (
            snapshot.resource != inv.resource
            or binding is None
            or inv.capability not in binding.capabilities
            or snapshot.binding_digest != digest(binding.model_dump(mode="json"))
        ):
            raise CoreError("EXECUTION_ACTION_CONTEXT_MISMATCH")
        return snapshot, attempt

    def _observe(self, snapshot, *, verify=False):
        channel, _, _ = self.router.channel_for(snapshot)
        evidence = self.router.observe_selected(snapshot)
        current = PathObservation.model_validate_json(canonical(evidence["observation"]))
        if current.status not in {"PRESENT", "MISSING"}:
            raise CoreError("EXECUTION_PATH_PREFLIGHT_UNAVAILABLE")
        old = snapshot.path_observation
        if (
            not verify
            and old
            and old.status == "PRESENT"
            and (current.status != "PRESENT" or (current.device, current.inode) != (old.device, old.inode))
        ):
            raise CoreError("EXECUTION_FILESYSTEM_IDENTITY_CHANGED")
        # A legitimate atomic write may replace its file inode. Verification
        # therefore delegates outcome/correlation to the original readback
        # adapter while retaining the exact context/channel and symlink guards.
        self.router.channel_for(snapshot)
        return channel, evidence

    def execute(self, inv):
        self._gate._execution_fence()
        snapshot, attempt = self._proof(inv)
        channel, evidence = self._observe(snapshot)
        key = "execution.context.dispatch:" + inv.action_id
        # Durable dispatch claim precedes the effect. A crash cannot cause this
        # decorator to resend, even if a caller bypasses Kernel.run by mistake.
        with self.store.transaction(
            "execution.context_dispatch",
            {
                "action_id": inv.action_id,
                "attempt_id": attempt["attempt_id"],
                "target_id": snapshot.target_id,
                "channel_id": snapshot.channel_id,
                "target_context_id": snapshot.target_context.context_id,
            },
        ) as tx:
            if self.store.one("core_meta", key):
                raise CoreError("EXECUTION_ALREADY_DISPATCHED_VERIFY_ONLY")
            tx.put(
                "core_meta",
                {
                    "key": key,
                    "value_json": canonical(
                        {
                            "snapshot_digest": digest(snapshot.model_dump(mode="json")),
                            "attempt_id": attempt["attempt_id"],
                            "metadata": evidence,
                        }
                    ),
                },
            )
        # Peer-side context is checked immediately before an existing adapter
        # executes. Remote channels must implement the same peer-side condition.
        self.router.channel_for(snapshot)
        receipt = channel.port.execute(inv)
        if type(receipt) is not Receipt:
            raise CoreError("EXECUTION_STRICT_RECEIPT_REQUIRED")
        return Receipt(external_id=receipt.external_id, result={**receipt.result, "execution_context": evidence})

    def verify(self, inv):
        snapshot, _ = self._proof(inv, verify=True)
        channel, evidence = self._observe(snapshot, verify=True)
        result = channel.port.verify(inv)
        if type(result) is not Verification:
            raise CoreError("EXECUTION_STRICT_VERIFICATION_REQUIRED")
        # Preserve result as the original semantic result; context is additional
        # evidence, never a MATCH generated by the router itself.
        return Verification(verdict=result.verdict, evidence={**result.evidence, "execution_context": evidence})
