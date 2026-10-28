import json
import os
import secrets

import pytest

from nana_core.contracts import CoreError
from nana_core.life.secret_binding import MemorySecretResolver
from nana_core.life.live_api.contracts import PairOffer, Role
from nana_core.life.live_api.provider_settings import CredentialBindingRequest
from nana_core.continuity.provider_config import ProviderProfile
from tests.provider_routing.helpers import config_service, update
from tests.first_life_android_v2.test_http_integration import running as running, http, login, base, PW


def test_memory_only_resolver_sealed_fd_and_redacted_errors():
    value = "TEST_ONLY_NOT_SECRET_" + secrets.token_hex(10)
    resolver = MemorySecretResolver()
    resolver.bind("test.primary", value)
    resolver.bind("test.vision", value + "2")
    fd, ref = resolver.inherited_fd()
    assert ref is None
    try:
        with pytest.raises(OSError):
            os.write(fd, b"change")
        child = MemorySecretResolver.from_fd(fd)
        assert child.available("test.primary") and child.available("test.vision")
        secret = child.resolve("test.primary")
        assert value not in str(secret) + repr(secret) + repr(child)
        assert secret.reveal_for_header() == value
        secret.clear()
        child.clear()
        assert not child.available("test.primary")
    finally:
        os.close(fd)
        resolver.clear()
    assert resolver.inherited_fd() is None
    with pytest.raises(CoreError) as error:
        resolver.bind("test.primary", value + "\n")
    assert value not in str(error.value)
    args = {"client_request_id": "bind", "idempotency_key": "bind", "expected_revision": 0,
            "run_generation": "0" * 32, "owner_epoch": 0,
            "provider_profile_id": "test.primary", "profile_revision": 1, "credential": value}
    dto = CredentialBindingRequest.model_validate_json(json.dumps(args))
    assert value not in str(dto) + repr(dto) + dto.model_dump_json()


def test_native_only_admin_binding_no_secret_in_durable_state(running):  # noqa: F811
    server, service = running
    service.allow_provider_configuration = True
    resolver = service.credential_resolver = MemorySecretResolver()
    config, authority = config_service(service.supervisor.home / "providers.json")
    profile = ProviderProfile(provider_profile_id="test.primary", display_name="Test", protocol="OPENAI_COMPATIBLE_CHAT",
                              base_url="https://example.test/v1", locality="REMOTE", secret_ref="test.primary")
    update(config, authority, "UPSERT_PROVIDER", provider=profile)
    headers = login(server, service)
    credential = "TEST_ONLY_NOT_SECRET_" + secrets.token_hex(12)
    args = {**base(service, "bind"), "provider_profile_id": "test.primary", "profile_revision": 1, "credential": credential}
    assert http(server, "providers/credential", "POST", args, headers)[0] == 403
    token, _ = service.auth.login(PW)
    admin = service.auth.authorize(token, "WEB")

    def native(roles):
        code = service.auth.offer(admin, PairOffer(device_name="test", roles=roles))
        device, refresh = service.auth.pair(code, "test")
        session = service.auth.native_session(device, refresh)
        return device, {"Authorization": "Bearer " + session}

    _, reader = native((Role.READER, Role.CONVERSATION))
    assert http(server, "providers/credential", "POST", args, reader)[0] == 403
    device, privileged = native((Role.READER, Role.HOST_ADMIN))
    assert http(server, "providers/credential", "POST", {**args, "profile_revision": 2}, privileged)[0] == 409
    status, row, _ = http(server, "providers/credential", "POST", args, privileged)
    assert status == 200 and row["data"]["state"] == "BOUND_IN_HOST_MEMORY"
    assert row["data"]["network_calls"] == 0 and row["data"]["live_permission_granted"] is False
    assert resolver.available("test.primary")
    assert credential not in json.dumps(row)
    assert credential not in config._path.read_text()
    assert credential not in service.auth.document.path.read_text()
    assert credential not in service.ledger.document.path.read_text()
    service.auth.revoke(admin, device)
    assert http(server, "providers/credential", "POST", args, privileged)[0] == 401
    resolver.clear()


def test_explicit_retention_reaches_existing_person_self_and_withdrawal(running):  # noqa: F811
    server, service = running
    headers = login(server, service)
    text = "PROJECT: 今天共同完成了有来源的格式检查。"
    request = {**base(service, "retain"), "text": text, "retain_shared_life": True}
    status, row, _ = http(server, "messages", "POST", request, headers)
    assert status == 200 and row["data"]["state"] == "VERIFIED"
    result = row["data"]["result"]
    assert result["raw_body_persisted"] is True
    memory_id = result["message_memory_id"]
    # Existing read-only inspector/MemoryService, not a parallel chat database.
    memories = http(server, "views/memories", headers=headers)[1]["data"]["memories"]
    assert any(m["memory_id"] == memory_id for m in memories)
    withdrawn = http(server, "commands", "POST", {
        **base(service, "withdraw-retained"), "operation": "WITHDRAW", "target_id": memory_id,
    }, headers)[1]
    assert withdrawn["data"]["state"] == "VERIFIED"
    after = http(server, "views/memories", headers=headers)[1]["data"]["memories"]
    assert all(m["memory_id"] != memory_id for m in after)
