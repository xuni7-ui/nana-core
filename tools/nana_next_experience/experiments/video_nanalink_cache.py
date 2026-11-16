"""Isolated PUBLIC video decode from NanaLink's original session media cache."""
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import tempfile

from nana_core.contracts import CoreError
from nana_core.nanalink.media import MediaCache, MediaHandle
from tools.nana_next_experience.experiments.video_pts_decode import DecodedFrames, decode


@dataclass(frozen=True, repr=False)
class CachedVideoWindow:
    source_ref: str
    source_sha256: str
    decoded: DecodedFrames = field(repr=False)
    privacy: str = 'PUBLIC'
    state: str = 'VERIFIED_SNAPSHOT_NOT_INGESTED'
    source_lifetime: str = 'RECHECK_REQUIRED_AT_USE'


def decode_cached_window(cache, handle, *, privacy, start_seconds, end_seconds,
                         width=160, height=90, max_frames=1200, timeout=120):
    """Read and hash a current PUBLIC handle; decode a private temp snapshot.

    PUBLIC is a caller assertion, not a privacy classifier. This does not grant
    access or insert observations. NanaLink's current-source callback is checked
    by each cache read and once after decoding; consumers must recheck again at
    their own handoff because authorization can change after this function.
    """
    if (type(cache) is not MediaCache or type(handle) is not MediaHandle or privacy!='PUBLIC' or
            type(handle.source_ref) is not str or not 1<=len(handle.source_ref)<=128 or
            type(handle.sha256) is not str or len(handle.sha256)!=64 or
            any(c not in '0123456789abcdef' for c in handle.sha256) or
            type(handle.size) is not int or not 1<=handle.size<=16*1024*1024):
        raise ValueError('invalid public media handle')
    authorized=cache.resolve(source_ref=handle.source_ref,sha256=handle.sha256)
    if authorized.size!=handle.size:raise CoreError('MEDIA_CACHE_MISS')
    with tempfile.TemporaryDirectory(prefix='nana-video-snapshot-') as directory:
        path=Path(directory)/'video';digest=hashlib.sha256();offset=0
        with path.open('xb') as output:
            while offset<handle.size:
                data=cache.read(handle,offset=offset,length=min(65536,handle.size-offset))
                if not data:raise CoreError('MEDIA_CACHE_READ_INCOMPLETE')
                output.write(data);digest.update(data);offset+=len(data)
        if offset!=handle.size or digest.hexdigest()!=handle.sha256:
            raise CoreError('MEDIA_CACHE_CONTENT_MISMATCH')
        cache.resolve(source_ref=handle.source_ref,sha256=handle.sha256)
        result=decode(handle.source_ref,path,width=width,height=height,max_frames=max_frames,
                      timeout=timeout,start_seconds=start_seconds,end_seconds=end_seconds)
        cache.resolve(source_ref=handle.source_ref,sha256=handle.sha256)
    return CachedVideoWindow(handle.source_ref,handle.sha256,result)
