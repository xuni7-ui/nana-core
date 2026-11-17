"""Bounded streaming, content-addressed opaque cache, never model context.

Callers supply already-authorized byte chunks and a live source validator.
No URL fetching or file-path guessing, no raw media in Subject memory. The
existing Bilibili frame/subtitle services retain their evidence semantics.
"""
import hashlib
import os
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from ..contracts import CoreError


@dataclass(frozen=True)
class MediaHandle:
    sha256: str
    size: int
    source_ref: str
    media_type: str


class MediaCache:
    def __init__(self, root, *, source_current, max_bytes=64 * 1024 * 1024, item_bytes=16 * 1024 * 1024, max_items=64):
        if not 1 <= item_bytes <= max_bytes <= 1024 * 1024 * 1024 or not 1 <= max_items <= 1024:
            raise ValueError('media budget')
        self.root = Path(root).absolute()
        self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
        if self.root.resolve() != self.root or self.root.stat().st_uid != os.getuid() or self.root.stat().st_mode & 0o077:
            raise CoreError('MEDIA_PRIVATE_DIRECTORY_REQUIRED')
        if any(self.root.iterdir()):
            raise CoreError('MEDIA_FRESH_SESSION_DIRECTORY_REQUIRED')
        self.current = source_current
        self.max_bytes, self.item_bytes, self.max_items = max_bytes, item_bytes, max_items
        self.items, self.total = OrderedDict(), 0
        self.sources = {}
        self.retired = set()
        self.retirement_overflow = False
        self.closed = False
        # This process only manages files it created. Unknown prior cache files
        # are neither trusted nor erased; use a fresh per-session directory.
        self.metrics = dict(ingested_bytes=0, reused_bytes=0, evicted_bytes=0)

    def _require_current(self, source_ref, *, admission_started=False):
        if self.closed:
            raise CoreError('MEDIA_CACHE_CLOSED')
        if self.retirement_overflow or source_ref in self.retired:
            raise CoreError('MEDIA_SOURCE_RETIRED')
        try:
            current = self.current(source_ref)
        except Exception:
            current = False
        if current is True:
            return
        known = admission_started or any(source_ref in refs for refs in self.sources.values())
        if known:
            # Once this session observes withdrawal, later reauthorization must
            # use a new source reference. Bounded overflow fails closed.
            if len(self.retired) >= self.max_items * 64:
                self.retirement_overflow = True
            else:
                self.retired.add(source_ref)
            for key in tuple(self.sources):
                refs = self.sources[key]
                refs.discard(source_ref)
                if not refs:
                    path, size = self.items[key]
                    path.unlink(missing_ok=True)
                    del self.items[key]
                    del self.sources[key]
                    self.total -= size
                    self.metrics['evicted_bytes'] += size
        raise CoreError('MEDIA_SOURCE_RETIRED')

    def put(self, chunks, *, source_ref, media_type='application/octet-stream'):
        if not isinstance(source_ref, str) or not 1 <= len(source_ref) <= 256 or not isinstance(media_type, str) or not 1 <= len(media_type) <= 128:
            raise CoreError('MEDIA_METADATA_BOUND')
        self._require_current(source_ref)
        h, size = hashlib.sha256(), 0
        fd, name = tempfile.mkstemp(prefix='nanalink-', dir=self.root)
        try:
            with os.fdopen(fd, 'wb') as stream:
                for chunk in chunks:
                    if type(chunk) is not bytes or len(chunk) > 1024 * 1024:
                        raise CoreError('MEDIA_CHUNK_BOUND')
                    size += len(chunk)
                    if size > self.item_bytes:
                        raise CoreError('MEDIA_ITEM_BUDGET')
                    h.update(chunk)
                    stream.write(chunk)
                stream.flush()
            self._require_current(source_ref, admission_started=True)
            key = h.hexdigest()
            handle = MediaHandle(key, size, source_ref, media_type)
            self.metrics['ingested_bytes'] += size
            if key in self.items:
                self.metrics['reused_bytes'] += size
                self.items.move_to_end(key)
                if len(self.sources[key]) >= 64 and source_ref not in self.sources[key]:
                    raise CoreError('MEDIA_SOURCE_REFERENCE_BUDGET')
                self.sources[key].add(source_ref)
                # A new source may independently support the same content.
                return handle
            while self.items and (self.total + size > self.max_bytes or len(self.items) >= self.max_items):
                old_key = next(iter(self.items))
                old_path, old_size = self.items[old_key]
                old_path.unlink()
                del self.items[old_key]
                self.sources.pop(old_key, None)
                self.total -= old_size
                self.metrics['evicted_bytes'] += old_size
            path = Path(name)
            self.items[key] = (path, size)
            self.sources[key] = {source_ref}
            self.total += size
            name = None
            return handle
        finally:
            if name is not None:
                Path(name).unlink(missing_ok=True)

    def resolve(self, *, source_ref, sha256):
        """Resolve only a source/content pair already admitted to this session."""
        self._require_current(source_ref)
        value = self.items.get(sha256)
        if not value or source_ref not in self.sources.get(sha256, set()):
            raise CoreError('MEDIA_CACHE_MISS')
        return MediaHandle(sha256, value[1], source_ref, 'application/octet-stream')

    def read(self, handle, *, offset=0, length=65536):
        self._require_current(handle.source_ref)
        if not 0 <= offset <= handle.size or not 1 <= length <= 1024 * 1024:
            raise CoreError('MEDIA_RANGE_BOUND')
        value = self.items.get(handle.sha256)
        if not value or value[1] != handle.size or handle.source_ref not in self.sources.get(handle.sha256, set()):
            raise CoreError('MEDIA_CACHE_MISS')
        self.items.move_to_end(handle.sha256)
        fd = os.open(value[0], os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            stream.seek(offset)
            data = stream.read(min(length, handle.size - offset))
        # A source may be withdrawn while the filesystem read is in progress.
        self._require_current(handle.source_ref)
        return data

    def close(self):
        self.closed = True
        for path, _ in self.items.values():
            path.unlink(missing_ok=True)
        self.items.clear()
        self.sources.clear()
        self.retired.clear()
        self.total = 0
