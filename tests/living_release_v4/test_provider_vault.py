import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from nana_core.contracts import CoreError
from nana_core.life.provider_vault import DurableSecretResolver
from tests.first_life_android_v2.test_http_integration import running as running


VALUE = "TEST_ONLY_NOT_SECRET_VAULT_FIRST"
ROTATED = "TEST_ONLY_NOT_SECRET_VAULT_ROTATED"
ENV = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}


def test_encrypted_host_storage_restart_rotation_revoke_and_cas(tmp_path):
    path = tmp_path / "vault"
    resolver = DurableSecretResolver(path, initialize=True)
    resolver.bind("test.primary", VALUE, expected_revision=0)
    assert resolver.metadata()["revision"] == 1
    with pytest.raises(CoreError, match="PROVIDER_VAULT_REVISION_CONFLICT"):
        resolver.bind("test.primary", ROTATED, expected_revision=0)
    resolver.clear()
    code = """import sys,json
from nana_core.life.provider_vault import DurableSecretResolver
data=json.load(sys.stdin);resolver=DurableSecretResolver(sys.argv[1])
value=resolver.resolve('test.primary')
if value.reveal_for_header()!=data['old']:raise ValueError('VALUE_MISMATCH')
value.clear();resolver.bind('test.primary',data['new'],expected_revision=1)
print(json.dumps({'revision':resolver.metadata()['revision'],'restored':True}))
resolver.clear()
"""
    child = subprocess.run([sys.executable, "-c", code, str(path)],
                           input=json.dumps({"old": VALUE, "new": ROTATED}), text=True, capture_output=True, check=True, env=ENV)
    assert json.loads(child.stdout) == {"revision": 2, "restored": True}
    reopened = DurableSecretResolver(path)
    secret = reopened.resolve("test.primary")
    assert secret.reveal_for_header() == ROTATED
    assert VALUE not in str(secret) + repr(reopened) + child.stdout + child.stderr
    secret.clear()
    reopened.revoke("test.primary", expected_revision=2)
    assert not DurableSecretResolver(path).available("test.primary")
    assert reopened.metadata()["revision"] == 3
    for file in path.iterdir():
        if file.is_file():
            assert file.stat().st_mode & 0o077 == 0
            assert VALUE.encode() not in file.read_bytes() and ROTATED.encode() not in file.read_bytes()


@pytest.mark.parametrize("stage,expected_revision", [("TEMP_FSYNCED", 1), ("REPLACED", 2)])
def test_actual_sigkill_atomic_vault_update(tmp_path, stage, expected_revision):
    path = tmp_path / "vault"
    resolver = DurableSecretResolver(path, initialize=True)
    resolver.bind("test.primary", VALUE)
    resolver.clear()
    code = """import sys,json,os,signal
from nana_core.life.provider_vault import DurableSecretResolver
class Crash(DurableSecretResolver):
 def _checkpoint(self,stage):
  if stage==sys.argv[2]:os.kill(os.getpid(),signal.SIGKILL)
data=json.load(sys.stdin);Crash(sys.argv[1]).bind('test.primary',data['new'],expected_revision=1)
"""
    child = subprocess.run([sys.executable, "-c", code, str(path), stage],
                           input=json.dumps({"new": ROTATED}), text=True, capture_output=True, env=ENV)
    assert child.returncode == -signal.SIGKILL
    reopened = DurableSecretResolver(path)
    assert reopened.metadata()["revision"] == expected_revision
    secret = reopened.resolve("test.primary")
    assert secret.reveal_for_header() == (VALUE if expected_revision == 1 else ROTATED)
    secret.clear()
    for file in path.iterdir():
        assert VALUE.encode() not in file.read_bytes() and ROTATED.encode() not in file.read_bytes()


