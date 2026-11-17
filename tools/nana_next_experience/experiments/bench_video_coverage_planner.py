"""Compare the isolated planner to its fixed pre-optimization Git version."""
import hashlib
import json
import resource
import statistics
import subprocess
import sys
import time
import tracemalloc
from types import ModuleType

from tools.nana_next_experience.experiments.video_coverage import Candidate, plan


BASE='d63c1ba163c47209aafda00b46768615a531c29f'
SOURCE='tools/nana_next_experience/experiments/video_coverage.py'
SHA256='6b11af1e8ee253ef987e5cceb0284e2ba4427fa710411d930466a6f15ee201fd'


def main():
    source=subprocess.check_output(['git','show',BASE+':'+SOURCE])
    if hashlib.sha256(source).hexdigest()!=SHA256:raise RuntimeError('baseline source mismatch')
    baseline=ModuleType('nana_fixed_coverage_baseline');sys.modules[baseline.__name__]=baseline
    exec(compile(source,SOURCE,'exec'),baseline.__dict__)
    cases=[]
    for count,budget,gap in ((80,4,20),(10000,256,40)):
        data=[Candidate(float(i),motion=1. if i%157==0 else 0.) for i in range(count)]
        timings={'baseline':[],'candidate':[]};cpus={'baseline':[],'candidate':[]}
        funcs={'baseline':baseline.plan,'candidate':plan};expected=None
        for name in ('baseline','candidate','candidate','baseline','baseline','candidate'):
            started=time.perf_counter();cpu=time.process_time()
            result=funcs[name](count,data,budget,max_gap=gap)
            timings[name].append(time.perf_counter()-started);cpus[name].append(time.process_time()-cpu)
            if expected is None:expected=result
            elif result!=expected:raise RuntimeError('planner output changed')
        peaks={}
        for name in ('baseline','candidate'):
            tracemalloc.start();result=funcs[name](count,data,budget,max_gap=gap)
            _,peaks[name]=tracemalloc.get_traced_memory();tracemalloc.stop()
            if result!=expected:raise RuntimeError('planner output changed')
        cases.append({'candidates':count,'budget':budget,'max_gap':gap,'output_identical':True,
            'baseline_wall_seconds':timings['baseline'],'candidate_wall_seconds':timings['candidate'],
            'baseline_wall_median':statistics.median(timings['baseline']),
            'candidate_wall_median':statistics.median(timings['candidate']),
            'baseline_cpu_seconds':cpus['baseline'],'candidate_cpu_seconds':cpus['candidate'],
            'python_traced_peak_bytes':peaks})
    print(json.dumps({'baseline_git_commit':BASE,'baseline_sha256':SHA256,'cases':cases,
        'process_peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'rss_scope':'whole benchmark including both modes, not per-mode memory',
        'ffmpeg_model_or_network_calls':0,'token_cost':'not measured'},indent=2))


if __name__=='__main__':main()
