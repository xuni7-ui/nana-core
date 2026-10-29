"""Owned generated sources only; no production/private history or credential reads."""
import json
import sqlite3

import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.contracts import IngressQualification, RealMemoryIngress
from nana_core.life.live_api.contracts import Binding
from nana_core.migration.archive import batch_plan, freeze, search, validate_batch_plan, verify, withdraw_source


BINDING = Binding(subject_id="owned-archive-subject", lineage_binding="a" * 64)


def generated(tmp_path, rows=None):
    source = tmp_path / "generated"
    source.mkdir()
    (source / ".nana-synthetic-legacy.json").write_text('{"synthetic_only":true}')
    raw = json.dumps(rows or [{"id": "one", "role": "assistant", "content": "Unassessed astronomy claim"}],
                     ensure_ascii=False, indent=2).encode() + b"\n"
    (source / "history.json").write_bytes(raw)
    return source, raw


def capture(source, target, **kwargs):
    return freeze(source, ["history.json"], target, BINDING, synthetic=True, **kwargs)


def test_full_bytes_and_independent_index_preserve_origin_without_memory_authority(tmp_path):
    source, raw = generated(tmp_path, [{"id": "claim", "role": "assistant", "content": "Astronomy model inference"},
                                      {"id": "ledger", "state": "VERIFIED", "text": "Astronomy action claim"}])
    database = source / "legacy.sqlite"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE memories(memory_id TEXT,content TEXT,embedding BLOB)")
        db.execute("INSERT INTO memories VALUES(?,?,?)", ("record-1", "Astronomy SQLite source", b"\x00\xff\x01"))
    original_sqlite = database.read_bytes()
    target = tmp_path / "archive"
    manifest = freeze(source, ["history.json", "legacy.sqlite"], target, BINDING, synthetic=True)
    assert manifest["records_indexed"] == 3
    assert (source / "history.json").read_bytes() == raw and database.read_bytes() == original_sqlite
    saved = {row["source_name"]: target / row["snapshot_path"] for row in manifest["files"].values()}
    assert saved["history.json"].read_bytes() == raw
    assert saved["legacy.sqlite"].read_bytes() == original_sqlite
    assert all(path.stat().st_mode & 0o777 == 0o400 for path in saved.values())
    verified = verify(target, expected_manifest_sha256=manifest["manifest_sha256"])
    assert verified["files_verified"] == 2 and verified["subject_id"] == BINDING.subject_id
    result = search(target, "Astronomy", expected_manifest_sha256=manifest["manifest_sha256"])
    assert len(result["items"]) == 3
    assert all(row["assessment"] == "UNASSESSED_LEGACY_SOURCE_CLAIM" and
               not row["core_experience"] and not row["execution_authority"] for row in result["items"])
    assert all(row["source_sha256"] == manifest["files"][row["source_id"]]["sha256"] for row in result["items"])
    assert not manifest["core_memory_imported"] and not manifest["grants_or_actions_imported"]


def test_verification_checks_binary_unsearchable_sources_and_manifest_pin(tmp_path):
    source, _ = generated(tmp_path)
    (source / "opaque.bin").write_bytes(b"\xff\x00\x81")
    target = tmp_path / "archive"
    manifest = freeze(source, ["history.json", "opaque.bin"], target, BINDING, synthetic=True)
    opaque = next(target / row["snapshot_path"] for row in manifest["files"].values() if row["source_name"] == "opaque.bin")
    opaque.chmod(0o600)
    opaque.write_bytes(b"\xff\x00\x82")
    with pytest.raises(CoreError, match="LEGACY_SOURCE_HASH_MISMATCH"):
        search(target, "Astronomy")
    opaque.write_bytes(b"\xff\x00\x81")
    path = target / "manifest.json"
    path.chmod(0o600)
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(CoreError, match="LEGACY_MANIFEST_HASH_MISMATCH"):
        verify(target, expected_manifest_sha256=manifest["manifest_sha256"])


