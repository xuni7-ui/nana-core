"""Small local-video perception API; no Nana Core, network or model required."""
import json
import math
from pathlib import Path
import time

from .video_audio_probe import AudioProbeOutputBound, AudioProbeUnavailable, _run_bounded, measure
from .video_coverage import Candidate, plan
from .video_ffmpeg_probe import probe
from .video_local_change import local_change
from .video_pts_decode import decode


def perceive_video(path, *, question=None, time_range=None, frame_budget=8,
                   max_runtime_seconds=90, transcriber=None):
    """Return in-memory PNGs, source-relative timestamps and qualified signals.

    `transcriber`, if supplied, is a caller-controlled function receiving
    (absolute_path, start_seconds, end_seconds); it must enforce its own time,
    privacy and cost limits. No transcriber or model is downloaded or invoked
    by default. The question is carried as context, not interpreted locally.
    FFmpeg subprocesses use the remaining wall budget; the whole call is a
    best-effort deadline, not an OS-level sandbox or hard real-time limit.
    """
    started=time.monotonic()
    if (type(frame_budget) is not int or not 1<=frame_budget<=32 or
            type(max_runtime_seconds) not in (int,float) or not math.isfinite(max_runtime_seconds) or
            not 1<=max_runtime_seconds<=300 or
            (question is not None and (type(question) is not str or len(question)>2000)) or
            (transcriber is not None and not callable(transcriber))):
        raise ValueError('invalid perception request')
    path=Path(path).resolve(strict=True)
    if not path.is_file() or not 1<=path.stat().st_size<=256*1024*1024:
        raise ValueError('invalid local media file')
    deadline=started+max_runtime_seconds
    def remaining():
        value=deadline-time.monotonic()
        if value<=0:raise TimeoutError('processing budget exhausted')
        return value
    def run(args,*,limit=1_000_000,timeout=None):
        return _run_bounded(args,timeout=min(remaining(),timeout or remaining()),
                            stdout_limit=limit,stderr_limit=100_000)
    try:
        meta=json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe',
            '-show_entries','format=duration,start_time:stream=index,codec_type,codec_name',
            '-of','json',str(path)],limit=100_000).stdout)
        duration=float(meta['format']['duration']);streams=meta['streams']
        if not math.isfinite(duration) or not 0<duration<=86400 or not any(s.get('codec_type')=='video' for s in streams):
            raise ValueError('invalid video duration or stream')
    except (AudioProbeUnavailable,AudioProbeOutputBound,KeyError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError('video metadata unavailable') from exc
    if time_range is None:start,end=0.0,duration
    elif (type(time_range) in (tuple,list) and len(time_range)==2 and
          all(type(x) in (int,float) and math.isfinite(x) for x in time_range) and
          0<=time_range[0]<time_range[1]<=duration):start,end=map(float,time_range)
    else:raise ValueError('invalid target time range')

    # Existing scdet scan is useful on short zero-origin clips. Long clips use
    # distributed windows; a request is never counted as an observed interval.
    selected=[];scan='NOT_RUN_LONG_OR_OFFSET';scan_details=None;errors=[]
    origin=float(meta['format'].get('start_time') or 0)
    if duration<=30 and abs(origin)<=0.001 and deadline-time.monotonic()>3:
        try:
            sample=probe(path,timeout=min(15,remaining()/2))
            scan='COMPLETE' if sample['scan_complete'] else 'PARTIAL_OR_UNQUALIFIED'
            scan_details={'frames_measured':sample['frames_measured'],'frames_scored':sample['frames_scored']}
            candidates=[Candidate(c.seconds-start,cut=c.cut) for c in sample['candidates'] if start<=c.seconds<end]
            if candidates:
                selection=plan(end-start,candidates,frame_budget,max_gap=max((end-start)*2/frame_budget,0.001))
                scores={c.seconds:c.cut for c in candidates}
                selected=[(start+t,scores[t]) for t in selection['timestamps']]
        except (ValueError,TimeoutError,AudioProbeUnavailable,AudioProbeOutputBound):
            scan='UNAVAILABLE_OR_BUDGET';errors.append('SCENE_SCAN_UNAVAILABLE')
    if not selected:
        last=max(start,end-min(1.0,(end-start)/2))
        selected=[((start+last)/2,None)] if frame_budget==1 else [
            (start+(last-start)*i/(frame_budget-1),None) for i in range(frame_budget)]
    frames=[];attempted=[];seen_frames=set()
    for target,score in selected:
        if time.monotonic()>=deadline:errors.append('PROCESSING_BUDGET_EXHAUSTED');break
        stop=min(end,target+1.0)
        if stop<=target:continue
        attempted.append((target,stop))
        try:
            result=decode('local.video',path,width=160,height=90,start_seconds=target,end_seconds=stop,
                          max_frames=1200,timeout=remaining())
            if not result.timestamps:
                errors.append('NO_FRAME_IN_REQUEST_WINDOW');continue
            identity=(result.pts_ticks[0],result.time_base,result.timeline_origin)
            if identity in seen_frames:continue
            seen_frames.add(identity)
            from PIL import Image
            import io
            stream=io.BytesIO();Image.frombytes('RGB',result.output_size,result.rgb24[:160*90*3]).save(stream,format='PNG')
            frames.append({'time_seconds':result.timestamps[0],'pts_tick':result.pts_ticks[0],
                           'time_base':result.time_base,'timeline_origin':result.timeline_origin,
                           'png':stream.getvalue(),'scene_change_score':score,'scene_candidate_seconds':target if score is not None else None,
                           'scene_score_qualification':('UNKNOWN' if score is None else
                               'SAME_FRAME_NOT_SEMANTIC' if result.timestamps[0]==target else
                               'SCAN_CANDIDATE_DIFFERS_FROM_OUTPUT_FRAME')})
        except (ValueError,TimeoutError,OSError):errors.append('FRAME_WINDOW_UNAVAILABLE')

    subtitle_stream=next((s for s in streams if s.get('codec_type')=='subtitle'),None)
    subtitles={'state':'NO_EMBEDDED_SUBTITLE','format':None,'text':None}
    if subtitle_stream:
        subtitles={'state':'UNAVAILABLE_OR_BUDGET','format':None,'text':None}
        try:
            raw=run(['ffmpeg','-v','error','-protocol_whitelist','file,pipe','-i',str(path),
                     '-map','0:s:0','-f','webvtt','pipe:1'],limit=1_000_000,timeout=10).stdout
            subtitles={'state':'AVAILABLE_FULL_TRACK_NOT_RANGE_FILTERED','format':'webvtt',
                       'text':raw.decode('utf-8',errors='strict'),'codec':subtitle_stream.get('codec_name')}
        except (ValueError,TimeoutError,UnicodeError,AudioProbeUnavailable,AudioProbeOutputBound):
            errors.append('SUBTITLE_UNAVAILABLE')
    audio={'state':'NOT_RUN_NO_TIME'}
    if not any(s.get('codec_type')=='audio' for s in streams):audio={'state':'NO_AUDIO'}
    elif time.monotonic()<deadline and end-start<=600:
        try:audio=measure(path,start_seconds=start,end_seconds=end,timeout=min(15,remaining()/2))
        except (ValueError,TimeoutError,OSError):audio={'state':'UNAVAILABLE_OR_BUDGET'};errors.append('AUDIO_PROBE_UNAVAILABLE')
    elif end-start>600:audio={'state':'NOT_RUN_RANGE_EXCEEDS_600_SECONDS'}
    transcript={'state':'NOT_RUN_NO_TRANSCRIBER','text':None}
    if transcriber is not None and time.monotonic()<deadline:
        try:
            text=transcriber(path,start,end)
            if type(text) is not str or len(text)>1_000_000:raise ValueError('invalid transcription')
            transcript={'state':'CALLER_TRANSCRIBER_UNVERIFIED','text':text}
        except Exception:
            transcript={'state':'TRANSCRIBER_FAILED','text':None};errors.append('TRANSCRIBER_FAILED')
    elif transcriber is not None:
        transcript={'state':'NOT_RUN_BUDGET','text':None}
    # Sparse-frame differences are cues, not continuous motion measurements.
    from PIL import Image,ImageChops,ImageStat
    import io
    changes=[]
    for before,after in zip(frames,frames[1:]):
        with Image.open(io.BytesIO(before['png'])) as a, Image.open(io.BytesIO(after['png'])) as b:
            difference=ImageStat.Stat(ImageChops.difference(a.convert('L'),b.convert('L'))).mean[0]
            local=local_change(a,b)
        changes.append({'from_seconds':before['time_seconds'],'to_seconds':after['time_seconds'],
                        'mean_gray_difference':difference,'local_change':local,
                        'qualification':'SPARSE_FRAME_DIFFERENCE_NOT_CONTINUOUS_MOTION'})
    points=sorted({f['time_seconds'] for f in frames});gaps=[];previous=start
    for point in points:
        if point>previous:gaps.append((previous,point))
        previous=point
    if previous<end:gaps.append((previous,end))
    outside=[]
    if start>0:outside.append((0.0,start))
    if end<duration:outside.append((end,duration))
    elapsed=time.monotonic()-started
    subtitle_bytes=len((subtitles.get('text') or '').encode('utf-8'))
    transcript_bytes=len((transcript.get('text') or '').encode('utf-8'))
    png_bytes=sum(len(f['png']) for f in frames)
    return {'schema_version':1,'duration_seconds':duration,'target_range':(start,end),'question':question,
            'question_use':'CONTEXT_ONLY_NOT_USED_FOR_SELECTION',
            'frames':frames,'scene_scan':scan,'scene_scan_details':scan_details,'requested_windows':attempted,
            'sparse_visual_changes':changes,
            'unobserved_intervals':gaps,'outside_requested_intervals':outside,
            'coverage':'POINT_SAMPLES_ONLY_NOT_CONTINUOUS_OBSERVATION',
            'subtitles':subtitles,'audio':audio,'transcript':transcript,'errors':errors,
            'elapsed_seconds':elapsed,'output_png_bytes':png_bytes,
            'output_sizes':{'png_bytes':png_bytes,'subtitle_utf8_bytes':subtitle_bytes,'transcript_utf8_bytes':transcript_bytes,
                            'media_and_text_bytes':png_bytes+subtitle_bytes+transcript_bytes},
            'budget':{'frame_limit':frame_budget,'wall_seconds_best_effort':max_runtime_seconds,
                      'deadline_exceeded':elapsed>max_runtime_seconds},
            'meaning':'local technical cues only; not semantic understanding or source authorization'}
