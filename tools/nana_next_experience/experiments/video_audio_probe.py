"""Optional bounded FFmpeg silence measurements, not speech recognition."""
import json
from fractions import Fraction
from decimal import Decimal
import math
import os
import selectors
from pathlib import Path
import re
import subprocess
import time

MAX_DURATION = 600


class AudioProbeUnavailable(ValueError):
    """FFmpeg or ffprobe could not complete the local acoustic measurement."""


class AudioProbeOutputBound(ValueError):
    """The local acoustic metadata exceeded its explicit bound."""


def _run_bounded(command, *, timeout, stdout_limit, stderr_limit):
    """Read both child pipes with hard in-memory bounds; terminate on excess.

    This is a local experiment, not a media sandbox. Limits apply separately to
    retained stdout/stderr; interpreter and decoded strings require extra memory.
    """
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0:
        raise ValueError('invalid audio analysis timeout')
    try:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except (OSError,subprocess.SubprocessError) as exc:
        raise AudioProbeUnavailable('local audio analysis unavailable') from exc
    streams={'stdout':bytearray(),'stderr':bytearray()}
    limits={'stdout':stdout_limit,'stderr':stderr_limit}
    deadline=time.monotonic()+timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout,selectors.EVENT_READ,'stdout')
            selector.register(process.stderr,selectors.EVENT_READ,'stderr')
            while selector.get_map():
                remaining=deadline-time.monotonic()
                if remaining<=0:raise AudioProbeUnavailable('local audio analysis unavailable')
                events=selector.select(remaining)
                if not events:raise AudioProbeUnavailable('local audio analysis unavailable')
                for key,_ in events:
                    name=key.data;buffer=streams[name];limit=limits[name]
                    chunk=os.read(key.fd,min(65536,limit-len(buffer)+1))
                    if not chunk:
                        selector.unregister(key.fileobj);continue
                    buffer.extend(chunk)
                    if len(buffer)>limit:raise AudioProbeOutputBound('audio analysis output exceeds bound')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise AudioProbeUnavailable('local audio analysis unavailable')
            try:status=process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:raise AudioProbeUnavailable('local audio analysis unavailable') from exc
            if status:raise AudioProbeUnavailable('local audio analysis unavailable')
            return subprocess.CompletedProcess(command,status,bytes(streams['stdout']),bytes(streams['stderr']))
    except (AudioProbeOutputBound,AudioProbeUnavailable):
        raise
    except (OSError,ValueError) as exc:
        raise AudioProbeUnavailable('local audio analysis unavailable') from exc
    finally:
        if process.poll() is None:
            try:process.kill()
            except ProcessLookupError:pass
            process.wait()
        process.stdout.close();process.stderr.close()