def test_bounded_plan_is_deterministic_binding_scoped_and_invalidated_by_withdrawal(tmp_path):
    source, raw = generated(tmp_path, [{"id": str(i), "text": "Astronomy generated " + str(i)} for i in range(205)])
    target = tmp_path / "archive"
    manifest = capture(source, target)
    plan = batch_plan(target, BINDING)
    assert plan == batch_plan(target, BINDING)
    assert plan["state"] == "SYNTHETIC_REVIEW_PLAN" and plan["records_planned"] == 205
    assert [batch["record_count"] for batch in plan["batches"]] == [100, 100, 5]
    assert [batch["segments"][0]["first_record"] for batch in plan["batches"]] == [0, 100, 200]
    assert validate_batch_plan(target, plan, BINDING) == plan
    with pytest.raises(CoreError, match="LEGACY_SUBJECT_LINEAGE_MISMATCH"):
        batch_plan(target, BINDING.model_copy(update={"lineage_binding": "b" * 64}))
    source_id = next(iter(manifest["files"]))
    receipt = withdraw_source(target, source_id, BINDING)
    assert receipt["state"] == "WITHDRAWN" and receipt["frozen_source_bytes_retained"]
    assert (target / manifest["files"][source_id]["snapshot_path"]).read_bytes() == raw
    assert withdraw_source(target, source_id, BINDING) == receipt
    assert search(target, "Astronomy")["items"] == []
    assert batch_plan(target, BINDING)["batches"] == []
    assert verify(target)["withdrawn_source_ids"] == [source_id]
    with pytest.raises(CoreError, match="LEGACY_BATCH_PLAN_STALE_OR_CHANGED"):
        validate_batch_plan(target, plan, BINDING)


def test_real_archive_private_reads_need_explicit_authorization_and_import_stays_disabled(tmp_path):
    source, _ = generated(tmp_path)
    target = tmp_path / "archive"
    with pytest.raises(CoreError, match="LEGACY_PRIVATE_READ_NOT_AUTHORIZED"):
        freeze(source, ["history.json"], target, BINDING)
    assert not target.exists()
    manifest = freeze(source, ["history.json"], target, BINDING, private_authorized=True)
    for read in (lambda: verify(target), lambda: search(target, "Astronomy"), lambda: batch_plan(target, BINDING)):
        with pytest.raises(CoreError, match="LEGACY_PRIVATE_READ_NOT_AUTHORIZED"):
            read()
    plan = batch_plan(target, BINDING, private_authorized=True, expected_manifest_sha256=manifest["manifest_sha256"])
    assert plan["state"] == "BLOCKED_REAL_MEMORY_IMPORT_DISABLED" and not plan["synthetic_only"]
    assert not plan["real_memory_ingress_enabled"] and not plan["execution_authority"]
    with pytest.raises(CoreError, match="REAL_MEMORY_IMPORT_DISABLED"):
        RealMemoryIngress().import_real(IngressQualification(**{key: True for key in IngressQualification.model_fields}), payload=plan)


@pytest.mark.parametrize("kind", ["wal", "symlink", "secret-field"])
def test_unfrozen_linked_or_secret_sources_are_rejected_before_capture(tmp_path, kind):
    source, _ = generated(tmp_path)
    target = tmp_path / "archive"
    if kind == "wal":
        (source / "history.json-wal").write_bytes(b"unfrozen")
    elif kind == "symlink":
        (source / "history.json").unlink()
        (source / "history.json").symlink_to(source / ".nana-synthetic-legacy.json")
    else:
        (source / "history.json").write_text('{"token":"OWNED_TEST_MARKER_NOT_A_CREDENTIAL"}')
    with pytest.raises(CoreError):
        capture(source, target)
    assert not target.exists()


def archive_cli(command, *arguments, expected=0):
    """Launch the actual operator entry point in a fresh process for each step."""
    from pathlib import Path
    import subprocess
    import sys
    repository = Path(__file__).resolve().parents[2]
    process = subprocess.run([sys.executable, str(repository / "tools/nana_living_release_v4/legacy_archive.py"),
        command, "--subject-id", BINDING.subject_id, "--lineage-binding", BINDING.lineage_binding,
        *map(str, arguments)], cwd=repository, text=True, capture_output=True, timeout=15)
    assert process.returncode == expected, process.stderr + process.stdout
    assert not process.stderr
    return json.loads(process.stdout)


