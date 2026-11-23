"""Compare fixed old/new audio log bounds in isolated local Python processes."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

BASE='782302bc3978fc9b3911adf61acc6e50d31d4e7e'
SOURCE='tools/nana_next_experience/experiments/video_audio_probe.py'
SOURCE_SHA='b2c6c4f4288a4ed22e4cdb7fd4bf36fda2559c9fe73db38e9979078b0afe13b5'


def main():
    original=subprocess.check_output(['git','show',BASE+':'+SOURCE])
    if hashlib.sha256(original).hexdigest()!=SOURCE_SHA:raise ValueError('baseline hash mismatch')
    with tempfile.TemporaryDirectory(prefix='nana-audio-output-bound-') as directory:
        root=Path(directory);baseline=root/'baseline.py';baseline.write_bytes(original);source=root/'packets.nut'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            'anullsrc=r=8000:cl=mono:d=5','-af','asetnsamples=n=1:p=0',
            '-c:a','pcm_s16le','-y',str(source)],check=True,timeout=20)
        script='''import importlib.util,json,resource,sys,time
if sys.argv[1]=='old':
 spec=importlib.util.spec_from_file_location('old_probe',sys.argv[2]);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
else:
 from tools.nana_next_experience.experiments import video_audio_probe as module
start=time.perf_counter()
try:module.measure(sys.argv[3]);state='UNEXPECTED_SUCCESS'
except module.AudioProbeOutputBound:state='OUTPUT_BOUND'
parent=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
print(json.dumps({'state':state,'wall_seconds':time.perf_counter()-start,'parent_peak_rss_kib':parent.ru_maxrss,
 'child_peak_rss_kib':children.ru_maxrss,'child_cpu_seconds':children.ru_utime+children.ru_stime}))'''
        samples={'old':[],'new':[]}
        for i in range(3):
            for mode in (('old','new') if i%2==0 else ('new','old')):
                output=subprocess.check_output([sys.executable,'-c',script,mode,str(baseline),str(source)],text=True,timeout=30)
                result=json.loads(output)
                if result['state']!='OUTPUT_BOUND':raise RuntimeError('unexpected baseline/candidate result')
                samples[mode].append(result)
        print(json.dumps({'baseline_commit':BASE,'baseline_sha256':SOURCE_SHA,'source_bytes':source.stat().st_size,
            'input':'synthetic 5s/8000Hz/40000 tiny audio packets','samples':samples,
            'median_wall_seconds':{mode:statistics.median(x['wall_seconds'] for x in rows) for mode,rows in samples.items()},
            'median_parent_peak_rss_kib':{mode:statistics.median(x['parent_peak_rss_kib'] for x in rows) for mode,rows in samples.items()},
            'scope':'Linux isolated processes; cap failure on both; no model, ASR, Token, billing or broad workload claim'},indent=2))


if __name__=='__main__':main()
