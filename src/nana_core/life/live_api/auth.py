"""Host credentials/devices, not Primary User relationship or Core Grants.

Access sessions expire and disappear on restart. Only salted password digests and
refresh-token hashes persist. Native secrets never enter a Web response or DTO.
"""

import collections
import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass
from .contracts import ApiError, Role
from .state import AtomicDocument


def token_hash(token):
    if type(token) is not str or not 24 <= len(token) <= 256:
        raise ApiError("SESSION_REQUIRED", 401)
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class Principal:
    principal_id: str
    roles: tuple[Role, ...]
    kind: str
    device_id: str | None
    generation: int

    def require(self, role):
        if role not in self.roles:
            raise ApiError("SCOPE_DENIED", 403)


class AuthService:
    def __init__(self, path, *, password=None, roles=(Role.READER, Role.CONVERSATION), clock=time.monotonic):
        self.clock = clock
        self.roles = tuple(Role(r) for r in roles)
        if password is not None and (type(password) is not str or not 12 <= len(password) <= 128):
            raise ApiError("OPERATOR_PASSWORD_REQUIRED")
        from pathlib import Path

        if password is None and not Path(path).exists():
            raise ApiError("OPERATOR_PASSWORD_REQUIRED")
        salt = secrets.token_hex(16)
        digest = (
            hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
            if password is not None
            else None
        )
        initial = {
            "schema_version": 1,
            "revision": 0,
            "salt": salt,
            "password_hash": digest,
            "generation": 0,
            "devices": {},
        }
        self.document = AtomicDocument(path, initial)
        data = self.document.read()
        if data.get("password_hash") is None or set(data) != set(initial):
            raise ApiError("AUTH_CONFIG_INVALID", 503)
        try:
            bytes.fromhex(data["salt"])
            bytes.fromhex(data["password_hash"])
            for row in data["devices"].values():
                if set(row) != {"name", "refresh_hash", "roles", "revoked"}:
                    raise ValueError()
                tuple(Role(r) for r in row["roles"])
        except (ValueError, TypeError, AttributeError):
            raise ApiError("AUTH_CONFIG_INVALID", 503) from None
        self.generation = self.document.update(self._next_generation)
        self.lock = threading.RLock()
        self.sessions = {}
        self.pairings = {}
        self.attempts = collections.deque(maxlen=10)
        self.confirmations = {}

    @staticmethod
    def _next_generation(data):
        data["generation"] += 1
        return data["generation"]

    def _rate(self):
        now = self.clock()
        while self.attempts and self.attempts[0] < now - 60:
            self.attempts.popleft()
        if len(self.attempts) >= 5:
            raise ApiError("AUTH_RATE_LIMIT", 429)
        self.attempts.append(now)

    def _session(self, principal):
        if len(self.sessions) >= 64:
            now = self.clock()
            self.sessions = {k: v for k, v in self.sessions.items() if v[0] > now}
        if len(self.sessions) >= 64:
            raise ApiError("SESSION_CAPACITY", 429)
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        self.sessions[token_hash(token)] = (self.clock() + 600, principal, csrf)
        return token, csrf

    def login(self, password):
        with self.lock:
            self._rate()
            if type(password) is not str or not 12 <= len(password) <= 128:
                raise ApiError("SESSION_DENIED", 401)
            data = self.document.read()
            candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(data["salt"]), n=16384, r=8, p=1).hex()
            if not hmac.compare_digest(candidate, data["password_hash"]):
                raise ApiError("SESSION_DENIED", 401)
            self.attempts.clear()
            return self._session(Principal("host.web", self.roles, "WEB", None, self.generation))

    def authorize(self, token, kind, *, csrf=None, mutating=False):
        with self.lock:
            row = self.sessions.get(token_hash(token))
            if not row or row[0] <= self.clock() or row[1].kind != kind or row[1].generation != self.generation:
                raise ApiError("SESSION_REVOKED", 401)
            p = row[1]
            if not set(p.roles) <= set(self.roles):
                raise ApiError("SESSION_REVOKED", 401)
            if p.device_id:
                device = self.document.read()["devices"].get(p.device_id)
                if not device or device["revoked"]:
                    raise ApiError("SESSION_REVOKED", 401)
            if kind == "WEB" and mutating and (type(csrf) is not str or not hmac.compare_digest(csrf, row[2])):
                raise ApiError("CSRF_DENIED", 403)
            return p

    def session_csrf(self, token):
        with self.lock:
            self.authorize(token, "WEB")
            return self.sessions[token_hash(token)][2]

    def logout(self, token):
        with self.lock:
            self.sessions.pop(token_hash(token), None)

    def offer(self, principal, offer):
        principal.require(Role.HOST_ADMIN)
        if not set(offer.roles) <= set(principal.roles) or not offer.roles:
            raise ApiError("ROLE_ESCALATION_DENIED", 403)
        with self.lock:
            if len(self.pairings) >= 16:
                self.pairings = {k: v for k, v in self.pairings.items() if v[0] > self.clock()}
            if len(self.pairings) >= 16:
                raise ApiError("PAIRING_CAPACITY", 429)
            code = secrets.token_urlsafe(32)
            self.pairings[token_hash(code)] = (self.clock() + offer.lifetime_seconds, offer)
            return code

    def pair(self, code, device_name):
        with self.lock:
            self._rate()
            row = self.pairings.pop(token_hash(code), None)
            if not row or row[0] < self.clock() or row[1].device_name != device_name:
                raise ApiError("PAIRING_DENIED", 403)
            refresh, device_id = secrets.token_urlsafe(48), secrets.token_hex(16)

            def add(data):
                if len(data["devices"]) >= 32:
                    raise ApiError("DEVICE_CAPACITY", 429)
                data["devices"][device_id] = {
                    "name": device_name,
                    "refresh_hash": token_hash(refresh),
                    "roles": [r.value for r in row[1].roles],
                    "revoked": False,
                }

            self.document.update(add)
            self.attempts.clear()
            return device_id, refresh

    def native_session(self, device_id, refresh):
        with self.lock:
            self._rate()
            row = self.document.read()["devices"].get(device_id)
            if not row or row["revoked"] or not hmac.compare_digest(token_hash(refresh), row["refresh_hash"]):
                raise ApiError("SESSION_DENIED", 401)
            self.attempts.clear()
            permitted = tuple(Role(r) for r in row["roles"] if Role(r) in self.roles)
            if not permitted:
                raise ApiError("SCOPE_DENIED", 403)
            return self._session(Principal("native." + device_id, permitted, "NATIVE", device_id, self.generation))[0]

    def devices(self, principal):
        principal.require(Role.HOST_ADMIN)
        return [
            {"device_id": key, "name": row["name"], "roles": row["roles"], "revoked": row["revoked"]}
            for key, row in self.document.read()["devices"].items()
        ]

    def revoke(self, principal, device_id):
        principal.require(Role.HOST_ADMIN)

        def change(data):
            if device_id not in data["devices"]:
                raise ApiError("DEVICE_NOT_FOUND", 404)
            data["devices"][device_id]["revoked"] = True

        self.document.update(change)

    def revoke_self(self, principal):
        if principal.kind != "NATIVE" or not principal.device_id:
            raise ApiError("NATIVE_DEVICE_REQUIRED", 403)

        def change(data):
            row = data["devices"].get(principal.device_id)
            if row is not None:
                row["revoked"] = True

        self.document.update(change)

    def confirm(self, principal, operation, revision, release_id):
        principal.require(Role.HOST_ADMIN)
        with self.lock:
            if len(self.confirmations) >= 32:
                self.confirmations = {k: v for k, v in self.confirmations.items() if v[0] > self.clock()}
            if len(self.confirmations) >= 32:
                raise ApiError("CONFIRMATION_CAPACITY", 429)
            token = secrets.token_urlsafe(32)
            self.confirmations[token_hash(token)] = (
                self.clock() + 90,
                principal.principal_id,
                operation,
                revision,
                release_id,
            )
            return token

    def consume_confirmation(self, principal, token, operation, revision, release_id):
        with self.lock:
            row = self.confirmations.pop(token_hash(token), None)
            if not row or row[0] < self.clock() or row[1:] != (principal.principal_id, operation, revision, release_id):
                raise ApiError("HOST_CONFIRMATION_REQUIRED", 403)