def test_actual_cli_capture_search_plan_withdraw_and_tamper_lifecycle(tmp_path):
    source, raw = generated(tmp_path, [{"id": str(i), "content": "Astronomy owned source " + str(i)} for i in range(3)])
    target, plan_path = tmp_path / "archive", tmp_path / "review-plan.json"
    manifest = archive_cli("freeze", "--source-root", source, "--file", "history.json",
                           "--destination", target, "--synthetic")
    pin = manifest["manifest_sha256"]
    common = ("--archive", target, "--manifest-sha256", pin)
    assert archive_cli("verify", *common)["files_verified"] == 1
    found = archive_cli("search", *common, "--query", "Astronomy")
    assert len(found["items"]) == 3 and not found["items"][0]["core_experience"]
    plan = archive_cli("import-preview", *common, "--batch-size", 2, "--output-plan", plan_path)
    assert [row["record_count"] for row in plan["batches"]] == [2, 1]
    assert json.loads(plan_path.read_text()) == plan and plan_path.stat().st_mode & 0o777 == 0o400
    assert archive_cli("validate-plan", *common, "--plan-file", plan_path) == plan
    plan_path.chmod(0o600)
    altered = {**plan, "records_planned": 4}
    plan_path.write_text(json.dumps(altered))
    invalid = archive_cli("validate-plan", *common, "--plan-file", plan_path, expected=2)
    assert invalid["code"] == "LEGACY_BATCH_PLAN_STALE_OR_CHANGED"
    plan_path.write_text(json.dumps(plan))
    source_id = next(iter(manifest["files"]))
    retired = archive_cli("withdraw", *common, "--source-id", source_id)
    assert retired["state"] == "WITHDRAWN" and retired["frozen_source_bytes_retained"]
    assert archive_cli("search", *common, "--query", "Astronomy")["items"] == []
    assert archive_cli("plan", *common)["records_planned"] == 0
    invalid = archive_cli("validate-plan", *common, "--plan-file", plan_path, expected=2)
    assert invalid["code"] == "LEGACY_BATCH_PLAN_STALE_OR_CHANGED"
    assert (source / "history.json").read_bytes() == raw
    frozen = target / manifest["files"][source_id]["snapshot_path"]
    assert frozen.read_bytes() == raw and frozen.stat().st_mode & 0o777 == 0o400
    frozen.chmod(0o600)
    frozen.write_bytes(raw + b"tampered")
    rejected = archive_cli("verify", *common, expected=2)
    assert rejected["code"] == "LEGACY_SOURCE_HASH_MISMATCH"


def test_cli_requires_explicit_private_read_or_owned_synthetic_marker_and_checks_lineage(tmp_path):
    source, _ = generated(tmp_path)
    target = tmp_path / "archive"
    denied = archive_cli("freeze", "--source-root", source, "--file", "history.json", "--destination", target,
                         expected=2)
    assert denied["code"] == "LEGACY_PRIVATE_READ_NOT_AUTHORIZED" and not target.exists()
    marker = source / ".nana-synthetic-legacy.json"
    marker.unlink()
    denied = archive_cli("freeze", "--source-root", source, "--file", "history.json", "--destination", target,
                         "--synthetic", expected=2)
    assert denied["code"] == "LEGACY_SYNTHETIC_MARKER_REQUIRED" and not target.exists()
    marker.write_text('{"synthetic_only":true}')
    archive_cli("freeze", "--source-root", source, "--file", "history.json", "--destination", target, "--synthetic")
    denied = archive_cli("search", "--archive", target, "--query", "Astronomy",
                         "--lineage-binding", "b" * 64, expected=2)
    assert denied["code"] == "LEGACY_SUBJECT_LINEAGE_MISMATCH"
