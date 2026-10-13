import json
import os
from pathlib import Path
import subprocess
import sys
from tools.nana_next_stage.qualification import qualify,matrix
from tools.nana_next_stage.__main__ import main


def test_qualification_runs_actual_prototypes_but_real_gates_remain_not_run(tmp_path):
    report=qualify(tmp_path/'experiment')
    assert report['engineering_gate']=='PASS' and all(report['checks'].values())
    assert report['physical_purge']=='NOT_IMPLEMENTED'
    assert all(v['real_acceptance']=='NOT_RUN_REAL_DEPENDENCY' for v in report['gates'].values())
    assert report['E12']=='NOT_RUN' and report['real_model_calls']==0
    for gate in ('N04','N05','N06','N11','N13'):assert report['gates'][gate]['readiness']=='PARTIAL'


def test_cli_default_e12_is_not_run_and_output_cannot_overwrite(tmp_path,capsys):
    root=tmp_path/'run'
    assert main(['e12','--output',str(root)])==0
    assert json.loads(capsys.readouterr().out)['E12']=='NOT_RUN'
    assert main(['e12','--output',str(root)])==2
    assert 'BLOCKED' in capsys.readouterr().out


def test_cli_real_plan_is_metadata_only_and_has_no_reader(tmp_path,capsys):
    out=tmp_path/'plan.json'
    assert main(['plan-template','--output',str(out)])==0
    plan=json.loads(out.read_text())
    assert plan['reader_enabled'] is False and 'records' not in plan and 'content' not in plan


def test_one_command_fresh_process_entry(tmp_path):
    env={**os.environ,'PYTHONPATH':str(Path.cwd())+os.pathsep+str(Path.cwd()/'src')}
    child=subprocess.run([sys.executable,'-m','tools.nana_next_stage','qualify','--output',str(tmp_path/'child')],
        env=env,capture_output=True,text=True,timeout=30)
    assert child.returncode==0,child.stderr
    output=json.loads(child.stdout)
    assert output['engineering_gate']=='PASS' and output['real_model_calls']==0 and output['E12']=='NOT_RUN'
