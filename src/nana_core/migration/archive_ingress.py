"""Approved frozen legacy claims enter the original MemoryService, never identity.

The controller runs on the existing Runtime owner. A private, expiring host
approval pins the entire reviewed plan, original files, Subject and lineage.
It grants this finite retention operation only, not actions, beliefs, spending,
relationship adoption or the generic (still disabled) RealMemoryIngress API.
Source rows remain unassessed semantic claims, not Core-lived experiences.
"""

import json
import os
from pathlib import Path
import stat
from typing import Literal

from pydantic import Field

from ..contracts import CoreError, DTO
from ..continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from ..continuity.memory import MemoryService
from ..continuity.privacy import _json_object
from ..life.live_api.contracts import Binding
from ..storage import canonical, digest
from .archive import _checked_archive, source_rows, validate_batch_plan

SUPPORTED_ARCHIVE_INGRESS_CONTRACT_VERSION = 1


class ArchiveImportApproval(DTO):
    contract: Literal["nana-legacy-import-approval/v1"] = "nana-legacy-import-approval/v1"
    subject_id: str = Field(min_length=1, max_length=96)
    lineage_binding: str = Field(pattern=r"^[a-f0-9]{64}$")
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    plan_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    entity_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    scope: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    privacy_class: Literal["PUBLIC", "PROJECT", "PERSONAL"]
    issued_at_us: int = Field(ge=0)
    expires_at_us: int = Field(ge=0)
    max_records: int = Field(ge=1, le=500000)
    import_unassessed_claims: Literal[True]
    synthetic_only: bool


def private_document(path, *, limit=2 * 1024 * 1024):
    """Read an explicit operator document; never discover files or credentials."""
    path = Path(path).absolute()
    if path.resolve() != path:
        raise CoreError("LEGACY_APPROVAL_PATH_UNSAFE")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_mode & 0o077
                or info.st_nlink != 1
                or info.st_size > limit
            ):
                raise ValueError()
            raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise ValueError()
            return json.loads(raw, object_pairs_hook=_json_object)
    except (OSError, ValueError, UnicodeError):
        raise CoreError("LEGACY_APPROVAL_DOCUMENT_INVALID") from None


class ArchiveIngressAuthority:
    """Ephemeral capability for exactly the validated per-batch evidence DTOs."""

    def __init__(self, runtime, approval, candidates, approval_path, archive_root):
        self.runtime, self.approval = runtime, approval
        self.approval_path = approval_path
        self.archive_root = archive_root
        self.candidates = {c.provenance.source_reference: c.model_dump(mode="json") for c in candidates}

    def permits(self, store, candidate):
        self.runtime.lease.assert_current()
        return (
            store is self.runtime.store
            and store.schema_target == 13
            and store.clock.utc_now_us() < self.approval.expires_at_us
            and private_document(self.approval_path) == self.approval.model_dump(mode="json")
            and not (self.archive_root / "withdrawn" / json.loads(candidate.text)["source_id"]).exists()
            and self.candidates.get(candidate.provenance.source_reference) == candidate.model_dump(mode="json")
        )


