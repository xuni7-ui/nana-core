"""Credential lifecycle and privilege boundaries, no network or real secret."""

import json
import pytest
from nana_core.life.live_api.auth import AuthService
from nana_core.life.live_api.contracts import ApiError, Login, PairOffer, Role, MessageRequest

PASSWORD = "TEST_ONLY_NOT_SECRET_operator"
ALL = tuple(Role)


def test_web_csrf_native_pair_revoke_and_restart(tmp_path):
    auth = AuthService(tmp_path / "host/auth.json", password=PASSWORD, roles=ALL)
    web, csrf = auth.login(PASSWORD)
    admin = auth.authorize(web, "WEB", csrf=csrf, mutating=True)
    with pytest.raises(ApiError, match="CSRF_DENIED"):
        auth.authorize(web, "WEB", csrf="invalid", mutating=True)
    with pytest.raises(ApiError, match="SESSION_REVOKED"):
        auth.authorize(web, "NATIVE")
    code = auth.offer(admin, PairOffer(device_name="Owned synthetic Android"))
    device, refresh = auth.pair(code, "Owned synthetic Android")
    with pytest.raises(ApiError, match="PAIRING_DENIED"):
        auth.pair(code, "Owned synthetic Android")
    access = auth.native_session(device, refresh)
    principal = auth.authorize(access, "NATIVE", mutating=True)
    with pytest.raises(ApiError, match="SCOPE_DENIED"):
        principal.require(Role.HOST_ADMIN)
    saved = (tmp_path / "host/auth.json").read_text()
    for secret in [PASSWORD, web, csrf, code, refresh, access]:
        assert secret not in saved
    assert not (tmp_path / "host/auth.json").stat().st_mode & 0o077
    reopened = AuthService(tmp_path / "host/auth.json", roles=ALL)
    with pytest.raises(ApiError, match="SESSION_REVOKED"):
        reopened.authorize(access, "NATIVE")
    new = reopened.native_session(device, refresh)
    assert reopened.authorize(new, "NATIVE").device_id == device
    op, guard = reopened.login(PASSWORD)
    admin2 = reopened.authorize(op, "WEB", csrf=guard, mutating=True)
    reopened.revoke(admin2, device)
    with pytest.raises(ApiError, match="SESSION_REVOKED"):
        reopened.authorize(new, "NATIVE")
    with pytest.raises(ApiError, match="SESSION_DENIED"):
        reopened.native_session(device, refresh)


def test_role_confirmation_and_rate_limit(tmp_path):
    auth = AuthService(tmp_path / "auth.json", password=PASSWORD, roles=(Role.READER,))
    web, csrf = auth.login(PASSWORD)
    reader = auth.authorize(web, "WEB")
    with pytest.raises(ApiError, match="SCOPE_DENIED"):
        auth.offer(reader, PairOffer(device_name="test", roles=(Role.HOST_ADMIN,)))
    admin_auth = AuthService(tmp_path / "other/auth.json", password=PASSWORD, roles=ALL)
    web, csrf = admin_auth.login(PASSWORD)
    admin = admin_auth.authorize(web, "WEB")
    confirmation = admin_auth.confirm(admin, "STOP", 1, None)
    with pytest.raises(ApiError, match="HOST_CONFIRMATION_REQUIRED"):
        admin_auth.consume_confirmation(admin, confirmation, "RESTART", 1, None)
    with pytest.raises(ApiError, match="HOST_CONFIRMATION_REQUIRED"):
        admin_auth.consume_confirmation(admin, confirmation, "STOP", 1, None)
    for _ in range(5):
        with pytest.raises(ApiError, match="SESSION_DENIED"):
            auth.login("TEST_ONLY_NOT_SECRET_wrong")
    with pytest.raises(ApiError, match="AUTH_RATE_LIMIT"):
        auth.login(PASSWORD)


def test_schema_extra_privacy_rejection_and_redaction():
    login = Login(password=PASSWORD, subject_id="owned-test")
    assert PASSWORD not in repr(login) and PASSWORD not in login.model_dump_json()
    request = dict(
        client_request_id="a",
        idempotency_key="a",
        expected_revision=0,
        run_generation="a" * 32,
        owner_epoch=1,
        text="Public synthetic project note",
    )
    for extra in [{"privacy_class": "SECRET"}, {"authority": "GRANT"}, {"caller_role": "HOST_ADMIN"}]:
        with pytest.raises(ValueError):
            MessageRequest.model_validate_json(json.dumps({**request, **extra}))


def test_corrupt_auth_never_silently_resets(tmp_path):
    path = tmp_path / "auth.json"
    AuthService(path, password=PASSWORD)
    path.write_text("{invalid json")
    with pytest.raises(ApiError, match="HOST_METADATA_CORRUPT"):
        AuthService(path, password=PASSWORD)
    assert path.read_text() == "{invalid json"


def test_openapi_consumer_can_resolve_every_schema_reference():
    import json
    from pathlib import Path

    doc = json.loads((Path(__file__).resolve().parents[2] / "contracts/nana-space-live-v2/openapi.json").read_text())

    def visit(value):
        if isinstance(value, dict):
            if "$ref" in value:
                target = doc
                for part in value["$ref"].removeprefix("#/").split("/"):
                    target = target[part]
                assert isinstance(target, (dict, bool))  # Empty JSON Schema is valid.
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(doc)
    assert "/api/nana-space/v2/session/native" in doc["paths"]
    assert doc["paths"]["/api/nana-space/v2/messages"]["post"]["requestBody"]["required"]