def test_actual_sigkill_before_vault_revocation_leaves_shared_profiles_disabled(tmp_path):
    from nana_core.continuity.provider_config import ProviderProfile
    from tests.provider_routing.helpers import config_service, update

    config, authority = config_service(tmp_path / "providers.json")
    for name in ("test.primary", "test.other"):
        update(config, authority, "UPSERT_PROVIDER", provider=ProviderProfile(
            provider_profile_id=name, display_name="Test", protocol="OPENAI_COMPATIBLE_CHAT",
            base_url="https://example.test/v1", locality="REMOTE", secret_ref="test.shared"))
    path = tmp_path / "vault"
    resolver = DurableSecretResolver(path, initialize=True)
    resolver.bind("test.shared", VALUE)
    resolver.clear()
    code = """import sys,os,signal
from types import SimpleNamespace
from pathlib import Path
from nana_core.continuity.provider_config import ProviderConfigService,ProviderConfigurationAuthority
from nana_core.life.provider_vault import DurableSecretResolver
from nana_core.life.live_api.provider_settings import _mutate_binding
class Crash(DurableSecretResolver):
 def revoke(self,*args,**kwargs):os.kill(os.getpid(),signal.SIGKILL)
authority=ProviderConfigurationAuthority()
service=ProviderConfigService(Path(sys.argv[1]),authority);config=service.load()
body=SimpleNamespace(action='REVOKE',expected_vault_revision=1)
_mutate_binding(Crash(sys.argv[2]),body,config.providers[0],service,config,authority)
"""
    child = subprocess.run([sys.executable, "-c", code, str(tmp_path / "providers.json"), str(path)],
                           capture_output=True, text=True, env=ENV, timeout=10)
    assert child.returncode == -signal.SIGKILL
    assert all(not profile.enabled for profile in config.load().providers)
    restored = DurableSecretResolver(path)
    assert restored.metadata()["revision"] == 1 and restored.available("test.shared")
    restored.clear()
    assert VALUE not in child.stdout + child.stderr + config._path.read_text()


def test_corruption_permissions_and_unknown_fields_fail_closed(tmp_path):
    path = tmp_path / "vault"
    resolver = DurableSecretResolver(path, initialize=True)
    resolver.bind("test.primary", VALUE)
    resolver.clear()
    document = path / "vault.json"
    original = document.read_bytes()
    for raw in (b"{", original.replace(b'"revision":1', b'"revision":9'),
                json.dumps({**json.loads(original), "allow_all": True}).encode()):
        document.write_bytes(raw)
        with pytest.raises(CoreError, match="PROVIDER_VAULT_CORRUPT"):
            DurableSecretResolver(path)
    document.write_bytes(original)
    (path / "wrapping.key").chmod(0o644)
    with pytest.raises(CoreError, match="PROVIDER_VAULT_PERMISSIONS_UNSAFE"):
        DurableSecretResolver(path)
    (path / "wrapping.key").chmod(0o600)
    document.unlink()
    with pytest.raises(CoreError, match="PROVIDER_VAULT_CORRUPT"):
        DurableSecretResolver(path, initialize=True)


def test_private_key_must_not_be_symlinked_or_shared(tmp_path):
    path = tmp_path / "vault"
    resolver = DurableSecretResolver(path, initialize=True)
    resolver.clear()
    os.link(path / "wrapping.key", tmp_path / "duplicate")
    with pytest.raises(CoreError, match="PROVIDER_VAULT_PERMISSIONS_UNSAFE"):
        DurableSecretResolver(path)


@pytest.mark.parametrize("home_alias", ["symlink", "parent_segment"])
def test_vault_cannot_be_created_inside_aliased_subject_home(tmp_path, home_alias):
    from nana_core.life.live_api.__main__ import HostConfiguration
    from tests.first_life_android_v2.test_supervisor import owned

    home, binding, release = owned(tmp_path)
    if home_alias == "symlink":
        alias = tmp_path / "subject-alias"
        alias.symlink_to(home, target_is_directory=True)
    else:
        extra = tmp_path / "extra"
        extra.mkdir()
        alias = extra / ".." / home.name
    vault = home / "provider-vault"
    settings = HostConfiguration(home=str(alias), host_state=str(tmp_path / "host"), binding=binding,
                                 releases=(release,), active_release=release.release_id,
                                 public_origin="https://space.test", web_root=str(tmp_path), provider_vault=str(vault))
    settings_file = tmp_path / "host.json"
    settings_file.write_text(settings.model_dump_json())
    settings_file.chmod(0o600)
    child = subprocess.run([sys.executable, "-m", "nana_core.life.live_api", "--config", str(settings_file),
                            "--live-provider-authorized"], capture_output=True, text=True, env=ENV, timeout=10)
    assert child.returncode == 2
    assert json.loads(child.stdout) == {"state": "BLOCKED", "code": "PROVIDER_VAULT_MUST_BE_HOST_LOCAL_OUTSIDE_SUBJECT"}
    assert not vault.exists()


