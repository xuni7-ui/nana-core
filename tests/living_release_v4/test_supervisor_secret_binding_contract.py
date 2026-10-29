"""Offline rollback compatibility for inherited credential formats."""

import json
import os
import sys
from pathlib import Path

import pytest

from nana_core.life import secret_binding
from nana_core.life.live_api.contracts import ApiError, Realm
from nana_core.life.live_api.supervisor import Release, Supervisor
from nana_core.life.provider_vault import DurableSecretResolver
from nana_core.life.secret_binding import MemorySecretResolver
from tests.first_life_android_v2.test_supervisor import ROOT, cleanup, owned


VALUE = "TEST_ONLY_NOT_SECRET_ROLLBACK"


def target_release(tmp_path, contract=None):
    root = tmp_path / "registered-target"
    root.mkdir()
    # Explicit DEV release metadata declares the loader contract. No Git-root
    # inference is involved; actual offline Core uses the current source tree.
    (root / "src").symlink_to(ROOT / "src", target_is_directory=True)
    metadata = {"source_commit": "e" * 40}
    if contract is not None:
        metadata["secret_binding_contract"] = contract
    (root / "runtime.json").write_text(json.dumps(metadata))
    return Release(release_id="registered-target", root=str(root), python=sys.executable,
                   source_commit="e" * 40)


@pytest.fixture
def controller(tmp_path):
    home, binding, current = owned(tmp_path)
    # Permit the inherited-FD startup path while retaining a zero total dispatch
    # budget and no provider/model routes. This never contacts a provider.
    configuration = json.loads((home / "life.json").read_text())
    configuration.update(provider_hosts=["example.invalid"], remote_privacy=["PUBLIC", "PROJECT"],
                         provider_cost_ceiling_micro=1, provider_calls_per_day=1)
    (home / "life.json").write_text(json.dumps(configuration))
    from nana_core.continuity.provider_config import ProviderConfigService, ProviderConfigurationAuthority

    authority = ProviderConfigurationAuthority()
    ProviderConfigService(home / "providers.json", authority).initialize(authority)
    resolver = DurableSecretResolver(tmp_path / "vault", initialize=True)
    resolver.bind("test.primary", VALUE)
    supervisor = Supervisor(home, tmp_path / "host", binding, [current],
                            active_release=current.release_id, provider_binding=resolver.inherited_fd)
    try:
        yield supervisor, resolver
    finally:
        cleanup(supervisor)
        resolver.clear()


def test_incompatible_rollback_preserves_actual_healthy_core_without_stop(controller, tmp_path, monkeypatch):
    supervisor, _ = controller
    target = target_release(tmp_path)
    supervisor.releases[target.release_id] = target
    before = supervisor.start()
    pid = supervisor.child.pid
    stop_calls = []
    stop = supervisor.stop

    def tracked_stop():
        stop_calls.append(True)
        return stop()

    monkeypatch.setattr(supervisor, "stop", tracked_stop)
    with pytest.raises(ApiError, match="INCOMPATIBLE_SECRET_BINDING_CONTRACT"):
        supervisor.change_release(target.release_id, rollback=True)
    assert stop_calls == []
    after = supervisor.status()
    assert supervisor.child.pid == pid and supervisor.child.poll() is None
    assert after["process_ready"] and after["owner_epoch"] == before["owner_epoch"]
    assert after["release_id"] == before["release_id"]
    assert not after["stop_latch"]


def test_contract_two_target_switches_and_consumes_guarded_fd(controller, tmp_path):
    supervisor, _ = controller
    target = target_release(tmp_path, 2)
    supervisor.releases[target.release_id] = target
    before = supervisor.start()
    after = supervisor.change_release(target.release_id)
    assert after["process_ready"] and after["owner_managed"]
    assert after["owner_epoch"] > before["owner_epoch"]
    assert after["subject_id"] == before["subject_id"]
    assert after["release_id"] == target.release_id


def test_restart_rejects_new_incompatible_binding_without_stopping_healthy_core(controller, tmp_path, monkeypatch):
    supervisor, resolver = controller
    target = target_release(tmp_path)
    supervisor.releases[target.release_id] = target
    supervisor._record(active_release=target.release_id)
    supervisor.provider_binding = None
    before = supervisor.start()
    pid = supervisor.child.pid
    supervisor.provider_binding = resolver.inherited_fd
    stop_calls = []
    stop = supervisor.stop

    def tracked_stop():
        stop_calls.append(True)
        return stop()

    monkeypatch.setattr(supervisor, "stop", tracked_stop)
    with pytest.raises(ApiError, match="INCOMPATIBLE_SECRET_BINDING_CONTRACT"):
        supervisor.restart()
    assert stop_calls == []
    after = supervisor.status()
    assert supervisor.child.pid == pid and supervisor.child.poll() is None
    assert after["process_ready"] and after["owner_epoch"] == before["owner_epoch"]
    assert after["release_id"] == target.release_id and not after["stop_latch"]


def test_legacy_plain_map_still_starts_with_contract_one_target(controller, tmp_path):
    supervisor, _ = controller
    resolver = MemorySecretResolver()
    resolver.bind("test.primary", VALUE)
    target = target_release(tmp_path)
    supervisor.releases[target.release_id] = target
    supervisor._record(active_release=target.release_id)
    supervisor.provider_binding = resolver.inherited_fd
    fd, reference = resolver.inherited_fd()
    try:
        assert reference is None
        assert json.loads(os.read(fd, 65536)) == {"test.primary": VALUE}
    finally:
        os.close(fd)
    try:
        after = supervisor.start()
        assert after["process_ready"] and after["release_id"] == target.release_id
        assert resolver.binding_contract_version == 1
    finally:
        resolver.clear()


