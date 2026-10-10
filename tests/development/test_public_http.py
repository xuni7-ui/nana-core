"""Protocol fixtures only: these tests never claim an actual public fetch."""
import json
import socket
import threading
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from nana_core.contracts import CoreError
from nana_core.development.public_http import PublicHTTPTransport, WebSpec
import nana_core.development.public_http as public_http


def records(*addresses):
    return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM,
             6, "", (ip, 443)) for ip in addresses]


class FakeSocket:
    def __init__(self, interrupted=None):
        self.timeouts = []
        self.interrupted = interrupted or threading.Event()

    def settimeout(self, value):
        self.timeouts.append(value)

    def dup(self):
        return FakeSocket(self.interrupted)

    def shutdown(self, how):
        self.interrupted.set()

    def close(self):
        pass


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b"public synthetic text"):
        self.status = status
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.body, self.offset, self.closed = body, 0, False
        self.reads = 0

    def getheader(self, key):
        return self.headers.get(key.lower())

    def read1(self, size):
        self.reads += 1
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, response):
        self.response = response
        self.sock = FakeSocket()
        self.tunnel, self.requests = None, []
        self.connected, self.closed = False, False

    def set_tunnel(self, host, port):
        self.tunnel = (host, port)

    def connect(self):
        self.connected = True

    def request(self, method, target, headers):
        self.requests.append((method, target, headers))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


@pytest.fixture
def environment(tmp_path, monkeypatch):
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"version": 1, "http_network_policy": {"type": "unrestricted"},
                                  "http_proxy": "http://development-proxy.invalid:8080"}))
    for name in ("HTTP_PROXY", "HTTPS_PROXY"):
        monkeypatch.setenv(name, "http://development-proxy.invalid:8080")
    for name in ("http_proxy", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    response = FakeResponse(headers={"Content-Type": "text/plain", "Set-Cookie": "never persisted",
                                     "ETag": "synthetic-tag"})
    connection = FakeConnection(response)
    transport = PublicHTTPTransport(resolver=lambda *args, **kwargs: records("93.184.216.34"), policy_path=policy)
    opened, tls_names = [], []
    def open_connection(host, port, timeout):
        opened.append((host, port, timeout))
        return connection
    class Context:
        def wrap_socket(self, sock, server_hostname):
            tls_names.append(server_hostname)
            return sock
    monkeypatch.setattr(transport, "_connection", open_connection)
    monkeypatch.setattr(transport, "_tls_context", lambda: Context())
    return transport, connection, response, opened, tls_names, policy


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/a", "https://u:p@example.com/",
    "https://example.com/?x=1", "https://example.com/?", "https://example.com/#x",
    "https://example.com:8443/", "http://example.com:443/", "https://example.com/a\r\nHeader:x"])
def test_spec_rejects_non_read_url_boundaries(url):
    with pytest.raises(ValidationError):
        WebSpec(url=url)


@pytest.mark.parametrize("kwargs", [{"method": "POST"}, {"timeout_seconds": 16}, {"max_bytes": 65537}])
def test_spec_bounded_method_time_size(kwargs):
    with pytest.raises(ValidationError):
        WebSpec(url="https://example.com/", **kwargs)


@pytest.mark.parametrize("address", ["127.0.0.1", "10.1.1.1", "169.254.169.254", "::1", "fc00::1",
    "::ffff:93.184.216.34", "224.0.0.1", "0.0.0.0"])
def test_non_public_address_never_reaches_proxy(environment, address):
    transport, connection, _, opened, _, _ = environment
    transport._resolver = lambda *args, **kwargs: records(address)
    with pytest.raises(CoreError, match="^WEB_DESTINATION_DENIED$"):
        transport.fetch(WebSpec(url="https://example.com/"))
    assert opened == [] and transport.http_requests == 0 and not connection.connected


