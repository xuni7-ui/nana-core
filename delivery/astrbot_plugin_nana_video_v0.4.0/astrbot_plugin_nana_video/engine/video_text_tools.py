"""Optional mature local OCR/ASR adapters; no downloads or cloud calls."""
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import time

from .video_audio_probe import _run_bounded


def _run(command, deadline, *, limit=1_000_000):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise TimeoutError('text processing budget exhausted')
    return _run_bounded(command,timeout=remaining,stdout_limit=limit,stderr_limit=100_000)


def tesseract_ocr(png, *, language='eng', timeout=15, tessdata_dir=None):
    """Return unverified text; uses caller-installed Tesseract and language data."""
    if (type(png) is not bytes or not 1<=len(png)<=16*1024*1024 or type(language) is not str or
            type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0 or
            not 1<=len(language)<=64 or not re.fullmatch(r'[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*',language)):
        raise ValueError('invalid OCR input')
    from PIL import Image
    import io
    deadline=time.monotonic()+timeout
    data_dir=None if tessdata_dir is None else Path(tessdata_dir).resolve(strict=True)
    if data_dir is not None and not data_dir.is_dir():raise ValueError('invalid Tesseract data directory')
    with tempfile.TemporaryDirectory(prefix='video-ocr-') as directory:
        path=Path(directory)/'frame.png'
        with Image.open(io.BytesIO(png)) as image:
            if image.width*image.height>262144:raise ValueError('OCR image exceeds pixel bound')
            image.convert('RGB').resize((image.width*3,image.height*3)).save(path,format='PNG')
        command=['tesseract',str(path),'stdout','-l',language,'--psm','11']
        if data_dir is not None:command+=['--tessdata-dir',str(data_dir)]
        output=_run(command,deadline,limit=100_000)
        return output.stdout.decode('utf-8',errors='replace').strip()


def pocketsphinx_asr(path, start, end, *, timeout=60, max_audio_seconds=30):
    """Run installed PocketSphinx English model, returning bounded word spans.

    The caller must verify time alignment and transcription. FFmpeg's seek is
    normalized independently; a source with nonzero or delayed audio can
    require additional alignment. Temporary plaintext WAV exists during use.
    """
    if (any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,end,timeout,max_audio_seconds)) or
            not 0<=start<end or timeout<=0 or not 1<=max_audio_seconds<=120):
        raise ValueError('invalid ASR window')
    deadline=time.monotonic()+timeout; actual_end=min(end,start+max_audio_seconds)
    with tempfile.TemporaryDirectory(prefix='video-asr-') as directory:
        wav=Path(directory)/'audio.wav'
        _run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe',
              '-ss',str(start),'-t',str(actual_end-start),'-i',str(path),'-map','0:a:0',
              '-ac','1','-ar','16000','-c:a','pcm_s16le','-y',str(wav)],deadline)
        script="""import json,sys,wave
from pocketsphinx import Decoder
d=Decoder(samprate=16000,loglevel='ERROR')
with wave.open(sys.argv[1],'rb') as w:
 d.start_utt()
 while True:
  data=w.readframes(4096)
  if not data: break
  d.process_raw(data,False,False)
 d.end_utt()
h=d.hyp()
words=[{'text':s.word,'start':s.start_frame/100,'end':(s.end_frame+1)/100} for s in d.seg() if not s.word.startswith('<') and not s.word.startswith('[')]
print(json.dumps({'text':h.hypstr if h else '', 'words':words},ensure_ascii=False))
"""
        result=json.loads(_run([sys.executable,'-c',script,str(wav)],deadline).stdout)
        if type(result) is not dict or type(result.get('text')) is not str or type(result.get('words')) is not list:
            raise ValueError('invalid local ASR result')
        for word in result['words']:
            word['start_seconds']=start+word.pop('start');word['end_seconds']=start+word.pop('end')
        return {'state':'POCKETSPHINX_ENGLISH_UNVERIFIED','text':result['text'],'words':result['words'],
                'requested_window':(start,end),'processed_window':(start,actual_end),
                'truncated':actual_end<end,'timeline_basis':'FFMPEG_NORMALIZED_CALLER_MUST_VERIFY'}
