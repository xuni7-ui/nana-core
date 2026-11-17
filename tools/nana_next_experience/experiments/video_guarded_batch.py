"""Isolated source-gated PUBLIC video image candidates; no subject actions."""
from dataclasses import dataclass, field
import math

from nana_core.nanalink.video_handoff import with_current_public_video
from tools.nana_next_experience.experiments.video_global_budget import select_windows, project_window
from tools.nana_next_experience.experiments.video_nanalink_cache import decode_cached_window
from tools.nana_next_experience.experiments.video_selected_images import selected_images
from tools.nana_next_experience.experiments.video_window_fusion import fuse_window


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


def guarded_images(app, cache, source_memory_id, *, scope, windows, detector, budget, max_gap,
                   width=160, height=90, max_frames=1200):
    """Run a trusted local detector within C's original public source gate.

    The detector must return a materialized (dsh, local_pairs) pair for each
    decoded window. It is trusted host code, not sandboxed by this function.
    The source gate cannot prevent arbitrary callback effects. No claim is made
    about Bilibili account/file attribution, video semantics, or permissions
    after return; consumers must recheck source and authorization at use.
    """
    if (type(windows) not in (tuple,list) or not 1<=len(windows)<=8 or not callable(detector) or
            type(budget) is not int or not 1<=budget<=256 or
            type(max_gap) not in (int,float) or not math.isfinite(max_gap) or max_gap<=0):
        raise ValueError('invalid guarded batch bounds')
    requests=[]
    for item in windows:
        if (type(item) not in (tuple,list) or len(item)!=2 or
                any(type(x) not in (int,float) or not math.isfinite(x) for x in item) or
                not 0<=item[0]<item[1] or item[1]-item[0]>600):
            raise ValueError('invalid requested window')
        requests.append((item[0],item[1]))
    def operation(handle):
        decoded=[];selections=[];total_bytes=0;duration=None
        for start,end in requests:
            snapshot=decode_cached_window(cache,handle,privacy='PUBLIC',start_seconds=start,end_seconds=end,
                                          width=width,height=height,max_frames=max_frames)
            window=snapshot.decoded;total_bytes+=len(window.rgb24)
            if total_bytes>64*1024*1024:raise ValueError('batch decoded-pixel bound exceeded')
            if duration is None:duration=window.duration_seconds
            if duration!=window.duration_seconds:raise ValueError('inconsistent media duration')
            if window.timestamps:
                signals=detector(window)
                if type(signals) not in (tuple,list) or len(signals)!=2:raise ValueError('invalid detector result')
                selected=fuse_window(window,signals[0],signals[1],budget=budget,max_gap=max_gap)
            else:
                selected=fuse_window(window,None,None,budget=budget,max_gap=max_gap)
            decoded.append(window);selections.append(selected)
        chosen=select_windows(source_memory_id,duration,selections,budget=budget,max_gap=max_gap)
        images=[]
        for i,(window,selection) in enumerate(zip(decoded,selections)):
            if not window.timestamps:continue
            images.extend(selected_images(window,project_window(chosen,selection,i)))
        return GuardedImageBatch(source_ref=source_memory_id,source_sha256=handle.sha256,images=tuple(images),
            cache_bytes_hashed=handle.size*len(requests),window_count=len(requests),decoded_rgb_bytes=total_bytes,
            unrequested_intervals=tuple(chosen['unrequested_intervals']),
            sampling_gaps=tuple(chosen['sampling_gaps_over_threshold']))
    return with_current_public_video(app,cache,source_memory_id,scope=scope,operation=operation)
