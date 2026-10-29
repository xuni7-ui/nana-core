"""Synthetic offline qualification of inherited host-vault credential epochs."""

import base64
import fcntl
import hashlib
import json
import os
import select
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from nana_core.contracts import CoreError
from nana_core.life.provider_vault import DurableSecretResolver
from nana_core.life.secret_binding import BOUND, VAULT_DOCUMENT_BOUND, MemorySecretResolver, _sealed_fd


VALUE = "TEST_ONLY_NOT_SECRET_EPOCH_FIRST"
ROTATED = "TEST_ONLY_NOT_SECRET_EPOCH_ROTATED"


def child_snapshot(resolver):
    fd, ref = resolver.inherited_fd()
    try:
        assert ref is None
        assert fcntl.fcntl(fd, getattr(fcntl, "F_GET_SEALS", 1034)) & 0x000F == 0x000F
        return MemorySecretResolver.from_fd(fd)
    finally:
        os.close(fd)


def assert_unavailable(resolver):
    assert not resolver.available("test.primary")
    with pytest.raises(CoreError, match="SECRET_UNAVAILABLE"):
        resolver.resolve("test.primary")
    assert resolver.inherited_fd() is None


def envelope(path):
    raw = (path / "vault.json").read_bytes()
    return {"NANA_SECRET_FD": 1, "bindings": {"test.primary": VALUE},
            "host_vault": {"path": str(path / "vault.json"),
                           "revision": json.loads(raw)["revision"],
                           "sha256": hashlib.sha256(raw).hexdigest()}}