def test_empty_durable_binding_allows_legacy_offline_start(controller, tmp_path):
    supervisor, resolver = controller
    resolver.revoke("test.primary")
    assert resolver.metadata()["bindings"] == 0 and resolver.inherited_fd() is None
    target = target_release(tmp_path)
    supervisor.releases[target.release_id] = target
    supervisor._record(active_release=target.release_id)
    after = supervisor.start()
    assert after["process_ready"] and after["release_id"] == target.release_id


def test_binding_added_after_empty_metadata_is_rechecked_before_popen(controller, tmp_path, monkeypatch):
    supervisor, resolver = controller
    resolver.revoke("test.primary")
    target = target_release(tmp_path)
    supervisor.releases[target.release_id] = target
    supervisor._record(active_release=target.release_id)
    original_export = resolver.inherited_fd
    exported = []

    def newly_bound_export():
        resolver.bind("test.primary", VALUE)
        supplied = original_export()
        exported.append(supplied[0])
        return supplied

    monkeypatch.setattr(resolver, "inherited_fd", newly_bound_export)
    # Keep a bound callback carrying the resolver's public contract metadata.
    from types import MethodType

    supervisor.provider_binding = MethodType(lambda self: newly_bound_export(), resolver)
    popen_calls = []
    monkeypatch.setattr("nana_core.life.live_api.supervisor.subprocess.Popen", lambda *args, **kwargs: popen_calls.append(True))
    before = supervisor.state.read()
    with pytest.raises(ApiError, match="INCOMPATIBLE_SECRET_BINDING_CONTRACT"):
        supervisor.start()
    assert popen_calls == [] and len(exported) == 1
    with pytest.raises(OSError):
        os.fstat(exported[0])
    assert supervisor.state.read() == before


def test_incompatible_start_does_not_export_or_mutate_stop_latch(controller, tmp_path, monkeypatch):
    supervisor, resolver = controller
    target = target_release(tmp_path)
    supervisor.releases[target.release_id] = target
    supervisor._record(active_release=target.release_id)
    exports = []
    from types import MethodType

    supervisor.provider_binding = MethodType(lambda self: exports.append(True), resolver)
    before = supervisor.state.read()
    with pytest.raises(ApiError, match="INCOMPATIBLE_SECRET_BINDING_CONTRACT"):
        supervisor.start()
    assert exports == [] and supervisor.state.read() == before


@pytest.mark.parametrize("contract", [True, "2", 0, -1])
def test_invalid_target_contract_rejected_before_stop(controller, tmp_path, monkeypatch, contract):
    supervisor, _ = controller
    target = target_release(tmp_path, contract)
    supervisor.releases[target.release_id] = target
    stop_calls = []
    monkeypatch.setattr(supervisor, "stop", lambda: stop_calls.append(True))
    with pytest.raises(ApiError, match="INCOMPATIBLE_SECRET_BINDING_CONTRACT"):
        supervisor.change_release(target.release_id, rollback=True)
    assert stop_calls == []


def test_metadata_failure_rejects_change_without_export_or_stop(controller, tmp_path, monkeypatch):
    supervisor, resolver = controller
    target = target_release(tmp_path, 2)
    supervisor.releases[target.release_id] = target
    stop_calls = []
    monkeypatch.setattr(supervisor, "stop", lambda: stop_calls.append(True))

    def unavailable_metadata():
        raise OSError("TEST_ONLY_UNAVAILABLE")

    monkeypatch.setattr(resolver, "metadata", unavailable_metadata)
    with pytest.raises(ApiError, match="INCOMPATIBLE_SECRET_BINDING_CONTRACT"):
        supervisor.change_release(target.release_id, rollback=True)
    assert stop_calls == []


def test_no_fd_binding_and_opaque_legacy_callback_remain_compatible(controller, tmp_path):
    supervisor, _ = controller
    target = target_release(tmp_path)
    supervisor.provider_binding = None
    supervisor._require_secret_binding_contract(target)
    supervisor.provider_binding = lambda: None
    supervisor._require_secret_binding_contract(target)


def test_development_fallback_requires_actual_loaded_decoder_and_never_production(controller, tmp_path):
    supervisor, _ = controller
    current = supervisor.releases[supervisor.state.read()["active_release"]]
    assert not (Path(current.root) / "runtime.json").exists()
    assert Path(current.root) / "src/nana_core/life/secret_binding.py" == Path(secret_binding.__file__).resolve()
    supervisor._require_secret_binding_contract(current)
    target = target_release(tmp_path)
    (Path(target.root) / "runtime.json").unlink()
    with pytest.raises(ApiError, match="INCOMPATIBLE_SECRET_BINDING_CONTRACT"):
        supervisor._require_secret_binding_contract(target)
    supervisor.binding = supervisor.binding.model_copy(update={"realm": Realm.PRODUCTION})
    with pytest.raises(ApiError, match="INCOMPATIBLE_SECRET_BINDING_CONTRACT"):
        supervisor._require_secret_binding_contract(current)
