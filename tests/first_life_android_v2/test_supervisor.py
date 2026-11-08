"""Actual owned subprocess lifecycle and original single-writer fence."""

import importlib.util
import subprocess
import sys
from pathlib import Path
import pytest
from nana_core.life.live_api.contracts import ApiError, Binding, Realm
from nana_core.life.live_api.supervisor import Supervisor, Release, existing_identity
from nana_core.life.live_api.ledger import OperationLedger
from nana_core.life.live_api.contracts import Completion

ROOT = Path(__file__).resolve().parents[2]


def owned(tmp_path):
    spec = importlib.util.spec_from_file_location("owned_v1_setup", ROOT / "apps/nana-space/gateway/dev_instance.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    home = tmp_path / "home"
    module.initialize(home)
    identity, lineage, unknown = existing_identity(home)
    binding = Binding(subject_id=identity, lineage_binding=lineage)
    release = Release(
        release_id="qualified",
        root=str(ROOT),
        python=sys.executable,
        source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    )
    return home, binding, release


def cleanup(supervisor):
    try:
        supervisor.stop()
    finally:
        if supervisor.child and supervisor.child.poll() is None:
            supervisor.child.kill()
            supervisor.child.wait(timeout=5)
        supervisor.close()


def test_actual_start_pause_stop_restart_and_sigkill(tmp_path):
    home, binding, release = owned(tmp_path)
    s = Supervisor(home, tmp_path / "host", binding, [release], active_release="qualified")
    try:
        first = s.start()
        assert first["process_ready"] and first["owner_managed"]
        with pytest.raises(ApiError, match="CORE_ALREADY_OWNED"):
            s.start()
        from nana_core.life.control import request

        assert request(home, {"operation": "control", "command": "pause"})["ok"]
        assert request(home, {"operation": "control", "command": "resume"})["ok"]
        stopped = s.stop()
        assert stopped["stop_latch"] and not stopped["runtime_active"]
        second = s.start()
        assert second["owner_epoch"] > first["owner_epoch"] and second["subject_id"] == binding.subject_id
        s.child.kill()
        s.child.wait(timeout=5)
        recovered = s.monitor_once()
        assert recovered["process_ready"] and recovered["owner_epoch"] > second["owner_epoch"]
        assert recovered["subject_id"] == binding.subject_id and recovered["lineage_binding"] == binding.lineage_binding
        s.stop()
        assert not s.monitor_once()["runtime_active"]
    finally:
        cleanup(s)


@pytest.mark.parametrize('peer', [None, False, True])
def test_managed_readiness_requires_current_control_peer(tmp_path, monkeypatch, peer):
    home, binding, release = owned(tmp_path)
    s = Supervisor(home, tmp_path/'host', binding, [release], active_release='qualified')
    raw = {'runtime': {'runtime_active': True, 'lease': {}}, 'process_ready': True,
           'control_ready': peer, 'storage_status': 'OBSERVING', 'disk_pressure': 'AVAILABLE'}
    monkeypatch.setattr('nana_core.life.live_api.supervisor.health', lambda unused: raw)
    try:
        assert s.status()['process_ready'] is (peer is True)
    finally:
        s.close()


def test_wrong_identity_and_production_activation_rejected(tmp_path):
    home, binding, release = owned(tmp_path)
    with pytest.raises(ApiError, match="INVALID_IDENTITY"):
        Supervisor(
            home,
            tmp_path / "wrong",
            binding.model_copy(update={"subject_id": "not-that-subject"}),
            [release],
            active_release="qualified",
        )
    with pytest.raises(ApiError, match="PRODUCTION_ACTIVATION_REQUIRED"):
        Supervisor(
            home,
            tmp_path / "prod",
            binding.model_copy(update={"realm": Realm.PRODUCTION}),
            [release],
            active_release="qualified",
        )
    s = Supervisor(home, tmp_path / "valid", binding, [release], active_release="qualified")
    try:
        with pytest.raises(ApiError, match="SUPERVISOR_ALREADY_OWNED"):
            Supervisor(home, tmp_path / "valid", binding, [release], active_release="qualified")
    finally:
        s.close()


def test_durable_unknown_receipt_never_replays_and_never_keeps_wording(tmp_path):
    path = tmp_path / "ops.json"
    l = OperationLedger(path)
    payload = {"text": "SYNTHETIC PROJECT BODY NOT HOST STATE"}
    l.reserve("key", "device.a", payload, "MESSAGE", 0, "request")
    l.transition("key", Completion.RUNNING, dispatched=True)
    assert payload["text"] not in path.read_text()
    reopened = OperationLedger(path)
    receipt = reopened.prior("key", "device.a", payload)
    assert receipt.state == Completion.UNKNOWN and receipt.no_retry and receipt.dispatch_happened
    with pytest.raises(ApiError, match="IDEMPOTENCY_COLLISION"):
        reopened.prior("key", "device.a", {"text": "different"})
    with pytest.raises(ApiError, match="RECEIPT_NOT_FOUND"):
        reopened.read("key", "device.b")


def test_controlled_release_switch_and_stop_latch_survives_reopen(tmp_path):
    home, binding, release = owned(tmp_path)
    next_release = release.model_copy(update={"release_id": "next-qualified"})
    supervisor = Supervisor(
        home, tmp_path / "host", binding, [release, next_release], active_release=release.release_id
    )
    try:
        first = supervisor.start()
        after = supervisor.change_release(next_release.release_id)
        assert after["subject_id"] == first["subject_id"] and after["owner_epoch"] > first["owner_epoch"]
        assert after["release_id"] == next_release.release_id
        old = supervisor.change_release(release.release_id, rollback=True)
        assert old["lineage_binding"] == first["lineage_binding"]
        supervisor.stop()
    finally:
        cleanup(supervisor)
    reopened = Supervisor(home, tmp_path / "host", binding, [release, next_release], active_release=release.release_id)
    try:
        assert reopened.status()["stop_latch"] and not reopened.monitor_once()["runtime_active"]
    finally:
        reopened.close()


def test_release_rechecks_outstanding_work_after_owner_stops(tmp_path, monkeypatch):
    home, binding, release = owned(tmp_path)
    candidate = release.model_copy(update={'release_id': 'candidate'})
    supervisor = Supervisor(home, tmp_path/'host', binding, [release, candidate], active_release=release.release_id)
    try:
        checks = iter((0, 1))
        monkeypatch.setattr(supervisor, 'verify_binding', lambda: next(checks))
        stopped = []
        monkeypatch.setattr(supervisor, 'stop', lambda: stopped.append(True))
        with pytest.raises(ApiError, match='PENDING_UNKNOWN_REQUIRES_REVIEW'):
            supervisor.change_release('candidate')
        assert stopped == [True]
        assert supervisor.state.read()['active_release'] == release.release_id
    finally:
        supervisor.close()


def test_manual_start_cannot_bypass_outstanding_work(tmp_path, monkeypatch):
    home, binding, release = owned(tmp_path)
    supervisor = Supervisor(home, tmp_path/'host', binding, [release], active_release=release.release_id)
    try:
        monkeypatch.setattr(supervisor, 'verify_binding', lambda: 1)
        monkeypatch.setattr(supervisor, 'status', lambda: {'runtime_active': False})
        with pytest.raises(ApiError, match='PENDING_UNKNOWN_REQUIRES_REVIEW'):
            supervisor.start()
        assert supervisor.child is None
    finally:
        supervisor.close()
