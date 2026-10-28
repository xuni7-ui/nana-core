import re
import secrets
import pytest
from tools.nana_first_life_unified_release.issue_pairing import issue
from tests.first_life_android_v2.test_http_integration import running as running, http, login


def test_official_issuer_and_original_pairing_session_work_together(running):  # noqa: F811
    server, service = running
    status, anonymous, _ = http(server, "bootstrap", headers={"Origin": "https://space.test"})
    assert status == 401 and anonymous == {"contract": "nana-space-live/v2", "code": "SESSION_REQUIRED"}
    headers = login(server, service)

    def call(path, method, body):
        status, row, _ = http(server, path, method, body, headers)
        if status != 200:
            raise ValueError("OFFICIAL_ISSUE_FAILED")
        return row

    code = issue(call, service.binding.subject_id, "这台安卓手机")
    assert len(code) == 43 and re.fullmatch(r"[A-Za-z0-9_-]{43}", code) is not None
    # Only ephemeral synthetic material, never a user's code or a persisted fixture.
    invalid = secrets.token_urlsafe(14)
    assert len(invalid) == 19
    assert (
        http(
            server,
            "device/pairing",
            "POST",
            {"code": invalid, "subject_id": service.binding.subject_id, "device_name": "这台安卓手机"},
        )[0]
        == 400
    )
    status, paired, _ = http(
        server,
        "device/pairing",
        "POST",
        {"code": code, "subject_id": service.binding.subject_id, "device_name": "这台安卓手机"},
    )
    assert status == 200
    assert (
        http(
            server,
            "device/pairing",
            "POST",
            {"code": code, "subject_id": service.binding.subject_id, "device_name": "这台安卓手机"},
        )[0]
        == 403
    )
    status, session, _ = http(
        server, "session/native", "POST", {k: paired[k] for k in ("device_id", "refresh_token", "subject_id")}
    )
    assert status == 200
    native = {"Authorization": "Bearer " + session["access_token"]}
    assert http(server, "bootstrap", headers=native)[0] == 200
    assert http(server, "devices/" + paired["device_id"], "DELETE", headers=headers)[0] == 200
    assert http(server, "bootstrap", headers=native)[0] == 401


def test_unknown_offer_is_not_replayed_or_locally_padded():
    attempts = []

    def ambiguous(*args):
        attempts.append(True)
        raise TimeoutError()

    with pytest.raises(TimeoutError):
        issue(ambiguous, "subject", "device")
    assert len(attempts) == 1
    with pytest.raises(ValueError, match="BFF_GENERATOR_PROTOCOL_MISMATCH"):
        issue(
            lambda *args: {
                "subject_id": "subject",
                "data": {"pairing_code": secrets.token_urlsafe(14), "one_time": True},
            },
            "subject",
            "device",
        )