def test_running_child_real_sealed_fd_revoke_then_reenable_cannot_reuse_binding(tmp_path):
    from nana_core.continuity.provider_config import ProviderProfile
    from nana_core.life.live_api.provider_settings import _mutate_binding
    from tests.provider_routing.helpers import config_service, update

    config, authority = config_service(tmp_path / "providers.json")
    profile = ProviderProfile(provider_profile_id="test.primary", display_name="Test",
                              protocol="OPENAI_COMPATIBLE_CHAT", base_url="https://example.test/v1",
                              locality="REMOTE", secret_ref="test.primary")
    update(config, authority, "UPSERT_PROVIDER", provider=profile)
    host = DurableSecretResolver(tmp_path / "vault", initialize=True)
    host.bind("test.primary", VALUE)
    fd, _ = host.inherited_fd()
    code = """import json,sys
from nana_core.contracts import CoreError
from nana_core.life.secret_binding import MemorySecretResolver
r=MemorySecretResolver.from_fd(int(sys.argv[1]))
for command in sys.stdin:
 available=r.available('test.primary')
 try:
  value=r.resolve('test.primary');resolved=value.reveal_for_header() is not None;value.clear()
 except CoreError:resolved=False
 print(json.dumps({'available':available,'resolved':resolved}),flush=True)
r.clear()
"""
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    child = subprocess.Popen([sys.executable, "-c", code, str(fd)], pass_fds=(fd,), env=env,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    os.close(fd)

    def inspect():
        child.stdin.write("inspect\n")
        child.stdin.flush()
        assert select.select([child.stdout], [], [], 10)[0]
        return json.loads(child.stdout.readline())

    try:
        assert inspect() == {"available": True, "resolved": True}
        _mutate_binding(host, SimpleNamespace(action="REVOKE", expected_vault_revision=1),
                        profile, config, config.load(), authority)
        assert not config.load().providers[0].enabled
        update(config, authority, "ENABLE_PROVIDER", target_id="test.primary")
        assert config.load().providers[0].enabled
        # Same already-running child, same originally inherited resolver, no
        # restart and no new FD or binding after the BFF mutation.
        assert inspect() == {"available": False, "resolved": False}
        assert not host.available("test.primary")
    finally:
        child.stdin.close()
        child.wait(timeout=10)
        output = child.stdout.read() + child.stderr.read()
        child.stdout.close()
        child.stderr.close()
        host.clear()
    assert child.returncode == 0 and VALUE not in output


def test_bind_rotate_revoke_fresh_snapshot_and_guarded_reexport(tmp_path):
    host = DurableSecretResolver(tmp_path / "vault", initialize=True)
    assert host.inherited_fd() is None
    host.bind("test.primary", VALUE)
    original = child_snapshot(host)
    reexported = child_snapshot(original)
    assert host.binding_contract_version == original.binding_contract_version == reexported.binding_contract_version == 2
    in_flight = original.resolve("test.primary")
    host.bind("test.primary", ROTATED, expected_revision=1)
    assert_unavailable(original)
    assert_unavailable(reexported)
    # A copied credential already handed to a dispatch remains immutable;
    # invalidating future selection does not claim cancellation or retry.
    assert in_flight.reveal_for_header() == VALUE
    in_flight.clear()
    fresh = child_snapshot(host)
    value = fresh.resolve("test.primary")
    assert value.reveal_for_header() == ROTATED
    value.clear()
    host.revoke("test.primary", expected_revision=2)
    assert_unavailable(fresh)
    host.bind("test.primary", VALUE, expected_revision=3)
    assert_unavailable(original)
    assert_unavailable(fresh)
    newest = child_snapshot(host)
    assert newest.available("test.primary")
    newest.clear()
    host.clear()


@pytest.mark.parametrize("damage", ["missing", "invalid_json", "same_revision_ciphertext", "extra_field",
                                    "oversize", "public_file", "public_parent", "public_host_parent",
                                    "hardlink", "symlink", "fifo", "directory", "symlink_parent"])
def test_corrupt_missing_or_unsafe_guard_fails_closed(tmp_path, damage):
    path = tmp_path / "vault"
    host = DurableSecretResolver(path, initialize=True)
    host.bind("test.primary", VALUE)
    child = child_snapshot(host)
    document = path / "vault.json"
    if damage == "missing":
        document.unlink()
    elif damage == "invalid_json":
        document.write_bytes(b"{")
    elif damage == "same_revision_ciphertext":
        body = json.loads(document.read_bytes())
        ciphertext = bytearray(base64.b64decode(body["ciphertext"]))
        ciphertext[0] ^= 1
        body["ciphertext"] = base64.b64encode(ciphertext).decode()
        document.write_text(json.dumps(body))
    elif damage == "extra_field":
        document.write_text(json.dumps({**json.loads(document.read_bytes()), "allow_all": True}))
    elif damage == "oversize":
        document.write_bytes(b" " * (VAULT_DOCUMENT_BOUND + 1))
    elif damage == "public_file":
        document.chmod(0o644)
    elif damage == "public_parent":
        path.chmod(0o755)
    elif damage == "public_host_parent":
        tmp_path.chmod(0o755)
    elif damage == "hardlink":
        os.link(document, tmp_path / "duplicate")
    elif damage == "symlink":
        saved = path / "saved.json"
        document.rename(saved)
        document.symlink_to(saved)
    elif damage == "fifo":
        document.unlink()
        os.mkfifo(document, 0o600)
    elif damage == "directory":
        document.unlink()
        document.mkdir(mode=0o700)
    else:
        saved = tmp_path / "saved-vault"
        path.rename(saved)
        path.symlink_to(saved, target_is_directory=True)
    try:
        assert_unavailable(child)
    finally:
        tmp_path.chmod(0o700)
        if path.is_dir():
            path.chmod(0o700)
        host.clear()


def test_guard_uses_ciphertext_only_and_never_reads_wrapping_key(tmp_path):
    path = tmp_path / "vault"
    host = DurableSecretResolver(path, initialize=True)
    host.bind("test.primary", VALUE)
    child = child_snapshot(host)
    host.clear()
    (path / "wrapping.key").unlink()
    assert child.available("test.primary")
    value = child.resolve("test.primary")
    assert value.reveal_for_header() == VALUE
    value.clear()
    child.clear()


@pytest.mark.parametrize("field,value", [("version", True), ("version", 0), ("version", 2),
                                         ("extra", True), ("bindings", []), ("bindings", {}),
                                         ("path", "vault.json"), ("path", "/tmp/../vault.json"),
                                         ("path", "/tmp//vault.json"), ("path", "/tmp/./vault.json"),
                                         ("path", "/tmp/"), ("path", "/tmp/\x00vault.json"),
                                         ("path", "/" + "a" * 4096),
                                         ("revision", True), ("revision", -1), ("revision", 2**63),
                                         ("sha256", "z" * 64), ("guard_extra", True),
                                         ("guard_missing", None), ("guard", [])])
def test_fd_envelope_strict_version_fields_types_and_bounds(tmp_path, field, value):
    host = DurableSecretResolver(tmp_path / "vault", initialize=True)
    host.bind("test.primary", VALUE)
    body = envelope(tmp_path / "vault")
    if field == "version":
        body["NANA_SECRET_FD"] = value
    elif field == "extra":
        body["allow_all"] = value
    elif field == "bindings":
        body["bindings"] = value
    elif field == "guard":
        body["host_vault"] = value
    elif field == "guard_extra":
        body["host_vault"]["allow_all"] = value
    elif field == "guard_missing":
        del body["host_vault"]["sha256"]
    else:
        body["host_vault"][field] = value
    fd, _ = _sealed_fd(body)
    try:
        with pytest.raises(CoreError, match="SECRET_BINDING_INVALID"):
            MemorySecretResolver.from_fd(fd)
    finally:
        os.close(fd)
        host.clear()


def test_legacy_plain_map_fd_retains_memory_only_semantics(tmp_path):
    host = MemorySecretResolver()
    assert host.binding_contract_version == 1
    host.bind("test.primary", VALUE)
    # Legacy references that look like envelope fields remain valid maps.
    host.bind("schema_version", "TEST_ONLY_NOT_SECRET_LEGACY_VERSION")
    child = child_snapshot(host)
    assert child.binding_contract_version == 1
    host.revoke("test.primary")
    assert child.available("test.primary")
    assert child.available("schema_version")
    child.clear()
    host.clear()
    # The new uppercase marker would be rejected by the original plain-map
    # binder, so an older binary fails closed instead of dropping the guard.
    with pytest.raises(CoreError, match="SECRET_BINDING_INVALID"):
        host.bind("NANA_SECRET_FD", VALUE)


def test_concurrent_atomic_snapshot_cannot_label_old_values_with_new_revision(tmp_path, monkeypatch):
    path = tmp_path / "vault"
    host = DurableSecretResolver(path, initialize=True)
    host.bind("test.primary", VALUE)
    writer = DurableSecretResolver(path)
    loaded = threading.Event()
    publish = threading.Event()
    original_load = host._load_snapshot
    result = []

    def paused_load():
        snapshot = original_load()
        loaded.set()
        assert publish.wait(10)
        return snapshot

    monkeypatch.setattr(host, "_load_snapshot", paused_load)
    thread = threading.Thread(target=lambda: result.append(host.inherited_fd()))
    thread.start()
    assert loaded.wait(10)
    try:
        writer.bind("test.primary", ROTATED, expected_revision=1)
    finally:
        publish.set()
        thread.join(timeout=10)
    assert not thread.is_alive()
    fd, _ = result.pop()
    try:
        document = json.loads(os.read(fd, BOUND + 1))
        assert document["host_vault"]["revision"] == 1
        assert document["bindings"]["test.primary"] == VALUE
        os.lseek(fd, 0, os.SEEK_SET)
        stale = MemorySecretResolver.from_fd(fd)
    finally:
        os.close(fd)
    assert_unavailable(stale)
    monkeypatch.setattr(host, "_load_snapshot", original_load)
    fresh = child_snapshot(host)
    value = fresh.resolve("test.primary")
    assert value.reveal_for_header() == ROTATED
    value.clear()
    fresh.clear()
    writer.clear()
    host.clear()


@pytest.mark.parametrize("mutation", ["rotate", "revoke_reenable"])
def test_cached_target_and_new_route_block_before_http_after_epoch_change(tmp_path, monkeypatch, mutation):
    from nana_core.continuity.provider_config import CapabilityRoute, ProviderProfile
    from nana_core.continuity.provider_routing import CapabilityRouter, RouteRequest, RoutingPolicy, RuntimeProviderFactory
    from nana_core.continuity.providers import ProviderRegistry
    from nana_core.continuity.world_loop.cognition import CognitionBudget, OpenAIJSONTransport
    from tests.provider_routing.helpers import config_service, model, update
    from tests.world_loop.helpers import capture, fresh, policy

    calls = []
    monkeypatch.setattr(OpenAIJSONTransport, "exchange", lambda *args: calls.append(True))
    config, authority = config_service(tmp_path / "providers.json")
    profile = ProviderProfile(provider_profile_id="test.primary", display_name="Test",
                              protocol="OPENAI_COMPATIBLE_CHAT", base_url="https://example.test/v1",
                              locality="REMOTE", secret_ref="test.primary")
    update(config, authority, "UPSERT_PROVIDER", provider=profile)
    update(config, authority, "UPSERT_MODEL", model=model("test.text", "test.primary"))
    update(config, authority, "SET_CAPABILITY_ROUTE", route=CapabilityRoute(
        operation="COGNITION", primary_model_profile_id="test.text"))
    host = DurableSecretResolver(tmp_path / "vault", initialize=True)
    host.bind("test.primary", VALUE)
    child = child_snapshot(host)
    factory = RuntimeProviderFactory(ProviderRegistry(), child, RoutingPolicy(
        allow_remote=True, allowed_remote_hosts=("example.test",)))
    router = CapabilityRouter(config, factory)
    request = RouteRequest(operation="COGNITION")
    cached = router.resolve(request, policy())
    assert cached._current()
    with fresh(tmp_path / "subject" / "self.db") as runtime:
        memory = capture(runtime, "source", {"fact": "TEST_ONLY epoch guard"})
        session = cached.cognition_session(runtime)
        prepared = session.prepare("before-epoch-change", "INTERPRET", (memory,),
                                   budget=CognitionBudget(cost_ceiling_micro=1))
        revision = config.load().revision
        if mutation == "rotate":
            host.bind("test.primary", ROTATED, expected_revision=1)
            assert config.load().revision == revision
        else:
            from nana_core.life.live_api.provider_settings import _mutate_binding
            _mutate_binding(host, SimpleNamespace(action="REVOKE", expected_vault_revision=1),
                            profile, config, config.load(), authority)
            update(config, authority, "ENABLE_PROVIDER", target_id="test.primary")
        assert not cached._current()
        assert session.execute(prepared)["state"] == "STALE"
        with pytest.raises(CoreError, match="ROUTE_CHANGED_BEFORE_DISPATCH"):
            cached.cognition_session(runtime).prepare("stale", "INTERPRET", (memory,))
    with pytest.raises(CoreError, match="SECRET_UNAVAILABLE"):
        router.resolve(request, policy())
    assert calls == []
    child.clear()
    host.clear()
