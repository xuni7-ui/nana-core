"""Project selected decoded frames into ephemeral image candidates, not observations."""
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import io
import math

from tools.nana_next_experience.experiments.video_pts_decode import DecodedFrames


@dataclass(frozen=True, repr=False)
class ImageCandidate:
    source_ref: str
    requested_window: tuple[float, float]
    source_seconds: float
    pts_tick: int
    time_base: tuple[int, int]
    timeline_origin: str
    output_size: tuple[int, int]
    pixel_sha256: str
    png: bytes = field(repr=False)
    source_attestation: str = 'CALLER_SUPPLIED_UNVERIFIED'
    state: str = 'CANDIDATE_NOT_INGESTED'


def selected_images(decoded, selection):
    """Yield in-memory PNGs with exact source timestamps and scaled-pixel hashes.

    Source IDs are caller assertions, not proof of byte identity, authorization,
    or continued source validity. The original platform/Store must establish and
    recheck these before any ingestion. No model or persistence is invoked.
    """
    from PIL import Image
    if (type(decoded) is not DecodedFrames or type(selection) is not dict or
            selection.get('status') != 'WINDOW_CANDIDATES_ONLY' or
            selection.get('selection_state') != 'CANDIDATES_NOT_DELIVERED' or
            selection.get('source_ref') != decoded.source_ref or
            selection.get('requested_window') != decoded.requested_window or
            selection.get('timeline_origin') != decoded.timeline_origin or
            selection.get('decoded_size') != decoded.output_size or
            decoded.coordinate_space != 'decoded_scaled_pixels_no_rotation' or
            type(decoded.requested_window) is not tuple or len(decoded.requested_window)!=2 or
            any(type(n) not in (int,float) or not math.isfinite(n) for n in decoded.requested_window) or
            not 0<=decoded.requested_window[0]<decoded.requested_window[1] or
            type(selection.get('selected_frames')) is not list or
            len(selection['selected_frames']) > 256 or
            type(decoded.output_size) is not tuple or len(decoded.output_size)!=2 or
            any(type(n) is not int or n<1 for n in decoded.output_size) or
            decoded.output_size[0]*decoded.output_size[1]>262144 or
            type(decoded.rgb24) is not bytes or type(decoded.timestamps) is not tuple or
            type(decoded.pts_ticks) is not tuple or len(decoded.timestamps)!=len(decoded.pts_ticks)):
        raise ValueError('incompatible decoded selection')
    size=decoded.output_size[0]*decoded.output_size[1]*3
    if len(decoded.rgb24)!=size*len(decoded.timestamps):raise ValueError('incomplete decoded pixels')
    if (type(decoded.time_base) is not tuple or len(decoded.time_base)!=2 or
            any(type(n) is not int or not 1<=n<=1000000000 for n in decoded.time_base)):
        raise ValueError('invalid time base')
    try:origin=Fraction(decoded.timeline_origin)
    except (ValueError,TypeError,ZeroDivisionError) as exc:raise ValueError('invalid origin') from exc
    indices={}
    for i,(seconds,tick) in enumerate(zip(decoded.timestamps,decoded.pts_ticks)):
        if (type(seconds) not in (int,float) or not math.isfinite(seconds) or type(tick) is not int or
                float(Fraction(tick*decoded.time_base[0],decoded.time_base[1])-origin)!=seconds or
                not decoded.requested_window[0]<=seconds<decoded.requested_window[1] or
                seconds in indices):
            raise ValueError('inconsistent source timestamp')
        indices[seconds]=i
    previous=None;validated=[]
    for selected in selection['selected_frames']:
        if type(selected) is not dict or set(selected)!={'seconds','pts_tick','time_base'}:
            raise ValueError('invalid selection')
        seconds=selected['seconds']
        if (type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds not in indices or
                (previous is not None and seconds<=previous) or
                selected['time_base']!=decoded.time_base or type(selected['pts_tick']) is not int or
                selected['pts_tick']!=decoded.pts_ticks[indices[seconds]]):
            raise ValueError('selected frame is not from decoded window')
        previous=seconds;validated.append((seconds,selected['pts_tick']))
    for seconds,tick in validated:
        i=indices[seconds];pixels=decoded.rgb24[i*size:(i+1)*size]
        stream=io.BytesIO();Image.frombytes('RGB',decoded.output_size,pixels).save(stream,format='PNG')
        yield ImageCandidate(decoded.source_ref,decoded.requested_window,seconds,tick,
            decoded.time_base,decoded.timeline_origin,decoded.output_size,hashlib.sha256(pixels).hexdigest(),
            stream.getvalue())
