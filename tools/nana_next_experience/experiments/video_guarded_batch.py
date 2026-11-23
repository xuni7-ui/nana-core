"""Isolated source-gated PUBLIC video image candidates; no subject actions."""
from dataclasses import dataclass, field, replace
import math

from nana_core.contracts import CoreError
from nana_core.nanalink.video_handoff import with_current_public_video,public_video_cache_handle
from tools.nana_next_experience.experiments.video_global_budget import select_windows, project_window
from tools.nana_next_experience.experiments.video_nanalink_cache import decode_cached_window
from tools.nana_next_experience.experiments.video_selected_images import selected_images
from tools.nana_next_experience.experiments.video_window_fusion import fuse_window
from tools.nana_next_experience.experiments.video_cached_snapshot import public_snapshot
from tools.nana_next_experience.experiments.video_pts_decode import decode
from tools.nana_next_experience.experiments.video_audio_probe import AudioProbeOutputBound,AudioProbeUnavailable,measure

MAX_BATCH_RGB_BYTES=64*1024*1024


@dataclass(frozen=True, repr=False)
class GuardedImageBatch:
    source_ref: str
    source_sha256: str
    images: tuple = field(repr=False)
    cache_bytes_hashed: int = 0
    window_count: int = 0
    decoded_rgb_bytes: int = 0
    unrequested_intervals: tuple = ()
    sampling_gaps: tuple = ()
    state: str = 'CANDIDATES_NOT_INGESTED'
    source_lifetime: str = 'RECHECK_REQUIRED_AT_USE'
    acoustic: dict | None = field(default=None,repr=False)
    acoustic_status: str = 'NOT_REQUESTED'
    audio_requested_window: tuple[float, float] | None = None


