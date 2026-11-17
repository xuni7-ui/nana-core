"""Optional relative-motion onset cues; not semantic or source authority."""
from statistics import median
import math


def propose(source_ref, frames, *, history_seconds=3, ratio=1.8, min_rate=8,
            cooldown_seconds=3, min_interval=.04, max_interval=1.5, max_proposals=64):
    """Find abrupt motion-rate increases relative to recent measured frames.

    Times are actual caller-supplied frame timestamps. Long/short frame gaps
    reset the baseline and are returned as unknown; no frames are invented.
    A cue can be noise, camera or background motion, not an important event.
    """
    from PIL import ImageFilter
    numbers=(history_seconds,ratio,min_rate,cooldown_seconds,min_interval,max_interval)
    if (type(source_ref) is not str or not 1<=len(source_ref)<=128 or
            type(frames) not in (list,tuple) or not 2<=len(frames)<=1200 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in numbers) or
            not 0<history_seconds<=60 or not 1<ratio<=100 or not 0<min_rate<=100000 or
            not 0<=cooldown_seconds<=60 or not 0<min_interval<max_interval<=60 or
            type(max_proposals) is not int or not 1<=max_proposals<=64):
        raise ValueError('invalid onset bounds')
    size=None;previous=-1
    for row in frames:
        if (type(row) not in (tuple,list) or len(row)!=2 or
                type(row[0]) not in (int,float) or not math.isfinite(row[0]) or
                not 0<=row[0]<=86400 or row[0]<=previous or not hasattr(row[1],'size')):
            raise ValueError('invalid onset frame')
        previous=row[0]
        if size is None:size=row[1].size
        if row[1].size!=size:raise ValueError('onset geometry mismatch')
    width,height=size
    if width<1 or height<1 or width*height>262144 or width*height*len(frames)>64000000:
        raise ValueError('onset frame resource bound')
    history=[];events=[];unknown=[];previous_time=None;previous_pixels=None;last_event=None
    for seconds,image in frames:
        pixels=image.convert('L').filter(ImageFilter.GaussianBlur(2)).tobytes()
        if previous_pixels is not None:
            dt=seconds-previous_time
            if not min_interval<=dt<=max_interval:
                unknown.append((previous_time,seconds));history.clear();last_event=None
            else:
                changes=[b-a for a,b in zip(previous_pixels,pixels)];shift=median(changes)
                rate=sum(abs(value-shift) for value in changes)/len(changes)/dt
                history=[item for item in history if 0<seconds-item[0]<=history_seconds]
                if len(history)>=3:
                    baseline=median(item[1] for item in history)
                    if (rate>=min_rate and rate>=ratio*max(baseline,1) and
                            (last_event is None or seconds-last_event>=cooldown_seconds)):
                        events.append({'seconds':seconds,'previous_seconds':previous_time,
                                       'rate':rate,'baseline_rate':baseline})
                        last_event=seconds
                history.append((seconds,rate))
        previous_time=seconds;previous_pixels=pixels
    return {'schema_version':1,'source_ref':source_ref,'input_size':size,'pairs_examined':len(frames)-1,
        'proposals':events[:max_proposals],'truncated':len(events)>max_proposals,
        'omitted_proposals':max(0,len(events)-max_proposals),'unknown_intervals':unknown,
        'meaning':'relative pixel motion only; not semantic importance or observed content',
        'source_attestation':'CALLER_SUPPLIED','model_calls':0,'storage':'NONE'}
