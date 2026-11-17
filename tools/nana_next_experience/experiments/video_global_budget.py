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
                    any(x not in ('dsh_cut','local_change_before','local_change_after','motion_onset') for x in cue['cues']) or
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


def project_window(global_selection, window, window_index):
    """Produce a selected_images-compatible view for one original window.

    The first window referencing an overlapping PTS owns its image candidate;
    a caller must preserve index order and the original decoded window. This
    view does not validate source bytes, authorization, or source lifetime.
    """
    if (type(global_selection) is not dict or global_selection.get('state')!='CANDIDATES_NOT_DELIVERED' or
            global_selection.get('whole_video_observed') is not False or
            type(global_selection.get('selected_frames')) is not list or
            type(global_selection.get('model_frame_budget')) is not int or
            not 1<=global_selection['model_frame_budget']<=256 or
            len(global_selection['selected_frames'])>global_selection['model_frame_budget'] or
            type(window_index) is not int or not 0<=window_index<256 or
            type(window) is not dict or window.get('status')!='WINDOW_CANDIDATES_ONLY' or
            window.get('selection_state')!='CANDIDATES_NOT_DELIVERED' or
            window.get('source_ref')!=global_selection.get('source_ref') or
            type(window.get('selected_frames')) is not list):
        raise ValueError('invalid global window projection')
    local=set()
    for frame in window['selected_frames']:
        if (type(frame) is not dict or set(frame)!={'seconds','pts_tick','time_base'} or
                type(frame['seconds']) not in (int,float) or not math.isfinite(frame['seconds']) or
                type(frame['pts_tick']) is not int or type(frame['time_base']) is not tuple or
                len(frame['time_base'])!=2 or any(type(n) is not int or n<1 for n in frame['time_base'])):
            raise ValueError('invalid local candidate')
        local.add((frame['seconds'],frame['pts_tick'],frame['time_base']))
    frames=[];previous=None
    for item in global_selection['selected_frames']:
        if (type(item) is not dict or type(item.get('window_indices')) is not list or
                not item['window_indices'] or
                any(type(i) is not int or not 0<=i<256 for i in item['window_indices']) or
                item['window_indices']!=sorted(set(item['window_indices'])) or
                type(item.get('seconds')) not in (int,float) or not math.isfinite(item['seconds']) or
                (previous is not None and item['seconds']<=previous) or
                type(item.get('pts_tick')) is not int or type(item.get('time_base')) is not tuple or
                len(item['time_base'])!=2 or any(type(n) is not int or n<1 for n in item['time_base'])):
            raise ValueError('invalid global candidate')
        previous=item['seconds']
        if window_index in item['window_indices'] and (item['seconds'],item['pts_tick'],item['time_base']) not in local:
            raise ValueError('global candidate not in referenced window')
        if item['window_indices'][0]==window_index:
            frames.append({k:item[k] for k in ('seconds','pts_tick','time_base')})
    return {'status':'WINDOW_CANDIDATES_ONLY','selection_state':'CANDIDATES_NOT_DELIVERED',
            'source_ref':window['source_ref'],'requested_window':window['requested_window'],
            'timeline_origin':window['timeline_origin'],'decoded_size':window['decoded_size'],
            'selected_frames':frames}
