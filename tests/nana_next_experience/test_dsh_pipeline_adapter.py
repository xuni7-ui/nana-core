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
