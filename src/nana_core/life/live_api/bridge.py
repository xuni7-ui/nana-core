"""Versioned application transitions into original UDS/Inspector contracts.

No Subject constructor or OperatorAuthority. A session role admits an application
request; Core still decides WHAT/WHY and retains its original execution checks.
"""

import hashlib
import json
import secrets
import threading
import time
from pathlib import Path
from ...contracts import CoreError
from ..control import request as core_request, LIMIT
from ..inspector import inspect
from .contracts import ApiError, Completion, Envelope, Page, Role
from .ledger import OperationLedger, fingerprint

PAGE_SECTIONS = {
    Page.HOME: ("activities", "concerns", "needs", "interests", "relationship", "goals"),
    Page.CHAT: ("decisions", "experience", "source_lifecycle"),
    Page.MEMORIES: ("experience", "provenance", "source_lifecycle"),
    Page.GOALS: ("goals", "suppressed_deferred", "unknown"),
    Page.JOURNAL: ("activities", "experience", "decisions"),
    Page.WORLD: ("world", "concerns", "source_lifecycle"),
    Page.GROWTH: ("skills", "learning", "experience"),
    Page.DEVICES: ("authority", "provider"),
    Page.RUNTIME: ("runtime", "health", "provider", "queue", "unknown", "authority"),
    Page.SETTINGS: ("authority", "provider", "suppressed_deferred"),
}


