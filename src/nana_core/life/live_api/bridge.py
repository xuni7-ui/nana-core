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
    Page.HOME: ("activities", "concerns", "needs", "affect", "interests", "relationship", "goals"),
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
    def __init__(
        self,
        supervisor,
        auth,
        state_root,
        *,
        allow_provider_configuration=False,
        allow_provider_runtime_budget=False,
        credential_resolver=None,
        platform_event_secret_refs=None,
    ):
        self.supervisor, self.auth = supervisor, auth
        self.allow_provider_configuration = allow_provider_configuration
        self.allow_provider_runtime_budget = allow_provider_runtime_budget
        self.credential_resolver = credential_resolver
        self.binding = supervisor.binding
        self.generation = secrets.token_hex(16)
        self.ledger = OperationLedger(Path(state_root) / "operations.json")
        self.write_lock = threading.RLock()
        self.priority_lock = threading.RLock()
        self.read_lock = threading.RLock()
        self.provider_catalog_after = 0
        self.event_sequence = 0
        self.event_digest = None
        self.events = []
        self.receipt_privacy = {}
        self.receipt_scopes = {}
        from .platform_events import PlatformEvents

        self.platform_events = PlatformEvents(self, platform_event_secret_refs or {})

    def _prune_receipt_cache(self):
        # Warm body visibility follows the bounded host ledger, never an
        # unbounded second dialogue history. Archived metadata has no wording.
        hot = self.ledger.document.read()['receipts']
        for cache in (self.receipt_privacy, self.receipt_scopes):
            for key in tuple(cache):
                if key not in hot:
                    cache.pop(key, None)

    def _receipt(self, key, principal):
        receipt = self.ledger.read(key, principal.principal_id)
        if receipt.state==Completion.UNKNOWN and receipt.operation=='MEMORY_NOTE':
            from .memory_notes import reconcile
            receipt=reconcile(self,key,principal,receipt)
        if receipt.state==Completion.UNKNOWN and receipt.operation=='LANGUAGE_FEEDBACK':
            receipt=self.reconcile_language_feedback(key,principal,receipt)
        if receipt.result and (
            self.receipt_privacy.get(key) != self._privacy_watermark()
            or not set(self.receipt_scopes.get(key, ())) <= set(self.privacy_for(principal))
        ):
            self.ledger.volatile.pop(key, None)
            return receipt.model_copy(update={"result": {"state": "BODY_WITHHELD_SOURCE_CHANGED"}})
        return receipt

    def privacy_for(self, principal=None):
        """Intersection of host binding and explicitly granted application role.

        Old devices and metadata-only responses never inherit PERSONAL merely
        because the host later permits it. Surface/Provider/Manager gates remain.
        """
        private = principal is not None and Role.PRIVATE_CONTEXT in principal.roles
        return tuple(p for p in self.binding.privacy if p != "PERSONAL" or private)

    def envelope(self, data, *, coverage="CURRENT", refs=(), principal=None):
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
            privacy_scope=self.privacy_for(principal),
            source_refs=tuple(refs)[:32],
            capabilities={
                "memory_metadata": True,
                "memory_search": True,
                "memory_notes": True,
                "conversation_feedback": True,
                "memory_use_feedback": True,
                "long_reply_feedback": True,
                "backup_status": True,
                "body_cache": False,
                "background_push": "UNAVAILABLE",
                "device_control": False,
                "social_delivery": "NOT_AUTHORIZED",
                "provider_authority": False,
                "provider_configuration_write": self.allow_provider_configuration,
                "provider_runtime_configuration": self.allow_provider_runtime_budget is True and self.allow_provider_configuration is True and self.supervisor.provider_live_authorized is True,
                "provider_readiness": True,
                "chat_streaming": True,
                "provider_model_discovery": self.allow_provider_configuration and self.credential_resolver is not None,
                "native_secret_binding": self.allow_provider_configuration and self.credential_resolver is not None,
                "durable_provider_binding": bool(getattr(self.credential_resolver, "persistent", False)),
                "shared_life_retention": True,
                "conversation_history": True,
                "platform_bilibili_history": True,
                "shared_life_candidates": True,
                "notification_inbox": True,
                "background_poll_hints": True,
                "platform_configuration_write": self.allow_provider_configuration,
                "platform_native_secret_binding": self.allow_provider_configuration
                and self.credential_resolver is not None,
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
                "notifications": {
                    "foreground": "SUPPORTED_AFTER_NATIVE_PERMISSION",
                    "background": "OS_SCHEDULED_METADATA_SUBSCRIPTION",
                    "instant_push": False,
                    "physical_delivery": "NOT_RUN",
                },
                "first_life": "NOT_READY",
                "identity_provenance": "EXISTING_BOUND_SUBJECT_NOT_AUTOMATIC_GENESIS",
            },
            principal=principal,
        )

    def conversation_history(self, principal):
        principal.require(Role.CONVERSATION)
        with self.read_lock:
            self.supervisor.verify_binding()
            before = self._privacy_watermark()
            response = core_request(
                self.supervisor.home,
                {
                    "operation": "conversation-history",
                    "privacy": list(self.privacy_for(principal)),
                    "scope": self.binding.scope,
                    "entity_id": self.binding.entity_id,
                },
            )
            if response.get("ok") is not True:
                raise ApiError("CONVERSATION_HISTORY_UNAVAILABLE", 503)
            after = self._privacy_watermark()
            data = (
                response["result"] if before == after else {"items": [], "coverage": "SOURCE_CHANGED_REFRESH_REQUIRED"}
            )
            data["privacy_watermark"] = after
            # Only original body-free metadata owned by this principal; no replay.
            data['pending_receipts_coverage'] = 'RECENT_ONLY_ARCHIVED_METADATA_AVAILABLE_BY_ORIGINAL_ID'
            data["pending_receipts"] = [
                {"receipt_id": key, "state": row["receipt"]["state"]}
                for key, row in self.ledger.document.read()["receipts"].items()
                if row["principal"] == principal.principal_id
                and row["receipt"]["operation"] == "MESSAGE"
                and row["receipt"]["state"] in {"REQUESTED", "UNKNOWN"}
            ][-32:]
            return self.envelope(data, principal=principal)

    def shared_candidates(self, principal):
        principal.require(Role.CONVERSATION)
        with self.read_lock:
            self.supervisor.verify_binding()
            before = self._privacy_watermark()
            response = core_request(
                self.supervisor.home,
                {
                    "operation": "shared-candidates",
                    "privacy": list(self.privacy_for(principal)),
                    "scope": self.binding.scope,
                    "entity_id": self.binding.entity_id,
                },
            )
            if response.get("ok") is not True:
                raise ApiError("SHARED_CANDIDATES_UNAVAILABLE", 503)
            after = self._privacy_watermark()
            data = (
                response["result"] if before == after else {"items": [], "coverage": "SOURCE_CHANGED_REFRESH_REQUIRED"}
            )
            data["privacy_watermark"] = after
            return self.envelope(data, principal=principal)

    def notification_inbox(self, principal):
        principal.require(Role.CONVERSATION)
        with self.read_lock:
            self.supervisor.verify_binding()
            before = self._privacy_watermark()
            response = core_request(
                self.supervisor.home,
                {
                    "operation": "notification-inbox",
                    "privacy": list(self.privacy_for(principal)),
                    "scope": self.binding.scope,
                    "entity_id": self.binding.entity_id,
                },
            )
            if response.get("ok") is not True:
                raise ApiError("NOTIFICATION_INBOX_UNAVAILABLE", 503)
            after = self._privacy_watermark()
            data = response["result"] if before == after else {"items": [], "state": "SOURCE_CHANGED_REFRESH_REQUIRED"}
            return self.envelope({**data, "privacy_watermark": after}, principal=principal)

    def bilibili_history(self, principal):
        principal.require(Role.READER)
        with self.read_lock:
            self.supervisor.verify_binding()
            before = self._privacy_watermark()
            response = core_request(
                self.supervisor.home,
                {
                    "operation": "bilibili-history",
                    "privacy": list(self.privacy_for(principal)),
                    "scope": self.binding.scope,
                    "entity_id": self.binding.entity_id,
                },
            )
            if response.get("ok") is not True:
                raise ApiError("BILIBILI_HISTORY_UNAVAILABLE", 503)
            after = self._privacy_watermark()
            if before != after:
                return self.envelope(
                    {"items": [], "privacy_watermark": after, "state": "SOURCE_CHANGED_REFRESH_REQUIRED"},
                    coverage="STALE",
                    principal=principal,
                )
            return self.envelope({**response["result"], "privacy_watermark": after}, principal=principal)

    def backup_status(self, principal):
        """Derived existing receipt metadata; never opens a snapshot or PC path."""
        principal.require(Role.READER)
        self.supervisor.verify_binding()
        rows = self.ledger.document.read()["receipts"].values()
        # A caller only sees receipts it owns. No backup body or host path.
        local = [
            {
                "receipt_id": r["receipt"]["receipt_id"],
                "state": r["receipt"]["state"],
                "dispatch_happened": r["receipt"]["dispatch_happened"],
                "created_at_us": r["created_at_us"],
            }
            for r in rows
            if r["principal"] == principal.principal_id and r["receipt"]["operation"] == "BACKUP"
        ][-16:]
        return self.envelope(
            {
                "local_receipts": local,
                "scope": "OWN_CALLER_METADATA_ONLY",
                "offsite_state": "STATUS_NOT_EXPOSED",
                "disaster_recovery": "NOT_QUALIFIED_BY_THIS_PROJECTION",
                "pc_delivery": "NOT_OBSERVED",
                "restore_check": "NOT_OBSERVED",
                "backup_schedule": "NOT_EXPOSED",
                "runnable_clone": False,
            },
            principal=principal,
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
                "readiness": result["result"].get("provider_readiness", {"state": "UNAVAILABLE_OLD_RUNTIME"}),
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
                    privacy=self.privacy_for(principal),
                    limit=16,
                )
            except (CoreError, OSError, ValueError):
                return self.envelope(
                    {"page": page.value, "items": [], "reason": "SOURCE_PROJECTION_UNAVAILABLE"},
                    coverage="UNAVAILABLE",
                    principal=principal,
                )
            if view.identity_id != self.binding.subject_id:
                raise ApiError("INVALID_IDENTITY", 409)
            privacy_after = self._privacy_watermark()
            if privacy_before != privacy_after:
                return self.envelope(
                    {"page": page.value, "items": [], "reason": "SOURCE_CHANGED_REFRESH_REQUIRED"},
                    coverage="STALE",
                    principal=principal,
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
                    "memory_bodies": "EXPLICIT_DEVICE_AND_HOST_SCOPE",
                    "phone_control": "NO_DEVICE_AGENT",
                    "background_push": "NOT_QUALIFIED",
                },
                "privacy_watermark": privacy_after,
            }
            if page == Page.SETTINGS:
                from .provider_settings import projection

                try:
                    current = (
                        core_request(
                            self.supervisor.home, {"operation": "view", "view": "provider-settings"}, timeout=2
                        )
                        if status["process_ready"]
                        else {}
                    )
                    data["provider_settings"] = (
                        current["result"] if current.get("ok") is True else projection(self.supervisor.home)
                    )
                except (CoreError, OSError, ValueError):
                    data["provider_settings"] = {"state": "UNAVAILABLE", "no_default_provider_selected": True}
            if page == Page.MEMORIES:
                data["memories"] = self._memories(principal)
                if self._privacy_watermark() != privacy_after:
                    return self.envelope(
                        {"page": page.value, "items": [], "memories": [], "reason": "SOURCE_CHANGED_REFRESH_REQUIRED"},
                        coverage="STALE",
                        principal=principal,
                    )
            if page == Page.DEVICES:
                state = (
                    core_request(self.supervisor.home, {"operation": "platform-status"}, timeout=2)
                    if status["process_ready"]
                    else {}
                )
                channels = state.get("result", {}).get("channels", []) if state.get("ok") is True else []
                data["surfaces"] = [
                    {"platform": "nana.space", "state": "BOUND_TO_THIS_SUBJECT"},
                    *[{"platform": c["platform"] + "." + c["channel_id"], "state": c["state"]} for c in channels],
                    {"platform": "android.device-control", "state": "NO_DEVICE_AGENT"},
                ]
                data["platform_runtime"] = state.get("result", {"state": "OWNER_UNAVAILABLE"})
            coverage = "CURRENT" if status["process_ready"] else "STALE"
            if not items and coverage == "CURRENT":
                coverage = "NO_DATA"
            refs = tuple(dict.fromkeys(r["reference"] for r in items))[:32]
            return self.envelope(data, coverage=coverage, refs=refs, principal=principal)

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
                        "source_refs": [],  # Shared invalidation ring contains no private references.
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
                },
                principal=principal,
            )

    def _prepare(self, principal, body, operation, role):
        principal.require(role)
        payload = body.model_dump(mode="json")
        if operation == "MESSAGE" and payload.get("require_model") is False:
            payload.pop("require_model")  # Preserve v2 receipt fingerprints.
        if operation == "MESSAGE" and payload.get("retain_shared_life") is False:
            payload.pop("retain_shared_life")
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

    def _call(self, principal, body, operation, role, call, verify, before=None, *, priority=False):
        # Receipt metadata CAS is independently locked. Only existing restrictive
        # controls may bypass the long conversational dispatch lock; the original
        # owner still serializes actual effects at its transport-wait safe point.
        with (self.priority_lock if priority else self.write_lock):
            old = self._prepare(principal, body, operation, role)
            if old:
                return self.envelope(
                    self._receipt(body.idempotency_key, principal).model_dump(mode="json"), principal=principal
                )
            key = body.idempotency_key
            try:
                if before is not None:
                    before()
            except ApiError as exc:
                self.ledger.transition(key, Completion.REJECTED, error=exc.code)
                return self.envelope(
                    self.ledger.read(key, principal.principal_id).model_dump(mode="json"), principal=principal
                )
            try:
                # Persist dispatch intention before any possible real effect.
                self.ledger.transition(key, Completion.RUNNING, dispatched=True)
                result = call()
                if not verify(result):
                    raise ApiError("RESULT_UNVERIFIED", 503)
                self.ledger.transition(key, Completion.VERIFIED, result=result)
                self.receipt_privacy[key] = self._privacy_watermark()
                self.receipt_scopes[key] = self.privacy_for(principal)
            except Exception:
                # No retry/fallback. The underlying original Core receipt remains
                # authoritative. Never turn a missing result into fake failure.
                self.ledger.transition(key, Completion.UNKNOWN, error="UNKNOWN_NEEDS_RECONCILIATION")
            self._prune_receipt_cache()
            return self.envelope(
                self.ledger.read(key, principal.principal_id).model_dump(mode="json"), principal=principal
            )

    def reconcile_language_feedback(self, key, principal, receipt):
        """Only a matching original commit can settle UNKNOWN; never resend."""
        import sqlite3
        from ...continuity.records import RecordService
        from ...storage import digest
        from ..inspector import _ReadView

        if Role.MANAGER not in principal.roles:
            return receipt
        with self.write_lock:
            saved=self.ledger.entry(key)
            if not saved or saved['principal']!=principal.principal_id:
                return receipt
            sample_id='web-review.'+digest([principal.principal_id,key])
            path=self.supervisor.home / 'subject/self.db'
            try:
                with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
                    db.row_factory=sqlite3.Row
                    db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
                    view=_ReadView(db,path,self.binding.scope,self.privacy_for(principal))
                    records=RecordService(view)
                    event=db.execute("SELECT data_json FROM events WHERE source_namespace='language.review' AND source_key=?",(sample_id,)).fetchone()
                    if not event:return receipt
                    rid=json.loads(event[0])['data']['record_id']
                    row=records.read(rid);payload=row['payload']
                    sample=payload.get('sample',{})
                    if (payload.get('person_kind')!='LIVED_LANGUAGE_SAMPLE'
                            or payload.get('request_digest')!=saved['digest']
                            or sample.get('sample_id')!=sample_id
                            or sample.get('provenance')!='USER_PROVIDED_REVIEW'
                            or sample.get('body_storage')!='DEPENDENT_RECORD'
                            or not records.current_support(rid)):
                        return receipt
                    exchange=records.read(sample['review_target'])
                    if exchange['payload'].get('entity_id')!=self.binding.entity_id:
                        return receipt
                    view.ensure_privacy_current()
            except Exception:
                return receipt
            current=self.ledger.read(key,principal.principal_id)
            if current.state!=Completion.UNKNOWN:return current
            self.ledger.transition(key,Completion.VERIFIED,result={'state':'EXPLICIT_FEEDBACK_SAVED',
                'sample_record_id':rid,'delivery_proven':False,'human_naturalness_qualified':False,
                'learning_state':'NOT_RECONCILED','reconciled_from_original_commit':True})
            self.receipt_privacy[key]=self._privacy_watermark()
            self.receipt_scopes[key]=self.privacy_for(principal)
            self._prune_receipt_cache()
            return self.ledger.read(key,principal.principal_id)

    def language_feedback(self, principal, body):
        """Retain an explicit review through the original owner, not delivery proof."""
        import sqlite3
        from ...continuity.records import RecordService
        from ...continuity.lived_language import LanguageSample, response_matches
        from ...storage import canonical, digest
        from ..inspector import _ReadView

        principal.require(Role.MANAGER)
        sample=body.sample.model_copy(update={'sample_id':'web-review.'+digest([principal.principal_id,body.idempotency_key])})

        def read_record(record_id):
            path=self.supervisor.home / 'subject/self.db'
            with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
                db.row_factory=sqlite3.Row
                db.execute('PRAGMA query_only=ON')
                db.execute('BEGIN')
                view=_ReadView(db,path,self.binding.scope,self.privacy_for(principal))
                records=RecordService(view)
                row=records.read(record_id)
                if not records.current_support(record_id):
                    raise ApiError('FEEDBACK_SOURCE_UNAVAILABLE',409)
                view.ensure_privacy_current()
                return row

        def before():
            try:
                exchange=read_record(body.exchange_record_id)
            except CoreError:
                raise ApiError('FEEDBACK_SOURCE_UNAVAILABLE',409) from None
            payload=exchange['payload']
            if (sample.provenance!='USER_PROVIDED_REVIEW' or sample.human_judgment=='UNREVIEWED'
                    or sample.review_target!=body.exchange_record_id
                    or payload.get('person_kind')!='CONVERSATION_EXCHANGE'
                    or payload.get('entity_id')!=self.binding.entity_id
                    or exchange['scope']!=self.binding.scope
                    or not response_matches(sample,payload.get('assistant_utterance'),body.response_sha256)):
                raise ApiError('FEEDBACK_TURN_MISMATCH',409)

        def call():
            response=core_request(self.supervisor.home,{'operation':'language-feedback',
                'sample':sample.model_dump(mode='json'),'exchange_record_id':body.exchange_record_id,
                **({'response_sha256':body.response_sha256} if body.response_sha256 is not None else {}),
                'request_digest':fingerprint(body.model_dump(mode='json'))})
            if response.get('ok') is not True:
                raise ApiError('FEEDBACK_CORE_UNCONFIRMED',503)
            result=response['result']
            record=read_record(result['sample_record_id'])
            saved=LanguageSample.model_validate_json(canonical(record['payload']['sample']))
            expected=sample.model_copy(update={'body_storage':'DEPENDENT_RECORD','memory_use':None})
            use=sample.memory_use.model_dump(mode='json') if sample.memory_use else None
            if (saved!=expected or record['payload'].get('memory_use_feedback')!=use
                    or record['payload'].get('response_sha256')!=body.response_sha256):
                raise ApiError('FEEDBACK_COMMIT_UNVERIFIED',503)
            return {**result,'state':'EXPLICIT_FEEDBACK_SAVED','delivery_proven':False}

        return self._call(principal,body,'LANGUAGE_FEEDBACK',Role.MANAGER,call,
            lambda result:result.get('state')=='EXPLICIT_FEEDBACK_SAVED',before)

    def send(self, principal, body, *, surface_binding_id=None, progress=None):
        if body.privacy_class not in self.privacy_for(principal):
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
            "retain_shared_life": body.retain_shared_life,
        }
        command = {"operation": "surface-stream" if progress is not None else "surface", "observation": observation}
        if len(json.dumps(command).encode()) >= LIMIT:
            raise ApiError("CORE_INPUT_BOUND", 413)

        def call():
            result = (core_request(self.supervisor.home, command, progress=progress) if progress is not None
                else core_request(self.supervisor.home, command))
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
                    "exchange_record_id",
                    "raw_body_persisted",
                    "route",
                )
                if k in row
            }
            safe.update(external_delivery=False, completion_kind="SUBJECT_REVIEW_NOT_SOCIAL_DELIVERY")
            return safe

        def before():
            if body.privacy_class == "PERSONAL":
                from ..config import load_config

                bindings = load_config(self.supervisor.home).surface_bindings
                surface = next((b for b in bindings if b.binding_id == observation["binding_id"]), None)
                if surface is None or "PERSONAL" not in surface.permitted_privacy:
                    raise ApiError("SURFACE_PRIVACY_NOT_BOUND", 403)
                if body.retain_shared_life and (
                    not surface.allow_personal_retention or not surface.personal_retention_consent_ref
                ):
                    raise ApiError("SURFACE_PERSONAL_RETENTION_NOT_AUTHORIZED", 403)
            if not body.require_model:
                return
            from ...continuity.dialogue_shadow.bridge import LiteralSpanInterpreter

            meaning = LiteralSpanInterpreter().interpret(body.text)
            if (
                meaning.kind in {"DECLINE_DEPTH", "DECLINE_DELIVERY", "REOPEN", "REOPEN_DELIVERY"}
                and meaning.basis == "LITERAL_SPAN"
            ):
                return  # Original C still reviews the boundary, without a model bill.
            try:
                ready = core_request(
                    self.supervisor.home, {"operation": "provider-readiness", "privacy": body.privacy_class}, timeout=2
                )
            except (CoreError, OSError):
                raise ApiError("PROVIDER_READINESS_UNAVAILABLE", 503) from None
            state = (
                ready.get("result", {}).get("state") if ready.get("ok") is True else "PROVIDER_READINESS_UNAVAILABLE"
            )
            if state != "READY_LOCAL_GATES":
                raise ApiError(state if isinstance(state, str) else "PROVIDER_READINESS_UNAVAILABLE", 409)

        return self._call(
            principal,
            body,
            "MESSAGE",
            Role.CONVERSATION,
            call,
            lambda row: row.get("state")
            in {"SHADOW_REPLY_CANDIDATE", "ALREADY_REVIEWED_NO_REPLAY", "ALREADY_REVIEWED_SOURCE_RETIRED"},
            before,
        )

    def command(self, principal, body):
        principal.require(Role.MANAGER)
        op = body.operation
        if op in {"PAUSE", "RESUME", "BUSY", "AVAILABLE", "REVOKE"}:
            command = {"operation": "control", "command": op.lower()}
        elif op == "WITHDRAW" and body.target_id:
            self._assert_memory_scope(body.target_id, principal)
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

        return self._call(principal, body, op, Role.MANAGER, call, lambda row: isinstance(row, dict), priority=op in {"PAUSE", "BUSY", "AVAILABLE", "REVOKE"})

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
            principal, body, body.operation, Role.HOST_ADMIN, call, lambda row: isinstance(row, dict), before, priority=body.operation == "STOP"
        )

    def receipt(self, principal, key):
        return self.envelope(self._receipt(key, principal).model_dump(mode="json"), principal=principal)

    def _assert_memory_scope(self, memory_id, principal=None):
        import sqlite3
        from ..inspector import _ReadView

        path = self.supervisor.home / "subject/self.db"
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            view = _ReadView(db, path, self.binding.scope, self.privacy_for(principal))
            row = view.one("memories", memory_id)
            if not row or row["entity_id"] != self.binding.entity_id:
                raise ApiError("SCOPE_DENIED", 403)

    def search_memories(self, principal, query):
        principal.require(Role.READER)
        with self.read_lock:
            self.supervisor.verify_binding()
            before = self._privacy_watermark()
            rows = self._memories(principal, query=query)
            if before!=self._privacy_watermark():
                raise ApiError('SOURCE_CHANGED_REFRESH_REQUIRED', 409)
            return self.envelope({'memories':rows, 'limit':64,
                'coverage':'LITERAL_TEXT_MATCH_NOT_SEMANTIC', 'privacy_watermark':before}, principal=principal)

    def _memories(self, principal=None, *, query=None):
        import sqlite3
        from ..inspector import _ReadView
        from ...continuity.memory import MemoryService

        path = self.supervisor.home / "subject/self.db"
        result = []
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            view = _ReadView(db, path, self.binding.scope, self.privacy_for(principal))
            memory = MemoryService(view)
            marks = ",".join("?" for _ in self.privacy_for(principal))
            args = (self.binding.entity_id, self.binding.scope, *self.privacy_for(principal))
            extra = ''
            if query is not None:
                # Explicit manager browse/search only, not a new ContextAssembler
                # retrieval policy. Literal matching works with CJK and does not
                # send the query to a model or create a plaintext cache.
                deadline = time.monotonic()+1
                db.set_progress_handler(lambda: int(time.monotonic()>deadline), 5000)
                extra = " AND assessment IN ('CURRENT','UNASSESSED') AND EXISTS (SELECT 1 FROM artifacts a WHERE a.artifact_id=memories.payload_artifact_id AND instr(lower(CAST(a.payload AS TEXT)),lower(?))>0)"
                args = (*args, query)
            try:
                rows = db.execute(
                    "SELECT memory_id FROM memories WHERE entity_id=? AND scope=? AND privacy_class IN ("
                    + marks + ") AND lifecycle='ACTIVE'" + extra
                    + " ORDER BY created_at_us DESC,rowid DESC LIMIT ?", (*args, 64 if query is not None else 32),
                ).fetchall()
            except sqlite3.OperationalError as exc:
                if query is not None and 'interrupt' in str(exc).lower():
                    raise ApiError('MEMORY_SEARCH_NARROW_QUERY', 422) from None
                raise
            finally:
                db.set_progress_handler(None, 0)
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
                from ..memory_notes import is_user_note
                result[-1]['user_provided_note']=is_user_note(current)
            view.ensure_privacy_current()
        return result
