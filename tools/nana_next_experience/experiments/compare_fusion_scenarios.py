"""Extend pinned four-method comparison with actual combined candidate outputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image
from tools.nana_next_experience.experiments.compare_video_scenarios import make_video, run
from tools.nana_next_experience.experiments.video_local_pairs import propose
from tools.nana_next_experience.experiments.video_fusion_prototype import fuse

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--dsh',type=Path,required=True)
    p.add_argument('--watch',type=Path,required=True);args=p.parse_args()
    # Original four-way script validates clean fixed upstream commits first.
    original=json.loads(run([sys.executable,str(ROOT/'compare_video_scenarios.py'),
        '--dsh',str(args.dsh),'--watch',str(args.watch)]).stdout)
    with tempfile.TemporaryDirectory(prefix='nana-fusion-scenarios-') as temp:
        root=Path(temp)
        for row in original['rows']:
            scenario=row['scenario'];video=root/(scenario+'.mp4');raw=root/(scenario+'.rgb')
            make_video(video,scenario)
            run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(video),
                 '-pix_fmt','rgb24','-f','rawvideo','-y',str(raw)])
            data=raw.read_bytes();frame_size=160*90*3
            if len(data)!=32*frame_size:raise ValueError('unexpected synthetic frame count')
            times=[i/4 for i in range(32)]
            frames=[(t,Image.frombytes('RGB',(160,90),data[i*frame_size:(i+1)*frame_size]))
                    for i,t in enumerate(times)]
            source='synthetic.'+scenario;pairs=propose(source,frames)
            request={'source_ref':source,'rgb_path':str(raw),'width':160,'height':90,'fps':4,
                     'timestamps':times,'max_frames_per_sheet':8}
            dsh=json.loads(run(['node',str(ROOT/'dsh_pipeline_adapter.mjs'),str(args.dsh.resolve())],
                payload=json.dumps(request).encode()).stdout)
            result=fuse(source,8,times,dsh,pairs,budget=4,max_gap=3)
            values=result['timestamps'];points=[0,*values,8]
            row['methods']['fused_candidate']={
                'timestamps':values,'frames':len(values),'within_budget':len(values)<=4,
                'max_gap_seconds':max(b-a for a,b in zip(points,points[1:])),
                'edit_followed_within_half_second':any(4<=x<=4.5 for x in values) if scenario=='dark_weak_cut' else None,
                'requested_offset_with_visible_text':any(3<=x<3.25 for x in values) if scenario=='brief_text_dynamic_brightness' else None,
                'local_pairs':len(pairs['proposals']),'local_pairs_truncated':pairs['truncated'],
                'model_calls':0}
    original['scope']+='; fused candidate uses actual decoded synthetic frames, no OCR or Provider'
    print(json.dumps(original,indent=2))


if __name__=='__main__':main()
