"""Native-only host vault binding, no account traffic or secret persistence."""

import pytest
from nana_core.contracts import CoreError
from nana_core.life.config import load_config, update_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.platform_runtime import QQChannelBinding
from nana_core.life.provider_vault import DurableSecretResolver
from nana_core.life.live_api.platform_credentials import PlatformCredentialRequest, normalized
from tests.first_life_android_v2.test_http_integration import running, http, login, base

VALUE = "TEST_ONLY_NOT_SECRET_PLATFORM_ACCOUNT_TOKEN"


def test_cookie_whitespace_is_canonicalized_without_relaxing_header_or_dto_guards():
    assert (
        normalized("SESSDATA=TEST_ONLY_NOT_SECRET; bili_jct=TEST_ONLY_NOT_SECRET; ", "COOKIE")
        == "SESSDATA=TEST_ONLY_NOT_SECRET;bili_jct=TEST_ONLY_NOT_SECRET"
    )
    for text in ("SESSDATA=a\r\nInjected=b", "SESSDATA=a b", "missing-equals"):
        with pytest.raises(CoreError):
            normalized(text, "COOKIE")
    with pytest.raises(CoreError):
        normalized("not valid csrf", "CSRF")


def native_headers(server, service, headers):
    offer = {"device_name": "TEST_ONLY_NOT_SECRET_phone", "roles": ["READER", "CONVERSATION", "HOST_ADMIN"]}
    code = http(server, "devices/offers", "POST", offer, headers)[1]["data"]["pairing_code"]
    paired = http(
        server,
        "device/pairing",
        "POST",
        {"code": code, "subject_id": service.binding.subject_id, "device_name": offer["device_name"]},
    )[1]
    session = http(
        server,
        "session/native",
        "POST",
        {
            "device_id": paired["device_id"],
            "refresh_token": paired["refresh_token"],
            "subject_id": service.binding.subject_id,
        },
    )[1]
    return {"Authorization": "Bearer " + session["access_token"], "X-Nana-Client": "ANDROID"}


def test_actual_native_bind_revoke_shared_channels_and_no_secret_in_subject(running, tmp_path):
    from nana_core.life.control import request

    server, service = running
    web = login(server, service)
    native = native_headers(server, service, web)
    service.allow_provider_configuration = True
    service.credential_resolver = DurableSecretResolver(tmp_path / "vault", initialize=True)
    home = service.supervisor.home
    cfg = load_config(home)
    b = SurfaceBinding(
        binding_id="qq.account",
        platform="qq.onebot",
        surface="chat.direct",
        adapter="qq.onebot",
        mode="PLATFORM_ADAPTER_NO_SEND",
    )
    channels = tuple(
        QQChannelBinding(
            channel_id=name,
            binding_id=b.binding_id,
            endpoint="http://127.0.0.1:10042",
            account_id="42",
            sender_id="43",
            target_id="43",
            credential_ref="platform.account",
            enabled=True,
            read_authorized=True,
        )
        for name in ("primary", "other")
    )
    config = cfg.model_copy(
        update={"revision": cfg.revision + 1, "surface_bindings": (*cfg.surface_bindings, b), "qq_channels": channels}
    )
    update_config(home, config, expected_revision=cfg.revision)
    assert request(home, {"operation": "platform-refresh"})["ok"]
    body = {
        **base(service, "platform-secret"),
        "platform": "qq",
        "channel_id": "primary",
        "slot": "AUTH",
        "action": "BIND",
        "configuration_revision": config.revision,
        "expected_vault_revision": 0,
        "credential": VALUE,
    }
    dto = PlatformCredentialRequest.model_validate(body)
    assert VALUE not in repr(dto) and VALUE not in dto.model_dump_json()
    assert http(server, "platform/credential", "POST", body, web)[0] == 403
    code, result, _ = http(server, "platform/credential", "POST", body, native)
    assert code == 200 and result["data"]["state"] == "BOUND_IN_HOST_VAULT", result
    assert VALUE not in str(result) and result["data"]["network_calls"] == 0
    assert service.credential_resolver.available("platform.account")
    assert http(server, "platform/credential", "POST", body, native)[0] == 409
    revoke = {k: v for k, v in body.items() if k != "credential"}
    revoke.update(action="REVOKE", expected_vault_revision=1)
    assert (
        http(server, "platform/credential", "POST", revoke, native)[1]["data"]["state"] == "REVOKED_CHANNELS_DISABLED"
    )
    assert not any(c.enabled for c in load_config(home).qq_channels)
    assert not service.credential_resolver.available("platform.account")
    for path in (home / "subject").glob("*"):
        if path.is_file():
            assert VALUE.encode() not in path.read_bytes()
    for path in (tmp_path / "vault").iterdir():
        if path.is_file():
            assert VALUE.encode() not in path.read_bytes()
    service.credential_resolver.clear()
