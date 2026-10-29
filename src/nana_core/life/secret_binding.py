"""Explicit host-local memory-only SecretResolver and anonymous inherited FD.

No environment discovery, secret files, credentials in configuration or Subject
records. Installing a value does not authorize network calls, budgets or restart.
Python cannot promise physical zeroization of immutable temporary strings.
"""

import fcntl
import json
import os
import re
import threading
import sys

from ..contracts import CoreError
from ..continuity.privacy import _json_object
from ..continuity.provider_config import ResolvedSecret

BOUND = 65536


class MemorySecretResolver:
    persistent = False
    def __init__(self):
        self.__values = {}
        self.__lock = threading.RLock()

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
            return reference in self.__values

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
            if reference not in self.__values:
                raise CoreError("SECRET_UNAVAILABLE")
            return ResolvedSecret(self.__values[reference].reveal_for_header())

    def clear(self):
        with self.__lock:
            for value in self.__values.values():
                value.clear()
            self.__values.clear()

    def inherited_fd(self):
        """Sealed anonymous RAM FD: no shell/env/argv payload or disk pathname."""
        with self.__lock:
            if not self.__values:
                return None
            raw = json.dumps({k: v.reveal_for_header() for k, v in self.__values.items()}).encode()
            if len(raw) > BOUND:
                raise CoreError("SECRET_BINDING_BOUND")
            if sys.platform != "linux" or not hasattr(os, "memfd_create"):
                raise CoreError("MEMORY_ONLY_SECRET_FD_UNAVAILABLE")
            fd = os.memfd_create("nana-resolver", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
            try:
                if os.write(fd, raw) != len(raw):
                    raise CoreError("SECRET_BINDING_BOUND")
                os.lseek(fd, 0, os.SEEK_SET)
                # Linux uapi constants. Some qualified CPython builds omit the
                # symbolic fcntl names despite the kernel supporting memfd seals.
                fcntl.fcntl(fd, getattr(fcntl, "F_ADD_SEALS", 1033), 0x000F)
                return fd, None
            except BaseException:
                os.close(fd)
                raise
            finally:
                raw = None

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
            if type(values) is not dict or not 1 <= len(values) <= 12:
                raise CoreError("SECRET_BINDING_INVALID")
            for reference, value in values.items():
                resolver.bind(reference, value)
            return resolver
        except (ValueError, UnicodeError):
            resolver.clear()
            raise CoreError("SECRET_BINDING_INVALID") from None
        except BaseException:
            resolver.clear()
            raise
        finally:
            if 'raw' in locals():
                raw[:] = b'\0' * len(raw)
