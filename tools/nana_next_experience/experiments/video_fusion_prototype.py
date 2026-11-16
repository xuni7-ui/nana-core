"""Combine two measured candidate signals under explicit sampling constraints.

This is not wired to a platform, Provider, Store, or Subject. Source identity,
authorization and withdrawal belong to the trusted caller and original Core.
"""
import math
from tools.nana_next_experience.experiments.video_coverage import Candidate
from tools.nana_next_experience.experiments.video_coverage_refine import refine


def fuse(source_ref, duration, decoded_timestamps, dsh, pairs, *, budget, max_gap):
    """Return only candidate times from actual decoded input, never observations.

    dsh contributes original cut timestamps; local pairs contribute both sides.
    Scores mean 'a measured cue is present', not semantic value. The caller
    must bind all three inputs to one original source and enforce model budget.
    """
    if (type(source_ref) is not str or not 1<=len(source_ref)<=128 or
            type(decoded_timestamps) not in (list,tuple) or not 1<=len(decoded_timestamps)<=1200 or
            type(dsh) is not dict or type(pairs) is not dict or
            dsh.get('source_ref')!=source_ref or pairs.get('source_ref')!=source_ref or
            dsh.get('qualification')!='LOCAL_PIPELINE_OUTPUT_ONLY' or pairs.get('schema_version')!=1):
        raise ValueError('unverified candidate source or bounds')
    if (type(duration) not in (int,float) or not math.isfinite(duration) or duration<=0 or
            type(budget) is not int or not 1<=budget<=256 or
            type(max_gap) not in (int,float) or not math.isfinite(max_gap) or max_gap<=0):
        raise ValueError('invalid video planning bounds')
    known=set();previous=-1
    for t in decoded_timestamps:
        if type(t) not in (int,float) or not math.isfinite(t) or not 0<=t<=duration or t<=previous:
            raise ValueError('invalid decoded timestamps')
        known.add(t);previous=t
    positions={t:i for i,t in enumerate(decoded_timestamps)}
    dsh_items=dsh.get('selected');pair_items=pairs.get('proposals')
    if (type(dsh_items) is not list or len(dsh_items)>1200 or
            type(pair_items) is not list or len(pair_items)>64 or type(pairs.get('truncated')) is not bool):
        raise ValueError('invalid measured candidate list')
    evidence={};seen_dsh=set();seen_pairs=set()
    for item in dsh_items:
        if type(item) is not dict:raise ValueError('invalid dsh item')
        t=item.get('seconds')
        if type(t) not in (int,float) or not math.isfinite(t) or t not in known or t in seen_dsh:
            raise ValueError('dsh timestamp was not decoded or is duplicate')
        seen_dsh.add(t)
        if item.get('reason')=='cut':evidence.setdefault(t,set()).add('dsh_cut')
    for item in pair_items:
        if type(item) is not dict:raise ValueError('invalid change pair')
        a=item.get('before_seconds');b=item.get('after_seconds')
        if (type(a) not in (int,float) or type(b) not in (int,float) or
                not math.isfinite(a) or not math.isfinite(b) or a not in known or b not in known):
            raise ValueError('change pair timestamp was not decoded')
        if positions[b]!=positions[a]+1 or (a,b) in seen_pairs:
            raise ValueError('change pair is not an adjacent unique input pair')
        seen_pairs.add((a,b))
        evidence.setdefault(a,set()).add('local_change_before')
        evidence.setdefault(b,set()).add('local_change_after')
    candidate=[Candidate(t,motion=1.0 if t in evidence else 0.0) for t in decoded_timestamps]
    selected=refine(duration,candidate,budget,max_gap=max_gap)
    return {'schema_version':1,'source_ref':source_ref,'source_attestation':'CALLER_SUPPLIED',
        'timestamps':selected['timestamps'],'gaps':selected['gaps'],
        'coverage_target_met':selected['coverage_target_met'],
        'selected_cues':[{'seconds':t,'cues':sorted(evidence.get(t,()))} for t in selected['timestamps']],
        'pair_proposals_truncated':pairs['truncated'],'dsh_frame_limit':'PER_SHEET_ONLY',
        'model_frame_budget':budget,'model_calls':0,'storage':'NONE',
        'meaning':'candidate sampling only; no semantic importance or source authorization inferred'}
