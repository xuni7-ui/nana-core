"""Five local sampling methods on one fixed public OpenCV sample; no model calls."""
import argparse
from bisect import bisect_left
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image
from tools.nana_next_experience.experiments.video_ffmpeg_probe import probe
from tools.nana_next_experience.experiments.video_local_pairs import propose
from tools.nana_next_experience.experiments.video_motion_onset import propose as motion_onsets
from tools.nana_next_experience.experiments.video_pts_decode import decode
from tools.nana_next_experience.experiments.video_window_fusion import fuse_window

VIDEO_SHA='4666099d0f704e310047b2f0a5ec9f936cb76a7271de9a2e70a0c57f82ac82dc'
UPSTREAM={'dsh':'0b4bd110074b3e2cd043da8b078f7272589d50b0',
          'watch':'8ca266f9cf9e5ffce7e9d424aa0e937a897b608d'}


def run(args,*,payload=None,cwd=None):
    env={'PATH':os.defpath,'LANG':'C.UTF-8'}
    return subprocess.run(args,input=payload,stdin=subprocess.DEVNULL if payload is None else None,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=120,cwd=cwd,env=env)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--video',type=Path,required=True)
    parser.add_argument('--dsh',type=Path,required=True);parser.add_argument('--watch',type=Path,required=True)
    args=parser.parse_args();video=args.video.resolve(strict=True)
    if video.stat().st_size!=1250680 or hashlib.sha256(video.read_bytes()).hexdigest()!=VIDEO_SHA:
        raise ValueError('sample hash mismatch')
    for name,root in (('dsh',args.dsh),('watch',args.watch)):
        if run(['git','-C',str(root),'rev-parse','HEAD']).stdout.decode().strip()!=UPSTREAM[name] or \
           run(['git','-C',str(root),'status','--porcelain','--untracked-files=no']).stdout:
            raise ValueError('upstream revision or tracked files differ')
    measurements={}
    def timed(label,fn):
        start=time.perf_counter();cpu=time.process_time();children=resource.getrusage(resource.RUSAGE_CHILDREN)
        result=fn();after=resource.getrusage(resource.RUSAGE_CHILDREN)
        measurements[label]={'wall_seconds':time.perf_counter()-start,'parent_cpu_seconds':time.process_time()-cpu,
            'child_cpu_seconds':after.ru_utime+after.ru_stime-children.ru_utime-children.ru_stime}
        return result
    with tempfile.TemporaryDirectory(prefix='nana-opencv-comparison-') as temp:
        root=Path(temp);raw=root/'frames.rgb';out=root/'watch';out.mkdir()
        config=root/'vw-config.json';config.write_text('{}')
        measured=timed('ffmpeg_scene_probe',lambda:probe(video));duration=measured['duration']
        decoded=timed('decode_rgb',lambda:decode('opencv.tree',video,width=160,height=120,
                                                 start_seconds=0,end_seconds=duration))
        raw.write_bytes(decoded.rgb24)
        times=list(decoded.timestamps)
        def closest(value):
            at=bisect_left(times,value);options=[times[i] for i in (at-1,at) if 0<=i<len(times)]
            return min(options,key=lambda x:(abs(x-value),x))
        uniform=[closest(duration*(i+.5)/4) for i in range(4)]
        scene=sorted(c.seconds for c in sorted(measured['candidates'],key=lambda x:(-x.cut,x.seconds))[:4])
        request={'source_ref':'opencv.tree','rgb_path':str(raw),'width':160,'height':120,'fps':15,
                 'timestamps':times,'max_frames_per_sheet':8}
        adapter=Path(__file__).with_name('dsh_pipeline_adapter.mjs')
        node=shutil.which('node')
        if node is None:raise ValueError('Node unavailable')
        dsh=json.loads(timed('original_dsh',lambda:run([node,str(adapter),str(args.dsh.resolve())],
                              payload=json.dumps(request).encode(),cwd=root)).stdout)
        watch=args.watch.resolve()/'vendor/vw.py'
        def original_watch():
            run([sys.executable,str(watch),'--config',str(config),'probe',str(video),
                 '--out',str(out),'--no-audio'],cwd=root)
            run([sys.executable,str(watch),'--config',str(config),'plan',str(out/'timeline.json'),
                 '--skeleton','2','--max','4','--burst','1','--out',str(out/'plan.json')],cwd=root)
            return json.loads((out/'plan.json').read_text()),json.loads((out/'timeline.json').read_text())
        watch_plan,watch_timeline=timed('original_watch',original_watch)
        size=160*120*3
        frames=[(t,Image.frombytes('RGB',(160,120),decoded.rgb24[i*size:(i+1)*size]))
                for i,t in enumerate(times)]
        pairs=timed('local_change_pairs',lambda:propose('opencv.tree',frames))
        fusion=timed('fusion_planning',lambda:fuse_window(decoded,dsh,pairs,budget=4,max_gap=8))
        onsets=timed('motion_onset_probe',lambda:motion_onsets('opencv.tree',frames))
        onset_fusion=timed('onset_fusion_planning',lambda:fuse_window(decoded,dsh,pairs,budget=4,max_gap=8,onsets=onsets))
        values={'uniform_actual_frames':uniform,'ffmpeg_top_scene_actual_frames':scene,
            'watch_original_requested_offsets':[x['t'] for x in watch_plan['shots']],
            'dsh_original_selected':[x['seconds'] for x in dsh['selected']],
            'fusion_actual_frames':[x['seconds'] for x in fusion['selected_frames']],
            'fusion_with_onsets_actual_frames':[x['seconds'] for x in onset_fusion['selected_frames']]}
        rows={}
        for name,items in values.items():
            points=[0,*sorted(items),duration]
            rows[name]={'timestamps':items,'frames_or_offsets':len(items),'within_four_frame_budget':len(items)<=4,
                'max_sampling_gap_seconds':max(b-a for a,b in zip(points,points[1:])),
                'in_visually_annotated_hand_entry_23_to_24_5_seconds':any(23<=x<24.5 for x in items)}
        rows['dsh_original_selected']['reported_cuts']=[x['seconds'] for x in dsh['selected'] if x['reason']=='cut']
        rows['dsh_original_selected']['dropped_sheets']=dsh.get('dropped_sheets')
        rows['dsh_original_selected']['fps_parameter']=15
        rows['watch_original_requested_offsets']['reported_cuts']=watch_timeline['cuts']
        rows['fusion_actual_frames']['selected_cues']=fusion['selected_cues']
        rows['fusion_with_onsets_actual_frames']['selected_cues']=onset_fusion['selected_cues']
        print(json.dumps({'sample':{'repository':'https://github.com/opencv/opencv',
            'commit':'5d0660acfed08650cafec4876b4792a369a20601','path':'samples/data/tree.avi',
            'sha256':VIDEO_SHA,'input_bytes':video.stat().st_size,'duration_seconds':duration,
            'root_license':'Apache-2.0; separate video authorship/license not independently confirmed',
            'event_annotation':'one visual inspection: hand enters frame about 23–24.5 seconds; tree/background motion continues',
            'frames_decoded':len(times),'declared_frames':measured['expected_frames'],
            'frame_size':[160,120],'decoded_rgb_bytes':len(decoded.rgb24)},
            'methods':rows,'ffmpeg_scan_complete':measured['scan_complete'],
            'local_change_pairs':{'examined':pairs['pairs_examined'],'proposed':len(pairs['proposals']),
                                  'in_hand_entry':[p['after_seconds'] for p in pairs['proposals'] if 23<=p['after_seconds']<24.5],
                                  'omitted':pairs['omitted_proposals'],
                                  'truncated':pairs['truncated']},
            'motion_onsets':{'timestamps':[p['seconds'] for p in onsets['proposals']],
                             'unknown_intervals':onsets['unknown_intervals'],'truncated':onsets['truncated']},
            'timing':measurements,'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'rss_scope':'whole parent process peak; excludes child process RSS',
            'limits':'one visually inspected clip; timestamp-in-range is not semantic accuracy; watch requests are not decoded images; dsh receives irregular actual frame timestamps with header-like fps 15; original dsh can exceed budget; no model/Token or platform calls'},indent=2))


if __name__=='__main__':main()