def test_mixed_dns_and_changed_dns_rejected(environment):
    transport, _, _, opened, _, _ = environment
    transport._resolver = lambda *args, **kwargs: records("93.184.216.34", "192.168.1.1")
    with pytest.raises(CoreError, match="WEB_DESTINATION_DENIED"):
        transport.fetch(WebSpec(url="https://example.com/"))
    sequence = iter([records("93.184.216.34"), records("8.8.8.8")])
    transport._resolver = lambda *args, **kwargs: next(sequence)
    with pytest.raises(CoreError, match="WEB_DNS_CHANGED"):
        transport.fetch(WebSpec(url="https://example.com/"))
    assert opened == [] and transport.proxy_connections == 0


def test_https_numeric_connect_original_hostname_sni_and_safe_headers(environment):
    transport, connection, response, opened, names, _ = environment
    spec = WebSpec(url="https://example.com/path")
    result = transport.fetch(spec)
    assert opened[0][:2] == ("development-proxy.invalid", 8080)
    assert connection.tunnel == ("93.184.216.34", 443) and names == ["example.com"]
    assert connection.requests == [("GET", "/path", {"Host": "example.com", "Accept-Encoding": "identity", "Connection": "close"})]
    assert result.approved_url == spec.url and result.body == response.body
    assert result.headers == {"content-type": "text/plain", "etag": "synthetic-tag"}
    assert result.fetched_at_us > 0 and result.evidence["DNS_checks"] == 2
    assert result.evidence["origin_peer_verified"] is False
    assert result.evidence["TLS_hostname_checked"] is True
    assert transport.http_requests == transport.proxy_connections == 1
    assert connection.closed and response.closed


def test_http_numeric_absolute_target_no_tls_and_no_proxy_bypass(environment, monkeypatch):
    transport, connection, _, _, names, _ = environment
    monkeypatch.setenv("NO_PROXY", "*")
    result = transport.fetch(WebSpec(url="http://example.com/page"))
    assert connection.tunnel is None and names == []
    assert connection.requests[0][:2] == ("GET", "http://93.184.216.34/page")
    assert connection.requests[0][2]["Host"] == "example.com"
    assert result.evidence["TLS_hostname_checked"] is False


def test_head_does_not_read_body_even_with_large_resource_length(environment):
    transport, connection, response, _, _, _ = environment
    response.headers["content-length"] = "999999"
    result = transport.fetch(WebSpec(url="https://example.com/", method="HEAD", max_bytes=1))
    assert result.body == b"" and response.reads == 0
    assert connection.requests[0][0] == "HEAD" and result.evidence["body_coverage"] == "HEAD_NO_BODY"


@pytest.mark.parametrize("status,headers,body,code", [
    (302, {"Location": "http://127.0.0.1/private"}, b"", "WEB_REDIRECT_DENIED"),
    (404, {}, b"private error detail", "WEB_STATUS_REJECTED"),
    (200, {"Content-Encoding": "gzip"}, b"compressed", "WEB_COMPRESSION_DENIED"),
    (200, {"Content-Length": "100"}, b"x", "WEB_BODY_LIMIT"),
    (200, {}, b"123456", "WEB_BODY_LIMIT"),
    (200, {"Content-Length": "5"}, b"x", "WEB_BODY_INCOMPLETE"),
])
def test_redirect_encoding_size_status_and_incomplete_fail_closed(environment, status, headers, body, code):
    transport, connection, response, _, _, _ = environment
    response.status, response.headers, response.body = status, {k.lower(): v for k, v in headers.items()}, body
    with pytest.raises(CoreError) as exc:
        transport.fetch(WebSpec(url="https://example.com/", max_bytes=5))
    assert str(exc.value) == code and len(connection.requests) == 1
    assert transport.http_requests == 1 and response.closed and connection.closed


@pytest.mark.parametrize("case,code", [("restricted", "WEB_PROXY_POLICY_UNSUPPORTED"),
    ("missing", "WEB_PROXY_REQUIRED"), ("proxy_auth", "WEB_PROXY_CONFIGURATION_REJECTED")])
def test_no_direct_fallback_or_credential_proxy(environment, monkeypatch, case, code):
    transport, _, _, opened, _, policy = environment
    if case == "restricted":
        policy.write_text(json.dumps({"version": 1, "http_network_policy": {"type": "restricted"}}))
    elif case == "missing":
        monkeypatch.delenv("HTTPS_PROXY")
    else:
        monkeypatch.setenv("HTTPS_PROXY", "http://user:synthetic-password@proxy.invalid:8080")
    with pytest.raises(CoreError, match="^" + code + "$"):
        transport.fetch(WebSpec(url="https://example.com/"))
    assert opened == [] and transport.http_requests == 0


