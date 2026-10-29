"""Explicit host-local AES-256-GCM resolver, never portable Subject data.

The wrapping key and authenticated ciphertext live in a private service-owned
directory. This protects against accidental plaintext disclosure, other users
and ciphertext corruption; it DOES NOT protect against root, the service UID,
or theft of both the wrapping key and vault. Provider rotation/revocation use
CAS and atomic replacement. No ambient credential discovery or network calls.
"""

import base64
import fcntl
import json
import os
import stat
import tempfile
import threading
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..contracts import CoreError
from ..continuity.privacy import _json_object
from .secret_binding import MemorySecretResolver

LIMIT = 128 * 1024
AAD = b"nana-host-provider-vault/v1\0"


def _private(path, *, directory=False):
    item = Path(path).lstat()
    correct = stat.S_ISDIR(item.st_mode) if directory else stat.S_ISREG(item.st_mode)
    if (not correct or item.st_uid != os.geteuid() or item.st_mode & 0o077
            or (not directory and item.st_nlink != 1)):
        raise CoreError("PROVIDER_VAULT_PERMISSIONS_UNSAFE")


def _read(path, bound):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        item = os.fstat(fd)
        if not stat.S_ISREG(item.st_mode) or item.st_uid != os.geteuid() or item.st_mode & 0o077 or item.st_nlink != 1:
            raise CoreError("PROVIDER_VAULT_PERMISSIONS_UNSAFE")
        raw = os.read(fd, bound + 1)
        if len(raw) > bound:
            raise CoreError("PROVIDER_VAULT_BOUND")
        return raw
    finally:
        os.close(fd)


def _fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class DurableSecretResolver(MemorySecretResolver):
    """Host explicitly selects this directory outside canonical Subject home."""

    persistent = True

    def __init__(self, directory, *, initialize=False):
        super().__init__()
        self.__directory = Path(directory).absolute()
        self.__lock = threading.RLock()
        self.__closed = False
        if self.__directory.resolve() != self.__directory:
            raise CoreError("PROVIDER_VAULT_PATH_UNSAFE")
        _private(self.__directory.parent, directory=True)
        if not self.__directory.exists():
            if not initialize:
                raise CoreError("PROVIDER_VAULT_UNAVAILABLE")
            self._initialize()
        _private(self.__directory, directory=True)
        try:
            key = _read(self.__directory / "wrapping.key", 32)
        except OSError:
            raise CoreError("PROVIDER_VAULT_KEY_UNAVAILABLE") from None
        if len(key) != 32:
            raise CoreError("PROVIDER_VAULT_CORRUPT")
        self.__aes = AESGCM(key)
        self._refresh()

    def __repr__(self):
        return "<DurableSecretResolver HOST_LOCAL_AES_256_GCM REDACTED>"

    def _initialize(self):
        staging = Path(tempfile.mkdtemp(prefix=".provider-vault-init-", dir=self.__directory.parent))
        key = os.urandom(32)
        aes = AESGCM(key)
        for name, value in (("wrapping.key", key), ("vault.json", self._encode(aes, 0, {}))):
            fd = os.open(staging / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(value)
                output.flush()
                os.fsync(output.fileno())
        _fsync_directory(staging)
        try:
            os.rename(staging, self.__directory)
        except FileExistsError:
            raise CoreError("PROVIDER_VAULT_INITIALIZATION_CONFLICT") from None
        _fsync_directory(self.__directory.parent)

    @staticmethod
    def _encode(aes, revision, values):
        raw = json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        nonce = os.urandom(12)
        encrypted = aes.encrypt(nonce, raw, AAD + revision.to_bytes(8, "big"))
        return json.dumps({"schema_version": 1, "revision": revision,
                           "nonce": base64.b64encode(nonce).decode(),
                           "ciphertext": base64.b64encode(encrypted).decode()}, separators=(",", ":")).encode()

    def _load(self):
        if self.__closed:
            raise CoreError("PROVIDER_VAULT_CLOSED")
        _private(self.__directory, directory=True)
        try:
            value = json.loads(_read(self.__directory / "vault.json", LIMIT), object_pairs_hook=_json_object)
            if (set(value) != {"schema_version", "revision", "nonce", "ciphertext"}
                    or type(value["schema_version"]) is not int or value["schema_version"] != 1
                    or type(value["revision"]) is not int or not 0 <= value["revision"] < 2**63):
                raise ValueError()
            nonce = base64.b64decode(value["nonce"], validate=True)
            if len(nonce) != 12:
                raise ValueError()
            raw = self.__aes.decrypt(nonce, base64.b64decode(value["ciphertext"], validate=True),
                                     AAD + value["revision"].to_bytes(8, "big"))
            values = json.loads(raw, object_pairs_hook=_json_object)
            if type(values) is not dict or len(values) > 12:
                raise ValueError()
            self._validate_values(values)
            return value["revision"], values
        except (OSError, ValueError, TypeError, KeyError, InvalidTag):
            raise CoreError("PROVIDER_VAULT_CORRUPT") from None

    @staticmethod
    def _validate_values(values):
        temporary = MemorySecretResolver()
        try:
            for reference, value in values.items():
                temporary.bind(reference, value)
        finally:
            temporary.clear()

    def _refresh(self):
        with self.__lock:
            revision, values = self._load()
            super().clear()
            for reference, value in values.items():
                super().bind(reference, value)
            return revision, len(values)

    def metadata(self):
        revision, count = self._refresh()
        return {"configured": True, "storage": "HOST_LOCAL_AES_256_GCM", "revision": revision,
                "bindings": count, "credential_persisted": True,
                "root_or_service_uid_compromise_protected": False}

    def _checkpoint(self, stage):
        pass  # Process-kill qualification seam, no environment switch.

    def _publish(self, revision, values):
        raw = self._encode(self.__aes, revision, values)
        if len(raw) > LIMIT:
            raise CoreError("PROVIDER_VAULT_BOUND")
        fd, name = tempfile.mkstemp(prefix=".vault-ciphertext-", dir=self.__directory)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            self._checkpoint("TEMP_FSYNCED")
            os.replace(name, self.__directory / "vault.json")
            _fsync_directory(self.__directory)
            self._checkpoint("REPLACED")
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _update(self, reference, value, expected_revision):
        with self.__lock:
            fd = os.open(self.__directory / "vault.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                _private(self.__directory / "vault.lock")
                fcntl.flock(fd, fcntl.LOCK_EX)
                revision, values = self._load()
                if expected_revision is not None and expected_revision != revision:
                    raise CoreError("PROVIDER_VAULT_REVISION_CONFLICT")
                if value is None:
                    values.pop(reference, None)
                else:
                    values[reference] = value
                self._validate_values(values)
                self._publish(revision + 1, values)
                self._refresh()
            finally:
                os.close(fd)

    def bind(self, reference, value, *, expected_revision=None):
        self._validate_values({reference: value})
        self._update(reference, value, expected_revision)

    def revoke(self, reference, *, expected_revision=None):
        self._validate_values({reference: "TEST_ONLY_VALIDATION_SENTINEL"})
        self._update(reference, None, expected_revision)

    def available(self, reference):
        self._refresh()
        return super().available(reference)

    def resolve(self, reference):
        self._refresh()
        return super().resolve(reference)

    def inherited_fd(self):
        self._refresh()
        return super().inherited_fd()

    def clear(self):
        with self.__lock:
            super().clear()
            self.__aes = None
            self.__closed = True
