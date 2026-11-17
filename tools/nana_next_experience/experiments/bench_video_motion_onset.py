"""Compare exact onset outputs and cost against fixed B baseline on one sample."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import statistics
import subprocess
import time
import tracemalloc
from types import ModuleType

from PIL import Image
from tools.nana_next_experience.experiments.video_motion_onset import propose
from tools.nana_next_experience.experiments.video_pts_decode import decode


BASE='b942268c86fdf0ff7e8837b7c3ddfc603f6d79f5'
SOURCE='tools/nana_next_experience/experiments/video_motion_onset.py'
BASE_SHA='b1475cbdf7d04abb7d88408b84d37bf0e0428a3d81c265f4dd6128560a2e76d1'
VIDEO_SHA='45cddc9490be69345cbdab64ca583be65987e864ca408038e648db99e10516cf'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--video',type=Path,required=True);args=parser.parse_args()
    path=args.video.resolve(strict=True)
    if path.stat().st_size!=8131690 or hashlib.sha256(path.read_bytes()).hexdigest()!=VIDEO_SHA:
        raise ValueError('sample hash mismatch')
    source=subprocess.check_output(['git','show',BASE+':'+SOURCE])
    if hashlib.sha256(source).hexdigest()!=BASE_SHA:raise ValueError('baseline hash mismatch')
    baseline=ModuleType('nana_fixed_motion_baseline');exec(compile(source,SOURCE,'exec'),baseline.__dict__)
    decoded=decode('opencv.vtest',path,width=160,height=120,start_seconds=0,end_seconds=79.5)
    size=160*120*3
    frames=[(t,Image.frombytes('RGB',(160,120),decoded.rgb24[i*size:(i+1)*size]))
            for i,t in enumerate(decoded.timestamps)]
    timings={'baseline':[],'candidate':[]};cpus={'baseline':[],'candidate':[]}
    functions={'baseline':baseline.propose,'candidate':propose};expected=None
    for name in ('baseline','candidate','candidate','baseline','baseline','candidate'):
        started=time.perf_counter();cpu=time.process_time();result=functions[name]('opencv.vtest',frames)
        timings[name].append(time.perf_counter()-started);cpus[name].append(time.process_time()-cpu)
        if expected is None:expected=result
        elif result!=expected:raise RuntimeError('onset output changed')
    peaks={}
    for name in ('baseline','candidate'):
        tracemalloc.start();result=functions[name]('opencv.vtest',frames[:5])
        _,peaks[name]=tracemalloc.get_traced_memory();tracemalloc.stop()
    print(json.dumps({'sample_sha256':VIDEO_SHA,'baseline_git_commit':BASE,'baseline_sha256':BASE_SHA,
        'frames':len(frames),'frame_size':[160,120],'output_identical':True,
        'onset_timestamps':[item['seconds'] for item in expected['proposals']],
        'baseline_wall_seconds':timings['baseline'],'candidate_wall_seconds':timings['candidate'],
        'baseline_wall_median':statistics.median(timings['baseline']),
        'candidate_wall_median':statistics.median(timings['candidate']),
        'baseline_cpu_seconds':cpus['baseline'],'candidate_cpu_seconds':cpus['candidate'],
        'python_traced_peak_bytes_first_five_frames_only':peaks,
        'process_peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'rss_scope':'whole process including both modes and decoded frames, not per-mode',
        'limits':'one recorded sample; timings exclude decode and models; no semantic quality or token claim'},indent=2))


if __name__=='__main__':main()
