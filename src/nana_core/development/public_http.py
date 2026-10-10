"""One bounded public GET/HEAD through the inherited proxy, without redirects.

DNS validation is not a claim about the proxy's origin peer. The proxy receives
a numeric destination; TLS still validates the approved hostname. No direct or
hostname-based fallback is permitted when that proxy operation fails.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import http.client
import ipaddress
import json
import os
from pathlib import Path
import queue
import socket
import ssl
import threading
import time
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from ..contracts import CoreError, DTO


class WebSpec(DTO):
    url: str = Field(min_length=1, max_length=2048)
    method: Literal["GET", "HEAD"] = "GET"
    timeout_seconds: int = Field(default=10, ge=1, le=15)
    max_bytes: int = Field(default=65536, ge=1, le=65536)
    provenance: Literal["public_read", "controlled_protocol"] = "public_read"

    @model_validator(mode="after")
    def url_boundary(self):
        try:
            url = urlsplit(self.url)
            if (url.scheme not in {"http", "https"} or not url.hostname
                or url.username is not None or url.password is not None
                or "?" in self.url or "#" in self.url
                or any(ord(c) <= 32 or ord(c) >= 127 for c in self.url)
                or url.port not in {None, 443 if url.scheme == "https" else 80}):
                raise ValueError()
        except ValueError:
            raise ValueError("public standard-port URL required") from None
        return self


@dataclass(frozen=True)
class FetchResponse:
    approved_url: str
    method: str
    status: int
    headers: dict[str, str]
    body: bytes
    fetched_at_us: int
    evidence: dict


class PublicHTTPTransport:
    is_public_transport = True

    def __init__(self, resolver=None, policy_path="/etc/codex/network-policy.json"):
        self._resolver = resolver or socket.getaddrinfo
        self._policy_path = Path(policy_path)
        self.http_requests = 0
        self.proxy_connections = 0

    def _addresses(self, host, port, timeout):
        result = queue.Queue(maxsize=1)
        def resolve():
            try:
                result.put((True, self._resolver(host, port, type=socket.SOCK_STREAM)))
            except Exception:
                result.put((False, None))
        # getaddrinfo has no timeout argument. A timed-out daemon may finish DNS
        # later, but it never opens HTTP and cannot extend this fetch's deadline.
        threading.Thread(target=resolve, daemon=True).start()
        try:
            try:
                succeeded, records = result.get(timeout=timeout)
            except queue.Empty:
                raise CoreError("WEB_TIMEOUT") from None
            if not succeeded:
                raise CoreError("WEB_DNS_FAILED")
            if len(records) > 16:
                raise CoreError("WEB_DNS_ADDRESS_LIMIT")
            addresses = {ipaddress.ip_address(record[4][0]) for record in records}
            if not addresses or any(not ip.is_global or ip.is_multicast or ip.is_reserved
                or getattr(ip, "ipv4_mapped", None) is not None for ip in addresses):
                raise CoreError("WEB_DESTINATION_DENIED")
            return frozenset(str(ip) for ip in addresses)
        except CoreError:
            raise
        except Exception:
            raise CoreError("WEB_DNS_FAILED") from None

    def _proxy(self, scheme):
        try:
            policy = json.loads(self._policy_path.read_text())
            if policy.get("version") != 1 or policy.get("http_network_policy", {}).get("type") != "unrestricted":
                raise CoreError("WEB_PROXY_POLICY_UNSUPPORTED")
            raw = os.environ.get(scheme.upper() + "_PROXY") or os.environ.get(scheme + "_proxy")
            if not raw:
                raise CoreError("WEB_PROXY_REQUIRED")
            approved_proxy = policy.get("http_proxy")
            if not isinstance(approved_proxy, str) or not approved_proxy:
                raise CoreError("WEB_PROXY_POLICY_UNSUPPORTED")
            if raw != approved_proxy:
                raise CoreError("WEB_PROXY_CONFIGURATION_REJECTED")
            proxy = urlsplit(raw)
            if (proxy.scheme != "http" or not proxy.hostname or proxy.username is not None
                or proxy.password is not None or proxy.path not in {"", "/"}
                or proxy.query or proxy.fragment or any(ord(c) <= 32 for c in raw)):
                raise CoreError("WEB_PROXY_CONFIGURATION_REJECTED")
            return proxy.hostname, proxy.port or 80
        except CoreError:
            raise
        except Exception:
            raise CoreError("WEB_PROXY_CONFIGURATION_REJECTED") from None

    @staticmethod
    def _connection(host, port, timeout):
        return http.client.HTTPConnection(host, port, timeout=timeout)

    @staticmethod
    def _tls_context():
        return ssl.create_default_context()

    def fetch(self, spec):
        try:
            spec = WebSpec.model_validate(spec.model_dump() if isinstance(spec, WebSpec) else spec)
        except Exception:
            raise CoreError("WEB_SPEC_REJECTED") from None
        deadline = time.monotonic() + spec.timeout_seconds

        def remaining():
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                raise CoreError("WEB_TIMEOUT")
            return timeout

        url = urlsplit(spec.url)
        port = 443 if url.scheme == "https" else 80
        proxy_host, proxy_port = self._proxy(url.scheme)
        first = self._addresses(url.hostname, port, remaining())
        remaining()
        second = self._addresses(url.hostname, port, remaining())
        remaining()
        if first != second:
            raise CoreError("WEB_DNS_CHANGED")
        selected = sorted(first)[0]
        numeric_host = f"[{selected}]" if ":" in selected else selected
        host_header = f"[{url.hostname}]" if ":" in url.hostname else url.hostname
        path = url.path or "/"
        connection = None
        response = None
        deadline_socket = None
        expired = threading.Event()
        watchdog = None

        def abort_blocking_io():
            expired.set()
            # A duplicate refers to this established TCP connection even while
            # SSL wraps/detaches the original socket or response owns its stream.
            sockets = (deadline_socket, connection.sock if connection is not None else None)
            for sock in sockets:
                if sock is not None:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except Exception:
                        pass
                    try:
                        sock.close()
                    except Exception:
                        pass
        try:
            connection = self._connection(proxy_host, proxy_port, remaining())
            watchdog = threading.Timer(remaining(), abort_blocking_io)
            watchdog.daemon = True
            watchdog.start()
            if url.scheme == "https":
                connection.set_tunnel(selected, port)
            self.proxy_connections += 1
            connection.connect()
            remaining()
            deadline_socket = connection.sock.dup()
            if url.scheme == "https":
                connection.sock.settimeout(remaining())
                connection.sock = self._tls_context().wrap_socket(connection.sock, server_hostname=url.hostname)
            connection.sock.settimeout(remaining())
            target = path if url.scheme == "https" else f"http://{numeric_host}{path}"
            self.http_requests += 1  # Attempt, not proof that the origin received it.
            connection.request(spec.method, target, headers={"Host": host_header,
                "Accept-Encoding": "identity", "Connection": "close"})
            connection.sock.settimeout(remaining())
            stream_socket = connection.sock
            response = connection.getresponse()
            remaining()
            if 300 <= response.status < 400:
                raise CoreError("WEB_REDIRECT_DENIED")
            if not 200 <= response.status < 300:
                raise CoreError("WEB_STATUS_REJECTED")
            if (response.getheader("Content-Encoding") or "identity").strip().lower() != "identity":
                raise CoreError("WEB_COMPRESSION_DENIED")
            length = response.getheader("Content-Length")
            if length is not None and (not length.isdecimal() or
                (spec.method == "GET" and int(length) > spec.max_bytes)):
                raise CoreError("WEB_BODY_LIMIT")
            body = bytearray()
            if spec.method == "GET":
                while True:
                    # The response may own the socket after Connection: close.
                    stream_socket.settimeout(remaining())
                    chunk = response.read1(min(8192, spec.max_bytes + 1 - len(body)))
                    remaining()
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(body) > spec.max_bytes:
                        raise CoreError("WEB_BODY_LIMIT")
            if length is not None and spec.method == "GET" and len(body) != int(length):
                raise CoreError("WEB_BODY_INCOMPLETE")
            headers = {key.lower(): value for key in ("Content-Type", "Date", "Last-Modified", "ETag")
                       if (value := response.getheader(key)) is not None}
            remaining()
            return FetchResponse(spec.url, spec.method, response.status, headers, bytes(body),
                int(datetime.now(timezone.utc).timestamp() * 1_000_000), {
                    "transport": "inherited_http_proxy_numeric_destination",
                    "selected_public_ip": selected, "validated_dns_addresses": sorted(first),
                    "dns_snapshots_equal": True, "origin_peer_verified": False,
                    "tls_hostname_verified": url.scheme == "https", "redirects_followed": 0,
                    "public_fetch": True, "proxy_numeric_target": True,
                    "TLS_hostname_checked": url.scheme == "https", "DNS_checks": 2,
                    "request_attempts": 1, "body_coverage": "HEAD_NO_BODY" if spec.method == "HEAD" else "FULL",
                    "provenance": spec.provenance})
        except CoreError:
            raise
        except (TimeoutError, socket.timeout):
            raise CoreError("WEB_TIMEOUT") from None
        except Exception:
            if expired.is_set() or time.monotonic() >= deadline:
                raise CoreError("WEB_TIMEOUT") from None
            raise CoreError("WEB_PROXY_REQUEST_FAILED") from None
        finally:
            if watchdog is not None:
                watchdog.cancel()
            if deadline_socket is not None:
                deadline_socket.close()
            if response is not None:
                response.close()
            if connection is not None:
                connection.close()