def test_proxy_denial_never_falls_back_to_domain_or_direct(environment, monkeypatch):
    transport, connection, _, _, _, _ = environment
    monkeypatch.setattr(connection, "connect", lambda: (_ for _ in ()).throw(OSError("unsafe proxy details")))
    with pytest.raises(CoreError) as exc:
        transport.fetch(WebSpec(url="https://example.com/"))
    assert str(exc.value) == "WEB_PROXY_REQUEST_FAILED"
    assert connection.tunnel == ("93.184.216.34", 443)
    assert transport.proxy_connections == 1 and transport.http_requests == 0 and connection.closed


def test_dns_timeout_does_not_start_proxy(environment):
    transport, _, _, opened, _, _ = environment
    release = threading.Event()
    transport._resolver = lambda *args, **kwargs: (release.wait(), records("93.184.216.34"))[1]
    try:
        with pytest.raises(CoreError, match="^WEB_TIMEOUT$"):
            transport._addresses("example.com", 443, .01)
    finally:
        release.set()
    assert opened == [] and transport.http_requests == 0


def test_invalid_constructed_spec_is_revalidated_without_value_leak(environment):
    transport, _, _, opened, _, _ = environment
    spec = WebSpec.model_construct(url="https://user:synthetic-secret@example.com/", method="DELETE")
    with pytest.raises(CoreError) as exc:
        transport.fetch(spec)
    assert str(exc.value) == "WEB_SPEC_REJECTED" and opened == []


def test_total_deadline_rejects_slow_body_without_another_request(environment, monkeypatch):
    transport, connection, response, _, _, _ = environment
    clock = [100.0]
    monkeypatch.setattr(public_http, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    def slow_chunk(size):
        clock[0] += 2.0
        return b"x"
    monkeypatch.setattr(response, "read1", slow_chunk)
    with pytest.raises(CoreError, match="^WEB_TIMEOUT$"):
        transport.fetch(WebSpec(url="https://example.com/", timeout_seconds=1))
    assert transport.http_requests == 1 and len(connection.requests) == 1
    assert response.closed and connection.closed


def test_hard_deadline_interrupts_blocked_headers(environment, monkeypatch):
    transport, connection, _, _, _, _ = environment
    blocked = threading.Event()
    def blocked_headers():
        blocked.set()
        assert connection.sock.interrupted.wait(3), "hard deadline failed to interrupt blocking headers"
        raise OSError("synthetic interrupted header stream")
    monkeypatch.setattr(connection, "getresponse", blocked_headers)
    with pytest.raises(CoreError, match="^WEB_TIMEOUT$"):
        transport.fetch(WebSpec(url="https://example.com/", timeout_seconds=1))
    assert blocked.is_set() and connection.closed and transport.http_requests == 1


@pytest.mark.parametrize("case", ["missing_policy_proxy", "unapproved_env_proxy"])
def test_proxy_must_match_trusted_policy(environment, monkeypatch, case):
    transport, _, _, opened, _, policy = environment
    if case == "missing_policy_proxy":
        policy.write_text(json.dumps({"version": 1, "http_network_policy": {"type": "unrestricted"}}))
    else:
        monkeypatch.setenv("HTTPS_PROXY", "http://169.254.169.254:80")
    with pytest.raises(CoreError):
        transport.fetch(WebSpec(url="https://example.com/"))
    assert opened == [] and transport.proxy_connections == 0


def test_dns_address_set_is_bounded(environment):
    transport, _, _, opened, _, _ = environment
    transport._resolver = lambda *args, **kwargs: records(*(f"8.8.8.{n}" for n in range(1, 18)))
    with pytest.raises(CoreError, match="^WEB_DNS_ADDRESS_LIMIT$"):
        transport.fetch(WebSpec(url="https://example.com/"))
    assert opened == [] and transport.http_requests == 0
