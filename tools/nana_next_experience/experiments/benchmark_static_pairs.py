"""Compare exact previous local-change implementation against identical-frame fast path.

Uses local git history only; checks the baseline's SHA256 before executing its
trusted, repository-owned experiment. No network, model or real input.
"""
import hashlib
import json
import statistics
import subprocess
import time
import types
from PIL import Image, ImageDraw
from tools.nana_next_experience.experiments import video_local_pairs as pairs
from tools.nana_next_experience.experiments.video_local_change import local_change

BASELINE='84e79d6'
BASELINE_HASH='e892f188fef4bc54c7c742bc13a17f17c2faef3e4e79004f7ddae2a2d954c9b7'


def main():
    source=subprocess.check_output(['git','show',BASELINE+':tools/nana_next_experience/experiments/video_local_change.py'])
    if hashlib.sha256(source).hexdigest()!=BASELINE_HASH:raise ValueError('baseline source fingerprint mismatch')
    previous=types.ModuleType('trusted_local_baseline');exec(compile(source,'baseline_local_change.py','exec'),previous.__dict__)
    base=Image.new('RGB',(320,180),(32,32,32));changed=base.copy()
    ImageDraw.Draw(changed).rectangle((20,20,70,32),fill=(255,255,255))
    still=[(i/4,changed.copy() if i==24 else base.copy()) for i in range(48)]
    moving=[]
    for i in range(48):
        image=base.copy();ImageDraw.Draw(image).rectangle((10+3*i,30,20+3*i,40),fill=(255,255,255))
        moving.append((i/4,image))
    output={}
    try:
        for label,frames in [('mostly_static',still),('continuous_local_motion',moving)]:
            wall={'baseline':[],'candidate':[]};cpu={'baseline':[],'candidate':[]};results={}
            for iteration in range(6):
                order=[('baseline',previous.local_change),('candidate',local_change)]
                if iteration%2:order.reverse()
                for name,implementation in order:
                    pairs.local_change=implementation
                    t=time.perf_counter();c=time.process_time()
                    results[name]=pairs.propose('source.synthetic',frames)
                    cpu[name].append((time.process_time()-c)*1000)
                    wall[name].append((time.perf_counter()-t)*1000)
                assert results['baseline']==results['candidate']
            output[label]={'input_frames':len(frames),'events':len(results['baseline']['proposals']),
                'truncated':results['baseline']['truncated'],
                'baseline_wall_median_ms':statistics.median(wall['baseline']),
                'candidate_wall_median_ms':statistics.median(wall['candidate']),
                'baseline_cpu_mean_ms':statistics.mean(cpu['baseline']),
                'candidate_cpu_mean_ms':statistics.mean(cpu['candidate'])}
    finally:pairs.local_change=local_change
    print(json.dumps({'baseline_commit':BASELINE,'baseline_source_sha256':BASELINE_HASH,
        'scope':'one 48-frame synthetic clip per case, six alternating runs, same pair output',
        'includes':'Pillow grayscale conversion and pair comparison; excludes decode and model calls',
        'cases':output,'model_calls':0,'actual_tokens':'NOT_MEASURED'},indent=2))


if __name__=='__main__':main()
