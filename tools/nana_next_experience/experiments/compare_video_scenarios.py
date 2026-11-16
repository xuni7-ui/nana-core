"""Reproducible weak-cut and continuous-motion comparison on generated video.

Requires trusted pinned dsh-see-now and video-watch-plus local checkouts.
Never contacts a platform, model, or Subject. Events are editorial ground truth,
not semantic importance; time windows and sample counts are reported explicitly.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from tools.nana_next_experience.experiments.video_ffmpeg_probe import probe
from tools.nana_next_experience.experiments.video_coverage_refine import refine

ADAPTER=Path(__file__).with_name('dsh_pipeline_adapter.mjs')


def run(command, *, payload=None):
    return subprocess.run(command,input=payload,stdin=subprocess.DEVNULL if payload is None else None,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=120)


def make_video(path,scenario):
    if scenario=='dark_weak_cut':
        command=['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            'color=c=0x202020:s=160x90:r=4:d=4','-f','lavfi','-i',
            'color=c=0x2b2b2b:s=160x90:r=4:d=4','-filter_complex',
            '[0:v][1:v]concat=n=2:v=1:a=0','-c:v','mpeg4','-threads','1','-y',str(path)]
    elif scenario=='brief_text_dynamic_brightness':
        font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        if not font.is_file():raise ValueError('DejaVu Sans fixture font required')
        filters=(f"eq=brightness='0.1*sin(2*PI*t)':eval=frame,"
                 f"drawtext=fontfile={font}:text=CODE7:fontcolor=white:fontsize=12:"
                 "x=15:y=15:enable='gte(t,3)*lt(t,3.25)'")
        command=['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            'color=c=0x202020:s=160x90:r=4:d=8','-vf',filters,
            '-c:v','mpeg4','-threads','1','-y',str(path)]
    elif scenario=='continuous_motion':
        command=['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            'testsrc2=s=160x90:r=4:d=8','-c:v','mpeg4','-threads','1','-y',str(path)]
    else:raise ValueError('unknown scenario')
    run(command)


def main():
    p=argparse.ArgumentParser();p.add_argument('--dsh',type=Path,required=True)
    p.add_argument('--watch',type=Path,required=True);args=p.parse_args()
    for root,revision in [(args.dsh,'0b4bd110074b3e2cd043da8b078f7272589d50b0'),
                          (args.watch,'8ca266f9cf9e5ffce7e9d424aa0e937a897b608d')]:
        actual=run(['git','-C',str(root),'rev-parse','HEAD']).stdout.decode().strip()
        dirty=run(['git','-C',str(root),'status','--porcelain','--untracked-files=no']).stdout
        if actual!=revision or dirty:raise ValueError('upstream checkout differs from pinned clean revision')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='nana-video-scenarios-') as temp:
        root=Path(temp)
        for scenario in ('dark_weak_cut','continuous_motion','brief_text_dynamic_brightness'):
            video=root/(scenario+'.mp4');raw=root/(scenario+'.rgb');out=root/(scenario+'-watch');out.mkdir()
            make_video(video,scenario)
            measured=probe(video)
            candidate=refine(measured['duration'],measured['candidates'],4,max_gap=3)
            run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(video),'-vf','scale=160:90',
                 '-pix_fmt','rgb24','-f','rawvideo','-y',str(raw)])
            payload={'source_ref':'synthetic.'+scenario,'rgb_path':str(raw),'width':160,'height':90,
                     'fps':4,'timestamps':[i/4 for i in range(32)],'max_frames_per_sheet':8}
            dsh=json.loads(run(['node',str(ADAPTER),str(args.dsh.resolve())],
                               payload=json.dumps(payload).encode()).stdout)
            vw=args.watch.resolve()/'vendor/vw.py'
            run([sys.executable,str(vw),'probe',str(video),'--out',str(out),'--no-audio'])
            run([sys.executable,str(vw),'plan',str(out/'timeline.json'),'--skeleton','2','--max','4',
                 '--burst','1','--out',str(out/'plan.json')])
            upstream=json.loads((out/'plan.json').read_text())
            times={'uniform':[1,3,5,7],
                   'watch_original':[row['t'] for row in upstream['shots']],
                   'dsh_original':[row['seconds'] for row in dsh['selected']],
                   'candidate_refined':list(candidate['timestamps'])}
            result={}
            for name,values in times.items():
                points=[0,*values,8]
                result[name]={'timestamps':values,'frames':len(values),
                    'max_gap_seconds':max(b-a for a,b in zip(points,points[1:])),
                    'within_budget':len(values)<=4,
                    'edit_followed_within_half_second':
                        any(4<=value<=4.5 for value in values) if scenario=='dark_weak_cut' else None,
                    'requested_offset_with_visible_text':
                        any(3<=value<3.25 for value in values) if scenario=='brief_text_dynamic_brightness' else None}
            result['dsh_original']['reported_cut_times']=[x['seconds'] for x in dsh['selected'] if x['reason']=='cut']
            result['watch_original']['reported_cut_times']=json.loads((out/'timeline.json').read_text())['cuts']
            rows.append({'scenario':scenario,'ground_truth':{'dark_weak_cut':'hard edit at 4s',
                           'continuous_motion':'continuous synthetic motion, no edit',
                           'brief_text_dynamic_brightness':'text visible only in frame at 3s'}[scenario],
                         'measurement_scan_complete':measured['scan_complete'],'methods':result})
        print(json.dumps({'fixtures':'generated dark weak cut, continuous motion, and brief text under dynamic brightness',
            'budget':'four selected frames; report any method exceeding it rather than silently truncating',
            'scope':'one fixture each; dsh sheet limit 8, watch --max 4; requested offsets, not decoded text or a semantic/token benchmark',
            'rows':rows},indent=2))


if __name__=='__main__':main()
