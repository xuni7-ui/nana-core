"""Experimental original-S5 image decode handoff, never a Store ingestion."""
from dataclasses import dataclass, field
from fractions import Fraction
import math

from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.perception import MediaDecoder, validate_decoded
from nana_core.nanalink.video_handoff import with_current_public_video
from tools.nana_next_experience.experiments.video_cached_snapshot import public_snapshot
from tools.nana_next_experience.experiments.video_guarded_batch import GuardedImageBatch
from tools.nana_next_experience.experiments.video_selected_images import ImageCandidate


@dataclass(frozen=True, repr=False)
class S5Frame:
    source_seconds: float
    pts_tick: int
    time_base: tuple
    timeline_origin: str
    coordinate_space: str
    decoded: dict = field(repr=False)


@dataclass(frozen=True, repr=False)
class S5DecodeBatch:
    source_ref: str
    source_sha256: str
    frames: tuple = field(repr=False)
    unrequested_intervals: tuple = ()
    sampling_gaps: tuple = ()
    source_bytes_rechecked: int = 0
    state: str = 'TECHNICAL_IMAGE_DECODE_ONLY_NOT_INGESTED'
    source_lifetime: str = 'RECHECK_REQUIRED_AT_USE'
    frame_attestation: str = 'TRUSTED_PIPELINE_NOT_INDEPENDENTLY_REDECODED'


def s5_decode_handoff(app, cache, batch, *, scope):
    """Decode trusted candidates through original S5 with current source checks.

    The original bytes are rehashed; matching a candidate PNG's pixel hash does
    not independently prove it came from those bytes or from a platform. A
    caller must trust the producing pipeline and recheck source at actual use.
    This creates no evidence, memory, observation, permission or model call.
    """
    if (type(batch) is not GuardedImageBatch or batch.state != 'CANDIDATES_NOT_INGESTED' or
            type(batch.images) is not tuple or len(batch.images)>256):
        raise ValueError('invalid video image batch')

    def operation(handle):
        if (handle.source_ref,handle.sha256)!=(batch.source_ref,batch.source_sha256):
            raise CoreError('NANALINK_VIDEO_SOURCE_CHANGED')
        frames=[];total=0;decoder=MediaDecoder()
        with public_snapshot(cache,handle,privacy='PUBLIC'):
            for image in batch.images:
                if (type(image) is not ImageCandidate or image.source_ref!=handle.source_ref or
                        image.state!='CANDIDATE_NOT_INGESTED' or type(image.png) is not bytes or
                        not 1<=len(image.png)<=16*1024*1024 or
                        image.coordinate_space not in ('decoded_scaled_pixels_no_rotation','ffmpeg_autorotate_scaled_pixels') or
                        type(image.pts_tick) is not int or type(image.time_base) is not tuple or
                        len(image.time_base)!=2 or any(type(v) is not int or not 1<=v<=1_000_000_000 for v in image.time_base) or
                        type(image.source_seconds) not in (int,float) or not math.isfinite(image.source_seconds) or
                        type(image.requested_window) is not tuple or len(image.requested_window)!=2 or
                        any(type(v) not in (int,float) or not math.isfinite(v) for v in image.requested_window) or
                        not 0<=image.requested_window[0]<=image.source_seconds<image.requested_window[1]):
                    raise ValueError('invalid video image candidate')
                try: origin=Fraction(image.timeline_origin)
                except (ValueError,TypeError,ZeroDivisionError) as exc: raise ValueError('invalid image timeline') from exc
                if float(Fraction(image.pts_tick*image.time_base[0],image.time_base[1])-origin)!=image.source_seconds:
                    raise ValueError('inconsistent image timestamp')
                total+=len(image.png)
                if total>64*1024*1024:raise ValueError('video image byte bound exceeded')
                decoded=validate_decoded(decoder.decode(image.png,'IMAGE'),'IMAGE')
                if (decoded['pixel_digest']!=image.pixel_sha256 or
                        (decoded['width'],decoded['height'])!=image.output_size):
                    raise ValueError('video image pixels changed')
                frames.append(S5Frame(image.source_seconds,image.pts_tick,image.time_base,image.timeline_origin,
                                      image.coordinate_space,decoded))
        return S5DecodeBatch(handle.source_ref,handle.sha256,tuple(frames),
                             batch.unrequested_intervals,batch.sampling_gaps,handle.size)
    return with_current_public_video(app,cache,batch.source_ref,scope=scope,operation=operation)
