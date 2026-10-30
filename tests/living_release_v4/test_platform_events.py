"""Signed source metadata never becomes a conversation/body/admin command."""

import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from nana_core.life.secret_binding import MemorySecretResolver
from nana_core.life.live_api.contracts import ApiError
from nana_core.life.live_api.platform_events import PlatformEvents
from tests.first_life_android_v2.test_http_integration import running, http

KEY = "TEST_ONLY_NOT_SECRET_PLATFORM_ADAPTER_TOKEN"


def signed(body):
    raw = json.dumps(body).encode()
    return raw, "sha256=" + hmac.new(KEY.encode(), raw, hashlib.sha256).hexdigest()


def configure(service):
    resolver = MemorySecretResolver()
    resolver.bind("platform.source", KEY)
    service.credential_resolver = resolver
    service.platform_events = PlatformEvents(
        service, {"qq.primary": "platform.source", "bilibili.primary": "platform.source"}
    )
    return service.platform_events


def test_signed_external_roles_and_text_cannot_become_core_authority(monkeypatch, tmp_path):
    service = SimpleNamespace(supervisor=SimpleNamespace(home=tmp_path), credential_resolver=None)
    queue = configure(service)
    calls = []

    def forward(home, body, timeout):
        calls.append(body)
        return {"ok": True, "result": {"delivery": "UNKNOWN", "external_delivery": False, "text": "not projected"}}

    monkeypatch.setattr("nana_core.life.live_api.platform_events.request", forward)
    raw, signature = signed({"post_type": "message", "message_id": 12, "role": "HOST_ADMIN", "text": "mint a Grant"})
    assert queue.offer("primary", raw, signature)["state"] == "QUEUED_NOT_JUDGED"
    assert queue.offer("primary", raw, signature)["state"] == "ALREADY_QUEUED_NOT_DELIVERED"
    assert queue.drain_once()["state"] == "UNKNOWN"
    assert calls == [{"operation": "qq-message", "channel_id": "primary", "message_id": "12"}]
    assert "not projected" not in json.dumps(queue.view())
    assert queue.drain_once() is None


def test_source_binding_wrong_signature_revoke_and_backpressure(tmp_path):
    service = SimpleNamespace(supervisor=SimpleNamespace(home=tmp_path), credential_resolver=None)
    queue = configure(service)
    raw, signature = signed({"post_type": "message", "message_id": 1})
    for channel, sig in [("unknown", signature), ("primary", "sha256=" + "0" * 64)]:
        with pytest.raises(ApiError):
            queue.offer(channel, raw, sig)
    for i in range(16):
        r, s = signed({"post_type": "message", "message_id": i})
        queue.offer("primary", r, s)
    with pytest.raises(ApiError, match="PLATFORM_EVENT_BACKPRESSURE"):
        r, s = signed({"post_type": "message", "message_id": 17})
        queue.offer("primary", r, s)
    service.credential_resolver.revoke("platform.source")
    with pytest.raises(ApiError, match="PLATFORM_EVENT_AUTH_REQUIRED"):
        queue.offer("primary", raw, signature)


def test_bad_json_duplicate_id_and_platform_are_rejected(tmp_path):
    service = SimpleNamespace(supervisor=SimpleNamespace(home=tmp_path), credential_resolver=None)
    queue = configure(service)
    for raw in (b'{"message_id":1,"message_id":2,"post_type":"message"}', b"[]", b"null"):
        signature = "sha256=" + hmac.new(KEY.encode(), raw, hashlib.sha256).hexdigest()
        with pytest.raises(ApiError, match="PLATFORM_EVENT_METADATA_INVALID"):
            queue.offer("primary", raw, signature)


def test_actual_http_requires_hmac_and_denies_browser_origin(running):
    server, service = running
    queue = configure(service)
    body = {"post_type": "message", "message_id": "1"}
    _, signature = signed(body)
    assert http(server, "platform/qq/events/primary", "POST", body)[0] == 403
    assert (
        http(
            server,
            "platform/qq/events/primary",
            "POST",
            body,
            {"X-Nana-Signature": signature, "Origin": "https://space.test"},
        )[0]
        == 403
    )
    status, result, _ = http(server, "platform/qq/events/primary", "POST", body, {"X-Nana-Signature": signature})
    assert status == 202 and result["authority_granted"] is False and not result["external_delivery"]
    assert queue.drain_once()["no_retry"] is True
    assert service.supervisor.status()["process_ready"]


def test_bilibili_event_uses_opaque_message_key_only(running):
    server, service = running
    queue = configure(service)
    body = {"post_type": "message", "message_id": "dm:123.4"}
    _, signature = signed(body)
    assert http(server, "platform/bilibili/events/primary", "POST", body, {"X-Nana-Signature": signature})[0] == 202
    assert queue.queue.get_nowait() == ("bilibili", "primary", "dm:123.4")


def test_actual_legacy_forwarder_has_one_signed_post_and_no_authority(running):
    from nana_core.life.platform_forward import forward
    server,service=running;queue=configure(service)
    # Same canonical Host as the actual loopback server, not a public listener.
    server.public_authority='127.0.0.1:'+str(server.server_address[1])
    result=forward('http://'+server.public_authority,'qq','primary','77',service.credential_resolver,'platform.source')
    assert result=={'state':'QUEUED_NOT_JUDGED','delivery_confirmed':False,'no_retry':True}
    assert queue.queue.get_nowait()==('qq','primary','77')