def guarded_images(app, cache, source_memory_id, *, scope, windows, detector, budget, max_gap,
                   width=160, height=90, max_frames=1200, shared_snapshot=False, orientation="raw", audio_window=None):
    """Run a trusted local detector within C's original public source gate.

    The detector returns materialized (dsh, local_pairs) or (dsh, local_pairs,
    onsets) for each decoded window. It is trusted host code, not sandboxed.
    The source gate cannot prevent arbitrary callback effects. No claim is made
    about Bilibili account/file attribution, video semantics, or permissions
    after return; consumers must recheck source and authorization at use. An
    optional audio window reuses the same snapshot but does not establish speech,
    subtitle alignment, source authority, or complete temporal coverage.
    """
    if (type(windows) not in (tuple,list) or not 1<=len(windows)<=8 or not callable(detector) or
            type(budget) is not int or not 1<=budget<=256 or
            type(max_gap) not in (int,float) or not math.isfinite(max_gap) or max_gap<=0 or
            type(width) is not int or type(height) is not int or width<1 or height<1 or width*height>262144 or
            type(max_frames) is not int or not 1<=max_frames<=1200 or type(shared_snapshot) is not bool or
            type(orientation) is not str or orientation not in ("raw","display")):
        raise ValueError('invalid guarded batch bounds')
    if audio_window is not None:
        if not shared_snapshot or type(audio_window) not in (tuple,list):
            raise ValueError('invalid shared audio window')
        audio_window=tuple(audio_window)
        if (len(audio_window)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in audio_window) or
                not 0<=audio_window[0]<audio_window[1] or audio_window[1]-audio_window[0]>600):
            raise ValueError('invalid shared audio window')
    requests=[]
    for item in windows:
        if (type(item) not in (tuple,list) or len(item)!=2 or
                any(type(x) not in (int,float) or not math.isfinite(x) for x in item) or
                not 0<=item[0]<item[1] or item[1]-item[0]>600):
            raise ValueError('invalid requested window')
        requests.append((item[0],item[1]))
    def produce(handle,load_window,bytes_hashed):
        decoded=[];selections=[];total_bytes=0;duration=None
        def current_source():
            current=public_video_cache_handle(app,cache,source_memory_id,scope=scope)
            if (current.source_ref,current.sha256,current.size)!=(handle.source_ref,handle.sha256,handle.size):
                raise CoreError('NANALINK_VIDEO_SOURCE_CHANGED')
        for start,end in requests:
            current_source()
            remaining_frames=(MAX_BATCH_RGB_BYTES-total_bytes)//(width*height*3)
            if remaining_frames<1:raise ValueError('batch decoded-pixel bound exhausted')
            window=load_window(start,end,min(max_frames,remaining_frames));total_bytes+=len(window.rgb24)
            current_source()
            if total_bytes>MAX_BATCH_RGB_BYTES:raise ValueError('batch decoded-pixel bound exceeded')
            if duration is None:duration=window.duration_seconds
            if duration!=window.duration_seconds:raise ValueError('inconsistent media duration')
            if window.timestamps:
                signals=detector(window)
                current_source()
                if type(signals) not in (tuple,list) or len(signals) not in (2,3):raise ValueError('invalid detector result')
                selected=fuse_window(window,signals[0],signals[1],budget=budget,max_gap=max_gap,
                                     onsets=signals[2] if len(signals)==3 else None)
            else:
                selected=fuse_window(window,None,None,budget=budget,max_gap=max_gap)
            decoded.append(window);selections.append(selected)
        chosen=select_windows(source_memory_id,duration,selections,budget=budget,max_gap=max_gap)
        images=[]
        for i,(window,selection) in enumerate(zip(decoded,selections)):
            if not window.timestamps:continue
            images.extend(selected_images(window,project_window(chosen,selection,i)))
        return GuardedImageBatch(source_ref=source_memory_id,source_sha256=handle.sha256,images=tuple(images),
            cache_bytes_hashed=bytes_hashed,window_count=len(requests),decoded_rgb_bytes=total_bytes,
            unrequested_intervals=tuple(chosen['unrequested_intervals']),
            sampling_gaps=tuple(chosen['sampling_gaps_over_threshold']))
    def operation(handle):
        if not shared_snapshot:
            def per_window(start,end,limit):
                return decode_cached_window(cache,handle,privacy='PUBLIC',start_seconds=start,end_seconds=end,
                                            width=width,height=height,max_frames=limit,orientation=orientation).decoded
            return produce(handle,per_window,handle.size*len(requests))
        with public_snapshot(cache,handle,privacy='PUBLIC') as path:
            def shared_window(start,end,limit):
                cache.resolve(source_ref=handle.source_ref,sha256=handle.sha256)
                result=decode(handle.source_ref,path,width=width,height=height,max_frames=limit,
                              start_seconds=start,end_seconds=end,orientation=orientation)
                cache.resolve(source_ref=handle.source_ref,sha256=handle.sha256)
                return result
            batch=produce(handle,shared_window,handle.size)
            if audio_window is not None:
                # The same source/bytes are rechecked around the second consumer;
                # an already withdrawn source must never yield its measurements.
                current=public_video_cache_handle(app,cache,source_memory_id,scope=scope)
                if (current.source_ref,current.sha256,current.size)!=(handle.source_ref,handle.sha256,handle.size):
                    raise CoreError('NANALINK_VIDEO_SOURCE_CHANGED')
                try:
                    acoustic=measure(path,start_seconds=audio_window[0],end_seconds=audio_window[1])
                    acoustic_status='AVAILABLE_NOT_QUALIFIED'
                except AudioProbeUnavailable:
                    acoustic=None;acoustic_status='PROBE_UNAVAILABLE'
                except AudioProbeOutputBound:
                    acoustic=None;acoustic_status='OUTPUT_BOUND'
                current=public_video_cache_handle(app,cache,source_memory_id,scope=scope)
                if (current.source_ref,current.sha256,current.size)!=(handle.source_ref,handle.sha256,handle.size):
                    raise CoreError('NANALINK_VIDEO_SOURCE_CHANGED')
                batch=replace(batch,acoustic=acoustic,acoustic_status=acoustic_status,
                              audio_requested_window=tuple(audio_window))
            return batch
    return with_current_public_video(app,cache,source_memory_id,scope=scope,operation=operation)
