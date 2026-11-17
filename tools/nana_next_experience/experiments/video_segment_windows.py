"""Bounded interval requests for long local video, never observed content."""
from fractions import Fraction
import math


def windows(source_ref, duration, *, window_seconds=600, overlap_seconds=2, max_windows=256):
    """Plan explicit overlapping half-open windows with a visible unplanned tail.

    Duration and source identity are caller supplied; no audio/video/model is
    read. An interval request never proves that any frame was observed.
    """
    if (type(source_ref) is not str or not 1<=len(source_ref)<=128 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in (duration,window_seconds,overlap_seconds)) or
            not 0<duration<=86400 or not 0<window_seconds<=600 or not 0<=overlap_seconds<window_seconds or
            type(max_windows) is not int or not 1<=max_windows<=256):
        raise ValueError('invalid window planning bounds')
    total=Fraction(str(duration));width=Fraction(str(window_seconds));overlap=Fraction(str(overlap_seconds))
    start=Fraction(0);planned=[]
    while start<total and len(planned)<max_windows:
        end=min(total,start+width)
        planned.append({'index':len(planned),'start_seconds':float(start),'end_seconds':float(end)})
        if end==total:break
        start=end-overlap
    final=end
    unplanned=[] if final>=total else [(float(final),float(total))]
    return {'schema_version':1,'source_ref':source_ref,'source_attestation':'CALLER_SUPPLIED',
            'duration_basis':'CALLER_SUPPLIED_UNVERIFIED','windows':planned,
            'unplanned_intervals':unplanned,'truncated':bool(unplanned),
            'status':'REQUESTS_ONLY_NOT_OBSERVED','model_calls':0,'storage':'NONE'}
