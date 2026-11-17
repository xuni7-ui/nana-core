import shutil
import subprocess

import pytest
from PIL import Image,ImageDraw,ImageChops
from statistics import median
import random

from tools.nana_next_experience.experiments.video_motion_onset import propose,_compensated_rate
from tools.nana_next_experience.experiments.video_pts_decode import decode
from tools.nana_next_experience.experiments.video_window_fusion import fuse_window
from tools.nana_next_experience.experiments.video_global_budget import select_windows


def gray(value,box=False):
    image=Image.new('RGB',(160,120),(value,)*3)
    if box:ImageDraw.Draw(image).rectangle((5,5,54,54),fill=(0,0,0))
    return image


def test_histogram_rate_matches_direct_pixel_oracle_including_median_ties():
    rng=random.Random(20261117)
    for width,height in ((1,1),(2,1),(3,3),(16,17)):
        for _ in range(50):
            a=bytes(rng.randrange(256) for _ in range(width*height))
            b=bytes(rng.randrange(256) for _ in range(width*height))
            values=[y-x for x,y in zip(a,b)];shift=median(values);dt=.25
            expected=sum(abs(v-shift) for v in values)/len(values)/dt
            assert _compensated_rate(Image.frombytes('L',(width,height),a),
                                     Image.frombytes('L',(width,height),b),dt)==expected


def test_motion_onset_is_only_change_cue_and_global_brightness_is_compensated():
    frames=[(i*.5,gray(100,box=i>=4)) for i in range(8)]
    result=propose('synthetic',frames)
    assert [x['seconds'] for x in result['proposals']]==[2.]
    assert result['proposals'][0]['previous_seconds']==1.5
    bright=[(i*.5,gray(100 if i<4 else 150)) for i in range(8)]
    assert propose('synthetic',bright)['proposals']==[]
    # An object moving in front of an irrelevant background is also a cue;
    # the algorithm cannot decide whether it matters to the subject.
    assert 'not semantic importance' in result['meaning']


def test_unmeasured_frame_gap_is_explicit_and_resets_baseline():
    frames=[(t,gray(100,box=t>=5)) for t in (0,.5,1,1.5,5,5.5)]
    result=propose('synthetic',frames)
    assert result['unknown_intervals']==[(1.5,5)] and result['proposals']==[]


def test_cooldown_can_suppress_a_second_distinct_change():
    frames=[]
    for i in range(12):
        image=gray(100)
        if 4<=i<8:ImageDraw.Draw(image).rectangle((5,5,54,54),fill=(0,0,0))
        if i>=8:ImageDraw.Draw(image).rectangle((90,50,139,99),fill=(0,0,0))
        frames.append((i*.5,image))
    result=propose('synthetic',frames,cooldown_seconds=3)
    assert [x['seconds'] for x in result['proposals']]==[2.]
    # A second independent change at 4s is inside the cooldown and may be lost.
    uncapped=propose('synthetic',frames,cooldown_seconds=0,max_proposals=1)
    assert uncapped['truncated'] and uncapped['omitted_proposals']>=1


def test_camera_like_frame_shift_can_also_trigger_a_motion_cue():
    # A scene-wide camera movement is observable motion, but not evidence of
    # a meaningful object or an action worth storing or acting on.
    texture=gray(100);ImageDraw.Draw(texture).rectangle((20,20,100,90),fill=(0,0,0))
    frames=[(i*.5,texture if i<4 else ImageChops.offset(texture,20,0)) for i in range(8)]
    result=propose('synthetic',frames)
    assert [x['seconds'] for x in result['proposals']]==[2.]


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='optional FFmpeg')
def test_actual_decoded_motion_cue_reaches_window_and_global_selection(tmp_path):
    path=tmp_path/'motion.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=gray:s=160x120:r=4:d=8','-vf',
        "drawbox=x=8:y=8:w=50:h=50:color=black:t=fill:enable='gte(t,3)'",
        '-c:v','mpeg4','-threads','1','-y',str(path)],check=True,timeout=20)
    decoded=decode('synthetic',path,width=160,height=120,start_seconds=0,end_seconds=8)
    size=160*120*3
    frames=[(t,Image.frombytes('RGB',(160,120),decoded.rgb24[i*size:(i+1)*size]))
            for i,t in enumerate(decoded.timestamps)]
    onsets=propose('synthetic',frames)
    assert [x['seconds'] for x in onsets['proposals']]==[3.]
    dsh={'source_ref':'synthetic','input_size':(160,120),'input_frames':len(frames),
         'qualification':'LOCAL_PIPELINE_OUTPUT_ONLY','selected':[],'dropped_sheets':0}
    pairs={'schema_version':1,'source_ref':'synthetic','input_size':(160,120),
           'pairs_examined':len(frames)-1,'truncated':False,'proposals':[]}
    old=fuse_window(decoded,dsh,pairs,budget=4,max_gap=3)
    new=fuse_window(decoded,dsh,pairs,budget=4,max_gap=3,onsets=onsets)
    assert 3. not in [f['seconds'] for f in old['selected_frames']]
    assert 3. in [f['seconds'] for f in new['selected_frames']]
    assert next(c for c in new['selected_cues'] if c['seconds']==3.)['cues']==['motion_onset']
    global_result=select_windows('synthetic',8,[new],budget=4,max_gap=3)
    assert any('motion_onset' in item['cues'] for item in global_result['selected_frames'])
    assert not new['whole_window_observed']
    with pytest.raises(ValueError,match='source or geometry'):
        fuse_window(decoded,dsh,pairs,budget=4,max_gap=3,onsets={**onsets,'source_ref':'wrong'})
