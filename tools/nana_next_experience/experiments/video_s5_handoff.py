"""Experimental original-S5 image decode handoff, never a Store ingestion."""
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import math

from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.perception import MediaDecoder, validate_decoded
from nana_core.nanalink.video_handoff import public_video_cache_handle,with_current_public_video
from tools.nana_next_experience.experiments.video_cached_snapshot import public_snapshot
from tools.nana_next_experience.experiments.video_guarded_batch import GuardedImageBatch
from tools.nana_next_experience.experiments.video_selected_images import ImageCandidate
from tools.nana_next_experience.experiments.video_pts_decode import decode as decode_source_window


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


def s5_decode_handoff(app, cache, batch, *, scope, verify_source_frames=False):
    """Decode trusted candidates through original S5 with current source checks.

    The original bytes are rehashed; matching a candidate PNG's pixel hash does
    not independently prove it came from those bytes or from a platform. A
    caller must trust the producing pipeline unless verify_source_frames=True,
    which redecodes each candidate window at the same resolution/orientation.
    The caller must still recheck source at actual use.
    This creates no evidence, memory, observation, permission or model call.
    """
    if (type(batch) is not GuardedImageBatch or batch.state != 'CANDIDATES_NOT_INGESTED' or
            type(batch.images) is not tuple or len(batch.images)>256 or type(verify_source_frames) is not bool):
        raise ValueError('invalid video image batch')

    def operation(handle):
        if (handle.source_ref,handle.sha256)!=(batch.source_ref,batch.source_sha256):
            raise CoreError('NANALINK_VIDEO_SOURCE_CHANGED')
        frames=[];total=0;decoder=MediaDecoder();groups={}
        with public_snapshot(cache,handle,privacy='PUBLIC') as path:
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
                if verify_source_frames:
                    key=(image.requested_window,image.output_size,image.coordinate_space)
                    groups.setdefault(key,[]).append(image)
                    if len(groups)>8:raise ValueError('video verification window bound exceeded')
                frames.append(S5Frame(image.source_seconds,image.pts_tick,image.time_base,image.timeline_origin,
                                      image.coordinate_space,decoded))
            for (window,size,space),images in groups.items():
                current=public_video_cache_handle(app,cache,handle.source_ref,scope=scope)
                if (current.source_ref,current.sha256,current.size)!=(handle.source_ref,handle.sha256,handle.size):
                    raise CoreError('NANALINK_VIDEO_SOURCE_CHANGED')
                original=decode_source_window(handle.source_ref,path,width=size[0],height=size[1],
                    max_frames=1200,start_seconds=window[0],end_seconds=window[1],
                    orientation='raw' if space=='decoded_scaled_pixels_no_rotation' else 'display')
                if (original.time_base,original.timeline_origin,original.coordinate_space)!=(images[0].time_base,images[0].timeline_origin,space):
                    raise ValueError('video image source timing mismatch')
                indices={tick:i for i,tick in enumerate(original.pts_ticks)};frame_size=size[0]*size[1]*3
                for image in images:
                    if (image.time_base,image.timeline_origin)!=(original.time_base,original.timeline_origin) or image.pts_tick not in indices:
                        raise ValueError('video image source frame missing')
                    index=indices[image.pts_tick]
                    pixels=original.rgb24[index*frame_size:(index+1)*frame_size]
                    if original.timestamps[index]!=image.source_seconds or hashlib.sha256(pixels).hexdigest()!=image.pixel_sha256:
                        raise ValueError('video image does not match source frame')
        return S5DecodeBatch(handle.source_ref,handle.sha256,tuple(frames),
                             batch.unrequested_intervals,batch.sampling_gaps,handle.size,
                             frame_attestation=('NO_FRAMES_TO_VERIFY' if verify_source_frames and not batch.images else
                                                'SOURCE_WINDOW_REDECODED_NO_PLATFORM_ATTESTATION' if verify_source_frames else
                                                'TRUSTED_PIPELINE_NOT_INDEPENDENTLY_REDECODED'))
    return with_current_public_video(app,cache,batch.source_ref,scope=scope,operation=operation)
