import os
from pathlib import Path
import json
import shutil
import subprocess
import pytest
from tools.nana_next_experience.experiments.video_pts_decode import decode
from tools.nana_next_experience.experiments.video_window_fusion import fuse_window
from tests.nana_next_experience.test_video_pts_decode import make_vfr


def test_empty_vfr_window_does_not_invent_a_scene(tmp_path):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):pytest.skip('optional FFmpeg unavailable')
    video=tmp_path/'vfr.mp4';make_vfr(video)
    decoded=decode('source.synthetic',video,start_seconds=.6,end_seconds=1.6)
    result=fuse_window(decoded,None,None,budget=4,max_gap=1)
    assert result['status']=='NO_NEW_FRAME_DECODED_NOT_OBSERVED'
    assert result['selected_frames']==[] and result['unknown_intervals']==[(.6,1.6)]
    assert result['whole_window_observed'] is False


def test_real_offset_pts_fuse_through_original_dsh_and_return_original_ticks(tmp_path):
    upstream=os.environ.get('NANA_DSH_SOURCE')
    if not upstream or not all(shutil.which(x) for x in ('node','ffmpeg','ffprobe')):
        pytest.skip('trusted dsh, Node and FFmpeg required')
    video=tmp_path/'vfr.mp4';offset=tmp_path/'offset.mp4';make_vfr(video)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(video),'-c','copy',
        '-output_ts_offset','5','-y',str(offset)],check=True,timeout=20)
    decoded=decode('source.synthetic',offset,start_seconds=.6,end_seconds=2.1)
    raw=tmp_path/'rgb';raw.write_bytes(decoded.rgb24)
    root=Path(__file__).resolve().parents[2]
    request={'source_ref':decoded.source_ref,'rgb_path':str(raw),'width':160,'height':90,
        'fps':4,'timestamps':decoded.timestamps,'max_frames_per_sheet':2}
    p=subprocess.run(['node',str(root/'tools/nana_next_experience/experiments/dsh_pipeline_adapter.mjs'),upstream],
        input=json.dumps(request),text=True,capture_output=True,check=True,timeout=40)
    dsh=json.loads(p.stdout)
    pairs={'schema_version':1,'source_ref':decoded.source_ref,'input_size':decoded.output_size,
           'pairs_examined':len(decoded.timestamps)-1,'truncated':False,'proposals':[]}
    output=fuse_window(decoded,dsh,pairs,budget=2,max_gap=2)
    assert output['source_ref']==decoded.source_ref and output['timeline_origin']=='5.000000'
    assert output['status']=='WINDOW_CANDIDATES_ONLY' and output['model_calls']==0
    assert all(x['seconds'] in decoded.timestamps and x['pts_tick'] in decoded.pts_ticks for x in output['selected_frames'])
    assert all(.6<=x['seconds']<2.1 for x in output['selected_frames'])
    assert output['selection_state']=='CANDIDATES_NOT_DELIVERED'
    assert output['decoded_size']==decoded.output_size and output['source_size']==decoded.source_size
    assert output['coordinate_space']=='decoded_scaled_pixels_no_rotation'
    assert output['whole_window_observed'] is False and output['gap_definition']=='ONLY_GAPS_OVER_REQUESTED_THRESHOLD'
    from tools.nana_next_experience.experiments.video_global_budget import select_windows
    global_output=select_windows(decoded.source_ref,decoded.duration_seconds,[output],budget=2,max_gap=2)
    assert all(any(frame['pts_tick']==f['pts_tick'] for f in output['selected_frames'])
               for frame in global_output['selected_frames'])
    assert global_output['candidate_deduplication']=='PTS_ONLY_BYTES_UNVERIFIED'
    pairs['proposals']=[{'before_seconds':decoded.timestamps[0],'after_seconds':decoded.timestamps[1],
        'source_box':(0,0,999,999),'coordinate_space':'input_pixels'}]
    with pytest.raises(ValueError,match='outside decoded'):fuse_window(decoded,dsh,pairs,budget=2,max_gap=2)
    pairs['proposals']=[]
    from dataclasses import replace
    tampered=replace(decoded,pts_ticks=(decoded.pts_ticks[0]+1,*decoded.pts_ticks[1:]))
    with pytest.raises(ValueError,match='source pts'):fuse_window(tampered,dsh,pairs,budget=2,max_gap=2)
    with pytest.raises(ValueError,match='source'):
        fuse_window(decoded,{**dsh,'input_size':[32,32]},pairs,budget=2,max_gap=2)
    pairs['source_ref']='different.source'
    with pytest.raises(ValueError,match='source'):fuse_window(decoded,dsh,pairs,budget=2,max_gap=2)


