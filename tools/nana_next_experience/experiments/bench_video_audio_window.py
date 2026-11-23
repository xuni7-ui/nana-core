"""Synthetic long-audio seek measurement; not speech, semantic, or token evidence."""
import json
from pathlib import Path
import resource
import statistics
import subprocess
import tempfile
import time

from tools.nana_next_experience.experiments.video_audio_probe import measure


def main():
    with tempfile.TemporaryDirectory(prefix='nana-audio-window-bench-') as root:
        source=Path(root)/'audio.flac'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            'sine=frequency=440:sample_rate=8000:duration=620','-c:a','flac','-y',str(source)],
            check=True,timeout=30)
        try:measure(source)
        except ValueError as exc:
            if 'duration outside experiment bounds' not in str(exc):raise
            baseline='FULL_INPUT_REJECTED_BY_EXISTING_BOUND'
        else:raise RuntimeError('expected bounded full-input rejection')
        wall=[];cpu=[];result=None
        for _ in range(3):
            before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter()
            result=measure(source,start_seconds=617,end_seconds=620)
            wall.append(time.perf_counter()-start);after=resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu.append(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        print(json.dumps({'source_bytes':source.stat().st_size,'declared_duration_s':result['duration'],
            'baseline':baseline,'requested_window_s':result['requested_window'],
            'measured_intervals_s':result.get('measured_intervals'),'state':result['state'],
            'coverage_state':result.get('coverage_state'),'wall_seconds':wall,
            'wall_median_seconds':statistics.median(wall),'ffmpeg_ffprobe_child_cpu_seconds':cpu,
            'peak_memory':'NOT_MEASURED','scope':'synthetic local FLAC; old full input is rejected, not a same-capability speed comparison; no ASR, model, Token or bill'},indent=2))


if __name__=='__main__':main()
