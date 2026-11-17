import shutil
import subprocess
from pathlib import Path

import pytest
Image=pytest.importorskip('PIL.Image')
ImageDraw=pytest.importorskip('PIL.ImageDraw')
from tools.nana_next_experience.experiments.video_local_change import crop_local_change
from tools.nana_next_experience.experiments.video_local_pairs import propose


def test_change_pair_preserves_both_input_times_and_bounded_overflow():
    images=[]
    for i in range(6):
        image=Image.new('L',(120,80),40)
        ImageDraw.Draw(image).rectangle((10+10*i,20,16+10*i,27),fill=220)
        images.append((i*.25,image))
    result=propose('source.synthetic',images,max_proposals=2)
    assert result['source_ref']=='source.synthetic' and result['pairs_examined']==5
    assert len(result['proposals'])==2 and result['omitted_proposals']==3 and result['truncated']
    assert result['proposals'][0]['before_seconds']==0 and result['proposals'][0]['after_seconds']==.25
    assert result['source_attestation']=='CALLER_SUPPLIED' and result['model_calls']==0


def test_duplicate_times_or_mixed_geometry_are_rejected():
    a=Image.new('L',(32,24));b=Image.new('L',(32,24))
    with pytest.raises(ValueError):propose('source',[(0,a),(0,b)])
    with pytest.raises(ValueError):propose('source',[(0,a),(1,Image.new('L',(24,32)))])


def test_actual_decoded_short_text_returns_before_and_after_frames(tmp_path):
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    if not shutil.which('ffmpeg') or not font.exists():pytest.skip('FFmpeg and fixture font required')
    video=tmp_path/'text.mp4';raw=tmp_path/'frames.rgb'
    filters=(f"eq=brightness='0.1*sin(2*PI*t)':eval=frame,"
             f"drawtext=fontfile={font}:text=CODE7:fontcolor=white:fontsize=12:"
             "x=15:y=15:enable='gte(t,3)*lt(t,3.25)'")
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=c=0x202020:s=160x90:r=4:d=8','-vf',filters,'-c:v','mpeg4','-threads','1',
        '-y',str(video)],check=True,timeout=20)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(video),
        '-pix_fmt','rgb24','-f','rawvideo','-y',str(raw)],check=True,timeout=20)
    data=raw.read_bytes();step=160*90*3
    assert len(data)==32*step
    frames=[(i/4,Image.frombytes('RGB',(160,90),data[i*step:(i+1)*step])) for i in range(32)]
    output=propose('source.synthetic.video',frames)
    event=next(x for x in output['proposals'] if x['after_seconds']==3.0)
    assert event['before_seconds']==2.75 and event['source_box'][0]<=15
    box=event['source_box'];proposal={'box':box,'coordinate_space':'input_pixels'}
    crop,metadata=crop_local_change(frames[12][1],proposal,scale=2)
    assert metadata['source_box']==box and crop.width>0 and crop.height>0
    assert 'importance' in output['meaning'] and not output['truncated']


def test_bounded_proposals_preserve_late_window_despite_early_burst():
    frames=[]
    for i in range(21):
        image=Image.new('L',(120,80),40)
        ImageDraw.Draw(image).rectangle((10+3*i,20,15+3*i,27),fill=220)
        frames.append((i*.25,image))
    later=Image.new('L',(120,80),40)
    ImageDraw.Draw(later).rectangle((90,20,95,27),fill=220)
    frames.append((99.0,later))
    result=propose('source.synthetic',frames,max_proposals=2)
    assert result['truncated'] and len(result['proposals'])==2
    assert result['proposals'][-1]['after_seconds']==99.0


def test_negative_source_timestamp_is_rejected():
    with pytest.raises(ValueError):
        propose('source', [(-.5,Image.new('L',(10,10))),(0,Image.new('L',(10,10)))])