def test_long_video_tail_window_preserves_source_ticks_through_real_pipeline(tmp_path):
    upstream=os.environ.get('NANA_DSH_SOURCE')
    if not upstream or not all(shutil.which(x) for x in ('node','ffmpeg','ffprobe')):
        pytest.skip('trusted dsh, Node and FFmpeg required')
    Image=pytest.importorskip('PIL.Image')
    from tools.nana_next_experience.experiments.video_local_pairs import propose
    video=tmp_path/'long.mp4';raw=tmp_path/'tail.rgb'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=black:s=32x32:r=1:d=601','-c:v','mpeg4','-g','1','-threads','1',
        '-y',str(video)],check=True,timeout=30)
    decoded=decode('source.synthetic',video,width=32,height=32,start_seconds=599,end_seconds=601)
    raw.write_bytes(decoded.rgb24);size=32*32*3
    frames=[(t,Image.frombytes('RGB',(32,32),decoded.rgb24[i*size:(i+1)*size]))
            for i,t in enumerate(decoded.timestamps)]
    pairs=propose(decoded.source_ref,frames)
    root=Path(__file__).resolve().parents[2]
    request={'source_ref':decoded.source_ref,'rgb_path':str(raw),'width':32,'height':32,
        'fps':1,'timestamps':decoded.timestamps,'max_frames_per_sheet':2}
    p=subprocess.run(['node',str(root/'tools/nana_next_experience/experiments/dsh_pipeline_adapter.mjs'),upstream],
        input=json.dumps(request),text=True,capture_output=True,check=True,timeout=40)
    output=fuse_window(decoded,json.loads(p.stdout),pairs,budget=2,max_gap=2)
    assert [item['seconds'] for item in output['selected_frames']]==[599.0,600.0]
    assert [item['pts_tick'] for item in output['selected_frames']]==list(decoded.pts_ticks)
    assert output['requested_window']==(599,601) and output['whole_window_observed'] is False
    assert output['model_calls']==0 and output['selection_state']=='CANDIDATES_NOT_DELIVERED'


def test_fractional_origin_survives_dsh_and_global_candidate_contract(tmp_path):
    upstream=os.environ.get('NANA_DSH_SOURCE')
    if not upstream or not all(shutil.which(x) for x in ('node','ffmpeg','ffprobe')):
        pytest.skip('trusted dsh, Node and FFmpeg required')
    video=tmp_path/'fractional-origin.ts'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=c=red:s=32x24:r=24:d=1','-c:v','mpeg2video','-threads','1',
        '-f','mpegts','-y',str(video)],check=True,timeout=20)
    decoded=decode('source.synthetic',video,width=32,height=24,start_seconds=0,end_seconds=.25)
    raw=tmp_path/'rgb';raw.write_bytes(decoded.rgb24)
    root=Path(__file__).resolve().parents[2]
    request={'source_ref':decoded.source_ref,'rgb_path':str(raw),'width':32,'height':24,
        'fps':24,'timestamps':decoded.timestamps,'max_frames_per_sheet':6}
    proc=subprocess.run(['node',str(root/'tools/nana_next_experience/experiments/dsh_pipeline_adapter.mjs'),upstream],
        input=json.dumps(request),text=True,capture_output=True,check=True,timeout=40)
    pairs={'schema_version':1,'source_ref':decoded.source_ref,'input_size':decoded.output_size,
           'pairs_examined':len(decoded.timestamps)-1,'truncated':False,'proposals':[]}
    output=fuse_window(decoded,json.loads(proc.stdout),pairs,budget=3,max_gap=.25)
    from tools.nana_next_experience.experiments.video_global_budget import select_windows
    selected=select_windows(decoded.source_ref,decoded.duration_seconds,[output],budget=3,max_gap=.25)
    assert output['timeline_origin']=='173/120'
    assert selected['selected_frames'] and all(f['pts_tick'] in decoded.pts_ticks for f in selected['selected_frames'])
    assert output['whole_window_observed'] is False