def measure(path, *, timeout=120, start_seconds=None, end_seconds=None):
    """Return measured silence intervals or NO_AUDIO for an explicit local file.

    Optional windows return container-relative requested times, subject to
    FFmpeg normalization and independent caller verification. A window is not
    full-video coverage. Silence is not proof of speech, language,
    speaker identity or meaning. No ASR, network, model, or persistence.
    """
    path=Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 256*1024*1024:
        raise ValueError('invalid local file')
    def run(command):
        return _run_bounded(command,timeout=timeout,stdout_limit=100000,stderr_limit=4_000_000)
    # FFmpeg measures only 0:a:0 below; do not enumerate unrelated tracks.
    info=json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-select_streams','a:0',
        '-show_entries','format=duration:stream=codec_type','-of','json',str(path)]).stdout)
    duration=float(info['format']['duration'])
    window=(start_seconds is not None or end_seconds is not None)
    if (not math.isfinite(duration) or not 0<duration<=(86400 if window else MAX_DURATION)):
        raise ValueError('duration outside experiment bounds')
    if window and (type(start_seconds) not in (int,float) or type(end_seconds) not in (int,float) or
                   not math.isfinite(start_seconds) or not math.isfinite(end_seconds) or
                   not 0<=start_seconds<end_seconds<=duration or end_seconds-start_seconds>MAX_DURATION):
        raise ValueError('invalid audio window')
    offset=Fraction(str(start_seconds)) if window else Fraction(0)
    limit=Fraction(str(end_seconds)) if window else Fraction(str(duration))
    def qualified(result):
        if window:result['requested_window']=(start_seconds,end_seconds)
        return result
    if not any(stream.get('codec_type')=='audio' for stream in info.get('streams',[])):
        return qualified({'state':'NO_AUDIO','duration':duration,'silence_intervals':[],
                'meaning':'no audio stream; speech content is unknown'})
    command=['ffmpeg','-hide_banner','-nostats','-protocol_whitelist','file,pipe']
    if window:
        command+=['-ss',str(start_seconds),'-t',str(Decimal(str(end_seconds))-Decimal(str(start_seconds)))]
    result=run(command+['-i',str(path),'-map','0:a:0','-vn','-af',
        'silencedetect=noise=-35dB:duration=1,asettb=expr=1/sr,ashowinfo',
        '-f','null','-'])
    records=[];start=None;coverage=[];frames=0;bad_timing=False
    for line in result.stderr.decode('utf-8',errors='replace').splitlines():
        frame=re.search(r'\[Parsed_ashowinfo_\d+\s+@[^\]]+\]\s+n:(\d+)\s+pts:(-?\d+)\s+pts_time:[^ ]+.*?\brate:(\d+)\s+nb_samples:(\d+)',line)
        if frame:
            index,pts,rate,samples=map(int,frame.groups())
            if index!=frames or rate<1 or samples<1:
                bad_timing=True
            else:
                begin=offset+Fraction(pts,rate);finish=offset+Fraction(pts+samples,rate)
                begin=max(offset,begin);finish=min(limit,finish)
                if begin<finish:
                    if coverage and begin<coverage[-1][0]:bad_timing=True
                    elif coverage and begin<=coverage[-1][1]:coverage[-1]=(coverage[-1][0],max(coverage[-1][1],finish))
                    else:coverage.append((begin,finish))
            frames+=1
        a=re.search(r'silence_start:\s*(-?[0-9.]+)',line)
        b=re.search(r'silence_end:\s*(-?[0-9.]+)',line)
        if a:
            if start is not None:raise ValueError('overlapping silence markers')
            start=float(offset+Fraction(a.group(1)))
        if b:
            end=float(offset+Fraction(b.group(1)))
            if start is None or not (math.isfinite(start) and math.isfinite(end) and
                    float(offset)<=start<=end<=float(limit)+0.1):
                raise ValueError('invalid silence markers')
            records.append((start,min(float(limit),end)));start=None
    measured=[(float(a),float(b)) for a,b in coverage]
    coverage_state=('FULL' if len(coverage)==1 and coverage[0][0]==0 and coverage[0][1]>=Fraction(str(duration)) else 'PARTIAL')
    if start is not None:
        if not math.isfinite(start) or not float(offset)<=start<=float(limit):
            raise ValueError('invalid silence marker')
        # A missing end marker is not an observed end; retain UNKNOWN rather
        # than silently extending to the media duration.
        return qualified({'state':'INCOMPLETE','duration':duration,'silence_intervals':records,
                'measured_intervals':measured,'coverage_state':coverage_state,'open_silence_start':start,'meaning':'acoustic threshold only; end unknown'})
    if bad_timing or not measured:
        return qualified({'state':'INCOMPLETE','duration':duration,'silence_intervals':records,
                'measured_intervals':measured,'coverage_state':'UNKNOWN',
                'meaning':'audio timing incomplete; no silence conclusion'})
    return qualified({'state':'MEASURED','duration':duration,'silence_intervals':records,
            'measured_intervals':measured,'coverage_state':coverage_state,
            'timeline_basis':'FFMPEG_NORMALIZED_CALLER_MUST_VERIFY',
            'meaning':'acoustic threshold only; not speech or semantic evidence'})
