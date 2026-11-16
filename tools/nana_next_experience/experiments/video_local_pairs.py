"""Bounded local-change proposals linking both sides of each measured pair."""
import math
from tools.nana_next_experience.experiments.video_local_change import local_change


def propose(source_ref, frames, *, max_proposals=64):
    """Return input-timestamped local change pairs, never semantic facts.

    frames is a sequence of (seconds, PIL image), already obtained by a
    trusted caller. The caller owns source identity/privacy and revalidation.
    No frame bytes or text are returned or retained.
    """
    if (type(source_ref) is not str or not 1<=len(source_ref)<=128 or
            type(frames) not in (list,tuple) or not 2<=len(frames)<=1200 or
            type(max_proposals) is not int or not 1<=max_proposals<=64):
        raise ValueError('invalid source or pair bounds')
    previous=-1;size=None
    for row in frames:
        if (type(row) not in (list,tuple) or len(row)!=2 or
                type(row[0]) not in (int,float) or not math.isfinite(row[0]) or
                not 0<=row[0]<=86400 or row[0]<=previous or not hasattr(row[1],'size')):
            raise ValueError('invalid or unordered frame')
        previous=row[0]
        if size is None:size=row[1].size
        if row[1].size!=size:raise ValueError('frame geometry mismatch')
    width,height=size
    if width<1 or height<1 or width*height>262144 or width*height*len(frames)>64000000:
        raise ValueError('frame resource bound')
    observed=[]
    for (before_time,before),(after_time,after) in zip(frames,frames[1:]):
        change=local_change(before,after)
        if change is None:continue
        item={'before_seconds':before_time,'after_seconds':after_time,
              'source_box':change['box'],'coordinate_space':'input_pixels',
              'changed_pixels':change['changed_pixels']}
        observed.append(item)
    proposals=observed
    if len(observed)>max_proposals:
        # Allocate by time first; a dense early burst cannot erase later events.
        start=frames[0][0];end=frames[-1][0];span=end-start
        buckets=[[] for _ in range(max_proposals)]
        for item in observed:
            index=min(max_proposals-1,int((item['after_seconds']-start)/span*max_proposals))
            buckets[index].append(item)
        picked=[]
        for index,bucket in enumerate(buckets):
            if not bucket:continue
            midpoint=start+(index+.5)*span/max_proposals
            picked.append(min(bucket,key=lambda x:(abs(x['after_seconds']-midpoint),x['after_seconds'])))
        # Fill spare slots in chronological order; metadata still reports loss.
        for item in observed:
            if len(picked)>=max_proposals:break
            if item not in picked:picked.append(item)
        proposals=sorted(picked,key=lambda x:x['after_seconds'])
    omitted=len(observed)-len(proposals)
    return {'schema_version':1,'source_ref':source_ref,'pairs_examined':len(frames)-1,
            'proposals':proposals,'omitted_proposals':omitted,'truncated':omitted>0,
            'source_attestation':'CALLER_SUPPLIED','storage':'NONE','model_calls':0,
            'meaning':'local changes only; neither meaning nor importance is inferred'}
