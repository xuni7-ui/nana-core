"""Atomic host-local infrastructure metadata, never portable Subject memory.

Only fixed auth hashes, operation digests/states and host latches belong here.
No messages, model wording, personal facts, credentials or arbitrary Core rows.
"""

import fcntl
import json
import os
import stat
import tempfile
import threading
from pathlib import Path
from .contracts import ApiError
from ...continuity.privacy import _json_object


class AtomicDocument:
    def __init__(self, path, initial):
        self.path = Path(path).absolute()
        self.lock = threading.RLock()
        parent = self.path.parent
        if parent.resolve() != parent:
            raise ApiError("HOST_PATH_DENIED")
        parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if parent.stat().st_uid != os.getuid() or parent.stat().st_mode & 0o077:
            raise ApiError("HOST_PRIVATE_DIRECTORY_REQUIRED")
        with self.locked():
            if not self.path.exists():
                self._write(initial)
            self.read()

    def locked(self):
        owner = self

        class Lock:
            def __enter__(self):
                owner.lock.acquire()
                try:
                    self.fd = os.open(str(owner.path) + ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
                    fcntl.flock(self.fd, fcntl.LOCK_EX)
                except BaseException:
                    owner.lock.release()
                    raise

            def __exit__(self, *args):
                os.close(self.fd)
                owner.lock.release()

        return Lock()

    def read(self):
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise ValueError()
                raw = stream.read(524289)
            if len(raw) > 524288:
                raise ValueError()
            data = json.loads(raw, object_pairs_hook=_json_object)
            if data.get("schema_version") != 1 or type(data.get("revision")) is not int:
                raise ValueError()
            return data
        except (OSError, ValueError, TypeError, AttributeError):
            raise ApiError("HOST_METADATA_CORRUPT", 503) from None

    def _write(self, data):
        raw = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(raw) > 524288:
            raise ApiError("HOST_METADATA_CAPACITY", 503)
        fd, name = tempfile.mkstemp(prefix=".gateway-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def update(self, change):
        with self.locked():
            data = self.read()
            result = change(data)
            data["revision"] += 1
            self._write(data)
            return result
