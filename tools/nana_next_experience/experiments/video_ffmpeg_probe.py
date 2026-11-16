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

from tools.nana_next_experience.experiments.video_coverage import Candidate, plan

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


def probe(path):
    """Return per-second maximum scene score, plus explicit scan completeness."""
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('invalid local file')
    metadata = json.loads(_run(['ffprobe','-v','error','-protocol_whitelist','file,pipe',
        '-show_entries','format=duration','-of','json',str(path)]))
    duration = float(metadata['format']['duration'])
    if not math.isfinite(duration) or not 0 < duration <= MAX_SECONDS:
        raise ValueError('duration outside experiment bounds')
    output = _run(['ffmpeg','-hide_banner','-loglevel','error','-protocol_whitelist','file,pipe',
        '-i',str(path),'-map','0:v:0','-vf','scdet=t=0,metadata=mode=print:file=-',
        '-an','-frames:v',str(MAX_FRAMES),'-f','null','-'])
    buckets = {}; timestamp = None; first_timestamp = None; last_timestamp = None; frames = 0
    for line in output.splitlines():
        match = re.search(r'^frame:\s*\d+\s+pts:.*?pts_time:([\d.]+)',line)
        if match:
            timestamp=float(match.group(1));last_timestamp=timestamp;frames+=1
            if first_timestamp is None: first_timestamp=timestamp
        elif line.startswith('lavfi.scd.score=') and timestamp is not None:
            score=float(line.partition('=')[2])
            if not math.isfinite(score) or score < 0 or timestamp < 0 or timestamp > duration:
                raise ValueError('invalid media measurement')
            second=int(timestamp)
            previous=buckets.get(second)
            if previous is None or score > previous.cut:
                buckets[second]=Candidate(timestamp,cut=score)
            timestamp=None
    if not buckets or last_timestamp is None:
        raise ValueError('no measured frames')
    # Reaching frame cap or ending early cannot qualify the remaining interval.
    complete = frames < MAX_FRAMES and first_timestamp <= 1.0 and duration-last_timestamp <= 1.0
    return {'duration':duration,'frames_measured':frames,'scan_complete':complete,
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
