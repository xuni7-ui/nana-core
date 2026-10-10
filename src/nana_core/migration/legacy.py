"""Preserve supplied legacy evidence without promoting it to trusted Core facts."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from typing import Annotated, Literal
from pydantic import Field, model_validator
from ..clock import parse_utc
from ..contracts import CoreError, DTO
from ..storage import canonical, digest


class LegacyRecord(DTO):
    schema_version: Literal[1] = 1
    synthetic_only: Literal[True] = True
    source_system: Literal["iris", "astrbot", "bili_agent"]
    dataset_id: str = Field(pattern=r"^synthetic:[a-zA-Z0-9_-]{1,64}$")
    record_id: str = Field(min_length=1, max_length=128)
    revision: str = Field(default="1", min_length=1, max_length=32)
    epistemic_kind: Literal["USER_STATEMENT", "MODEL_INFERENCE", "OBSERVATION", "SUMMARY", "ACTION_CLAIM"]
    content: str = Field(min_length=1, max_length=50_000)
    content_coverage: Literal["FULL", "EXCERPT", "SUMMARY"]
    # Exact supplied payload, including whitespace. None means not available;
    # completeness labels describe supplied material, not all historical truth.
    source_payload: str | None = Field(default=None, max_length=200_000)
    source_coverage: Literal["FULL", "EXCERPT", "SUMMARY", "UNAVAILABLE"]
    original_time: str | int | Annotated[float, Field(allow_inf_nan=False)] | None = None
    time_format: Literal["iso8601", "unix_seconds", "unix_millis", "unknown"] = "unknown"
    legacy_source_refs: tuple[str, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def evidence_labels(self):
        if (self.source_payload is None) != (self.source_coverage == "UNAVAILABLE"):
            raise ValueError("unavailable evidence must stay unavailable")
        if self.epistemic_kind == "SUMMARY" and self.content_coverage != "SUMMARY":
            raise ValueError("a legacy summary is not original full evidence")
        return self


def original_time_us(record):
    value = record.original_time
    if record.time_format == "iso8601":
        return parse_utc(value) if isinstance(value, str) else None
    if record.time_format in {"unix_seconds", "unix_millis"} and value is not None:
        try:
            number = Decimal(str(value))
            if not number.is_finite():
                return None
            seconds = number / 1000 if record.time_format == "unix_millis" else number
            # Explicit units only, never guess seconds vs milliseconds/local TZ.
            datetime.fromtimestamp(float(seconds), tz=timezone.utc)
            return int(seconds * 1_000_000)
        except (ValueError, OverflowError, InvalidOperation, OSError):
            return None
    return None


class LegacyImporter:
    """Local trusted operator import into existing events/artifacts/memory_items.

    No imports of host modules, action receipts/grants/strategies/identity writes.
    One record is atomic; a partial batch is safely resumable via source key.
    """
    def __init__(self, store):
        self.store = store

    def import_record(self, record: LegacyRecord):
        if not isinstance(record, LegacyRecord):
            raise CoreError("STRICT_LEGACY_RECORD_REQUIRED")
        record = LegacyRecord.model_validate(record.model_dump())
        namespace = "legacy.synthetic:" + record.source_system + ":" + record.dataset_id
        key = canonical([record.record_id, record.revision])
        payload = record.model_dump_json().encode()
        previous = self.store.db.execute("SELECT * FROM events WHERE source_namespace=? AND source_key=?",
            (namespace, key)).fetchone()
        if previous:
            if self.store.artifact(previous["artifact_id"]) != payload:
                raise CoreError("LEGACY_SOURCE_KEY_COLLISION")
            return {"event_id": previous["event_id"], "added": False}
        occurred = original_time_us(record)
        with self.store.transaction("migration.legacy_imported", {
            "source_system": record.source_system, "dataset_id": record.dataset_id,
            "record_id": record.record_id, "revision": record.revision,
            "time_quality": "SOURCE" if occurred is not None else "UNKNOWN",
            "source_payload_hash": digest(record.source_payload.encode()) if record.source_payload is not None else None,
        }, namespace, key, occurred) as tx:
            tx.payload_id = tx.artifact(payload)
            tx.put("memory_items", {"memory_id": tx.event_id, "kind": "CLAIM", "status": "ACTIVE",
                "created_event_id": tx.event_id, "body_json": canonical({
                    "epistemic_kind": record.epistemic_kind, "assessment": "UNASSESSED",
                    "origin": {"source_system": record.source_system, "dataset_id": record.dataset_id,
                        "record_id": record.record_id, "revision": record.revision},
                    "content": record.content, "content_coverage": record.content_coverage,
                    "original_time_raw": record.original_time, "time_format": record.time_format,
                    "source_payload_coverage": record.source_coverage,
                    "legacy_source_refs": [{"ref": r, "resolution": "UNRESOLVED_LEGACY_REF"} for r in record.legacy_source_refs],
                    "source_refs": [{"event_id": tx.event_id, "artifact_id": tx.payload_id,
                        "coverage": "FULL", "meaning": "complete supplied import envelope, not complete original history"}],
                    "execution_evidence": False})})
        return {"event_id": tx.event_id, "added": True}

    def import_batch(self, records, fault=None):
        if len(records) > 100 or not all(isinstance(r, LegacyRecord) for r in records):
            raise CoreError("INVALID_SYNTHETIC_IMPORT_BATCH")
        results = []
        for record in records:
            result = self.import_record(record)
            results.append(result)
            if fault:
                fault("after_record_commit", record.record_id)
        return results

    def supplied_source(self, event_id):
        event = self.store.event(event_id)
        if event["kind"] != "migration.legacy_imported":
            raise CoreError("NOT_A_LEGACY_IMPORT")
        record = LegacyRecord.model_validate_json(self.store.artifact(event["artifact_id"]))
        return {"payload": record.source_payload, "coverage": record.source_coverage,
            "sha256": digest(record.source_payload.encode()) if record.source_payload is not None else None}


def synthetic_records():
    """Generated compatibility envelopes, not exports of any real Iris database."""
    return (
        LegacyRecord(source_system="iris", dataset_id="synthetic:iris-l2", record_id="statement-1",
            epistemic_kind="USER_STATEMENT", content="A fictional reader prefers private reading cards.",
            content_coverage="FULL", source_payload=' { "speaker": "synthetic-reader", "text": "prefers private cards" }\n',
            source_coverage="FULL", original_time="2026-09-01T09:30:00+08:00", time_format="iso8601"),
        LegacyRecord(source_system="iris", dataset_id="synthetic:iris-l2", record_id="inference-1",
            epistemic_kind="MODEL_INFERENCE", content="An old model inferred that the fictional reader enjoys astronomy.",
            content_coverage="FULL", source_payload=None, source_coverage="UNAVAILABLE",
            original_time="unknown-local-time", time_format="iso8601", legacy_source_refs=("synthetic:message-7",)),
        LegacyRecord(source_system="astrbot", dataset_id="synthetic:conversation", record_id="summary-1",
            epistemic_kind="SUMMARY", content="A compressed fictional reading conversation.", content_coverage="SUMMARY",
            source_payload="Only a synthetic summary is available.", source_coverage="SUMMARY",
            original_time=1756688400000, time_format="unix_millis", legacy_source_refs=("synthetic:missing-original",)),
        LegacyRecord(source_system="bili_agent", dataset_id="synthetic:ledger", record_id="receipt-1",
            epistemic_kind="ACTION_CLAIM", content="Legacy synthetic ledger claimed VERIFIED; independent evidence absent.",
            content_coverage="FULL", source_payload='{"synthetic_status":"VERIFIED","synthetic_action":"old-1"}',
            source_coverage="FULL", original_time=1756688400, time_format="unix_seconds"),
    )
