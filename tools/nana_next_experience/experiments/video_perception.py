"""Small local-video perception API; no Nana Core, network or model required."""
import json
import math
import base64
from pathlib import Path
import re
import time

from .video_audio_probe import AudioProbeOutputBound, AudioProbeUnavailable, _run_bounded, measure
from .video_coverage import Candidate, plan
from .video_ffmpeg_probe import probe
from .video_local_change import local_change
from .video_pts_decode import decode
from .video_text_tools import pocketsphinx_asr, tesseract_ocr


def _focus_candidates(question, subtitles, start, end):
    """Find explicit timestamps and simple text matches; not semantic search."""
    if not question:return []
    points=[]
    for minutes,seconds in re.findall(r'(?<!\d)(\d{1,3}):(\d{2}(?:\.\d+)?)(?!\d)',question):
        value=int(minutes)*60+float(seconds)
        if start<=value<end:points.append((value,'QUESTION_TIMESTAMP'))
    for value in re.findall(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|秒)\b',question,re.I):
        value=float(value)
        if start<=value<end:points.append((value,'QUESTION_TIMESTAMP'))
    terms=_question_terms(question)
    if subtitles and terms:
        def seconds(value):
            parts=value.split(':');return sum(float(part)*60**i for i,part in enumerate(reversed(parts)))
        for block in re.split(r'\n\s*\n',subtitles):
            match=re.search(r'((?:\d{2}:)?\d{2}:\d{2}\.\d{3})\s*-->\s*((?:\d{2}:)?\d{2}:\d{2}\.\d{3})',block)
            if match and any(term in block.casefold() for term in terms):
                a,b=seconds(match.group(1)),seconds(match.group(2));point=max(start,a)+(min(end,b)-max(start,a))/2
                if max(start,a)<min(end,b):points.append((point,'QUESTION_SUBTITLE_MATCH'))
    return points


def _question_terms(question):
    ignored={'what','when','where','which','does','show','video','there','about','字幕','画面','视频','出现','什么'}
    return [term.casefold() for term in re.findall(r'[A-Za-z0-9_]{2,}|[\u4e00-\u9fff]{2,}',question or '')
            if term.casefold() not in ignored]


