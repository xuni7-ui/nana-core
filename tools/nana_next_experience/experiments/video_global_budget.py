"""Experimental global candidate budget across overlapping video windows."""
from fractions import Fraction
import math

from tools.nana_next_experience.experiments.video_coverage import Candidate
from tools.nana_next_experience.experiments.video_coverage_refine import refine


def select_windows(source_ref, duration, window_results, *, budget, max_gap):
    """Select PTS-deduplicated candidates; this never proves video was observed.

    Window results and duration are caller-supplied. Equal source IDs and PTS
    do not establish equal input bytes, authorization, or source validity. The
    referenced decoded window must remain available to produce each image.
    """
    if (type(source_ref) is not str or not 1<=len(source_ref)<=128 or
            type(duration) not in (int,float) or not math.isfinite(duration) or not 0<duration<=86400 or
            type(window_results) not in (tuple,list) or not 1<=len(window_results)<=256 or
            type(budget) is not int or not 1<=budget<=256 or
            type(max_gap) not in (int,float) or not math.isfinite(max_gap) or max_gap<=0):
        raise ValueError('invalid global budget bounds')
    frames={};intervals=[];origin=None;time_base=None;size=None;source_size=None
    for window_index,window in enumerate(window_results):
        if (type(window) is not dict or window.get('source_ref')!=source_ref or
                window.get('status') not in ('WINDOW_CANDIDATES_ONLY','NO_NEW_FRAME_DECODED_NOT_OBSERVED') or
                window.get('whole_window_observed') is not False or
                type(window.get('requested_window')) is not tuple or len(window['requested_window'])!=2 or
                type(window.get('selected_frames')) is not list or len(window['selected_frames'])>256):
            raise ValueError('invalid window result')
        start,end=window['requested_window']
        if (any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,end)) or
                not 0<=start<end<=duration):raise ValueError('invalid window interval')
        intervals.append((start,end))
        if window['status']=='NO_NEW_FRAME_DECODED_NOT_OBSERVED':
            if window['selected_frames']:raise ValueError('empty window has frames')
            continue
        if (window.get('selection_state')!='CANDIDATES_NOT_DELIVERED' or
                window.get('timestamp_basis')!='container_relative' or
                window.get('coordinate_space')!='decoded_scaled_pixels_no_rotation' or
                type(window.get('decoded_size')) is not tuple or len(window['decoded_size'])!=2 or
                any(type(v) is not int or v<1 for v in window['decoded_size']) or
                type(window.get('source_size')) is not tuple or len(window['source_size'])!=2 or
                any(type(v) is not int or v<1 for v in window['source_size']) or
                not window['selected_frames']):
            raise ValueError('incompatible window geometry or state')
        try:window_origin=Fraction(window['timeline_origin'])
        except (KeyError,ValueError,TypeError,ZeroDivisionError) as exc:raise ValueError('invalid origin') from exc
        if origin is None:origin=window_origin;size=window['decoded_size'];source_size=window['source_size']
        if window_origin!=origin or window['decoded_size']!=size or window['source_size']!=source_size:
            raise ValueError('incompatible window origin or size')
        cues=window.get('selected_cues',[])
        if type(cues) is not list or len(cues)>len(window['selected_frames']):
            raise ValueError('invalid selected cues')
        cue_map={}
        for cue in cues:
            if (type(cue) is not dict or set(cue)!={'seconds','cues'} or
                    type(cue['seconds']) not in (int,float) or not math.isfinite(cue['seconds']) or
                    cue['seconds'] in cue_map or type(cue['cues']) is not list or
                    any(x not in ('dsh_cut','local_change_before','local_change_after') for x in cue['cues']) or
                    len(set(cue['cues']))!=len(cue['cues'])):
                raise ValueError('invalid selected cues')
            cue_map[cue['seconds']]=cue['cues']
        previous=None;local_times=set()
        for frame in window['selected_frames']:
            if type(frame) is not dict or set(frame)!={'seconds','pts_tick','time_base'}:
                raise ValueError('invalid selected frame')
            seconds=frame['seconds'];tick=frame['pts_tick'];base=frame['time_base']
            if (type(seconds) not in (int,float) or not math.isfinite(seconds) or
                    not start<=seconds<end or (previous is not None and seconds<=previous) or
                    type(tick) is not int or type(base) is not tuple or len(base)!=2 or
                    any(type(v) is not int or not 1<=v<=1000000000 for v in base) or
                    float(Fraction(tick*base[0],base[1])-origin)!=seconds):
                raise ValueError('invalid selected frame timestamp')
            previous=seconds;local_times.add(seconds)
            if time_base is None:time_base=base
            if base!=time_base:raise ValueError('incompatible time base')
            if seconds in frames and frames[seconds]['pts_tick']!=tick:
                raise ValueError('ambiguous candidate timestamp')
            record=frames.setdefault(seconds,{'seconds':seconds,'pts_tick':tick,'time_base':base,'window_indices':[],
                                               'cues':set()})
            record['window_indices'].append(window_index)
            record['cues'].update(cue_map.get(seconds,()))
            if len(frames)>10000:raise ValueError('global candidate bound exceeded')
        if not set(cue_map).issubset(local_times):raise ValueError('cue is not a selected frame')
    intervals.sort();unrequested=[];end=0
    for lo,hi in intervals:
        if lo>end:unrequested.append((end,lo))
        end=max(end,hi)
    if end<duration:unrequested.append((end,duration))
    if frames:
        selected=refine(duration,[Candidate(t,motion=1.0 if v['cues'] else 0.0)
                                  for t,v in frames.items()],budget,max_gap=max_gap)
        chosen=[{**frames[t],'cues':sorted(frames[t]['cues'])} for t in selected['timestamps']]
        gaps=selected['gaps'];gap_target=selected['coverage_target_met']
    else:
        chosen=[];gaps=((0.0,duration),) if duration>max_gap else ();gap_target=False
    return {'schema_version':1,'source_ref':source_ref,'source_attestation':'CALLER_SUPPLIED_UNVERIFIED',
            'duration_basis':'CALLER_SUPPLIED_UNVERIFIED','selected_frames':chosen,
            'candidate_count':len(frames),'candidate_deduplication':'PTS_ONLY_BYTES_UNVERIFIED',
            'model_frame_budget':budget,'unrequested_intervals':unrequested,
            'sampling_gaps_over_threshold':gaps,'sampling_gap_target_met':gap_target,
            'whole_video_observed':False,'state':'CANDIDATES_NOT_DELIVERED','model_calls':0}