class ArchiveImportService:
    def __init__(self, app):
        self.app, self.runtime, self.store = app, app.runtime, app.runtime.store

    def _register(self, root, approval):
        from ..life.live_api.state import AtomicDocument

        document = AtomicDocument(
            self.app.home / "legacy-source-bindings.json", {"schema_version": 1, "revision": 0, "archives": {}}
        )
        name = approval.manifest_sha256
        existing = document.read()["archives"].get(name)
        entry = {"root": str(root), "subject_id": approval.subject_id, "lineage_binding": approval.lineage_binding}
        if existing is not None:
            if existing != entry:
                raise CoreError("LEGACY_HOST_SOURCE_BINDING_CONFLICT")
            return

        def register(value):
            if len(value["archives"]) >= 16:
                raise CoreError("LEGACY_HOST_SOURCE_BINDING_CAPACITY")
            value["archives"][name] = entry

        document.update(register)

    def reconcile(self):
        """Honor a retired archive after a crash or archive-only withdrawal.

        The registry contains explicit host paths and opaque bindings only;
        it is outside the portable Subject package and contains no history.
        """
        registry = self.app.home / "legacy-source-bindings.json"
        if not registry.exists():
            return {"retired": 0}
        value = private_document(registry)
        if (
            set(value) != {"schema_version", "revision", "archives"}
            or type(value["archives"]) is not dict
            or len(value["archives"]) > 16
        ):
            raise CoreError("LEGACY_HOST_SOURCE_BINDINGS_INVALID")
        from ..life.live_api.supervisor import existing_identity

        identity, lineage, _ = existing_identity(self.app.home)
        count = 0
        for manifest_hash, entry in value["archives"].items():
            if (entry["subject_id"], entry["lineage_binding"]) != (identity, lineage):
                raise CoreError("LEGACY_HOST_SOURCE_BINDING_CONFLICT")
            root = Path(entry["root"])
            if not root.is_dir() or not any((root / "withdrawn").iterdir()):
                continue
            _, _, _, retired = _checked_archive(root, private_authorized=True, expected_manifest_sha256=manifest_hash)
            count += self._erase_sources(manifest_hash, retired)
        return {"retired": count}

    def _approved(self, archive, plan, approval_path):
        runtime = self.runtime
        runtime.lease.assert_current()
        try:
            approval = ArchiveImportApproval.model_validate(private_document(approval_path))
        except ValueError:
            raise CoreError("LEGACY_IMPORT_APPROVAL_INVALID") from None
        binding = Binding(subject_id=runtime.identity_id, lineage_binding=approval.lineage_binding)
        from ..life.live_api.supervisor import existing_identity

        if (
            approval.subject_id != runtime.identity_id
            or approval.lineage_binding != existing_identity(self.app.home)[1]
            or approval.scope not in runtime.config.scopes
            or approval.entity_id != runtime.config.entity_id
            or approval.privacy_class not in runtime.config.privacy_classes
            or approval.privacy_class not in self.app.policy.readable_privacy
        ):
            raise CoreError("LEGACY_IMPORT_APPROVAL_BINDING_MISMATCH")
        now = self.store.clock.utc_now_us()
        if (
            not approval.issued_at_us <= now < approval.expires_at_us
            or approval.expires_at_us - approval.issued_at_us > 86400_000000
        ):
            raise CoreError("LEGACY_IMPORT_APPROVAL_EXPIRED_OR_INVALID")
        root, manifest, manifest_hash, retired = _checked_archive(
            archive, private_authorized=True, expected_manifest_sha256=approval.manifest_sha256
        )
        current = validate_batch_plan(
            archive, plan, binding, private_authorized=True, expected_manifest_sha256=manifest_hash
        )
        if (
            approval.plan_digest != digest(current)
            or approval.synthetic_only != manifest["synthetic"]
            or current["records_planned"] > approval.max_records
        ):
            raise CoreError("LEGACY_IMPORT_PLAN_NOT_APPROVED")
        return root, manifest, approval, retired

    def import_batch(self, archive, plan, approval_path, batch_id, *, fault=None):
        """Resume atomically per claim by immutable source position; never replay effects."""
        root, manifest, approval, _ = self._approved(archive, plan, approval_path)
        self._register(root, approval)
        batch = next((b for b in plan["batches"] if b["batch_id"] == batch_id), None)
        if batch is None:
            raise CoreError("LEGACY_IMPORT_BATCH_NOT_APPROVED")
        from contextlib import closing
        import sqlite3

        evidence = []
        with closing(sqlite3.connect((root / "source-index.sqlite").as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
            for segment in batch["segments"]:
                from itertools import islice

                snapshot = root / manifest["files"][segment["source_id"]]["snapshot_path"]
                originals = list(
                    islice(
                        source_rows(snapshot),
                        segment["first_record"],
                        segment["first_record"] + segment["record_count"],
                    )
                )
                rows = db.execute(
                    "SELECT legacy_kind,legacy_key,content FROM source_text WHERE source_id=? "
                    "ORDER BY rowid LIMIT ? OFFSET ?",
                    (segment["source_id"], segment["record_count"], segment["first_record"]),
                ).fetchall()
                if len(rows) != segment["record_count"] or len(originals) != len(rows):
                    raise CoreError("LEGACY_IMPORT_INDEX_RANGE_CHANGED")
                for offset, (kind, key, text) in enumerate(rows, segment["first_record"]):
                    original_kind, original_key, original = originals[offset - segment["first_record"]]
                    if (original_kind, original_key) != (kind, key):
                        raise CoreError("LEGACY_IMPORT_INDEX_RANGE_CHANGED")
                    raw_time = next(
                        (
                            original[k]
                            for k in ("timestamp", "created_time", "ts", "t_utc")
                            if k in original and type(original[k]) in (str, int, float)
                        ),
                        None,
                    )
                    from ..clock import parse_utc

                    event_time = parse_utc(raw_time) if type(raw_time) is str else None
                    reference = digest([approval.manifest_sha256, segment["source_id"], offset])
                    body = canonical(
                        {
                            "origin": "LEGACY_SOURCE_CLAIM_NOT_CORE_EXPERIENCE",
                            "assessment": "UNASSESSED",
                            "synthetic": manifest["synthetic"],
                            "manifest_sha256": approval.manifest_sha256,
                            "source_id": segment["source_id"],
                            "source_sha256": segment["source_sha256"],
                            "legacy_kind": kind,
                            "legacy_key": key,
                            "source_position": offset,
                            "content": text[:12000],
                            "coverage": "INDEXED_EXCERPT_FULL_BYTES_IN_FROZEN_ARCHIVE",
                            "legacy_time_raw": str(raw_time)[:128] if raw_time is not None else None,
                            "legacy_record_time_us": event_time,
                            "legacy_role": str(original.get("role", "UNKNOWN"))[:32],
                            "time_quality": "EXPLICIT_TIMEZONE"
                            if event_time is not None
                            else "UNKNOWN_NO_UNIT_OR_TIMEZONE_GUESS",
                            "legacy_record_time_is_not_proof_of_underlying_event": True,
                            "execution_authority": False,
                        }
                    )
                    prior = self.store.db.execute(
                        "SELECT observed_time_us FROM continuity_evidence WHERE "
                        "source_namespace=? AND source_reference=?",
                        ("recorded.legacy.archive", reference),
                    ).fetchone()
                    evidence.append(
                        EvidenceInput(
                            provenance=Provenance(
                                domain="LEGACY_ARCHIVE",
                                source_namespace="recorded.legacy.archive",
                                source_reference=reference,
                                source_revision=approval.manifest_sha256[:32],
                                source_kind="DIRECT_OBSERVATION",
                                coverage="EXCERPT",
                            ),
                            text=body,
                            privacy_class=approval.privacy_class,
                            observed_time_us=prior[0] if prior else approval.issued_at_us,
                        )
                    )
        authority = ArchiveIngressAuthority(self.runtime, approval, evidence, approval_path, root)
        memory = MemoryService(self.store, authority)
        results = []
        for item in evidence:
            eid = memory.capture(item)
            mid = memory.add(
                MemoryCandidate(
                    entity_id=approval.entity_id,
                    scope=approval.scope,
                    memory_type=MemoryType.SEMANTIC,
                    epistemic_kind="BELIEF",
                    source_evidence_id=eid,
                    text=item.text,
                    predicate_key="legacy:" + item.provenance.source_reference,
                    confidence=0,
                )
            )
            results.append({"source_reference": item.provenance.source_reference, "memory_id": mid})
            if fault:
                fault("after_claim", mid)
        return {
            "state": "UNASSESSED_CLAIMS_IMPORTED",
            "batch_id": batch_id,
            "items": results,
            "subject_id": self.runtime.identity_id,
            "core_lived_experiences_created": 0,
            "execution_authority": False,
            "source_files_modified": False,
        }

    def withdraw(self, archive, approval_path, source_id):
        """Retire archive search first, then original privacy erasure. Safe to resume."""
        approval = ArchiveImportApproval.model_validate(private_document(approval_path))
        if approval.subject_id != self.runtime.identity_id:
            raise CoreError("LEGACY_IMPORT_APPROVAL_BINDING_MISMATCH")
        self.runtime.lease.assert_current()
        from ..life.live_api.supervisor import existing_identity

        if approval.lineage_binding != existing_identity(self.app.home)[1]:
            raise CoreError("LEGACY_IMPORT_APPROVAL_BINDING_MISMATCH")
        from .archive import withdraw_source

        withdraw_source(
            archive,
            source_id,
            Binding(subject_id=approval.subject_id, lineage_binding=approval.lineage_binding),
            private_authorized=True,
            expected_manifest_sha256=approval.manifest_sha256,
        )
        count = self._erase_sources(approval.manifest_sha256, (source_id,))
        return {
            "state": "WITHDRAWN",
            "evidence_retired": count,
            "frozen_source_bytes_retained": True,
            "execution_authority": False,
        }

    def _erase_sources(self, manifest_hash, source_ids):
        memory = MemoryService(self.store, self.runtime.authority)
        count = 0
        for raw in self.store.db.execute(
            "SELECT evidence_id,payload_artifact_id FROM continuity_evidence "
            "WHERE source_namespace='recorded.legacy.archive' AND state='AVAILABLE'"
        ).fetchall():
            item = json.loads(self.store.artifact(raw["payload_artifact_id"]))
            body = json.loads(item["text"])
            if body["manifest_sha256"] == manifest_hash and body["source_id"] in source_ids:
                for row in self.store.db.execute(
                    "SELECT memory_id FROM memories WHERE source_evidence_id=? AND lifecycle!='DELETED'",
                    (raw["evidence_id"],),
                ).fetchall():
                    memory.forget(row[0], self.runtime.authority)
                    count += 1
        return count
