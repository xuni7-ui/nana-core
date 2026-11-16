"""Experimental timing cross-check; never a transcript or source authority."""
import math
from bisect import bisect_left, bisect_right


def review(cues, acoustic, *, acoustic_source_id, timeline_aligned=False):
    """Compare source-identified caption spans to measured acoustic silence.

    Captions may describe silence, music or sound, so a flagged overlap is
    only a request to inspect evidence. No caption text is accepted/stored.
    timeline_aligned must be independently established by the caller.
    """
    if (type(acoustic_source_id) is not str or not 1<=len(acoustic_source_id)<=128 or
            type(timeline_aligned) is not bool or type(acoustic) is not dict):
        raise ValueError('source and alignment are required')
    duration=acoustic.get('duration')
    if type(duration) not in (int,float) or not math.isfinite(duration) or duration<=0:
        raise ValueError('invalid duration')
    state=acoustic.get('state')
    if state not in {'MEASURED','NO_AUDIO','INCOMPLETE'}:
        raise ValueError('invalid acoustic state')
    intervals=acoustic.get('silence_intervals')
    if type(intervals) is not list or len(intervals)>10000:
        raise ValueError('invalid intervals')
    previous=0.0
    for interval in intervals:
        if (type(interval) not in (list,tuple) or len(interval)!=2 or
                any(type(x) not in (int,float) or not math.isfinite(x) for x in interval)):
            raise ValueError('invalid silence interval')
        start,end=interval
        if not previous<=start<end<=duration:raise ValueError('invalid interval ordering')
        previous=end
    starts=[item[0] for item in intervals]; ends=[item[1] for item in intervals]
    prefix=[0.0]
    for start,end in intervals:prefix.append(prefix[-1]+end-start)
    if type(cues) not in (list,tuple) or len(cues)>10000:
        raise ValueError('invalid captions')
    output=[];ids=set()
    for cue in cues:
        if type(cue) is not dict or set(cue)!={'cue_id','source_id','start','end'}:
            raise ValueError('caption input must contain only source and time')
        cue_id=cue['cue_id'];source_id=cue['source_id'];start=cue['start'];end=cue['end']
        if (type(cue_id) is not str or not 1<=len(cue_id)<=128 or cue_id in ids or
                type(source_id) is not str or not 1<=len(source_id)<=128 or
                any(type(x) not in (int,float) or not math.isfinite(x) for x in (start,end)) or
                not 0<=start<=end<=duration):
            raise ValueError('invalid caption span')
        ids.add(cue_id)
        status='UNKNOWN';fraction=None
        if state=='MEASURED' and timeline_aligned and start<end:
            # Sorted, non-overlapping intervals permit exact range sums.
            left=bisect_right(ends,start);right=bisect_left(starts,end)
            if right-left<=8:
                # Preserve precision for very short captions and boundaries.
                overlap=sum(max(0,min(end,b)-max(start,a)) for a,b in intervals[left:right])
            else:
                overlap=prefix[right]-prefix[left]
                overlap-=max(0,start-starts[left])+max(0,ends[right-1]-end)
            overlap=max(0.0,min(end-start,overlap)) # floating-point roundoff
            fraction=overlap/(end-start)
            status='REVIEW_SILENCE_OVERLAP' if fraction>=0.8 else 'BELOW_SILENCE_REVIEW_THRESHOLD'
        output.append({'cue_id':cue_id,'caption_source_id':source_id,'acoustic_source_id':acoustic_source_id,
            'start':start,'end':end,'silence_overlap_fraction':fraction,'status':status,
            'meaning':'timing check only; not speech, subtitle correctness, or a fact'})
    return output


def review_storyboard(app, source_memory_id, *, scope, privacy_classes, acoustic,
                      acoustic_source_id, timeline_aligned=False):
    """Experiment against NanaLink v1's original-memory, read-only projection.

    The caller must independently validate the audio's source and timing;
    no cross-source or durable withdrawal guarantee is created by this helper.
    Each call re-reads the original source and obeys its access/withdrawal.
    """
    from nana_core.nanalink.video_handoff import storyboard_samples
    handoff=storyboard_samples(app,source_memory_id,scope=scope,privacy_classes=privacy_classes)
    if (handoff['schema_version']!=1 or not handoff['bounded_sample_input_valid'] or
            type(acoustic) is not dict or acoustic_source_id!=source_memory_id or
            acoustic.get('duration')!=handoff['duration_seconds']):
        raise ValueError('unverified source or timeline')
    cues=[]
    for row in handoff['subtitle_ranges']:
        if (row.get('source_memory_id')!=source_memory_id or row.get('source')!='PUBLISHER_SUBTITLE' or
                type(row.get('segment_index')) is not int or row['segment_index']<0):
            raise ValueError('invalid original subtitle lineage')
        cues.append({'cue_id':f"segment.{row['segment_index']}", 'source_id':source_memory_id,
                     'start':row['from_seconds'],'end':row['to_seconds']})
    return {'schema_version':1,'source_memory_id':source_memory_id,
            'scope':handoff['scope'],'privacy_class':handoff['privacy_class'],
            'origin':handoff['origin'],'bvid':handoff['bvid'],'cid':handoff['cid'],
            'event_time_us':handoff['event_time_us'],'observed_at_us':handoff['observed_at_us'],
            'account_binding':handoff['account_binding'],
            'timeline_alignment':'CALLER_ATTESTED' if timeline_aligned else 'UNKNOWN',
            'reviews':review(cues,acoustic,acoustic_source_id=acoustic_source_id,timeline_aligned=timeline_aligned),
            'storage':'NONE','network_calls':0,'model_calls':0}
