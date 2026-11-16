import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
ROOT=Path(__file__).resolve().parents[2]
UPSTREAM=os.environ.get('NANA_DSH_SOURCE')
pytestmark=pytest.mark.skipif(not UPSTREAM or not shutil.which('node'),reason='trusted dsh checkout and Node required')


def test_upstream_restore_preserves_newer_queue_and_unknown_is_not_retried():
    assert subprocess.check_output(['git','-C',UPSTREAM,'rev-parse','HEAD'],text=True).strip()==\
        '0b4bd110074b3e2cd043da8b078f7272589d50b0'
    program=ROOT/'tools/nana_next_experience/experiments/dsh_restore_fixture.mjs'
    result=subprocess.run(['node',str(program),UPSTREAM],capture_output=True,text=True,check=True,timeout=40)
    outcome=json.loads(result.stdout)
    assert outcome['restored_empty'] and outcome['restored_same_sheet']
    assert not outcome['restore_with_newer'] and outcome['new_from']>outcome['old_from']
    assert outcome['pending_after_unknown']==0 and outcome['unknown_state']=='UNKNOWN_NOT_RETRIED'
    assert outcome['model_calls']==outcome['external_sends']==0
