"""Long-lived infrastructure metadata, no private bodies or Subject storage."""

import json
import pytest

from nana_core.life.live_api.contracts import ApiError, Completion
from nana_core.life.live_api.ledger import OperationLedger, HOT_LIMIT


def populate(ledger, count, *, state=Completion.VERIFIED, start=0):
    for i in range(start, start + count):
        key = "message." + str(i)
        ledger.reserve(key, "owner", {"synthetic": i}, "MESSAGE", ledger.revision, key)
        ledger.transition(key, Completion.RUNNING, dispatched=True)
        ledger.transition(key, state, result={"text": "UNRETAINED_RESPONSE_CANARY"})


def test_thousand_calls_remain_available_and_all_old_keys_stay_fenced_after_restart(tmp_path):
    ledger = OperationLedger(tmp_path / "private" / "operations.json")
    populate(ledger, 1000)
    assert len(ledger.document.read()["receipts"]) <= HOT_LIMIT
    assert len(ledger.volatile) <= HOT_LIMIT
    archived = ledger._archive_path("message.0")
    assert archived.exists()
    assert "UNRETAINED_RESPONSE_CANARY" not in archived.read_text()
    assert archived.stat().st_mode & 0o077 == 0
    assert set(ledger.document.read()) == {"schema_version", "revision", "receipts", "archive_format"}
    ledger = OperationLedger(ledger.document.path)
    for i in (0, 1, 128, 256, 500, 999):
        old = ledger.prior("message." + str(i), "owner", {"synthetic": i})
        assert old.state == Completion.VERIFIED and old.result == {} and old.dispatch_happened
    with pytest.raises(ApiError, match="IDEMPOTENCY_COLLISION"):
        ledger.reserve("message.0", "owner", {"synthetic": 0}, "MESSAGE", ledger.revision, "message.0")
    with pytest.raises(ApiError, match="IDEMPOTENCY_COLLISION"):
        ledger.prior("message.0", "owner", {"synthetic": "different"})
    with pytest.raises(ApiError, match="RECEIPT_NOT_FOUND"):
        ledger.read("message.0", "other")
    populate(ledger, 1, start=1000)


def test_unknown_can_archive_without_unlocking_retry_and_verified_reconciliation_promotes_atomically(tmp_path):
    ledger = OperationLedger(tmp_path / "p" / "operations.json")
    populate(ledger, 300, state=Completion.UNKNOWN)
    assert ledger.entry("message.0")["receipt"]["state"] == "UNKNOWN"
    assert "message.0" not in ledger.document.read()["receipts"]
    ledger = OperationLedger(ledger.document.path)
    assert ledger.prior("message.0", "owner", {"synthetic": 0}).state == Completion.UNKNOWN
    ledger.transition("message.0", Completion.VERIFIED, result={"proof": "SYNTHETIC independently checked"})
    assert ledger.read("message.0", "owner").state == Completion.VERIFIED
    populate(ledger, 160, start=300)
    assert "message.0" not in ledger.document.read()["receipts"]
    assert OperationLedger(ledger.document.path).read("message.0", "owner").state == Completion.VERIFIED


def test_crash_after_cold_copy_before_hot_replace_preserves_both_and_never_replays(tmp_path, monkeypatch):
    ledger = OperationLedger(tmp_path / "p" / "operations.json")
    populate(ledger, HOT_LIMIT)
    original = ledger.document._write

    def crash(_):
        raise OSError("SYNTHETIC root replace interrupted")

    monkeypatch.setattr(ledger.document, "_write", crash)
    with pytest.raises(OSError):
        ledger.reserve("next", "owner", {}, "MESSAGE", ledger.revision, "next")
    assert ledger._archive_path("message.0").exists()
    assert ledger.entry("message.0")["receipt"]["state"] == "VERIFIED"
    monkeypatch.setattr(ledger.document, "_write", original)
    ledger = OperationLedger(ledger.document.path)
    assert ledger.prior("message.0", "owner", {"synthetic": 0}).dispatch_happened
    ledger.reserve("next", "owner", {}, "MESSAGE", ledger.revision, "next")
    assert ledger.read("next", "owner").state == Completion.REQUESTED


def test_corrupted_or_redirected_archive_fails_closed(tmp_path):
    ledger = OperationLedger(tmp_path / "p" / "operations.json")
    populate(ledger, HOT_LIMIT + 32)
    path = ledger._archive_path("message.0")
    value = json.loads(path.read_text())
    value["receipt_key"] = "other"
    path.write_text(json.dumps(value))
    with pytest.raises(ApiError, match="RECEIPT_ARCHIVE_INVALID"):
        ledger.read("message.0", "owner")
    path.unlink()
    path.symlink_to(tmp_path / "outside.json")
    with pytest.raises(ApiError):
        ledger.read("message.0", "owner")


def test_legacy_root_is_read_without_rewriting_and_live_work_cannot_be_archived(tmp_path):
    ledger = OperationLedger(tmp_path / "p" / "operations.json")
    before = ledger.document.path.read_bytes()
    OperationLedger(ledger.document.path)
    assert ledger.document.path.read_bytes() == before
    for i in range(HOT_LIMIT):
        ledger.reserve("live." + str(i), "owner", {}, "MESSAGE", ledger.revision, "live." + str(i))
    with pytest.raises(ApiError, match="RECEIPT_ACTIVE_CAPACITY"):
        ledger.reserve("too-many", "owner", {}, "MESSAGE", ledger.revision, "too-many")
    assert not ledger.archive_root.exists()


def test_archive_copy_failure_does_not_remove_hot_keys_or_dispatched_state(tmp_path, monkeypatch):
    ledger = OperationLedger(tmp_path / "p" / "operations.json")
    populate(ledger, HOT_LIMIT)
    original = ledger._archive

    def interrupted(key, row):
        original(key, row)
        raise OSError("SYNTHETIC readback boundary")

    monkeypatch.setattr(ledger, "_archive", interrupted)
    with pytest.raises(OSError):
        ledger.reserve("next", "owner", {}, "MESSAGE", ledger.revision, "next")
    assert len(ledger.document.read()["receipts"]) == HOT_LIMIT
    assert ledger.prior("message.0", "owner", {"synthetic": 0}).dispatch_happened
    assert ledger.entry("next") is None
