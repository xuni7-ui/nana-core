"""Explicit host-local memory-only SecretResolver and anonymous inherited FD.

No environment discovery, secret files, credentials in configuration or Subject
records. Installing a value does not authorize network calls, budgets or restart.
Python cannot promise physical zeroization of immutable temporary strings.
"""

import base64
import fcntl
import hashlib
import json
import os
import re
import stat
import threading
import sys

from ..contracts import CoreError
from ..continuity.privacy import _json_object
from ..continuity.provider_config import ResolvedSecret

BOUND = 65536
VAULT_DOCUMENT_BOUND = 128 * 1024
SUPPORTED_FD_CONTRACT_VERSION = 2
_ENVELOPE = "NANA_SECRET_FD"  # Uppercase cannot collide with a legacy secret reference.


def _sealed_fd(document):
    raw = json.dumps(document, separators=(",", ":")).encode()
    if len(raw) > BOUND:
        raise CoreError("SECRET_BINDING_BOUND")
    if sys.platform != "linux" or not hasattr(os, "memfd_create"):
        raise CoreError("MEMORY_ONLY_SECRET_FD_UNAVAILABLE")
    fd = os.memfd_create("nana-resolver", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        if os.write(fd, raw) != len(raw):
            raise CoreError("SECRET_BINDING_BOUND")
        os.lseek(fd, 0, os.SEEK_SET)
        # Some qualified CPython builds omit the Linux uapi seal names.
        fcntl.fcntl(fd, getattr(fcntl, "F_ADD_SEALS", 1033), 0x000F)
        return fd, None
    except BaseException:
        os.close(fd)
        raise
    finally:
        raw = None


def _vault_document(raw):
    """Validate public ciphertext metadata without accessing a wrapping key."""
    value = json.loads(raw, object_pairs_hook=_json_object)
    if (type(value) is not dict
            or set(value) != {"schema_version", "revision", "nonce", "ciphertext"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or type(value["revision"]) is not int or not 0 <= value["revision"] < 2**63
            or type(value["nonce"]) is not str or len(value["nonce"]) != 16
            or type(value["ciphertext"]) is not str
            or not 24 <= len(value["ciphertext"]) <= VAULT_DOCUMENT_BOUND):
        raise ValueError()
    nonce = base64.b64decode(value["nonce"], validate=True)
    ciphertext = base64.b64decode(value["ciphertext"], validate=True)
    if (len(nonce) != 12 or len(ciphertext) < 16
            or base64.b64encode(nonce).decode() != value["nonce"]
            or base64.b64encode(ciphertext).decode() != value["ciphertext"]):
        raise ValueError()
    return value, nonce, ciphertext


def _guard_shape(guard):
    if (type(guard) is not dict or set(guard) != {"path", "revision", "sha256"}
            or type(guard["path"]) is not str
            or not 1 <= len(guard["path"].encode()) <= 4096
            or not guard["path"].startswith("/")
            or any(part in {"", ".", ".."} for part in guard["path"].split("/")[1:])
            or any(ord(c) < 32 or ord(c) == 127 for c in guard["path"])
            or type(guard["revision"]) is not int or not 0 <= guard["revision"] < 2**63
            or type(guard["sha256"]) is not str
            or not re.fullmatch(r"[a-f0-9]{64}", guard["sha256"])):
        raise ValueError()


def _private_directory(fd):
    item = os.fstat(fd)
    if not stat.S_ISDIR(item.st_mode) or item.st_uid != os.geteuid() or item.st_mode & 0o077:
        raise ValueError()


def _guard_document(path):
    """Walk explicit absolute components with pinned FDs; never follow symlinks."""
    components = path.split("/")[1:]
    parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for index, component in enumerate(components[:-1]):
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=parent)
            os.close(parent)
            parent = child
            # The explicitly selected vault and its service-owned parent must
            # be private. Shared ancestors such as /tmp need not be private.
            if index >= len(components) - 3:
                _private_directory(parent)
        _private_directory(parent)
        fd = os.open(components[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                     dir_fd=parent)
        try:
            item = os.fstat(fd)
            if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.geteuid()
                    or item.st_mode & 0o077 or item.st_nlink != 1
                    or item.st_size > VAULT_DOCUMENT_BOUND):
                raise ValueError()
            raw = bytearray()
            while len(raw) <= VAULT_DOCUMENT_BOUND:
                part = os.read(fd, min(4096, VAULT_DOCUMENT_BOUND + 1 - len(raw)))
                if not part:
                    break
                raw.extend(part)
            if len(raw) > VAULT_DOCUMENT_BOUND:
                raise ValueError()
            return raw
        finally:
            os.close(fd)
    finally:
        os.close(parent)


class MemorySecretResolver:
    persistent = False
    binding_contract_version = 1
    def __init__(self):
        self.__values = {}
        self.__lock = threading.RLock()
        self.__guard = None

    def __repr__(self):
        return "<MemorySecretResolver REDACTED>"

    def bind(self, reference, value):
        if (type(reference) is not str or not re.fullmatch(r"[a-z][a-z0-9._-]{0,95}", reference)
                or type(value) is not str or not 1 <= len(value.encode()) <= 4096
                or any(ord(c) < 33 or ord(c) > 126 for c in value)):
            raise CoreError("SECRET_BINDING_INVALID")
        with self.__lock:
            if reference not in self.__values and len(self.__values) >= 12:
                raise CoreError("SECRET_BINDING_CAPACITY")
            old = self.__values.get(reference)
            self.__values[reference] = ResolvedSecret(value)
            if old:
                old.clear()

    def available(self, reference):
        with self.__lock:
            return self._guard_current() and reference in self.__values

    def revoke(self, reference):
        with self.__lock:
            value = self.__values.pop(reference, None)
            if value is not None:
                value.clear()
            return value is not None

    def metadata(self):
        with self.__lock:
            return {"configured": True, "storage": "MEMORY_ONLY", "revision": None,
                    "bindings": len(self.__values), "credential_persisted": False}

    def resolve(self, reference):
        with self.__lock:
            if not self._guard_current() or reference not in self.__values:
                raise CoreError("SECRET_UNAVAILABLE")
            return ResolvedSecret(self.__values[reference].reveal_for_header())

    def clear(self):
        with self.__lock:
            for value in self.__values.values():
                value.clear()
            self.__values.clear()

    def inherited_fd(self):
        """Sealed RAM FD; durable guards add an explicit ciphertext-only path."""
        with self.__lock:
            if not self._guard_current() or not self.__values:
                return None
            values = {k: v.reveal_for_header() for k, v in self.__values.items()}
            if self.__guard is not None:
                values = {_ENVELOPE: 1, "bindings": values, "host_vault": self.__guard}
            return _sealed_fd(values)

    def _guard_current(self):
        # This gates future selection only. A previously resolved credential
        # may already be in flight and cannot be recalled or retried here.
        if self.__guard is None:
            return True
        try:
            raw = _guard_document(self.__guard["path"])
            document, _, _ = _vault_document(raw)
            if (document["revision"] == self.__guard["revision"]
                    and hashlib.sha256(raw).hexdigest() == self.__guard["sha256"]):
                return True
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
            pass
        self.clear()
        return False

    @classmethod
    def from_fd(cls, fd):
        resolver = cls()
        try:
            raw = bytearray()
            while len(raw) <= BOUND:
                part = os.read(fd, min(4096, BOUND + 1 - len(raw)))
                if not part:
                    break
                raw.extend(part)
            if len(raw) > BOUND:
                raise CoreError("SECRET_BINDING_BOUND")
            values = json.loads(raw, object_pairs_hook=_json_object)
            if type(values) is dict and _ENVELOPE in values:
                if (set(values) != {_ENVELOPE, "bindings", "host_vault"}
                        or type(values[_ENVELOPE]) is not int or values[_ENVELOPE] != 1):
                    raise ValueError()
                _guard_shape(values["host_vault"])
                resolver.__guard = values["host_vault"]
                resolver.binding_contract_version = 2
                values = values["bindings"]
            if type(values) is not dict or not 1 <= len(values) <= 12:
                raise CoreError("SECRET_BINDING_INVALID")
            for reference, value in values.items():
                resolver.bind(reference, value)
            return resolver
        except (ValueError, UnicodeError, RecursionError):
            resolver.clear()
            raise CoreError("SECRET_BINDING_INVALID") from None
        except BaseException:
            resolver.clear()
            raise
        finally:
            if 'raw' in locals():
                raw[:] = b'\0' * len(raw)
