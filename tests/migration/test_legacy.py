import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import pytest
from pydantic import ValidationError
from nana_core.clock import ManualClock, parse_utc
from nana_core.contracts import CoreError
from nana_core.migration.legacy import LegacyImporter, LegacyRecord, original_time_us, synthetic_records
from nana_core.storage import Store

pytestmark = pytest.mark.s6


def test_import_preserves_identity_origin_exact_payload_and_unknown_time(tmp_path):
    with Store(tmp_path / "core.db", ManualClock()) as store:
        identity = store.identity
        importer = LegacyImporter(store)
        results = importer.import_batch(synthetic_records())
        assert store.identity == identity
        event = store.event(results[0]["event_id"])
        assert event["occurred_at_us"] == parse_utc(synthetic_records()[0].original_time)
        assert importer.supplied_source(event["event_id"])["payload"] == synthetic_records()[0].source_payload
        unknown = store.event(results[1]["event_id"])
        assert unknown["occurred_at_us"] is None
        assert json.loads(unknown["data_json"])["data"]["time_quality"] == "UNKNOWN"
        summaries = [json.loads(m["body_json"]) for m in store.all("memory_items")]
        assert all(m["assessment"] == "UNASSESSED" for m in summaries)
        assert summaries[2]["content_coverage"] == "SUMMARY"
        assert summaries[1]["source_payload_coverage"] == "UNAVAILABLE"
        assert not summaries[3]["execution_evidence"]
        for table in ("actions", "grants", "budgets", "strategies", "goals"):
            assert store.all(table) == []


def test_duplicate_import_and_revision_conflict(tmp_path):
    with Store(tmp_path / "core.db") as store:
        importer = LegacyImporter(store)
        first = importer.import_batch(synthetic_records())
        second = importer.import_batch(synthetic_records())
        assert [r["event_id"] for r in first] == [r["event_id"] for r in second]
        assert not any(r["added"] for r in second)
        assert len(store.all("memory_items")) == 4
        changed = synthetic_records()[0].model_copy(update={"content": "Changed synthetic content."})
        with pytest.raises(CoreError, match="LEGACY_SOURCE_KEY_COLLISION"):
            importer.import_record(changed)
        assert importer.import_record(changed.model_copy(update={"revision": "2"}))["added"]


@pytest.mark.parametrize("value,fmt,expected", [
    ("2026-09-01T09:30:00+08:00", "iso8601", parse_utc("2026-09-01T01:30:00Z")),
    (1756688400, "unix_seconds", 1756688400000000),
    (1756688400000, "unix_millis", 1756688400000000),
    ("2026-09-01T09:30:00", "iso8601", None),
    (1756688400000, "unknown", None),
])
def test_explicit_legacy_time_units(value, fmt, expected):
    record = synthetic_records()[0].model_copy(update={"original_time": value, "time_format": fmt})
    assert original_time_us(record) == expected


@pytest.mark.parametrize("changes", [{"synthetic_only": False}, {"content_coverage": "FULL"},
    {"source_payload": None}, {"dataset_id": "production:iris"}, {"grant": "execute-all"}])
def test_strict_import_envelope_and_completeness(changes):
    data = synthetic_records()[2].model_dump()
    data.update(changes)
    with pytest.raises(ValidationError):
        LegacyRecord.model_validate(data)


def test_atomic_record_rollback_and_replay(tmp_path, monkeypatch):
    with Store(tmp_path / "core.db") as store:
        importer = LegacyImporter(store)
        original = store._put
        def fail(table, row):
            if table == "memory_items": raise RuntimeError("synthetic interrupted import")
            return original(table, row)
        monkeypatch.setattr(store, "_put", fail)
        with pytest.raises(RuntimeError): importer.import_record(synthetic_records()[0])
        assert store.all("memory_items") == [] and store.all("artifacts") == []
        monkeypatch.setattr(store, "_put", original)
        importer.import_batch(synthetic_records())
        snapshot, events = store.snapshot(), store.all("events")
        store.replay(tmp_path / "replayed.db")
    with Store(tmp_path / "replayed.db") as replay:
        expected = snapshot
        expected["core_meta"][0]["value_json"] = "true"
        assert replay.snapshot() == expected
        assert replay.all("events") == events
        assert LegacyImporter(replay).supplied_source(events[1]["event_id"])["payload"] == synthetic_records()[0].source_payload


def test_real_sigkill_partial_import_resumes_without_new_identity(tmp_path):
    path = tmp_path / "core.db"
    with Store(path) as store:
        identity = store.identity
    code = """
import os,signal,sys
from nana_core.storage import Store
from nana_core.migration.legacy import LegacyImporter,synthetic_records
with Store(sys.argv[1]) as store:
 def fault(point,record_id): os.kill(os.getpid(),signal.SIGKILL)
 LegacyImporter(store).import_batch(synthetic_records(),fault=fault)
"""
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    child = subprocess.run([sys.executable, "-c", code, str(path)], env=env, capture_output=True, timeout=10)
    assert child.returncode == -signal.SIGKILL
    with Store(path) as store:
        assert store.identity == identity and len(store.all("memory_items")) == 1
        result = LegacyImporter(store).import_batch(synthetic_records())
        assert sum(r["added"] for r in result) == 3
        assert len(store.all("memory_items")) == 4
