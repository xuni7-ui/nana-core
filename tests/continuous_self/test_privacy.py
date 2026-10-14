import json
import os
import signal
import subprocess
import sys

import pytest

from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from nana_core.continuity.memory import MemoryService
from .conftest import evidence
from .test_memory import add

CANARY = "SYNTHETIC_ERASURE_CONTENT_b9417f_never_real_private_data"


def derived(memory, parent, source, text=CANARY):
    return memory.add(MemoryCandidate(entity_id="synthetic-sister", scope="synthetic-home",
        memory_type=MemoryType.SEMANTIC, epistemic_kind="SUMMARY", source_evidence_id=source,
        text=text, derived_from=(parent,)))


def test_correction_invalidates_summaries_and_delete_erases_all_controlled_payloads(cognitive):
    store, memory, authority = cognitive
    source = evidence(memory, "erasable", CANARY)
    a = add(memory, source, CANARY, predicate_key="preference")
    summary = derived(memory, a, evidence(memory, "summary", CANARY, kind="MODEL_DERIVATION"))
    newer = add(memory, evidence(memory, "newer", "B", when=300), "B",
                predicate_key="preference", correction_of=a)
    assert memory.read(summary, include_inactive=True)["assessment"] == "WITHDRAWN"
    backup = store.path.with_name("managed-backup.db")
    store.backup(backup)
    with pytest.raises(CoreError, match="UNAUTHENTICATED_OPERATOR"):
        memory.forget(a, OperatorAuthority())
    report = memory.forget(a, authority)
    assert report["state"] == "COMPLETE"
    for key in (a, summary):
        with pytest.raises(CoreError, match="MEMORY_UNAVAILABLE"):
            memory.read(key, include_inactive=True)
    assert memory.read(newer)["text"] == "B"
    with pytest.raises(CoreError, match="SOURCE_DELETED"):
        evidence(memory, "erasable", CANARY)
    with pytest.raises(CoreError, match="SOURCE_DELETED"):
        memory.capture(EvidenceInput(provenance=Provenance(source_namespace="synthetic.continuity",
            source_reference="erasable", source_revision="2", source_kind="USER_STATEMENT"),
            text=CANARY, event_time_us=400, observed_time_us=401, privacy_class="PERSONAL"))
    with pytest.raises(CoreError, match="MEMORY_UNAVAILABLE"):
        derived(memory, a, evidence(memory, "new-summary", "unrelated", kind="MODEL_DERIVATION"))
    replay = store.path.with_name("replay.db")
    store.replay(replay)
    for path in (backup, replay):
        with ContinuityStore(path, store.clock) as restored:
            assert MemoryService(restored).query(scopes=("synthetic-home",), privacy_classes=("PERSONAL",)) == [memory.read(newer)]
            assert restored.one("core_meta", "recovery_quarantine")["value_json"] == "true"
    for path in (store.path, backup, replay):
        assert CANARY.encode() not in path.read_bytes()
        for suffix in ("-wal", "-shm"):
            extra = path.with_name(path.name + suffix)
            assert not extra.exists() or CANARY.encode() not in extra.read_bytes()
    assert CANARY not in store.privacy.path.read_text()
    assert not store.db.execute("SELECT 1 FROM memory_terms WHERE memory_id IN (?,?)", (a, summary)).fetchone()


def test_suppression_archive_confidence_and_no_resurrection(cognitive):
    store, memory, authority = cognitive
    a = add(memory, evidence(memory, "suppress", "synthetic preference"), "synthetic preference")
    memory.assess_confidence(a, 0.75, authority)
    assert memory.read(a)["confidence"] == 0.75
    memory.set_lifecycle(a, "ARCHIVED", authority)
    assert not memory.query(scopes=("synthetic-home",), privacy_classes=("PERSONAL",))
    assert memory.read(a, include_inactive=True)["text"]
    memory.set_lifecycle(a, "ACTIVE", authority)
    memory.set_lifecycle(a, "SUPPRESSED", authority)
    assert store.artifact(store.one("memories", a)["payload_artifact_id"])
    memory.forget(a, authority)
    with pytest.raises(CoreError, match="MEMORY_UNAVAILABLE"):
        memory.set_lifecycle(a, "ACTIVE", authority)


def test_real_sigkill_after_durable_delete_intent_recovers_before_reads(tmp_path):
    path = tmp_path / "crash.db"
    authority = OperatorAuthority()
    with ContinuityStore(path, ManualClock()) as store:
        identity = IdentityService(store, authority).current().identity_id
        memory = MemoryService(store, authority)
        memory.entity("synthetic-sister", "PERSON")
        a = add(memory, evidence(memory, "crash-source", CANARY), CANARY)
    # Real child process dies after journal fsync, before SQLite erasure begins.
    code = '''
import os,signal,sys
from nana_core.continuity import ContinuityStore
from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity.memory import MemoryService
with ContinuityStore(sys.argv[1], ManualClock()) as s:
 a=OperatorAuthority()
 def killed(): os.kill(os.getpid(),signal.SIGKILL)
 s.privacy.ensure_current=killed
 MemoryService(s,a).forget(sys.argv[2],a)
'''
    child = subprocess.run([sys.executable, "-c", code, str(path), a], capture_output=True, timeout=10)
    assert child.returncode == -signal.SIGKILL
    with ContinuityStore(path, ManualClock()) as recovered:
        assert recovered.identity["identity_id"] == identity
        with pytest.raises(CoreError, match="MEMORY_UNAVAILABLE"):
            MemoryService(recovered).read(a)
        assert CANARY.encode() not in path.read_bytes()
        assert len(recovered.privacy.read()["intents"]) == 1


def test_old_unmanaged_clone_without_current_privacy_anchor_is_blocked(cognitive, tmp_path):
    store, _, _ = cognitive
    clone = tmp_path / "unmanaged.db"
    import sqlite3
    with sqlite3.connect(clone) as target:
        store.db.backup(target)
    with pytest.raises(CoreError, match="PRIVACY_ANCHOR_MISSING"):
        ContinuityStore(clone)
    public_dir = tmp_path / "public-dir"
    public_dir.mkdir(mode=0o755)
    with pytest.raises(CoreError, match="PRIVATE_CONTINUITY_DIRECTORY_REQUIRED"):
        ContinuityStore(public_dir / "unsafe.db")
    assert not (public_dir / "unsafe.db").exists()


def test_delete_from_restored_copy_invalidates_live_origin_and_corrupt_anchor_blocks(cognitive):
    store, memory, authority = cognitive
    a = add(memory, evidence(memory, "shared-copy-source", CANARY), CANARY)
    backup = store.path.with_name("live-restored.db")
    store.backup(backup)
    with ContinuityStore(backup, store.clock) as restored:
        report = MemoryService(restored, authority).forget(a, authority)
        assert report["state"] == "PENDING_BACKUP_PURGE"  # origin writer still owns its lock
        assert report["pending_backup_count"] == 1
        with pytest.raises(CoreError, match="MEMORY_UNAVAILABLE"):
            memory.read(a)  # active original sees the shared tombstone before next read
    assert CANARY.encode() not in store.path.read_bytes()
    original = store.privacy.path.read_text()
    try:
        store.privacy.path.write_text('{"schema_version":1,"schema_version":1}')
        with pytest.raises(CoreError, match="PRIVACY_ANCHOR_INVALID"):
            memory.query(scopes=("synthetic-home",), privacy_classes=("PERSONAL",))
    finally:
        store.privacy.path.write_text(original)
