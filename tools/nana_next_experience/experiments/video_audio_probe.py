"""Optional bounded FFmpeg silence measurements, not speech recognition."""
import json
import math
from pathlib import Path
import re
import subprocess

MAX_DURATION = 600


def measure(path, *, timeout=120):
    """Return measured silence intervals or NO_AUDIO for an explicit local file.

    Silence is an acoustic threshold result, not proof of speech, language,
    speaker identity or meaning. No ASR, network, model, or persistence.
    """
    path=Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 256*1024*1024:
        raise ValueError('invalid local file')
    def run(command):
        try:
            return subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,timeout=timeout,check=True)
        except (OSError,subprocess.SubprocessError) as exc:
            raise ValueError('local audio analysis unavailable') from exc
    info=json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe',
        '-show_entries','format=duration:stream=codec_type','-of','json',str(path)]).stdout)
    duration=float(info['format']['duration'])
    if not math.isfinite(duration) or not 0<duration<=MAX_DURATION:
        raise ValueError('duration outside experiment bounds')
    if not any(stream.get('codec_type')=='audio' for stream in info.get('streams',[])):
        return {'state':'NO_AUDIO','duration':duration,'silence_intervals':[],
                'meaning':'no audio stream; speech content is unknown'}
    result=run(['ffmpeg','-hide_banner','-nostats','-protocol_whitelist','file,pipe',
        '-i',str(path),'-map','0:a:0','-vn','-af','silencedetect=noise=-35dB:duration=1',
        '-f','null','-'])
    if len(result.stderr)>1_000_000:
        raise ValueError('audio analysis output exceeds bound')
    records=[];start=None
    for line in result.stderr.decode('utf-8',errors='replace').splitlines():
        a=re.search(r'silence_start:\s*(-?[0-9.]+)',line)
        b=re.search(r'silence_end:\s*(-?[0-9.]+)',line)
        if a:
            if start is not None:raise ValueError('overlapping silence markers')
            start=float(a.group(1))
        if b:
            end=float(b.group(1))
            if start is None or not (math.isfinite(start) and math.isfinite(end) and
                    0<=start<=end<=duration+0.1):
                raise ValueError('invalid silence markers')
            records.append((start,min(duration,end)));start=None
    if start is not None:
        if not math.isfinite(start) or not 0<=start<=duration:
            raise ValueError('invalid silence marker')
        # A missing end marker is not an observed end; retain UNKNOWN rather
        # than silently extending to the media duration.
        return {'state':'INCOMPLETE','duration':duration,'silence_intervals':records,
                'open_silence_start':start,'meaning':'acoustic threshold only; end unknown'}
    return {'state':'MEASURED','duration':duration,'silence_intervals':records,
            'meaning':'acoustic threshold only; not speech or semantic evidence'}
