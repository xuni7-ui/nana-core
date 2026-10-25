"""Loopback-only authenticated browser bridge to an existing original Core owner.

No Core construction, SQL access, grants, control passthrough, paid provider or
browser-supplied home/path. Only explicit owned development instances qualify.
"""

import argparse, collections, getpass, hashlib, hmac, json, mimetypes, re, secrets, sys, threading, time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
try:
    from .dev_instance import check_home
except ImportError:
    from dev_instance import check_home
PREFIX = "/api/nana-space/v1/"
SECTIONS = {
    "runtime",
    "goals",
    "activities",
    "concerns",
    "needs",
    "affect",
    "interests",
    "suppressed_deferred",
    "decisions",
    "experience",
    "provenance",
    "authority",
    "unknown",
    "provider",
    "queue",
    "source_lifecycle",
    "health",
    "skills",
    "world",
    "learning",
}


class BoundaryError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status


def token(value, maximum=256):
    if (
        type(value) is not str
        or not 1 <= len(value) <= maximum
        or any(ord(c) < 32 for c in value)
    ):
        raise BoundaryError("INVALID_TOKEN")
    return value


def strict_object(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[k] = v
    return result


class Bridge:
    def __init__(self, home, identity, password, *, read_only=False):
        self.home = check_home(home, identity)
        self.identity = identity
        self.read_only = read_only
        if not 12 <= len(password) <= 128:
            raise ValueError("LOCAL_PASSWORD_LENGTH_12_128")
        self.salt = secrets.token_bytes(16)
        self.password_hash = hashlib.scrypt(
            password.encode(), salt=self.salt, n=16384, r=8, p=1
        )
        self.run_id = secrets.token_hex(8)
        self.sessions = {}
        self.attempts = collections.deque(maxlen=5)
        self.receipts = collections.OrderedDict()
        self.lock = threading.Lock()
        self.auth_lock = threading.Lock()

    def login(self, password, identity):
        with self.auth_lock:
            now = time.monotonic()
            while self.attempts and self.attempts[0] < now - 60:
                self.attempts.popleft()
            if len(self.attempts) >= 5:
                raise BoundaryError("AUTH_RATE_LIMIT", 429)
            self.attempts.append(now)
            if (
                identity != self.identity
                or type(password) is not str
                or len(password) > 128
            ):
                raise BoundaryError("SESSION_DENIED", 403)
            candidate = hashlib.scrypt(
                password.encode(), salt=self.salt, n=16384, r=8, p=1
            )
            if not hmac.compare_digest(candidate, self.password_hash):
                raise BoundaryError("SESSION_DENIED", 403)
            sid = secrets.token_urlsafe(32)
            self.sessions = {sid: now + 3600}  # one active local browser session
            self.attempts.clear()
            return sid

    def authorize(self, cookie):
        try:
            jar = SimpleCookie()
            jar.load(cookie or "")
            sid = jar["nana_space_session"].value
        except (KeyError, ValueError):
            raise BoundaryError("SESSION_REQUIRED", 401) from None
        with self.auth_lock:
            if self.sessions.get(sid, 0) < time.monotonic():
                raise BoundaryError("SESSION_EXPIRED", 401)

    def core(self, request):
        from nana_core.life.control import request as call

        return call(self.home, request, timeout=6)

    def owner_status(self):
        result = self.core({"operation": "view", "view": "status"})
        if result.get("ok") is not True:
            raise BoundaryError("CORE_UNAVAILABLE", 503)
        status = result["result"]
        if status.get("provider") != "OFFLINE_NO_PROVIDER":
            raise BoundaryError("QUALIFICATION_PROFILE_CHANGED", 409)
        if status.get("identity_id") != self.identity:
            raise BoundaryError("SUBJECT_IDENTITY_MISMATCH", 409)
        return status

    def envelope(self, data):
        return {
            "contract": "nana-space-live/v1",
            "subject_id": self.identity,
            "realm": "OWNED_DEVELOPMENT_ONLY",
            "run_id": self.run_id,
            "as_of_us": time.time_ns() // 1000,
            "execution_authority": False,
            "data": data,
        }

    def snapshot(self):
        from nana_core.life.inspector import inspect

        with self.lock:
            status = self.owner_status()
            snapshot = inspect(
                self.home,
                scope="project-work",
                entity_id="project-user",
                privacy=("PUBLIC", "PROJECT"),
                limit=16,
            ).model_dump(mode="json")
            if snapshot["identity_id"] != self.identity:
                raise BoundaryError("SUBJECT_IDENTITY_MISMATCH", 409)
            safe = {
                k: snapshot[k]
                for k in [
                    "schema_version",
                    "derived",
                    "read_only",
                    "identity_id",
                    "as_of_us",
                    "coverage",
                    "governance_visibility",
                    "execution_authority",
                    "resources",
                ]
            }
            safe["sections"] = {
                key: [
                    {
                        k: row[k]
                        for k in [
                            "category",
                            "reference",
                            "state",
                            "record_id",
                            "as_of_us",
                            "source_memory_ids",
                        ]
                    }
                    for row in rows
                ]
                for key, rows in snapshot["sections"].items()
                if key in SECTIONS
            }
            return self.envelope(
                {
                    "inspector": safe,
                    "runtime": {
                        k: status[k]
                        for k in ["autonomy", "provider", "external_social_delivery"]
                    },
                    "capabilities": {
                        "read_only": True,
                        "send_input": not self.read_only,
                        "max_message_characters": 2048,
                        "privacy": ["PROJECT"],
                        "memory_bodies": False,
                        "provider_settings": False,
                        "perception_capture": False,
                        "actions": False,
                    },
                }
            )

    def send(self, body):
        if self.read_only:
            raise BoundaryError("SEND_INPUT_DENIED", 403)
        if set(body) != {"message_id", "text", "run_id"}:
            raise BoundaryError("MESSAGE_FIELDS_DENIED")
        mid = token(body["message_id"], 64)
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,64}", mid):
            raise BoundaryError("MESSAGE_ID_INVALID")
        text = body["text"]
        if type(text) is not str or not 1 <= len(text.strip()) <= 2048:
            raise BoundaryError("MESSAGE_BOUND")
        if body["run_id"] != self.run_id:
            raise BoundaryError("SESSION_GENERATION_CHANGED_NO_REPLAY", 409)
        digest = hashlib.sha256(text.encode()).hexdigest()
        with self.lock:
            if mid in self.receipts:
                prior = self.receipts[mid]
                if prior["digest"] != digest:
                    raise BoundaryError("MESSAGE_ID_COLLISION", 409)
                return self.envelope(prior["receipt"])
            self.owner_status()  # fail before dispatch if identity/owner unavailable
            if len(self.receipts) >= 128:
                raise BoundaryError("SESSION_RECEIPT_BOUND", 429)
            receipt = {
                "message_id": mid,
                "state": "UNKNOWN",
                "text": None,
                "no_retry": True,
            }
            self.receipts[mid] = {"digest": digest, "receipt": receipt}
            try:
                answer = self.core(
                    {
                        "operation": "surface",
                        "observation": {
                            "binding_id": "nana.space",
                            "event_id": f"{self.run_id}.{mid}"[:96],
                            "thread_id": "space",
                            "topic": "daily",
                            "text": text,
                            "privacy_class": "PROJECT",
                            "retain_shared_life": False,
                        },
                    }
                )
                if answer.get("ok") is True:
                    result = answer["result"]
                    if result.get("state") == "ALREADY_REVIEWED_NO_REPLAY":
                        receipt["state"] = "UNKNOWN"
                    else:
                        receipt.update(
                            {
                                k: result.get(k)
                                for k in [
                                    "text",
                                    "provider_state",
                                    "render_state",
                                    "mode",
                                    "judgment",
                                    "intention",
                                    "message_memory_id",
                                    "raw_body_persisted",
                                ]
                            }
                        )
                        receipt["text"] = (
                            receipt["text"][:4096]
                            if type(receipt["text"]) is str
                            else None
                        )
                        receipt["state"] = (
                            "REVIEWED" if receipt["text"] is not None else "UNKNOWN"
                        )
                        receipt["no_retry"] = True
                # Any lost response or owner rejection after send remains UNKNOWN.
            except Exception:
                pass  # never replay; no raw input/model text in logs or errors
            return self.envelope(receipt)

    def receipt(self, mid):
        with self.lock:
            row = self.receipts.get(mid)
            return self.envelope(
                row["receipt"]
                if row
                else {
                    "message_id": mid,
                    "state": "UNKNOWN",
                    "no_retry": True,
                    "text": None,
                }
            )


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, bridge, dist):
        self.bridge = bridge
        self.dist = Path(dist).resolve()
        if not (self.dist / "index.html").is_file():
            raise ValueError("BUILD_REQUIRED")
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(8)

    def headers_out(self, status, kind, length, extra=()):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()

    def reply(self, status, data, extra=()):
        self.close_connection = True
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.headers_out(status, "application/json; charset=utf-8", len(raw), extra)
        self.wfile.write(raw)

    def boundary(self, post=False):
        if self.headers.get("Host") != urlsplit(self.server.origin).netloc:
            raise BoundaryError("HOST_DENIED", 403)
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise BoundaryError("ORIGIN_DENIED", 403)
        origin = self.headers.get("Origin")
        if (post and origin != self.server.origin) or (
            origin is not None and origin != self.server.origin
        ):
            raise BoundaryError("ORIGIN_DENIED", 403)

    def body(self):
        if (
            self.headers.get("Transfer-Encoding")
            or self.headers.get("Content-Type") != "application/json"
        ):
            raise BoundaryError("JSON_REQUIRED", 415)
        value = self.headers.get("Content-Length", "")
        if not value.isdecimal() or not 1 <= int(value) <= 16384:
            raise BoundaryError("BODY_BOUND", 413)
        raw = self.rfile.read(int(value))
        if len(raw) != int(value):
            raise BoundaryError("INCOMPLETE_BODY")
        try:
            body = json.loads(raw, object_pairs_hook=strict_object)
        except (ValueError, RecursionError, UnicodeError):
            raise BoundaryError("JSON_INVALID") from None
        if type(body) is not dict:
            raise BoundaryError("JSON_OBJECT_REQUIRED")
        return body

    def handle_request(self, post=False):
        try:
            self.boundary(post)
            url = urlsplit(self.path)
            if url.fragment or (
                url.query
                and (url.path.startswith(PREFIX) or url.query != "source=core")
            ):
                raise BoundaryError("QUERY_DENIED")
            path = url.path
            if post and path == PREFIX + "session":
                data = self.body()
                if set(data) != {"password", "subject_id"}:
                    raise BoundaryError("SESSION_FIELDS_DENIED")
                sid = self.server.bridge.login(data["password"], data["subject_id"])
                return self.reply(
                    200,
                    self.server.bridge.envelope({"authenticated": True}),
                    [
                        (
                            "Set-Cookie",
                            f"nana_space_session={sid}; HttpOnly; SameSite=Strict; Path=/api/nana-space/v1/; Max-Age=3600",
                        )
                    ],
                )
            if path.startswith(PREFIX):
                self.server.bridge.authorize(self.headers.get("Cookie"))
                if not post and path == PREFIX + "snapshot":
                    return self.reply(200, self.server.bridge.snapshot())
                if post and path == PREFIX + "messages":
                    return self.reply(200, self.server.bridge.send(self.body()))
                if not post and re.fullmatch(
                    re.escape(PREFIX) + r"receipts/[A-Za-z0-9._:-]{1,64}", path
                ):
                    return self.reply(
                        200, self.server.bridge.receipt(path.rsplit("/", 1)[-1])
                    )
                raise BoundaryError("ENDPOINT_DENIED", 404)
            if post:
                raise BoundaryError("ENDPOINT_DENIED", 404)
            asset = unquote(path).lstrip("/") or "index.html"
            target = (self.server.dist / asset).resolve()
            if (
                not target.is_relative_to(self.server.dist)
                or not (
                    asset in {"index.html", "favicon.svg"}
                    or asset.startswith("assets/")
                )
                or not target.is_file()
            ):
                raise BoundaryError("ASSET_NOT_FOUND", 404)
            raw = target.read_bytes()
            self.headers_out(
                200,
                mimetypes.guess_type(str(target))[0] or "application/octet-stream",
                len(raw),
            )
            self.wfile.write(raw)
        except BoundaryError as exc:
            self.reply(exc.status, {"code": exc.code, "execution_authority": False})
        except (BrokenPipeError, ConnectionError):
            pass
        except Exception:
            self.reply(503, {"code": "CORE_UNAVAILABLE", "execution_authority": False})

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request(True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--subject-id", required=True)
    p.add_argument("--port", type=int, default=4174)
    p.add_argument("--auth-fd", type=int)
    p.add_argument("--read-only", action="store_true")
    a = p.parse_args()
    if a.auth_fd is None:
        password = getpass.getpass(
            "Local session password (12–128 characters; memory only): "
        )
    else:
        import os

        password = os.read(a.auth_fd, 513).decode().removesuffix("\n").removesuffix("\r")
    bridge = Bridge(a.home, a.subject_id, password, read_only=a.read_only)
    password = None
    server = Server(a.port, bridge, Path(__file__).resolve().parents[1] / "dist")
    print(
        f"Nana Space local development surface: {server.origin} / subject {a.subject_id}",
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        bridge.sessions.clear()
        bridge.receipts.clear()


if __name__ == "__main__":
    main()
