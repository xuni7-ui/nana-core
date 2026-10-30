"""Loopback-only BFF, secure Web sessions and native-only credential exchanges.

TLS terminates at an explicitly configured trusted private HTTPS proxy. The Core
UDS is never exposed. No credential/body/access log and no arbitrary HTTP/SQL/exec
endpoint. Invalid input returns stable codes, never Pydantic input repr or paths.
"""

import http.cookies
import ipaddress
import json
import mimetypes
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from ...continuity.privacy import _json_object
from .contracts import (
    ApiError,
    Login,
    PairRequest,
    PairOffer,
    MessageRequest,
    CommandRequest,
    HostRequest,
    HostConfirmation,
    Page,
    Role,
)

PREFIX = "/api/nana-space/v2"
COOKIE = "__Host-nana_v2"
BODY_LIMIT = 32768


def https_origin(value):
    try:
        u = urllib.parse.urlsplit(value)
        if (
            u.scheme != "https"
            or not u.hostname
            or u.username is not None
            or u.password is not None
            or u.path not in ("", "/")
            or u.query
            or u.fragment
        ):
            raise ValueError()
        if any(c in value for c in ("\r", "\n", "\\")) or u.port is not None and not 1 <= u.port <= 65535:
            raise ValueError()
        return "https://" + (u.hostname.lower() if u.port in (None, 443) else u.netloc.lower())
    except ValueError:
        raise ApiError("EXPLICIT_HTTPS_ORIGIN_REQUIRED") from None


class ApiServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address, service, *, public_origin, web_root=None, tls_context=None):
        if not ipaddress.ip_address(address[0]).is_loopback:
            raise ApiError("LOOPBACK_LISTENER_REQUIRED")
        self.service = service
        self.public_origin = https_origin(public_origin)
        self.public_authority = urllib.parse.urlsplit(self.public_origin).netloc
        self.web_root = Path(web_root).resolve() if web_root else None
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)
        if tls_context is not None:
            self.socket = tls_context.wrap_socket(self.socket, server_side=True)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "NanaSpaceV2"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def handle(self):
        self.request.settimeout(30)
        try:
            super().handle()
        except (OSError, TimeoutError):
            pass

    def _headers(self, code, content_type, length, *, cookie=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        if code >= 400:
            self.close_connection = True
            self.send_header("Connection", "close")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'",
        )
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _json(self, code, value, cookie=None):
        raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
        self._headers(code, "application/json; charset=utf-8", len(raw), cookie=cookie)
        self.wfile.write(raw)

    def _body(self):
        if self.headers.get("Transfer-Encoding") is not None:
            raise ApiError("TRANSFER_ENCODING_DENIED", 400)
        lengths = self.headers.get_all("Content-Length") or []
        if len(lengths) != 1 or not lengths[0].isdigit():
            raise ApiError("CONTENT_LENGTH_REQUIRED", 411)
        length = int(lengths[0])
        if length > BODY_LIMIT:
            raise ApiError("REQUEST_TOO_LARGE", 413)
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            raise ApiError("JSON_REQUIRED", 415)
        try:
            raw = self.rfile.read(length)
            self._raw_request_body = raw
            if len(raw) != length:
                raise ValueError()
            value = json.loads(
                raw, object_pairs_hook=_json_object, parse_constant=lambda x: (_ for _ in ()).throw(ValueError())
            )
            if type(value) is not dict:
                raise ValueError()
            return value
        except (ValueError, UnicodeError):
            raise ApiError("INVALID_JSON", 400) from None

    def _model(self, cls, data):
        try:
            return cls.model_validate_json(json.dumps(data))
        except (ValueError, TypeError):
            raise ApiError("INVALID_REQUEST", 400) from None

    def _origin(self, *, required):
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.public_origin:
            raise ApiError("ORIGIN_DENIED", 403)
        if required and origin != self.server.public_origin:
            raise ApiError("ORIGIN_REQUIRED", 403)
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise ApiError("ORIGIN_DENIED", 403)

    def _token(self):
        header = self.headers.get("Authorization")
        if header is not None:
            if self.headers.get("Origin") is not None:
                raise ApiError("NATIVE_ORIGIN_DENIED", 403)
            if not header.startswith("Bearer "):
                raise ApiError("SESSION_REQUIRED", 401)
            return header[7:], "NATIVE"
        self._origin(required=self.command not in {"GET", "HEAD"})
        try:
            jar = http.cookies.SimpleCookie()
            jar.load(self.headers.get("Cookie", ""))
            return jar[COOKIE].value, "WEB"
        except (KeyError, ValueError):
            raise ApiError("SESSION_REQUIRED", 401) from None

    def _auth(self):
        token, kind = self._token()
        return self.server.service.auth.authorize(
            token, kind, csrf=self.headers.get("X-Nana-CSRF"), mutating=self.command not in {"GET", "HEAD"}
        )

    def _run(self):
        try:
            self._route()
        except ApiError as exc:
            self._json(exc.status, {"contract": "nana-space-live/v2", "code": exc.code})
        except (OSError, TimeoutError):
            self.close_connection = True
        except Exception:
            # No exception repr/local variables: inputs may contain credentials.
            self._json(503, {"contract": "nana-space-live/v2", "code": "SERVICE_UNAVAILABLE"})

    do_GET = _run
    do_POST = _run
    do_DELETE = _run
    do_OPTIONS = _run

    def _route(self):
        service = self.server.service
        for name in ("Authorization", "Cookie", "Origin", "X-Nana-CSRF", "Content-Type", "X-Nana-Signature"):
            if len(self.headers.get_all(name) or []) > 1:
                raise ApiError("AMBIGUOUS_HEADERS", 400)
        host = self.headers.get_all("Host") or []
        if len(host) != 1 or host[0].lower() != self.server.public_authority:
            raise ApiError("HOST_DENIED", 403)
        split = urllib.parse.urlsplit(self.path)
        if (
            split.scheme
            or split.netloc
            or split.fragment
            or "\\" in self.path
            or "%" in split.path
            or ".." in split.path.split("/")
        ):
            raise ApiError("PATH_DENIED", 400)
        if self.command == "OPTIONS":
            raise ApiError("CORS_NOT_ENABLED", 403)
        path = split.path
        try:
            query = (
                urllib.parse.parse_qs(split.query, keep_blank_values=True, strict_parsing=True) if split.query else {}
            )
        except ValueError:
            raise ApiError("QUERY_INVALID", 400) from None
        if any(len(v) != 1 for v in query.values()):
            raise ApiError("QUERY_INVALID")
        if path.startswith("/api/nana-space/v1"):
            raise ApiError("V1_DEVELOPMENT_GATEWAY_REQUIRED", 403)
        if not path.startswith(PREFIX + "/"):
            if self.command != "GET":
                raise ApiError("NOT_FOUND", 404)
            self._static(path, query)
            return
        route = path[len(PREFIX) + 1 :]
        if (route.startswith('platform/qq/events/') or route.startswith('platform/bilibili/events/')) and self.command=='POST':
            if self.headers.get('Origin') is not None:raise ApiError('PLATFORM_EVENT_ORIGIN_DENIED',403)
            platform=route.split('/')[1]
            channel=route.split('/events/',1)[1]
            self._body()
            result=service.platform_events.offer(channel,self._raw_request_body,self.headers.get('X-Nana-Signature'),platform=platform)
            self._json(202,{'contract':'nana-space-live/v2',**result})
            return
        allowed_query = {"cursor"} if route == "events" else set()
        if set(query) - allowed_query:
            raise ApiError("QUERY_INVALID")
        if route == "session" and self.command == "POST":
            self._origin(required=True)
            body = self._model(Login, self._body())
            if body.subject_id != service.binding.subject_id:
                raise ApiError("INVALID_IDENTITY", 403)
            token, csrf = service.auth.login(body.password)
            self._json(
                200,
                service.envelope({"authenticated": True, "csrf": csrf}),
                COOKIE + "=" + token + "; Path=/; Max-Age=600; HttpOnly; Secure; SameSite=Strict",
            )
            return
        if route == "device/pairing" and self.command == "POST":
            if self.headers.get("Origin") is not None:
                raise ApiError("NATIVE_ORIGIN_DENIED", 403)
            body = self._model(PairRequest, self._body())
            if body.subject_id != service.binding.subject_id:
                raise ApiError("INVALID_IDENTITY", 403)
            device, refresh = service.auth.pair(body.code, body.device_name)
            # Native-only exchange. The Native bridge MUST consume this privately
            # and returns only sanitized bootstrap/status to WebView JavaScript.
            self._json(
                200,
                {
                    "device_id": device,
                    "refresh_token": refresh,
                    "realm": service.binding.realm.value,
                    "subject_id": service.binding.subject_id,
                    "lineage_binding": service.binding.lineage_binding,
                    "contract": "nana-space-live/v2",
                },
            )
            return
        if route == "session/native" and self.command == "POST":
            if self.headers.get("Origin") is not None:
                raise ApiError("NATIVE_ORIGIN_DENIED", 403)
            body = self._body()
            if (
                set(body) != {"device_id", "refresh_token", "subject_id"}
                or body["subject_id"] != service.binding.subject_id
            ):
                raise ApiError("INVALID_REQUEST")
            if type(body["device_id"]) is not str or not re.fullmatch("[a-f0-9]{32}", body["device_id"]):
                raise ApiError("INVALID_REQUEST")
            token = service.auth.native_session(body["device_id"], body["refresh_token"])
            self._json(200, {"access_token": token, "expires_in": 600, "contract": "nana-space-live/v2"})
            return
        principal = self._auth()
        if route == "session" and self.command == "DELETE":
            token, kind = self._token()
            if kind == "NATIVE":
                service.auth.revoke_self(principal)
            service.auth.logout(token)
            self._json(
                200,
                service.envelope({"logged_out": True}),
                COOKIE + "=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict",
            )
            return
        if self.command == "GET":
            if route == "bootstrap":
                value = service.bootstrap(principal)
                token, kind = self._token()
                if kind == "WEB":
                    value["data"]["csrf"] = service.auth.session_csrf(token)
            elif route.startswith("views/"):
                try:
                    page = Page(route.removeprefix("views/"))
                except ValueError:
                    raise ApiError("VIEW_NOT_FOUND", 404) from None
                value = service.snapshot(principal, page)
            elif route == "events":
                value = service.events_since(principal, (query.get("cursor") or [None])[0])
            elif route.startswith("receipts/"):
                key = route.removeprefix("receipts/")
                if not re.fullmatch("[A-Za-z0-9._:-]{1,96}", key):
                    raise ApiError("RECEIPT_NOT_FOUND", 404)
                value = service.receipt(principal, key)
            elif route == "devices":
                value = service.envelope({"devices": service.auth.devices(principal)})
            elif route == "host/operations":
                principal.require(Role.HOST_ADMIN)
                value = service.envelope({"host": service.supervisor.status()})
            elif route == "backup/status":
                value = service.backup_status(principal)
            elif route == "conversation/history":
                value = service.conversation_history(principal)
            elif route == "life/shares":
                value = service.shared_candidates(principal)
            elif route == 'notifications/inbox':
                value = service.notification_inbox(principal)
            elif route == "platform/bilibili":
                value = service.bilibili_history(principal)
            elif route=='platform/status':
                from .platform_settings import status
                value=status(service,principal)
            elif route == "providers/status":
                principal.require(Role.READER)
                value = service.envelope(service.provider_status())
            elif route == "providers/credentials":
                from .provider_settings import credential_status
                value = credential_status(service, principal)
            elif route == "notifications":
                principal.require(Role.READER)
                value = service.envelope(
                    {
                        "foreground": "AVAILABLE_WITH_PERMISSION",
                        "background": "NOT_QUALIFIED",
                        "push_provider": "UNCONFIGURED",
                        "private_body_in_push": False,
                    }
                )
            else:
                raise ApiError("NOT_FOUND", 404)
            self._auth()  # Revocation during a long projection withholds its body.
            self._json(200, value)
            return
        if self.command == "DELETE" and route.startswith("devices/"):
            service.auth.revoke(principal, route.removeprefix("devices/"))
            self._json(200, service.envelope({"revoked": True}))
            return
        if self.command != "POST":
            raise ApiError("METHOD_DENIED", 405)
        body = self._body()
        if route=='platform/credential':
            from .platform_credentials import PlatformCredentialRequest,bind
            value=bind(service,principal,self._model(PlatformCredentialRequest,body))
        elif route=='platform/commands':
            from .platform_settings import PlatformConfigurationRequest,configure
            value=configure(service,principal,self._model(PlatformConfigurationRequest,body))
        elif route == "providers/commands":
            from .provider_settings import ProviderConfigurationRequest, configure
            value = configure(service, principal, self._model(ProviderConfigurationRequest, body))
        elif route == "providers/credential":
            from .provider_settings import CredentialBindingRequest, bind_credential
            value = bind_credential(service, principal, self._model(CredentialBindingRequest, body))
        elif route == "messages":
            value = service.send(principal, self._model(MessageRequest, body))
        elif route in {"commands", "privacy/withdrawal"}:
            request = self._model(CommandRequest, body)
            if route == "privacy/withdrawal" and request.operation != "WITHDRAW":
                raise ApiError("COMMAND_DENIED", 403)
            value = service.command(principal, request)
        elif route == "devices/offers":
            code = service.auth.offer(principal, self._model(PairOffer, body))
            value = service.envelope(
                {"pairing_code": code, "expires_in": body.get("lifetime_seconds", 120), "one_time": True}
            )
        elif route == "host/confirmations":
            request = self._model(HostConfirmation, body)
            if request.expected_revision != service.ledger.revision:
                raise ApiError("REVISION_CONFLICT", 409)
            token = service.auth.confirm(principal, request.operation, request.expected_revision, request.release_id)
            value = service.envelope({"confirmation_id": token, "expires_in": 90})
        elif route == "host/operations":
            value = service.host_operation(principal, self._model(HostRequest, body))
        else:
            raise ApiError("NOT_FOUND", 404)
        self._auth()  # Admission is not a perpetual authorization after dispatch.
        self._json(200, value)

    def _static(self, path, query):
        root = self.server.web_root
        if root is None:
            raise ApiError("WEB_BUILD_UNAVAILABLE", 404)
        if path == "/":
            # The live server never defaults to the historical Demo route.
            self.send_response(303)
            self.send_header("Location", "/index.html?source=live")
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        relative = path.lstrip("/")
        if not relative or relative.startswith(".") or any(p.startswith(".") for p in Path(relative).parts):
            raise ApiError("NOT_FOUND", 404)
        target = root / relative
        if (
            target.resolve() != target
            or not target.is_relative_to(root)
            or not target.is_file()
            or target.stat().st_size > 8 * 1024 * 1024
        ):
            raise ApiError("NOT_FOUND", 404)
        if target.suffix not in {".html", ".js", ".css", ".svg", ".png", ".webp", ".woff2", ".ico"}:
            raise ApiError("NOT_FOUND", 404)
        if target.name == "index.html" and query.get("source") != ["live"]:
            raise ApiError("LIVE_ENTRY_REQUIRED", 403)
        raw = target.read_bytes()
        kind = mimetypes.guess_type(target)[0] or "application/octet-stream"
        self._headers(200, kind, len(raw))
        self.wfile.write(raw)
