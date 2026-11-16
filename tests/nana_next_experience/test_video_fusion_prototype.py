import pytest
from tools.nana_next_experience.experiments.video_fusion_prototype import fuse


def inputs():
    source='source.fixture'
    dsh={'source_ref':source,'qualification':'LOCAL_PIPELINE_OUTPUT_ONLY',
         'selected':[{'seconds':4.0,'reason':'cut'}]}
    pairs={'source_ref':source,'schema_version':1,'truncated':False,
           'proposals':[{'before_seconds':2.75,'after_seconds':3.0}]}
    return source,[i/4 for i in range(32)],dsh,pairs


def test_candidate_fusion_keeps_measured_lineage_and_budget():
    source,times,dsh,pairs=inputs()
    result=fuse(source,8,times,dsh,pairs,budget=4,max_gap=3)
    assert len(result['timestamps'])<=4 and set(result['timestamps'])<=set(times)
    assert result['source_ref']==source and result['source_attestation']=='CALLER_SUPPLIED'
    assert result['model_calls']==0 and result['storage']=='NONE'
    assert result['coverage_target_met'] and not result['pair_proposals_truncated']


def test_unmatched_source_and_undecoded_event_are_rejected():
    source,times,dsh,pairs=inputs()
    with pytest.raises(ValueError):fuse('different',8,times,dsh,pairs,budget=4,max_gap=3)
    pairs['proposals'][0]['after_seconds']=3.1
    with pytest.raises(ValueError,match='not decoded'):fuse(source,8,times,dsh,pairs,budget=4,max_gap=3)


def test_truncated_pair_input_is_explicit_in_output():
    source,times,dsh,pairs=inputs();pairs['truncated']=True
    result=fuse(source,8,times,dsh,pairs,budget=4,max_gap=3)
    assert result['pair_proposals_truncated'] is True


def test_nonadjacent_or_duplicate_pairs_cannot_claim_frame_lineage():
    source,times,dsh,pairs=inputs()
    pairs['proposals'][0]['after_seconds']=4.0
    with pytest.raises(ValueError,match='adjacent'):fuse(source,8,times,dsh,pairs,budget=4,max_gap=3)
    pairs['proposals']=[{'before_seconds':2.75,'after_seconds':3.0}]*2
    with pytest.raises(ValueError,match='unique'):fuse(source,8,times,dsh,pairs,budget=4,max_gap=3)


def test_real_dsh_and_local_changes_preserve_short_text_under_same_budget(tmp_path):
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    Image=pytest.importorskip('PIL.Image')
    from tools.nana_next_experience.experiments.compare_video_scenarios import make_video
    from tools.nana_next_experience.experiments.video_local_pairs import propose
    from tools.nana_next_experience.experiments.video_ffmpeg_probe import probe
    from tools.nana_next_experience.experiments.video_coverage_refine import refine
    upstream=os.environ.get('NANA_DSH_SOURCE')
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    if not upstream or not shutil.which('node') or not shutil.which('ffmpeg') or not font.exists():
        pytest.skip('fixed dsh checkout, Node, FFmpeg and fixture font required')
    assert subprocess.check_output(['git','-C',upstream,'rev-parse','HEAD'],text=True).strip()==\
        '0b4bd110074b3e2cd043da8b078f7272589d50b0'
    video=tmp_path/'fixture.mp4';raw=tmp_path/'frames.rgb'
    make_video(video,'brief_text_dynamic_brightness')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(video),
        '-pix_fmt','rgb24','-f','rawvideo','-y',str(raw)],check=True,timeout=20)
    data=raw.read_bytes();frame_size=160*90*3
    assert len(data)==32*frame_size
    times=[i/4 for i in range(32)]
    frames=[(t,Image.frombytes('RGB',(160,90),data[i*frame_size:(i+1)*frame_size]))
            for i,t in enumerate(times)]
    source='source.synthetic.video';pairs=propose(source,frames)
    root=Path(__file__).resolve().parents[2]
    adapter=root/'tools/nana_next_experience/experiments/dsh_pipeline_adapter.mjs'
    request={'source_ref':source,'rgb_path':str(raw),'width':160,'height':90,'fps':4,
             'timestamps':times,'max_frames_per_sheet':8}
    result=subprocess.run(['node',str(adapter),upstream],input=json.dumps(request),text=True,
                          capture_output=True,check=True,timeout=40)
    dsh=json.loads(result.stdout)
    measurement=probe(video)
    baseline=refine(8,measurement['candidates'],4,max_gap=3)
    combined=fuse(source,8,times,dsh,pairs,budget=4,max_gap=3)
    assert 3.0 not in baseline['timestamps'] and 3.0 in combined['timestamps']
    assert len(combined['timestamps'])==4 and combined['coverage_target_met']
    assert combined['source_ref']==source and combined['model_calls']==0


def test_cursor_change_can_consume_budget_without_proving_text():
    Image=pytest.importorskip('PIL.Image')
    ImageDraw=pytest.importorskip('PIL.ImageDraw')
    from tools.nana_next_experience.experiments.video_local_pairs import propose
    source='source.synthetic.cursor';frames=[]
    for i in range(32):
        image=Image.new('L',(120,80),40)
        if i==12:ImageDraw.Draw(image).rectangle((20,20,28,28),fill=230)
        frames.append((i/4,image))
    pairs=propose(source,frames)
    dsh={'source_ref':source,'qualification':'LOCAL_PIPELINE_OUTPUT_ONLY','selected':[]}
    result=fuse(source,8,[t for t,_ in frames],dsh,pairs,budget=4,max_gap=3)
    assert 3.0 in result['timestamps']
    assert 'no semantic importance' in result['meaning']
    assert result['model_calls']==0