def _bounded_model_context(context, limit=16000):
    """Preserve coverage and status when long text exceeds the model context budget."""
    text=json.dumps(context,ensure_ascii=False,separators=(',',':'))
    if len(text)<=limit:return text,False
    kept=('video_duration_seconds','target_range_seconds','coverage','unobserved_intervals',
          'outside_requested_intervals','subtitle_state','transcript_state','transcript_timeline_basis',
          'transcript_processed_window','transcript_truncated','errors','warnings')
    compact={key:context[key] for key in kept}
    compact['model_context_omitted_fields']=['transcript_words','ocr_probes_not_delivered_as_images',
                                               'sparse_visual_changes']
    values={'question':context['question'],'subtitles_excerpt':context['subtitles_full_track'],
            'transcript_excerpt':context['transcript']}
    caps={'question':2000,'subtitles_excerpt':12000,'transcript_excerpt':12000}
    while True:
        omitted={}
        for key,value in values.items():
            if value is None:
                compact[key]=None
                continue
            cap=caps[key]
            compact[key]=value if len(value)<=cap else (value[:(cap+1)//2]+'\n[... omitted ...]\n'+
                                                        (value[-(cap//2):] if cap//2 else '') if cap else '')
            omitted[key]=max(0,len(value)-cap)
        compact['excerpt_omitted_characters']=omitted
        text=json.dumps(compact,ensure_ascii=False,separators=(',',':'))
        if len(text)<=limit:return text,True
        key=max(caps,key=lambda k:min(caps[k],len(values[k] or '')))
        if not values[key] or caps[key]==0:raise ValueError('model context metadata exceeds bound')
        caps[key]//=2


def perceive_video(path, *, question=None, time_range=None, frame_budget=8,
                   max_runtime_seconds=90, transcriber=None, ocr=False, ocr_language='eng', ocr_data_dir=None,
                   asr=None, focus_times=(), sampling='adaptive', model_content=False,
                   ocr_probe_budget=0, focus_terms=(), asr_max_seconds=30, output_size=(160,90)):
    """Return in-memory PNGs, source-relative timestamps and qualified signals.

    `transcriber`, if supplied, is a caller-controlled function receiving
    (absolute_path, start_seconds, end_seconds); it must enforce its own time,
    privacy and cost limits. No transcriber or model is downloaded or invoked
    by default. Questions can guide sampling only through explicit time or
    literal subtitle matches; OCR/ASR are optional locally installed tools.
    FFmpeg subprocesses use the remaining wall budget; the whole call is a
    best-effort deadline, not an OS-level sandbox or hard real-time limit.
    """
    started=time.monotonic()
    if (type(frame_budget) is not int or not 1<=frame_budget<=32 or
            type(max_runtime_seconds) not in (int,float) or not math.isfinite(max_runtime_seconds) or
            not 1<=max_runtime_seconds<=300 or
            (question is not None and (type(question) is not str or len(question)>2000)) or
            (transcriber is not None and not callable(transcriber)) or type(ocr) is not bool or type(model_content) is not bool or
            asr not in (None,'pocketsphinx') or sampling not in ('adaptive','uniform') or (asr is not None and transcriber is not None) or
            type(ocr_probe_budget) is not int or not 0<=ocr_probe_budget<=32 or (ocr_probe_budget and not ocr) or
            type(output_size) not in (tuple,list) or len(output_size)!=2 or
            any(type(v) is not int or not 1<=v<=1024 for v in output_size) or output_size[0]*output_size[1]>262144 or
            type(asr_max_seconds) not in (int,float) or not math.isfinite(asr_max_seconds) or not 1<=asr_max_seconds<=120 or
            type(focus_terms) not in (tuple,list) or len(focus_terms)>16 or
            any(type(t) is not str or not 1<=len(t)<=64 for t in focus_terms) or
            type(focus_times) not in (tuple,list) or len(focus_times)>16 or
            any(type(t) not in (int,float) or not math.isfinite(t) for t in focus_times)):
        raise ValueError('invalid perception request')
    path=Path(path).resolve(strict=True)
    output_width,output_height=output_size
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
    if any(not start<=t<end for t in focus_times):raise ValueError('focus time outside target range')

    errors=[]
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
    # Existing scdet scan is useful on short zero-origin clips. Long clips use
    # distributed windows; a request is never counted as an observed interval.
    selected=[];scan='NOT_RUN_UNIFORM_REQUESTED' if sampling=='uniform' else 'NOT_RUN_LONG_OR_OFFSET';scan_details=None;warnings=[]
    origin=float(meta['format'].get('start_time') or 0)
    if sampling=='adaptive' and duration<=30 and abs(origin)<=0.001 and deadline-time.monotonic()>3:
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
    selected=[(t,score,'COVERAGE_OR_SCENE') for t,score in selected]
    # A small part of the same output budget can follow explicit timestamps or
    # literal subtitle matches. This is not a semantic answer to the question.
    hints=[(t,'CALLER_FOCUS_TIME') for t in focus_times if start<=t<end]
    hints+=_focus_candidates(question,subtitles.get('text') if abs(origin)<=0.001 else None,start,end)
    # Optional bounded OCR exploration. It consumes a separate
    # processing budget; only the matched point competes for an output frame.
    ocr_probes=[];terms=[t.casefold() for t in focus_terms] or _question_terms(question)
    if ocr_probe_budget and terms and not hints:
        last=max(start,end-min(1.0,(end-start)/2))
        targets=[(start+last)/2] if ocr_probe_budget==1 else [
            start+(last-start)*i/(ocr_probe_budget-1) for i in range(ocr_probe_budget)]
        for target in targets:
            if time.monotonic()>=deadline:break
            stop=min(end,target+1.0)
            retry=None
            try:
                try:
                    decoded=decode('local.video',path,width=output_width,height=output_height,start_seconds=target,end_seconds=stop,
                                   max_frames=1200,timeout=remaining())
                except ValueError as exc:
                    retry=math.ceil((target+1e-9)*10)/10
                    if str(exc)!='decoded frame outside requested window' or retry>=stop:raise
                    decoded=decode('local.video',path,width=output_width,height=output_height,start_seconds=retry,end_seconds=stop,
                                   max_frames=1200,timeout=remaining())
            except (ValueError,TimeoutError,OSError):
                ocr_probes.append({'requested_seconds':target,'state':'FRAME_UNAVAILABLE',
                                   'retry_start_seconds':retry})
                continue
            if not decoded.timestamps:
                ocr_probes.append({'requested_seconds':target,'state':'NO_FRAME',
                                   'retry_start_seconds':retry});continue
            try:
                from PIL import Image
                import io
                stream=io.BytesIO();Image.frombytes('RGB',decoded.output_size,decoded.rgb24[:output_width*output_height*3]).save(stream,format='PNG')
                text=tesseract_ocr(stream.getvalue(),language=ocr_language,timeout=min(15,remaining()),tessdata_dir=ocr_data_dir)
                matched=any(term in text.casefold() for term in terms)
                ocr_probes.append({'requested_seconds':target,'time_seconds':decoded.timestamps[0],
                                   'state':'TESSERACT_UNVERIFIED','matched':matched,
                                   'retry_start_seconds':retry})
                if matched:
                    hints.append((decoded.timestamps[0],'QUESTION_OCR_MATCH'));break
            except (ValueError,TimeoutError,OSError):
                ocr_probes.append({'requested_seconds':target,'state':'OCR_UNAVAILABLE',
                                   'retry_start_seconds':retry})
                break
    used=set();applied=0;applied_times=[]
    for target,reason in hints:
        if applied>=max(1,frame_budget//4):break
        if any(abs(target-t)<0.25 for t in applied_times):continue
        available=[i for i in range(len(selected)) if i not in used]
        if not available:break
        index=min(available,key=lambda i:abs(selected[i][0]-target))
        selected[index]=(target,None,reason);used.add(index);applied+=1;applied_times.append(target)
    selected.sort(key=lambda item:item[0])
    frames=[];attempted=[];seen_frames=set()
    for target,score,reason in selected:
        if time.monotonic()>=deadline:errors.append('PROCESSING_BUDGET_EXHAUSTED');break
        stop=min(end,target+1.0)
        if stop<=target:continue
        attempted.append((target,stop))
        try:
            try:
                result=decode('local.video',path,width=output_width,height=output_height,start_seconds=target,end_seconds=stop,
                              max_frames=1200,timeout=remaining())
            except ValueError as exc:
                # Some seek/trim timebases round a frame just outside a decimal
                # boundary. Never accept it; retry from a later 0.1s boundary.
                retry=math.ceil((target+1e-9)*10)/10
                if str(exc)!='decoded frame outside requested window' or retry>=stop:raise
                attempted.append((retry,stop))
                result=decode('local.video',path,width=output_width,height=output_height,start_seconds=retry,end_seconds=stop,
                              max_frames=1200,timeout=remaining())
                warnings.append('FRAME_WINDOW_RETRIED_WITH_LATER_START')
            if not result.timestamps:
                errors.append('NO_FRAME_IN_REQUEST_WINDOW');continue
            identity=(result.pts_ticks[0],result.time_base,result.timeline_origin)
            if identity in seen_frames:continue
            seen_frames.add(identity)
            from PIL import Image
            import io
            stream=io.BytesIO();Image.frombytes('RGB',result.output_size,result.rgb24[:output_width*output_height*3]).save(stream,format='PNG')
            frames.append({'time_seconds':result.timestamps[0],'pts_tick':result.pts_ticks[0],
                           'time_base':result.time_base,'timeline_origin':result.timeline_origin,
                           'selection_reason':reason,
                           'png':stream.getvalue(),'scene_change_score':score,'scene_candidate_seconds':target if score is not None else None,
                           'scene_score_qualification':('UNKNOWN' if score is None else
                               'SAME_FRAME_NOT_SEMANTIC' if result.timestamps[0]==target else
                               'SCAN_CANDIDATE_DIFFERS_FROM_OUTPUT_FRAME')})
        except (ValueError,TimeoutError,OSError):errors.append('FRAME_WINDOW_UNAVAILABLE')

    if ocr:
        for frame in frames:
            if time.monotonic()>=deadline:
                frame['ocr']={'state':'NOT_RUN_BUDGET','text':None};continue
            try:
                text=tesseract_ocr(frame['png'],language=ocr_language,timeout=min(15,remaining()),tessdata_dir=ocr_data_dir)
                frame['ocr']={'state':'TESSERACT_UNVERIFIED','text':text,'language':ocr_language}
            except (ValueError,TimeoutError,OSError):
                frame['ocr']={'state':'OCR_UNAVAILABLE','text':None};errors.append('OCR_UNAVAILABLE')
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
    elif asr=='pocketsphinx':
        if audio['state']=='NO_AUDIO':transcript={'state':'NO_AUDIO','text':None}
        elif time.monotonic()>=deadline:transcript={'state':'NOT_RUN_BUDGET','text':None}
        else:
            try:transcript=pocketsphinx_asr(path,start,end,timeout=remaining(),max_audio_seconds=asr_max_seconds)
            except (ValueError,TimeoutError,OSError):
                transcript={'state':'ASR_UNAVAILABLE','text':None};errors.append('ASR_UNAVAILABLE')
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
    ocr_bytes=sum(len((f.get('ocr',{}).get('text') or '').encode('utf-8')) for f in frames)
    png_bytes=sum(len(f['png']) for f in frames)
    result={'schema_version':1,'duration_seconds':duration,'target_range':(start,end),'question':question,
            'question_use':'LITERAL_TEXT_OR_EXPLICIT_TIMESTAMP_ONLY' if question or focus_terms or focus_times else 'NO_QUESTION',
            'focus_hints_applied':applied,
            'frames':frames,'scene_scan':scan,'scene_scan_details':scan_details,'requested_windows':attempted,
            'ocr_probes':ocr_probes,
            'ocr_probe_status':('NOT_REQUESTED' if not ocr_probe_budget else
                                'NO_FOCUS_TERMS' if not terms else
                                'MATCHED' if any(p.get('matched') for p in ocr_probes) else
                                'NOT_RUN_EXISTING_HINT' if not ocr_probes and hints else
                                'NO_MATCH_OR_INCOMPLETE'),
            'sparse_visual_changes':changes,
            'unobserved_intervals':gaps,'outside_requested_intervals':outside,
            'coverage':'POINT_SAMPLES_ONLY_NOT_CONTINUOUS_OBSERVATION',
            'subtitles':subtitles,'audio':audio,'transcript':transcript,'errors':errors,'warnings':warnings,
            'elapsed_seconds':elapsed,'output_png_bytes':png_bytes,
            'output_sizes':{'png_bytes':png_bytes,'subtitle_utf8_bytes':subtitle_bytes,'transcript_utf8_bytes':transcript_bytes,
                            'ocr_utf8_bytes':ocr_bytes,'media_and_text_bytes':png_bytes+subtitle_bytes+transcript_bytes+ocr_bytes},
            'budget':{'frame_limit':frame_budget,'output_size':(output_width,output_height),
                      'ocr_probe_limit':ocr_probe_budget,'wall_seconds_best_effort':max_runtime_seconds,
                      'deadline_exceeded':elapsed>max_runtime_seconds},
            'meaning':'local technical cues only; not semantic understanding or source authorization'}
    if model_content:
        context={'question':question,'video_duration_seconds':duration,'target_range_seconds':(start,end),
                 'coverage':result['coverage'],'unobserved_intervals':gaps,'outside_requested_intervals':outside,
                 'subtitle_state':subtitles['state'],'subtitles_full_track':subtitles.get('text'),
                 'transcript_state':transcript['state'],'transcript':transcript.get('text'),
                 'transcript_words':transcript.get('words'),'transcript_timeline_basis':transcript.get('timeline_basis'),
                 'transcript_processed_window':transcript.get('processed_window'),
                 'transcript_truncated':transcript.get('truncated'),
                 'ocr_probes_not_delivered_as_images':ocr_probes,
                 'sparse_visual_changes':changes,'errors':errors,'warnings':warnings}
        text,truncated=_bounded_model_context(context)
        preamble='Technical video materials; unsampled intervals remain unknown. OCR and transcription are unverified and may be wrong.'
        if truncated:preamble+=' Context is truncated; excerpts contain only their beginning and end.'
        content=[{'type':'text','text':preamble+'\n'+text}]
        for frame in frames:
            ocr_value=frame.get('ocr')
            if ocr_value and type(ocr_value.get('text')) is str and len(ocr_value['text'])>2000:
                ocr_value={**ocr_value,'text':ocr_value['text'][:2000],'truncated_for_model_content':True}
            label={'frame_time_seconds':frame['time_seconds'],'pts_tick':frame['pts_tick'],
                   'time_base':frame['time_base'],'selection_reason':frame['selection_reason'],
                   'ocr':ocr_value}
            content.append({'type':'text','text':json.dumps(label,ensure_ascii=False,separators=(',',':'))})
            content.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(frame['png']).decode('ascii')}})
        result['model_content']={'format':'OPENAI_COMPATIBLE_CHAT_CONTENT','items':content,
                                 'context_truncated':truncated,'token_cost':'UNKNOWN_NOT_MEASURED'}
        result['output_sizes']['model_content_json_utf8_bytes']=len(json.dumps(content,ensure_ascii=False).encode('utf-8'))
        result['elapsed_seconds']=time.monotonic()-started
        result['budget']['deadline_exceeded']=result['elapsed_seconds']>max_runtime_seconds
    return result
