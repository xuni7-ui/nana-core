"""Temporary, hash-verified PUBLIC cache snapshot for one trusted batch."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import tempfile

from nana_core.contracts import CoreError
from nana_core.nanalink.media import MediaCache,MediaHandle


@contextmanager
def public_snapshot(cache,handle,*,privacy):
    """Yield a private temporary path; caller must recheck source during use.

    PUBLIC is caller-attested, not classification. A snapshot is not a source
    authority and is removed on exit, including failure or withdrawal.
    """
    if (type(cache) is not MediaCache or type(handle) is not MediaHandle or privacy!='PUBLIC' or
            type(handle.source_ref) is not str or not 1<=len(handle.source_ref)<=128 or
            type(handle.sha256) is not str or len(handle.sha256)!=64 or
            any(c not in '0123456789abcdef' for c in handle.sha256) or
            type(handle.size) is not int or not 1<=handle.size<=16*1024*1024):
        raise ValueError('invalid public media handle')
    current=cache.resolve(source_ref=handle.source_ref,sha256=handle.sha256)
    if current.size!=handle.size:raise CoreError('MEDIA_CACHE_MISS')
    with tempfile.TemporaryDirectory(prefix='nana-video-batch-') as directory:
        path=Path(directory)/'video';digest=hashlib.sha256();offset=0
        with path.open('xb') as output:
            while offset<handle.size:
                data=cache.read(handle,offset=offset,length=min(65536,handle.size-offset))
                if not data:raise CoreError('MEDIA_CACHE_READ_INCOMPLETE')
                output.write(data);digest.update(data);offset+=len(data)
        if offset!=handle.size or digest.hexdigest()!=handle.sha256:
            raise CoreError('MEDIA_CACHE_CONTENT_MISMATCH')
        cache.resolve(source_ref=handle.source_ref,sha256=handle.sha256)
        yield path
        cache.resolve(source_ref=handle.source_ref,sha256=handle.sha256)
