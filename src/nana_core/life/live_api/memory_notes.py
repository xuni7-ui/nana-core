"""Authenticated explicit note retention through the existing single Core IPC."""

from typing import Literal
from pydantic import Field, model_validator
from .contracts import WriteRequest, Role, ApiError
from ..control import request as core_request


class MemoryNoteRequest(WriteRequest):
    text: str = Field(min_length=1, max_length=2048, repr=False)
    privacy_class: Literal["PUBLIC", "PROJECT", "PERSONAL"]
    consent: Literal[True]
    target_id: str | None = Field(default=None, min_length=1, max_length=96)

    @model_validator(mode="before")
    @classmethod
    def explicit_consent(cls, value):
        if not isinstance(value, dict) or value.get("consent") is not True:
            raise ValueError("explicit retention consent required")
        text = value.get("text")
        if type(text) is str:
            from ..memory_notes import screen
            from ...contracts import CoreError

            try:
                screen(text)
            except CoreError:
                raise ValueError("credential content is not a memory note") from None
        return value


def save(service, principal, body):
    principal.require(Role.MANAGER)
    if body.privacy_class not in service.privacy_for(principal):
        raise ApiError("SCOPE_DENIED", 403)
    from ...storage import digest
    from .ledger import fingerprint

    request_id = "v2-note." + digest([principal.principal_id, body.idempotency_key])
    command = {
        "operation": "memory-note",
        "text": body.text,
        "privacy": body.privacy_class,
        "request_id": request_id,
        "target_id": body.target_id,
        "surface_binding_id": service.binding.surface_binding_id,
        "request_digest": fingerprint(body.model_dump(mode="json")),
    }

    def before():
        if body.target_id:
            try:
                target = _read(service, principal, body.target_id)
            except Exception:
                raise ApiError("MEMORY_NOTE_TARGET_STALE", 409) from None
            from ..memory_notes import is_user_note
            from ...continuity.memory import PRIVACY_RANK

            if not is_user_note(target):
                raise ApiError("MEMORY_NOTE_TARGET_DENIED", 409)
            if PRIVACY_RANK[body.privacy_class] < PRIVACY_RANK[target["privacy_class"]]:
                raise ApiError("MEMORY_NOTE_PRIVACY_DOWNGRADE_DENIED", 403)
        if body.privacy_class == "PERSONAL":
            from ..config import load_config

            config = load_config(service.supervisor.home)
            surface = next(
                (s for s in config.surface_bindings if s.binding_id == service.binding.surface_binding_id), None
            )
            if (
                surface is None
                or not surface.allow_personal_retention
                or not surface.personal_retention_consent_ref
                or "PERSONAL" not in surface.permitted_privacy
            ):
                raise ApiError("SURFACE_PERSONAL_RETENTION_NOT_AUTHORIZED", 403)

    def call():
        result = core_request(service.supervisor.home, command, timeout=6)
        if result.get("ok") is not True:
            raise ApiError("MEMORY_NOTE_REJECTED", 409)
        saved = result["result"]
        mid = saved.get("memory_id")
        if type(mid) is not str:
            raise ApiError("MEMORY_NOTE_UNVERIFIED", 503)
        # Independently reopen the original Store's read-only scope projection;
        # a successful dispatch or a returned ID alone is not a saved note.
        _verify(service, principal, body, mid)
        return saved

    return service._call(
        principal,
        body,
        "MEMORY_NOTE",
        Role.MANAGER,
        call,
        lambda row: row.get("state") == "USER_NOTE_SAVED" and row.get("nana_lived_experience") is False,
        before,
    )


def _verify(service, principal, body, mid):
    from ..memory_notes import is_user_note

    note = _read(service, principal, mid)
    if not is_user_note(note) or (note["text"], note["privacy_class"], note["correction_of"]) != (
        body.text,
        body.privacy_class,
        body.target_id,
    ):
        raise ApiError("MEMORY_NOTE_UNVERIFIED", 503)


def _read(service, principal, mid):
    import sqlite3
    from ..inspector import _ReadView
    from ...continuity.memory import MemoryService

    path = service.supervisor.home / "subject/self.db"
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        view = _ReadView(db, path, service.binding.scope, service.privacy_for(principal))
        header = view.one("memories", mid)
        if not header or header["entity_id"] != service.binding.entity_id:
            raise ApiError("SCOPE_DENIED", 403)
        note = MemoryService(view).read(mid)
        if (note["entity_id"], note["scope"]) != (service.binding.entity_id, service.binding.scope):
            raise ApiError("SCOPE_DENIED", 403)
        view.ensure_privacy_current()
        return note


def reconcile(service, key, principal, receipt):
    """Read a bound original-Core commit proof; never dispatch the note again."""
    import sqlite3
    from ...storage import digest
    from ...continuity.records import RecordService
    from ..inspector import _ReadView
    from ..memory_notes import _receipt, is_user_note
    from .contracts import Completion

    if Role.MANAGER not in principal.roles:
        return receipt
    with service.write_lock:
        saved = service.ledger.entry(key)
        if not saved or saved["principal"] != principal.principal_id:
            return receipt
        request_id = "v2-note." + digest([principal.principal_id, key])
        target = "user-note-request:" + digest(request_id)
        path = service.supervisor.home / "subject/self.db"
        try:
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA query_only=ON")
                db.execute("BEGIN")
                view = _ReadView(db, path, service.binding.scope, service.privacy_for(principal))
                records = RecordService(view)
                row = db.execute(
                    "SELECT record_id FROM continuity_records WHERE record_kind='RUNTIME_WORK' AND target_id=? ORDER BY rowid DESC LIMIT 1",
                    (target,),
                ).fetchone()
                if not row or not records.current_support(row[0]):
                    return receipt
                body = records.read(row[0])["payload"]
                if (
                    body.get("kind") != "USER_MEMORY_NOTE_RECEIPT"
                    or body.get("request_id") != request_id
                    or body.get("request_digest") != saved["digest"]
                ):
                    return receipt
                header = view.one("memories", body["memory_id"])
                if not header or header["entity_id"] != service.binding.entity_id:
                    return receipt
                note = records.memory.read(body["memory_id"])
                if not is_user_note(note) or (note["entity_id"], note["scope"]) != (
                    service.binding.entity_id,
                    service.binding.scope,
                ):
                    return receipt
                view.ensure_privacy_current()
        except Exception:
            return receipt  # Absent/withdrawn/unavailable never means failure or retry.
        current = service.ledger.read(key, principal.principal_id)
        if current.state != Completion.UNKNOWN:
            return current
        service.ledger.transition(
            key, Completion.VERIFIED, result=_receipt(body["memory_id"], body.get("correction_of"))
        )
        service.receipt_privacy[key] = service._privacy_watermark()
        service.receipt_scopes[key] = service.privacy_for(principal)
        service._prune_receipt_cache()
        return service.ledger.read(key, principal.principal_id)