class GatewayService:
    def __init__(self, supervisor, auth, state_root):
        self.supervisor, self.auth = supervisor, auth
        self.binding = supervisor.binding
        self.generation = secrets.token_hex(16)
        self.ledger = OperationLedger(Path(state_root) / "operations.json")
        self.write_lock = threading.RLock()
        self.read_lock = threading.RLock()
        self.event_sequence = 0
        self.event_digest = None
        self.events = []
        self.receipt_privacy = {}

    def _receipt(self, key, principal):
        receipt = self.ledger.read(key, principal)
        if receipt.result and self.receipt_privacy.get(key) != self._privacy_watermark():
            self.ledger.volatile.pop(key, None)
            return receipt.model_copy(update={"result": {"state": "BODY_WITHHELD_SOURCE_CHANGED"}})
        return receipt

    def envelope(self, data, *, coverage="CURRENT", refs=()):
        status = self.supervisor.status()
        return Envelope(
            realm=self.binding.realm,
            subject_id=self.binding.subject_id,
            lineage_binding=self.binding.lineage_binding,
            owner_epoch=status["owner_epoch"],
            run_generation=self.generation,
            session_generation=self.auth.generation,
            as_of_us=time.time_ns() // 1000,
            revision=self.ledger.revision,
            coverage=coverage,
            privacy_scope=self.binding.privacy,
            source_refs=tuple(refs)[:32],
            capabilities={
                "memory_metadata": True,
                "body_cache": False,
                "background_push": "UNAVAILABLE",
                "device_control": False,
                "social_delivery": "NOT_AUTHORIZED",
                "provider_authority": False,
            },
            data=data,
        ).model_dump(mode="json")

    def bootstrap(self, principal):
        principal.require(Role.READER)
        status = self.supervisor.status()
        return self.envelope(
            {
                "host": status,
                "roles": [r.value for r in principal.roles],
                "provider": self.provider_status(),
                "pages": [p.value for p in Page],
                "notifications": {"foreground": "SUPPORTED_AFTER_NATIVE_PERMISSION", "background": "NOT_QUALIFIED"},
                "first_life": "NOT_READY",
                "identity_provenance": "EXISTING_BOUND_SUBJECT_NOT_AUTOMATIC_GENESIS",
            }
        )

    def provider_status(self):
        status = self.supervisor.status()
        if not status["process_ready"]:
            return {"state": "UNAVAILABLE_CORE_STOPPED", "real_model_qualification": "NOT_RUN_THIS_MISSION"}
        try:
            result = core_request(self.supervisor.home, {"operation": "view", "view": "status"}, timeout=2)
            if result.get("ok") is not True:
                raise ApiError("CORE_UNAVAILABLE", 503)
            return {
                "state": result["result"].get("provider", "UNKNOWN"),
                "real_model_qualification": "NOT_RUN_THIS_MISSION",
                "secret_value_available_to_client": False,
            }
        except (CoreError, OSError):
            return {"state": "UNKNOWN", "real_model_qualification": "NOT_RUN_THIS_MISSION"}

    def snapshot(self, principal, page):
        principal.require(Role.READER)
        page = Page(page)
        with self.read_lock:
            self.supervisor.verify_binding()
            try:
                privacy_before = self._privacy_watermark()
                view = inspect(
                    self.supervisor.home,
                    scope=self.binding.scope,
                    entity_id=self.binding.entity_id,
                    privacy=self.binding.privacy,
                    limit=16,
                )
            except (CoreError, OSError, ValueError):
                return self.envelope(
                    {"page": page.value, "items": [], "reason": "SOURCE_PROJECTION_UNAVAILABLE"}, coverage="UNAVAILABLE"
                )
            if view.identity_id != self.binding.subject_id:
                raise ApiError("INVALID_IDENTITY", 409)
            privacy_after = self._privacy_watermark()
            if privacy_before != privacy_after:
                return self.envelope(
                    {"page": page.value, "items": [], "reason": "SOURCE_CHANGED_REFRESH_REQUIRED"}, coverage="STALE"
                )
            items = []
            for name in PAGE_SECTIONS[page]:
                for row in view.sections.get(name, ()):
                    items.append({"section": name, **row.model_dump(mode="json")})
            status = self.supervisor.status()
            data = {
                "page": page.value,
                "items": items,
                "host": status,
                "resources": view.resources,
                "projection_coverage": view.coverage,
                "provider": self.provider_status(),
                "limitations": {
                    "private_history": "NOT_IMPORTED_OR_AUTHORIZED",
                    "memory_bodies": "SCOPED_PUBLIC_PROJECT_ONLY",
                    "phone_control": "NO_DEVICE_AGENT",
                    "background_push": "NOT_QUALIFIED",
                },
                "privacy_watermark": privacy_after,
            }
            if page == Page.SETTINGS:
                from ..provider import provider_status

                try:
                    data["provider_settings"] = provider_status(self.supervisor.home)["provider_settings"]
                except (CoreError, OSError, ValueError):
                    data["provider_settings"] = {"state": "UNAVAILABLE", "no_default_provider_selected": True}
            if page == Page.MEMORIES:
                data["memories"] = self._memories()
                if self._privacy_watermark() != privacy_after:
                    return self.envelope(
                        {"page": page.value, "items": [], "memories": [], "reason": "SOURCE_CHANGED_REFRESH_REQUIRED"},
                        coverage="STALE",
                    )
            if page == Page.DEVICES:
                data["surfaces"] = [
                    {"platform": "nana.space", "state": "BOUND_TO_THIS_SUBJECT"},
                    {"platform": "qq", "state": "SHADOW_ONLY_PRODUCTION_NOT_CONNECTED"},
                    {"platform": "bilibili", "state": "NOT_CONNECTED"},
                    {"platform": "android.device-control", "state": "NO_DEVICE_AGENT"},
                ]
            coverage = "CURRENT" if status["process_ready"] else "STALE"
            if not items and coverage == "CURRENT":
                coverage = "NO_DATA"
            refs = tuple(dict.fromkeys(r["reference"] for r in items))[:32]
            return self.envelope(data, coverage=coverage, refs=refs)

    def _privacy_watermark(self):
        # Original Inspector already validated the original journal. Hash only,
        # no second memory or deletion authority and no exposed host path.
        from ...continuity.privacy import _load

        side = Path(str(self.supervisor.home / "subject/self.db") + ".privacy.json")
        link = _load(side)
        anchor = Path(link.get("anchor_path", str(side)))
        return hashlib.sha256(anchor.read_bytes()).hexdigest()

    def events_since(self, principal, cursor=None):
        principal.require(Role.READER)
        with self.read_lock:
            snapshot = self.snapshot(principal, Page.HOME)
            stable = {
                "items": snapshot["data"].get("items", []),
                "host": snapshot["data"].get("host", {}),
                "privacy": snapshot["data"].get("privacy_watermark"),
                "revision": snapshot["revision"],
            }
            value = fingerprint(stable)
            if value != self.event_digest:
                self.event_sequence += 1
                self.event_digest = value
                self.events.append(
                    {
                        "sequence": self.event_sequence,
                        "kind": "INVALIDATE_SCOPED_SNAPSHOT",
                        "as_of_us": snapshot["as_of_us"],
                        "source_refs": snapshot["source_refs"],
                    }
                )
                self.events = self.events[-64:]
            gap = False
            sequence = 0
            if cursor:
                parts = cursor.split(".")
                if len(parts) != 2 or parts[0] != self.generation or not parts[1].isdigit():
                    gap = True
                else:
                    sequence = int(parts[1])
                    gap = sequence > self.event_sequence or (self.events and sequence < self.events[0]["sequence"] - 1)
            events = [] if gap else [e for e in self.events if e["sequence"] > sequence][:32]
            return self.envelope(
                {
                    "cursor": self.generation + "." + str(self.event_sequence),
                    "gap": bool(gap),
                    "snapshot_required": bool(gap),
                    "events": events,
                    "no_command_replay": True,
                }
            )

    def _prepare(self, principal, body, operation, role):
        principal.require(role)
        payload = body.model_dump(mode="json")
        old = self.ledger.prior(body.idempotency_key, principal.principal_id, payload)
        if old:
            return old
        if body.run_generation != self.generation:
            raise ApiError("STALE_RUN_NO_REPLAY", 409)
        status = self.supervisor.status()
        if body.owner_epoch != status["owner_epoch"]:
            raise ApiError("STALE_EPOCH", 409)
        self.ledger.reserve(
            body.idempotency_key,
            principal.principal_id,
            payload,
            operation,
            body.expected_revision,
            body.client_request_id,
        )
        return None

    def _call(self, principal, body, operation, role, call, verify, before=None):
        with self.write_lock:
            old = self._prepare(principal, body, operation, role)
            if old:
                return self.envelope(
                    self._receipt(body.idempotency_key, principal.principal_id).model_dump(mode="json")
                )
            key = body.idempotency_key
            try:
                if before is not None:
                    before()
            except ApiError as exc:
                self.ledger.transition(key, Completion.REJECTED, error=exc.code)
                return self.envelope(self.ledger.read(key, principal.principal_id).model_dump(mode="json"))
            try:
                # Persist dispatch intention before any possible real effect.
                self.ledger.transition(key, Completion.RUNNING, dispatched=True)
                result = call()
                if not verify(result):
                    raise ApiError("RESULT_UNVERIFIED", 503)
                self.ledger.transition(key, Completion.VERIFIED, result=result)
                self.receipt_privacy[key] = self._privacy_watermark()
            except Exception:
                # No retry/fallback. The underlying original Core receipt remains
                # authoritative. Never turn a missing result into fake failure.
                self.ledger.transition(key, Completion.UNKNOWN, error="UNKNOWN_NEEDS_RECONCILIATION")
            return self.envelope(self.ledger.read(key, principal.principal_id).model_dump(mode="json"))

    def send(self, principal, body, *, surface_binding_id=None):
        if body.privacy_class not in self.binding.privacy:
            raise ApiError("SCOPE_DENIED", 403)
        event_id = (
            "v2." + hashlib.sha256((principal.principal_id + "\0" + body.client_request_id).encode()).hexdigest()[:56]
        )
        observation = {
            "binding_id": surface_binding_id or self.binding.surface_binding_id,
            "event_id": event_id,
            "thread_id": body.thread_id,
            "topic": body.topic,
            "text": body.text,
            "privacy_class": body.privacy_class,
        }
        command = {"operation": "surface", "observation": observation}
        if len(json.dumps(command).encode()) >= LIMIT:
            raise ApiError("CORE_INPUT_BOUND", 413)

        def call():
            result = core_request(self.supervisor.home, command, timeout=20)
            if result.get("ok") is not True:
                raise ApiError("CORE_INPUT_REJECTED", 409)
            row = result["result"]
            safe = {
                k: row[k]
                for k in (
                    "state",
                    "text",
                    "provider_state",
                    "render_state",
                    "mode",
                    "judgment",
                    "intention",
                    "message_memory_id",
                    "raw_body_persisted",
                )
                if k in row
            }
            safe.update(external_delivery=False, completion_kind="SUBJECT_REVIEW_NOT_SOCIAL_DELIVERY")
            return safe

        return self._call(
            principal,
            body,
            "MESSAGE",
            Role.CONVERSATION,
            call,
            lambda row: row.get("state")
            in {"SHADOW_REPLY_CANDIDATE", "ALREADY_REVIEWED_NO_REPLAY", "ALREADY_REVIEWED_SOURCE_RETIRED"},
        )

    def command(self, principal, body):
        principal.require(Role.MANAGER)
        op = body.operation
        if op in {"PAUSE", "RESUME", "BUSY", "AVAILABLE", "REVOKE"}:
            command = {"operation": "control", "command": op.lower()}
        elif op == "WITHDRAW" and body.target_id:
            self._assert_memory_scope(body.target_id)
            command = {"operation": "forget", "memory_id": body.target_id}
        elif op == "SET_SURFACE" and body.target_id and body.target_revision is not None and body.enabled is not None:
            command = {
                "operation": "surface-enabled",
                "binding_id": body.target_id,
                "enabled": body.enabled,
                "expected_revision": body.target_revision,
            }
        else:
            raise ApiError("COMMAND_ARGUMENT_REQUIRED")

        def call():
            r = core_request(self.supervisor.home, command, timeout=6)
            if r.get("ok") is not True:
                raise ApiError("CORE_COMMAND_REJECTED", 409)
            result = r["result"]
            if op in {"PAUSE", "RESUME"}:
                after = core_request(self.supervisor.home, {"operation": "view", "view": "status"}, timeout=2)
                expected = "PAUSED" if op == "PAUSE" else "RUNNING"
                if after.get("result", {}).get("autonomy") != expected:
                    raise ApiError("CONTROL_UNVERIFIED", 503)
            return {"operation": op, "core_result": result, "subject_desire_rewritten": False, "grants_created": False}

        return self._call(principal, body, op, Role.MANAGER, call, lambda row: isinstance(row, dict))

    def host_operation(self, principal, body):
        principal.require(Role.HOST_ADMIN)

        def call():
            if body.operation == "START":
                return self.supervisor.start()
            if body.operation == "STOP":
                return self.supervisor.stop()
            if body.operation == "RESTART":
                return self.supervisor.restart()
            if body.operation == "BACKUP":
                name = "host-" + hashlib.sha256(body.idempotency_key.encode()).hexdigest()[:24]
                r = core_request(self.supervisor.home, {"operation": "backup", "name": name}, timeout=10)
                if r.get("ok") is not True:
                    raise ApiError("BACKUP_UNVERIFIED", 503)
                row = r["result"]
                return {"state": row["state"], "identity_id": row["identity_id"], "quarantined_review_copy": True}
            if body.operation in {"UPGRADE", "ROLLBACK"}:
                return self.supervisor.change_release(body.release_id, rollback=body.operation == "ROLLBACK")
            raise ApiError("CAPABILITY_UNAVAILABLE", 409)

        def before():
            if body.operation in {"UPGRADE", "ROLLBACK"} and (
                not body.release_id or body.release_id not in self.supervisor.releases
            ):
                raise ApiError("QUALIFIED_RELEASE_REQUIRED", 409)
            self.auth.consume_confirmation(
                principal, body.confirmation_id, body.operation, body.expected_revision, body.release_id
            )

        return self._call(
            principal, body, body.operation, Role.HOST_ADMIN, call, lambda row: isinstance(row, dict), before
        )

    def receipt(self, principal, key):
        return self.envelope(self._receipt(key, principal.principal_id).model_dump(mode="json"))

    def _assert_memory_scope(self, memory_id):
        import sqlite3
        from ..inspector import _ReadView

        path = self.supervisor.home / "subject/self.db"
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            view = _ReadView(db, path, self.binding.scope, self.binding.privacy)
            row = view.one("memories", memory_id)
            if not row or row["entity_id"] != self.binding.entity_id:
                raise ApiError("SCOPE_DENIED", 403)

    def _memories(self):
        import sqlite3
        from ..inspector import _ReadView
        from ...continuity.memory import MemoryService

        path = self.supervisor.home / "subject/self.db"
        result = []
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            view = _ReadView(db, path, self.binding.scope, self.binding.privacy)
            memory = MemoryService(view)
            marks = ",".join("?" for _ in self.binding.privacy)
            rows = db.execute(
                "SELECT memory_id FROM memories WHERE entity_id=? AND scope=? AND privacy_class IN ("
                + marks
                + ") AND lifecycle='ACTIVE' ORDER BY created_at_us DESC LIMIT 32",
                (self.binding.entity_id, self.binding.scope, *self.binding.privacy),
            ).fetchall()
            for row in rows:
                try:
                    current = memory.read(row["memory_id"])
                except CoreError:
                    continue
                result.append(
                    {
                        k: current[k]
                        for k in (
                            "memory_id",
                            "memory_type",
                            "epistemic_kind",
                            "assessment",
                            "privacy_class",
                            "source_evidence_id",
                            "created_at_us",
                            "text",
                        )
                        if k in current
                    }
                )
            view.ensure_privacy_current()
        return result
