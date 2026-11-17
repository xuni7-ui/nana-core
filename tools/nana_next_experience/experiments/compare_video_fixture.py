"""Run four actual implementations on one synthetic video; no network/models.

PYTHONPATH=src:. python tools/nana_next_experience/experiments/compare_video_fixture.py \
  --dsh /path/to/dsh-see-now --watch /path/to/video-watch-plus
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from tools.nana_next_experience.experiments.video_ffmpeg_probe import probe
from tools.nana_next_experience.experiments.video_coverage import plan


def run(command, **kwargs):
    return subprocess.run(command,stdin=subprocess.DEVNULL,check=True,timeout=120,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kwargs)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dsh',type=Path,required=True)
    parser.add_argument('--watch',type=Path,required=True);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nana-vision-comparison-') as temp:
        root=Path(temp);video=root/'scenes.mp4';raw=root/'scenes.rgb';out=root/'watch';out.mkdir()
        run(['ffmpeg','-hide_banner','-loglevel','error',
             '-f','lavfi','-i','color=black:s=160x90:r=4:d=4',
             '-f','lavfi','-i','color=white:s=160x90:r=4:d=4',
             '-f','lavfi','-i','testsrc2=s=160x90:r=4:d=4',
             '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0',
             '-c:v','mpeg4','-threads','1','-y',str(video)])
        start=time.perf_counter();measured=probe(video)
        candidate=plan(measured['duration'],measured['candidates'],4,max_gap=3)['timestamps']
        candidate_seconds=time.perf_counter()-start
        watch=args.watch.resolve()/'vendor/vw.py'
        start=time.perf_counter()
        run([sys.executable,str(watch),'probe',str(video),'--out',str(out),'--no-audio'])
        run([sys.executable,str(watch),'plan',str(out/'timeline.json'),'--skeleton','2',
             '--max','4','--burst','1','--out',str(out/'plan.json')])
        watch_seconds=time.perf_counter()-start
        watch_times=[x['t'] for x in json.loads((out/'plan.json').read_text())['shots']]
        run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(video),'-vf','scale=160:90',
             '-pix_fmt','rgb24','-f','rawvideo','-y',str(raw)])
        script=root/'dsh.mjs';script.write_text('''import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
const {createPipeline}=await import(pathToFileURL(process.argv[2]).href);
const bytes=readFileSync(process.argv[3]), size=160*90*3;
const pipeline=createPipeline({width:160,height:90,fps:4,maxFrames:8});
for(let i=0;i<bytes.length/size;i++) pipeline.push({t:i/4,buf:bytes.subarray(i*size,(i+1)*size)});
pipeline.finish(); console.log(JSON.stringify(pipeline.log.map(x=>x.t)));
''')
        start=time.perf_counter()
        dsh_times=json.loads(run(['node',str(script),str(args.dsh.resolve()/'src/pipeline.js'),str(raw)]).stdout)
        dsh_seconds=time.perf_counter()-start
        methods={'uniform':[1.5,4.5,7.5,10.5],'video_watch_plus':watch_times,
                 'dsh_original':dsh_times,'coverage_candidate':candidate}
        if any(len(times)!=4 for times in methods.values()):
            raise ValueError('actual output differs from four-frame budget; no equal-budget result')
        results={}
        for name,times in methods.items():
            points=[0,*times,12]
            results[name]={'timestamps':list(times),'count':len(times),
                'max_gap_seconds':max(b-a for a,b in zip(points,points[1:])),
                'cuts_followed_within_half_second':sum(any(0<=t-event<=0.5 for t in times) for event in (4,8))}
        print(json.dumps({'fixture':'12s synthetic black/white/testsrc2, cuts 4s and 8s',
            'real_provider_calls':0,'semantic_accuracy':'not measured',
            'latency_note':'single runs with different pipelines; dsh excludes raw decode; not comparable',
            'single_wall_seconds':{'candidate_probe_and_plan':candidate_seconds,
                'watch_probe_and_plan':watch_seconds,'dsh_pipeline_only':dsh_seconds},
            'results':results},indent=2))


if __name__=='__main__':main()