def test_actual_bff_process_restart_restores_binding_without_new_provider_input(tmp_path):
    import http.client
    import select
    import socket
    from nana_core.continuity.provider_config import ProviderProfile
    from nana_core.life.live_api.__main__ import HostConfiguration
    from nana_core.life.live_api.contracts import Role
    from tests.first_life_android_v2.test_supervisor import owned
    from tests.provider_routing.helpers import config_service, update

    home, binding, release = owned(tmp_path)
    config, authority = config_service(home / "providers.json")
    update(config, authority, "UPSERT_PROVIDER", provider=ProviderProfile(
        provider_profile_id="test.primary", display_name="Test", protocol="OPENAI_COMPATIBLE_CHAT",
        base_url="https://example.test/v1", locality="REMOTE", secret_ref="test.primary"))
    vault = tmp_path / "vault"
    resolver = DurableSecretResolver(vault, initialize=True)
    resolver.bind("test.primary", VALUE)
    resolver.clear()
    state = tmp_path / "host"
    state.mkdir(mode=0o700)
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", 0))
        port = port_probe.getsockname()[1]
    settings = HostConfiguration(home=str(home), host_state=str(state), binding=binding, releases=(release,),
                                 active_release=release.release_id, public_origin="https://space.test", web_root=str(tmp_path),
                                 port=port, roles=tuple(Role), provider_vault=str(vault), allow_provider_configuration=True)
    settings_file = tmp_path / "host.json"
    settings_file.write_text(settings.model_dump_json())
    settings_file.chmod(0o600)
    password = "TEST_ONLY_NOT_SECRET_BFF_PASSWORD"

    def request(path, method="GET", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(method, "/api/nana-space/v2/" + path, None if body is None else json.dumps(body),
                           {"Host": "space.test", "Origin": "https://space.test", "Content-Type": "application/json", **(headers or {})})
        response = connection.getresponse()
        value, cookie = json.loads(response.read()), response.getheader("Set-Cookie")
        connection.close()
        assert response.status == 200
        return value, cookie

    children = []
    try:
        for _ in range(2):
            child = subprocess.Popen([sys.executable, "-m", "nana_core.life.live_api", "--config", str(settings_file),
                                      "--password-fd", "0", "--live-provider-authorized"], env=ENV,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            children.append(child)
            child.stdin.write(password + "\n")
            child.stdin.close()
            assert select.select([child.stdout], [], [], 10)[0], "BFF_NOT_READY"
            ready = json.loads(child.stdout.readline())
            assert ready["state"] == "BFF_READY" and ready["subject_id"] == binding.subject_id
            session, cookie = request("session", "POST", {"subject_id": binding.subject_id, "password": password})
            status, _ = request("providers/credentials", headers={"Cookie": cookie.split(";")[0], "X-Nana-CSRF": session["data"]["csrf"]})
            assert status["data"]["vault"]["storage"] == "HOST_LOCAL_AES_256_GCM"
            assert status["data"]["profiles"][0]["secret_state"] == "AVAILABLE"
            assert VALUE not in json.dumps(status)
            child.kill()
            child.wait(timeout=5)
            assert child.returncode == -signal.SIGKILL
            assert VALUE not in child.stderr.read()
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
            child.stdout.close()
            child.stderr.close()


def test_native_vault_cas_metadata_and_shared_reference_revocation(running, tmp_path):  # noqa: F811
    from nana_core.continuity.provider_config import ProviderProfile
    from nana_core.life.live_api.contracts import PairOffer, Role
    from tests.first_life_android_v2.test_http_integration import http, login, base, PW
    from tests.provider_routing.helpers import config_service, update

    server, service = running
    service.allow_provider_configuration = True
    service.credential_resolver = DurableSecretResolver(tmp_path / "vault", initialize=True)
    config, authority = config_service(service.supervisor.home / "providers.json")
    for name in ("test.primary", "test.other"):
        update(config, authority, "UPSERT_PROVIDER", provider=ProviderProfile(provider_profile_id=name, display_name="Test",
            protocol="OPENAI_COMPATIBLE_CHAT", base_url="https://example.test/v1", locality="REMOTE", secret_ref="test.shared"))
    web = login(server, service)
    token, _ = service.auth.login(PW)
    admin = service.auth.authorize(token, "WEB")
    offer = service.auth.offer(admin, PairOffer(device_name="vault-test", roles=(Role.READER, Role.HOST_ADMIN)))
    device, refresh = service.auth.pair(offer, "vault-test")
    native = {"Authorization": "Bearer " + service.auth.native_session(device, refresh)}
    args = {**base(service, "vault-bind"), "provider_profile_id": "test.primary", "profile_revision": 1,
            "expected_vault_revision": 0, "credential": VALUE}
    assert http(server, "providers/credential", "POST", args, web)[0] == 403
    missing_revision = {key: value for key, value in args.items() if key != "expected_vault_revision"}
    code, missing, _ = http(server, "providers/credential", "POST", missing_revision, native)
    assert code == 409 and missing["code"] == "PROVIDER_VAULT_REVISION_REQUIRED"
    assert service.credential_resolver.metadata()["revision"] == 0
    code, row, _ = http(server, "providers/credential", "POST", args, native)
    assert code == 200 and row["data"]["state"] == "BOUND_IN_HOST_VAULT"
    assert row["data"]["vault"]["revision"] == 1 and row["data"]["credential_persisted"]
    stale = {**args, "credential": ROTATED}
    assert http(server, "providers/credential", "POST", stale, native)[0] == 409
    meta = http(server, "providers/credentials", headers=web)[1]
    assert all(p["secret_state"] == "AVAILABLE" for p in meta["data"]["profiles"])
    assert "secret_ref" not in json.dumps(meta) and VALUE not in json.dumps(meta)
    rotation = {**base(service, "vault-rotate"), "provider_profile_id": "test.primary", "profile_revision": 1,
                "expected_vault_revision": 1, "credential": ROTATED}
    code, rotated, _ = http(server, "providers/credential", "POST", rotation, native)
    assert code == 200 and rotated["data"]["vault"]["revision"] == 2
    assert ROTATED not in json.dumps(rotated)
    reopened = DurableSecretResolver(tmp_path / "vault")
    secret = reopened.resolve("test.shared")
    assert secret.reveal_for_header() == ROTATED
    secret.clear()
    reopened.clear()
    revoke = {**base(service, "vault-revoke"), "action": "REVOKE", "provider_profile_id": "test.primary",
              "profile_revision": 1, "expected_vault_revision": 1}
    assert http(server, "providers/credential", "POST", revoke, native)[0] == 409
    assert all(p.enabled for p in config.load().providers)
    missing_revoke_revision = {key: value for key, value in revoke.items() if key != "expected_vault_revision"}
    assert http(server, "providers/credential", "POST", missing_revoke_revision, native)[0] == 409
    assert all(p.enabled for p in config.load().providers)
    revoke["expected_vault_revision"] = 2
    code, revoked, _ = http(server, "providers/credential", "POST", revoke, native)
    assert code == 200 and revoked["data"]["state"] == "REVOKED_PROVIDER_DISABLED"
    assert set(revoked["data"]["disabled_provider_profile_ids"]) == {"test.primary", "test.other"}
    assert not service.credential_resolver.available("test.shared")
    assert all(not p.enabled for p in config.load().providers)
    assert VALUE not in service.ledger.document.path.read_text()
    assert VALUE not in config._path.read_text()
    assert ROTATED not in service.ledger.document.path.read_text() + config._path.read_text()
    assert not service.supervisor.home.joinpath("vault").exists()
    service.credential_resolver.clear()
