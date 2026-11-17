"""Apply B's isolated candidate fusion within one exact-PTS source window."""
from fractions import Fraction
import math
from tools.nana_next_experience.experiments.video_pts_decode import DecodedFrames
from tools.nana_next_experience.experiments.video_fusion_prototype import fuse


def fuse_window(decoded, dsh, pairs, *, budget, max_gap, onsets=None):
    """Rebase only for local planning, then return original PTS and coordinates.

    A decoded window, source ID and cue outputs are caller-supplied; this is
    not authentication, platform delivery, memory, or semantic observation.
    """
    if (type(decoded) is not DecodedFrames or type(decoded.requested_window) is not tuple or
            len(decoded.requested_window)!=2 or type(decoded.source_ref) is not str or
            not 1<=len(decoded.source_ref)<=128 or type(decoded.rgb24) is not bytes or
            type(decoded.timestamps) is not tuple or type(decoded.pts_ticks) is not tuple or
            type(decoded.output_size) is not tuple or len(decoded.output_size)!=2 or
            any(type(v) is not int or v<1 for v in decoded.output_size) or
            decoded.output_size[0]*decoded.output_size[1]>262144 or
            decoded.timestamp_basis!='container_relative' or
            type(decoded.duration_seconds) not in (int,float) or not math.isfinite(decoded.duration_seconds) or
            decoded.duration_seconds<=0 or type(decoded.source_size) is not tuple or len(decoded.source_size)!=2 or
            any(type(v) is not int or v<1 for v in decoded.source_size) or type(budget) is not int or not 1<=budget<=256 or
            type(max_gap) not in (int,float) or not math.isfinite(max_gap) or max_gap<=0):
        raise ValueError('invalid decoded window or budget')
    start,end=decoded.requested_window
    if (type(start) not in (int,float) or type(end) not in (int,float) or
            not math.isfinite(start) or not math.isfinite(end) or not 0<=start<end<=decoded.duration_seconds):
        raise ValueError('invalid window')
    if not decoded.timestamps:
        if decoded.rgb24 or decoded.pts_ticks or decoded.window_state!='NO_NEW_FRAME_DECODED_NOT_OBSERVED':
            raise ValueError('inconsistent empty window')
        return {'status':'NO_NEW_FRAME_DECODED_NOT_OBSERVED','source_ref':decoded.source_ref,
            'requested_window':(start,end),'selected_frames':[],'unknown_intervals':[(start,end)],
            'whole_window_observed':False,'model_calls':0,'storage':'NONE'}
    if (decoded.window_state!='FRAMES_DECODED_NOT_COVERAGE' or
            len(decoded.timestamps)!=len(decoded.pts_ticks) or
            len(decoded.rgb24)!=len(decoded.timestamps)*decoded.output_size[0]*decoded.output_size[1]*3 or
            type(dsh) is not dict or type(pairs) is not dict or
            dsh.get('source_ref')!=decoded.source_ref or pairs.get('source_ref')!=decoded.source_ref or
            type(dsh.get('input_size')) not in (tuple,list) or
            type(pairs.get('input_size')) not in (tuple,list) or
            tuple(dsh['input_size'])!=decoded.output_size or
            tuple(pairs['input_size'])!=decoded.output_size or
            type(dsh.get('input_frames')) is not int or dsh['input_frames']!=len(decoded.timestamps) or
            type(pairs.get('pairs_examined')) is not int or pairs['pairs_examined']!=len(decoded.timestamps)-1):
        raise ValueError('source or decoded frame mismatch')
    numerator,denominator=decoded.time_base
    if type(numerator) is not int or type(denominator) is not int or not 1<=numerator<=1000000000 or not 1<=denominator<=1000000000:
        raise ValueError('invalid source time base')
    try:origin=Fraction(decoded.timeline_origin);window_start=Fraction(str(start));window_end=Fraction(str(end))
    except (ValueError,ZeroDivisionError) as exc:raise ValueError('invalid source origin') from exc
    to_local={};to_global={};ticks_by_global={}
    for seconds,tick in zip(decoded.timestamps,decoded.pts_ticks):
        if type(tick) is not int:raise ValueError('invalid source pts')
        exact=Fraction(tick*numerator,denominator)-origin
        if not window_start<=exact<window_end or float(exact)!=seconds:
            raise ValueError('source pts or window mismatch')
        relative=float(exact-window_start)
        if relative in to_global:raise ValueError('ambiguous local timestamp')
        to_local[seconds]=relative;to_global[relative]=seconds;ticks_by_global[seconds]=tick
    def local_time(value):
        if type(value) not in (int,float) or not math.isfinite(value) or value not in to_local:
            raise ValueError('cue is not a decoded frame')
        return to_local[value]
    if (type(dsh.get('selected')) is not list or type(pairs.get('proposals')) is not list or
            any(type(item) is not dict or 'seconds' not in item for item in dsh['selected']) or
            any(type(item) is not dict or 'before_seconds' not in item or 'after_seconds' not in item
                for item in pairs['proposals'])):
        raise ValueError('invalid candidate inputs')
    local_dsh={**dsh,'selected':[{**item,'seconds':local_time(item['seconds'])} for item in dsh['selected']]}
    for item in pairs['proposals']:
        box=item.get('source_box')
        if box is not None and (type(box) not in (tuple,list) or len(box)!=4 or
                any(type(v) is not int for v in box) or not 0<=box[0]<box[2]<=decoded.output_size[0] or
                not 0<=box[1]<box[3]<=decoded.output_size[1]):
            raise ValueError('change box outside decoded frame')
    local_pairs={**pairs,'proposals':[{**item,'before_seconds':local_time(item['before_seconds']),
        'after_seconds':local_time(item['after_seconds'])} for item in pairs['proposals']]}
    local_onsets=None;unknown_onsets=[]
    if onsets is not None:
        if (type(onsets) is not dict or onsets.get('source_ref')!=decoded.source_ref or
                type(onsets.get('input_size')) not in (tuple,list) or tuple(onsets['input_size'])!=decoded.output_size or
                type(onsets.get('pairs_examined')) is not int or onsets['pairs_examined']!=len(decoded.timestamps)-1 or
                type(onsets.get('proposals')) is not list or type(onsets.get('unknown_intervals')) is not list or
                any(type(item) is not dict or 'seconds' not in item or 'previous_seconds' not in item
                    for item in onsets['proposals']) or
                len(onsets['unknown_intervals'])>len(decoded.timestamps)-1):
            raise ValueError('invalid onset source or geometry')
        positions={t:i for i,t in enumerate(decoded.timestamps)}
        for interval in onsets['unknown_intervals']:
            if (type(interval) not in (tuple,list) or len(interval)!=2 or
                    any(type(t) not in (int,float) or not math.isfinite(t) for t in interval) or
                    interval[0] not in positions or interval[1] not in positions or
                    positions[interval[1]]!=positions[interval[0]]+1):
                raise ValueError('invalid onset unknown interval')
            unknown_onsets.append(tuple(interval))
        local_onsets={**onsets,'proposals':[{**item,'seconds':local_time(item['seconds']),
            'previous_seconds':local_time(item['previous_seconds'])} for item in onsets['proposals']]}
    duration=float(window_end-window_start)
    result=fuse(decoded.source_ref,duration,[to_local[t] for t in decoded.timestamps],local_dsh,local_pairs,
                budget=budget,max_gap=max_gap,onsets=local_onsets)
    def global_time(value):
        if value==0:return start
        if value==duration:return end
        if value not in to_global:raise ValueError('planner returned unknown timestamp')
        return to_global[value]
    selected=[{'seconds':to_global[t],'pts_tick':ticks_by_global[to_global[t]],
               'time_base':decoded.time_base} for t in result['timestamps']]
    pair_refs=[{**item,'before_seconds':to_global[item['before_seconds']],
                'after_seconds':to_global[item['after_seconds']]} for item in result['selected_pair_refs']]
    cues=[{**item,'seconds':to_global[item['seconds']]} for item in result['selected_cues']]
    return {'schema_version':1,'status':'WINDOW_CANDIDATES_ONLY','source_ref':decoded.source_ref,
        'source_attestation':'CALLER_SUPPLIED','requested_window':(start,end),
        'timeline_origin':decoded.timeline_origin,'video_start':decoded.video_start,
        'timestamp_basis':decoded.timestamp_basis,'source_size':decoded.source_size,
        'decoded_size':decoded.output_size,'coordinate_space':decoded.coordinate_space,
        'selected_frames':selected,'selected_pair_refs':pair_refs,'selected_cues':cues,
        'unobserved_sampling_gaps':[(global_time(a),global_time(b)) for a,b in result['gaps']],
        'coverage_target_met':result['coverage_target_met'],'whole_window_observed':False,
        'gap_definition':'ONLY_GAPS_OVER_REQUESTED_THRESHOLD',
        'pair_proposals_truncated':result['pair_proposals_truncated'],
        'onset_proposals_truncated':result['onset_proposals_truncated'],'onset_unknown_intervals':unknown_onsets,
        'dsh_dropped_sheets':result['dsh_dropped_sheets'],
        'selection_state':'CANDIDATES_NOT_DELIVERED','model_calls':0,'storage':'NONE'}
