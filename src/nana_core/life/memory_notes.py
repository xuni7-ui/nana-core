"""Explicit user notes in the original MemoryService, never lived experience.

Called at the single Runtime owner's safe point. User corrections can replace
only this note family, not observations, identity, lessons or legacy archives.
No model call, Grant, execution permission or new memory authority is created.
"""

import re

from ..contracts import CoreError
from ..storage import digest
from ..continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from ..continuity.memory import MemoryService, is_user_note
from ..migration.archive import SECRET
from ..migration.source_safety import safe_payload


def screen(text):
    if SECRET.search(text.encode()):
        raise CoreError("MEMORY_NOTE_CREDENTIAL_DENIED")
    try:
        safe_payload(text)
    except CoreError:
        raise CoreError("MEMORY_NOTE_CREDENTIAL_DENIED") from None


def save(app, *, text, privacy, request_id, target_id=None, surface_binding_id=None, request_digest=None):
    r = app.runtime
    r.lease.assert_current()
    memory = MemoryService(r.store)
    if type(text) is not str or not 1 <= len(text.strip()) <= 2048 or len(text) > 2048:
        raise CoreError("MEMORY_NOTE_TEXT_BOUND")
    if privacy not in r.config.privacy_classes or privacy not in {"PUBLIC", "PROJECT", "PERSONAL"}:
        raise CoreError("MEMORY_NOTE_PRIVACY_DENIED")
    binding = app.surfaces._binding(surface_binding_id) if surface_binding_id is not None else None
    if binding and privacy not in binding.permitted_privacy:
        raise CoreError("MEMORY_NOTE_PRIVACY_DENIED")
    entity_id = r.config.entity_id
    scope = binding.scope if binding else r.config.scopes[0]
    if privacy == "PERSONAL":
        if (
            binding is None
            or "PERSONAL" not in binding.permitted_privacy
            or not binding.allow_personal_retention
            or not binding.personal_retention_consent_ref
        ):
            raise CoreError("SURFACE_PERSONAL_RETENTION_NOT_AUTHORIZED")
    if type(request_id) is not str or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", request_id):
        raise CoreError("MEMORY_NOTE_REQUEST_REQUIRED")
    if request_digest is not None and (
        type(request_digest) is not str or not re.fullmatch(r"[a-f0-9]{64}", request_digest)
    ):
        raise CoreError("MEMORY_NOTE_REQUEST_REQUIRED")
    if target_id is not None and (type(target_id) is not str or not 1 <= len(target_id) <= 96):
        raise CoreError("MEMORY_NOTE_CORRECTION_TARGET_DENIED")
    screen(text)
    reference = "note:" + digest(request_id)
    old = r.store.db.execute(
        "SELECT * FROM continuity_evidence WHERE source_namespace='recorded.conversation.input' AND source_reference=?",
        (reference,),
    ).fetchone()
    if old:
        if old["state"] == "DELETED":
            raise CoreError("SOURCE_DELETED")
        prior = r.store.db.execute(
            "SELECT memory_id FROM memories WHERE source_evidence_id=? ORDER BY rowid DESC LIMIT 1",
            (old["evidence_id"],),
        ).fetchone()
        if prior:
            header = r.store.one("memories", prior[0])
            if (header["entity_id"], header["scope"], header["privacy_class"]) != (entity_id, scope, privacy):
                raise CoreError("MEMORY_NOTE_REQUEST_CONFLICT")
            existing = memory.read(prior[0], include_inactive=True)
            if not is_user_note(existing) or (
                existing["entity_id"],
                existing["scope"],
                existing["text"],
                existing["privacy_class"],
                existing["correction_of"],
            ) != (entity_id, scope, text, privacy, target_id):
                raise CoreError("MEMORY_NOTE_REQUEST_CONFLICT")
            # Do not recreate a superseded/withdrawn result on a duplicate.
            if existing["lifecycle"] != "ACTIVE" or existing["assessment"] != "CURRENT":
                raise CoreError("MEMORY_NOTE_SOURCE_RETIRED")
            return _finish(r, existing["memory_id"], target_id, request_id, request_digest)
    predicate = "user-note." + digest(reference)
    if target_id is not None:
        header = r.store.one("memories", target_id)
        if not header or (header["entity_id"], header["scope"]) != (entity_id, scope):
            raise CoreError("MEMORY_NOTE_CORRECTION_TARGET_DENIED")
        from ..continuity.memory import PRIVACY_RANK

        if PRIVACY_RANK[privacy] < PRIVACY_RANK[header["privacy_class"]]:
            raise CoreError("MEMORY_NOTE_PRIVACY_DOWNGRADE_DENIED")
        previous = memory.read(target_id)
        if not is_user_note(previous):
            raise CoreError("MEMORY_NOTE_CORRECTION_TARGET_DENIED")
        predicate = previous["predicate_key"]
    now = r.clock.utc_now_us()
    eid = memory.capture(
        EvidenceInput(
            provenance=Provenance(
                domain="CONSENTED_INTERACTION",
                source_namespace="recorded.conversation.input",
                source_reference=reference,
                source_kind="USER_STATEMENT",
            ),
            text=text,
            privacy_class=privacy,
            retention_consent_ref=reference,
            observed_time_us=old["observed_time_us"] if old else now,
            event_time_us=old["event_time_us"] if old else now,
        )
    )
    mid = memory.add(
        MemoryCandidate(
            entity_id=entity_id,
            scope=scope,
            memory_type=MemoryType.SEMANTIC,
            epistemic_kind="STATEMENT",
            source_evidence_id=eid,
            text=text,
            predicate_key=predicate,
            correction_of=target_id,
        )
    )
    return _finish(r, mid, target_id, request_id, request_digest)


def _finish(runtime, mid, target, request_id, request_digest):
    """A sourced commit proof, not a second ledger or an invented experience.

    It can independently reconcile a lost transport reply. If a crash happens
    before this proof commits, the caller must keep UNKNOWN rather than resend.
    Privacy erases its support/payload, including the request digest, as usual.
    """
    if request_digest is not None:
        from ..continuity.records import RecordService

        records = RecordService(runtime.store)
        key = "user-note-request:" + digest(request_id)
        old = runtime.store.db.execute(
            "SELECT record_id FROM continuity_records WHERE record_kind='RUNTIME_WORK' AND target_id=?", (key,)
        ).fetchone()
        payload = {
            "kind": "USER_MEMORY_NOTE_RECEIPT",
            "request_id": request_id,
            "request_digest": request_digest,
            "memory_id": mid,
            "correction_of": target,
        }
        if old:
            if not records.current_support(old[0]) or records.read(old[0])["payload"] != payload:
                raise CoreError("MEMORY_NOTE_REQUEST_CONFLICT")
        else:
            note = records.memory.read(mid)
            with runtime.store.transaction("life.user_note_commit_proof", {"memory_id": mid}) as tx:
                records.create(
                    tx, kind="RUNTIME_WORK", scope=note["scope"], payload=payload, memories=(mid,), target_id=key
                )
    return _receipt(mid, target)


def _receipt(mid, target):
    return {
        "state": "USER_NOTE_SAVED",
        "memory_id": mid,
        "correction_of": target,
        "provenance": "USER_PROVIDED_NOT_VERIFIED_FACT",
        "nana_lived_experience": False,
        "model_calls": 0,
        "execution_authority": False,
    }
