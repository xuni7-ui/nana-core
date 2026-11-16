"""Bounded, streaming window subdivision for optional local visual experiments."""
import math
from fractions import Fraction

from tools.nana_next_experience.experiments.video_pts_decode import decode, FrameBoundExceeded


def iter_windows(source_ref, path, start, end, *, max_attempts=256, **decode_options):
    """Yield decoded windows, then a completion record with any remaining requests.

    Subdivide only the explicit frame-bound failure, not corrupt media, timeouts,
    or unknown errors. Hold at most one successful RGB window at a time if the
    caller consumes and releases it. Requests and frames are not observations;
    source authorization and any cross-window aggregation belong to the caller.
    """
    if (type(start) not in (int, float) or type(end) not in (int, float) or
            not math.isfinite(start) or not math.isfinite(end) or
            not 0 <= start < end or end-start > 600 or
            type(max_attempts) is not int or not 1 <= max_attempts <= 256 or
            'start_seconds' in decode_options or 'end_seconds' in decode_options):
        raise ValueError('invalid adaptive window bounds')
    pending=[(start,end)]
    attempts=0
    while pending and attempts<max_attempts:
        left,right=pending.pop()
        attempts+=1
        try:
            result=decode(source_ref,path,start_seconds=left,end_seconds=right,**decode_options)
        except FrameBoundExceeded:
            middle=float((Fraction(str(left))+Fraction(str(right)))/2)
            if not left<middle<right:
                pending.append((left,right))
                break
            # Stack right first so the next emitted window remains chronological.
            pending.extend(((middle,right),(left,middle)))
            continue
        yield {'status':'DECODED_REQUEST_NOT_OBSERVATION','decoded':result}
        del result
    yield {'status':'REQUESTS_ONLY_NOT_OBSERVED','attempts':attempts,
           'unprocessed_intervals':list(reversed(pending)),
           'complete_requests':not pending,'source_attestation':'CALLER_SUPPLIED'}
