"""Actual upstream adapter boundary; optional trusted checkout, never network."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[2]
ADAPTER=ROOT/'tools/nana_next_experience/experiments/dsh_pipeline_adapter.mjs'
UPSTREAM=os.environ.get('NANA_DSH_SOURCE')
pytestmark=pytest.mark.skipif(not UPSTREAM or not shutil.which('node'),reason='trusted dsh checkout and Node required')


def execute(payload):
    return subprocess.run(['node',str(ADAPTER),UPSTREAM],input=json.dumps(payload),text=True,
                          capture_output=True,timeout=40)


def test_actual_pipeline_retains_exact_source_frame_times(tmp_path):
    assert subprocess.check_output(['git','-C',UPSTREAM,'rev-parse','HEAD'],text=True).strip()==\
        '0b4bd110074b3e2cd043da8b078f7272589d50b0'
    w,h=160,90;frame=w*h*3
    raw=tmp_path/'frames.rgb'
    raw.write_bytes(bytes(frame)*16+bytes([255])*frame*16+bytes([80,140,200])*w*h*16)
    timestamps=[i/4 for i in range(48)]
    result=execute({'source_ref':'source.fixture','rgb_path':str(raw),'width':w,'height':h,
        'fps':4,'timestamps':timestamps,'max_frames_per_sheet':8})
    assert result.returncode==0,result.stderr
    output=json.loads(result.stdout)
    assert output['source_ref']=='source.fixture' and output['input_frames']==48
    assert {4,8}<={x['seconds'] for x in output['selected']}
    assert all(item['seconds'] in timestamps for item in output['selected'])
    assert output['qualification']=='LOCAL_PIPELINE_OUTPUT_ONLY' and output['model_calls']==0


def test_ambiguous_rounded_timestamps_are_rejected_without_guessing(tmp_path):
    raw=tmp_path/'frames.rgb';raw.write_bytes(bytes(18))
    result=execute({'source_ref':'source.fixture','rgb_path':str(raw),'width':3,'height':1,
        'fps':120,'timestamps':[0.001,0.002],'max_frames_per_sheet':2})
    assert result.returncode!=0 and 'ambiguous' in result.stderr


def test_mismatched_rgb_byte_length_is_rejected(tmp_path):
    raw=tmp_path/'frames.rgb';raw.write_bytes(bytes(8))
    result=execute({'source_ref':'source.fixture','rgb_path':str(raw),'width':3,'height':1,
        'fps':4,'timestamps':[0.0],'max_frames_per_sheet':2})
    assert result.returncode!=0 and 'RGB input' in result.stderr


def test_backpressure_separates_selection_log_from_queued_sheets(tmp_path):
    w,h=160,90;frame=w*h*3;raw=tmp_path/'alternating.rgb'
    raw.write_bytes(b''.join((bytes(frame) if (i//4)%2==0 else bytes([255])*frame) for i in range(48)))
    timestamps=[i/4 for i in range(48)]
    result=execute({'source_ref':'source.fixture','rgb_path':str(raw),'width':w,'height':h,
        'fps':4,'timestamps':timestamps,'max_frames_per_sheet':2})
    assert result.returncode==0,result.stderr
    output=json.loads(result.stdout)
    assert output['selection_state']=='SELECTED_NOT_DELIVERED' and output['model_calls']==0
    assert output['stats']['sheets']>=2 and output['queued_sheets']==1
    assert output['dropped_sheets']==output['stats']['sheets']-output['queued_sheets']
    assert output['dropped_sheets']>0
    assert set(output['queued_frame_seconds'])<={x['seconds'] for x in output['selected']}
    assert len(output['queued_frame_seconds'])<len(output['selected'])


def test_dropped_sheet_state_remains_visible_to_fusion(tmp_path):
    from tools.nana_next_experience.experiments.video_fusion_prototype import fuse
    w,h=160,90;frame=w*h*3;raw=tmp_path/'alternating.rgb'
    raw.write_bytes(b''.join((bytes(frame) if (i//4)%2==0 else bytes([255])*frame) for i in range(48)))
    timestamps=[i/4 for i in range(48)];source='source.fixture'
    result=execute({'source_ref':source,'rgb_path':str(raw),'width':w,'height':h,
        'fps':4,'timestamps':timestamps,'max_frames_per_sheet':2})
    assert result.returncode==0,result.stderr
    dsh=json.loads(result.stdout)
    pairs={'source_ref':source,'schema_version':1,'truncated':False,'proposals':[]}
    combined=fuse(source,12,timestamps,dsh,pairs,budget=4,max_gap=4)
    assert combined['dsh_dropped_sheets']==dsh['dropped_sheets']>0
    assert combined['selection_state']=='CANDIDATES_NOT_DELIVERED' and combined['model_calls']==0


def test_local_consumption_relives_backpressure_without_claiming_delivery(tmp_path):
    w,h=160,90;frame=w*h*3;raw=tmp_path/'alternating.rgb'
    raw.write_bytes(b''.join((bytes(frame) if (i//4)%2==0 else bytes([255])*frame) for i in range(48)))
    timestamps=[i/4 for i in range(48)];base={'source_ref':'source.fixture','rgb_path':str(raw),
        'width':w,'height':h,'fps':4,'timestamps':timestamps,'max_frames_per_sheet':2}
    blocked=execute(base);slow=execute({**base,'take_every_n_frames':24});immediate=execute({**base,'take_every_n_frames':1})
    assert blocked.returncode==slow.returncode==immediate.returncode==0,(blocked.stderr,slow.stderr,immediate.stderr)
    a=json.loads(blocked.stdout);middle=json.loads(slow.stdout);b=json.loads(immediate.stdout)
    assert a['dropped_sheets']>0 and a['locally_taken_sheets']==0
    assert b['dropped_sheets']==0 and b['locally_taken_sheets']>0
    assert 0<middle['dropped_sheets']<a['dropped_sheets'] and middle['locally_taken_sheets']>0
    for output in (a,middle,b):
        assert output['stats']['sheets']==output['queued_sheets']+output['dropped_sheets']+output['locally_taken_sheets']
        assert output['selection_state']=='SELECTED_NOT_DELIVERED'
        assert output['local_take_state']=='TAKEN_LOCALLY_NOT_DELIVERED' and output['model_calls']==0
        assert set(output['locally_taken_frame_seconds'])<={x['seconds'] for x in output['selected']}
