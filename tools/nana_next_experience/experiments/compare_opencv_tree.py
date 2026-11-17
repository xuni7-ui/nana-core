"""Local sampling comparisons on fixed public OpenCV samples; no model calls."""
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

SAMPLES={
    'tree':{'path':'samples/data/tree.avi','size':1250680,'fps':15,'gap':8,
        'sha256':'4666099d0f704e310047b2f0a5ec9f936cb76a7271de9a2e70a0c57f82ac82dc',
        'annotation':'one visual inspection: hand enters frame about 23–24.5 seconds; tree/background motion continues'},
    'vtest':{'path':'samples/data/vtest.avi','size':8131690,'fps':10,'gap':20,
        'sha256':'45cddc9490be69345cbdab64ca583be65987e864ca408038e648db99e10516cf',
        'annotation':'held-out fixed-camera pedestrian motion; no frame-level semantic ground truth'},
}
UPSTREAM={'dsh':'0b4bd110074b3e2cd043da8b078f7272589d50b0',
          'watch':'8ca266f9cf9e5ffce7e9d424aa0e937a897b608d'}


def run(args,*,payload=None,cwd=None):
    env={'PATH':os.defpath,'LANG':'C.UTF-8'}
    return subprocess.run(args,input=payload,stdin=subprocess.DEVNULL if payload is None else None,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=120,cwd=cwd,env=env)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--video',type=Path,required=True)
    parser.add_argument('--sample',choices=tuple(SAMPLES),default='tree')
    parser.add_argument('--native-core',action='store_true',help='also run original sandboxed S5 VIDEO decoder for the <=30s sample')
    parser.add_argument('--dsh',type=Path,required=True);parser.add_argument('--watch',type=Path,required=True)
    args=parser.parse_args();video=args.video.resolve(strict=True);sample=SAMPLES[args.sample]
    if video.stat().st_size!=sample['size'] or hashlib.sha256(video.read_bytes()).hexdigest()!=sample['sha256']:
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
        measured=timed('ffmpeg_scene_probe',lambda:probe(video));duration=measured['duration'];source='opencv.'+args.sample
        decoded=timed('decode_rgb',lambda:decode(source,video,width=160,height=120,
                                                 start_seconds=0,end_seconds=duration))
        raw.write_bytes(decoded.rgb24)
        times=list(decoded.timestamps)
        def closest(value):
            at=bisect_left(times,value);options=[times[i] for i in (at-1,at) if 0<=i<len(times)]
            return min(options,key=lambda x:(abs(x-value),x))
        uniform=[closest(duration*(i+.5)/4) for i in range(4)]
        scene=sorted(c.seconds for c in sorted(measured['candidates'],key=lambda x:(-x.cut,x.seconds))[:4])
        request={'source_ref':source,'rgb_path':str(raw),'width':160,'height':120,'fps':sample['fps'],
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
        pairs=timed('local_change_pairs',lambda:propose(source,frames))
        fusion=timed('fusion_planning',lambda:fuse_window(decoded,dsh,pairs,budget=4,max_gap=sample['gap']))
        onsets=timed('motion_onset_probe',lambda:motion_onsets(source,frames))
        onset_fusion=timed('onset_fusion_planning',lambda:fuse_window(decoded,dsh,pairs,budget=4,max_gap=sample['gap'],onsets=onsets))
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
                'in_visually_annotated_hand_entry_23_to_24_5_seconds':
                    any(23<=x<24.5 for x in items) if args.sample=='tree' else None}
        rows['dsh_original_selected']['reported_cuts']=[x['seconds'] for x in dsh['selected'] if x['reason']=='cut']
        rows['dsh_original_selected']['dropped_sheets']=dsh.get('dropped_sheets')
        rows['dsh_original_selected']['fps_parameter']=sample['fps']
        rows['watch_original_requested_offsets']['reported_cuts']=watch_timeline['cuts']
        rows['fusion_actual_frames']['selected_cues']=fusion['selected_cues']
        rows['fusion_with_onsets_actual_frames']['selected_cues']=onset_fusion['selected_cues']
        native=None
        if args.native_core:
            if duration>30:raise ValueError('original S5 video duration bound is 30 seconds')
            from nana_core.continuity.world_loop.perception import MediaDecoder
            original=timed('original_s5_decoder',lambda:MediaDecoder().decode(video.read_bytes(),'VIDEO'))
            old8=fuse_window(decoded,dsh,pairs,budget=8,max_gap=4.7)
            new8=fuse_window(decoded,dsh,pairs,budget=8,max_gap=4.7,onsets=onsets)
            def describe_eight(values):
                points=[0,*values,duration]
                return {'timestamps':values,'frames':len(values),
                    'max_sampling_gap_seconds':max(b-a for a,b in zip(points,points[1:])),
                    'hand_entry_23_to_24_5_seconds':any(23<=t<24.5 for t in values)}
            native={'original_s5':describe_eight([f['sample_s'] for f in original['frames']]),
                    'fusion_without_onset':describe_eight([f['seconds'] for f in old8['selected_frames']]),
                    'fusion_with_onset':describe_eight([f['seconds'] for f in new8['selected_frames']]),
                    'original_s5_pixels':[96,64],'candidate_pixels':[160,120],
                    'limits':'8-frame comparison only; different image geometry, no matched Provider tokens or semantic score'}
        print(json.dumps({'sample':{'repository':'https://github.com/opencv/opencv',
            'commit':'5d0660acfed08650cafec4876b4792a369a20601','path':sample['path'],
            'sha256':sample['sha256'],'input_bytes':video.stat().st_size,'duration_seconds':duration,
            'root_license':'Apache-2.0; separate video authorship/license not independently confirmed',
            'event_annotation':sample['annotation'],'fusion_max_gap_target_seconds':sample['gap'],
            'frames_decoded':len(times),'declared_frames':measured['expected_frames'],
            'frame_size':[160,120],'decoded_rgb_bytes':len(decoded.rgb24)},
            'methods':rows,'ffmpeg_scan_complete':measured['scan_complete'],
            'native_s5_eight_frame_comparison':native,
            'local_change_pairs':{'examined':pairs['pairs_examined'],'proposed':len(pairs['proposals']),
                                  'in_hand_entry':[p['after_seconds'] for p in pairs['proposals'] if 23<=p['after_seconds']<24.5]
                                      if args.sample=='tree' else None,
                                  'omitted':pairs['omitted_proposals'],
                                  'truncated':pairs['truncated']},
            'motion_onsets':{'timestamps':[p['seconds'] for p in onsets['proposals']],
                             'unknown_intervals':onsets['unknown_intervals'],'truncated':onsets['truncated']},
            'timing':measurements,'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'rss_scope':'whole parent process peak; excludes child process RSS',
            'limits':'one visually inspected clip per run; timestamp-in-range is not semantic accuracy; watch requests are not decoded images; dsh receives actual timestamps and a nominal fps parameter; original dsh can exceed budget; no model/Token or platform calls'},indent=2))


if __name__=='__main__':main()
