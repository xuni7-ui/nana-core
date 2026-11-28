"""Bounded local-only FFmpeg scene measurements for the coverage prototype.

This research command is not a source/observation authority. It never sends
frames or invokes a model. FFmpeg/ffprobe are optional external dependencies.
"""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess

from .video_coverage import Candidate, plan

MAX_SECONDS = 600
MAX_FRAMES = 36000


def _run(args, timeout=120):
    try:
        result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=timeout, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError('local media analysis unavailable') from exc
    if len(result.stdout) > 8_000_000:
        raise ValueError('analysis output exceeds bound')
    return result.stdout.decode('utf-8', errors='strict')


def probe(path, *, timeout=120):
    """Return per-quarter-second maximum scene score and scan completeness."""
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('invalid local file')
    metadata = json.loads(_run(['ffprobe','-v','error','-protocol_whitelist','file,pipe',
        '-select_streams','v:0','-show_entries','format=duration:stream=nb_frames,avg_frame_rate,start_time',
        '-of','json',str(path)], timeout=timeout))
    duration = float(metadata['format']['duration'])
    if not math.isfinite(duration) or not 0 < duration <= MAX_SECONDS:
        raise ValueError('duration outside experiment bounds')
    output = _run(['ffmpeg','-hide_banner','-loglevel','error','-protocol_whitelist','file,pipe',
        '-i',str(path),'-map','0:v:0','-vf','scdet=t=0,metadata=mode=print:file=-',
        '-an','-frames:v',str(MAX_FRAMES),'-f','null','-'], timeout=timeout)
    buckets = {}; timestamp = None; first_timestamp = None; last_timestamp = None; frames = 0; scores = 0; ordered = True
    for line in output.splitlines():
        match = re.search(r'^frame:\s*\d+\s+pts:.*?pts_time:([\d.]+)',line)
        if match:
            timestamp=float(match.group(1))
            if last_timestamp is not None and timestamp<=last_timestamp: ordered=False
            last_timestamp=timestamp;frames+=1
            if first_timestamp is None: first_timestamp=timestamp
        elif line.startswith('lavfi.scd.score=') and timestamp is not None:
            score=float(line.partition('=')[2])
            if not math.isfinite(score) or score < 0 or timestamp < 0 or timestamp > duration:
                raise ValueError('invalid media measurement')
            scores+=1
            bucket=int(timestamp*4)
            previous=buckets.get(bucket)
            if previous is None or score > previous.cut:
                buckets[bucket]=Candidate(timestamp,cut=score)
            timestamp=None
    if not buckets or last_timestamp is None:
        raise ValueError('no measured frames')
    # The end timestamp alone cannot reveal a skipped frame. Missing stream
    # metadata means completeness is unqualified, never silently 'complete'.
    try:
        stream=metadata['streams'][0]
        expected=int(stream['nb_frames'])
        numerator,denominator=(int(x) for x in stream['avg_frame_rate'].split('/'))
        fps=numerator/denominator
        media_start=float(stream['start_time'])
        complete=(ordered and 0<expected<=MAX_FRAMES and frames==scores==expected and math.isfinite(fps)
                  and fps>0 and math.isfinite(media_start) and abs(media_start)<=0.001
                  and 0<=first_timestamp<=1/fps+0.001
                  and 0<=duration-last_timestamp<=max(0.05,1.5/fps))
    except (KeyError,IndexError,TypeError,ValueError,ZeroDivisionError,OverflowError):
        expected=None;complete=False
    return {'duration':duration,'frames_measured':frames,'frames_scored':scores,'expected_frames':expected,
            'scan_complete':complete,
            'scanned_until':last_timestamp,'candidates':tuple(buckets[k] for k in sorted(buckets))}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('media');parser.add_argument('--budget',type=int,default=8)
    parser.add_argument('--max-gap',type=float,default=5)
    args=parser.parse_args();result=probe(args.media)
    selection=plan(result['duration'],result['candidates'],args.budget,max_gap=args.max_gap)
    print(json.dumps({**{k:v for k,v in result.items() if k!='candidates'},'selection':selection,
                      'signal':'FFmpeg scdet change, not semantic importance'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
