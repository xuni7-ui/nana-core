import json,os,subprocess,sys
from pathlib import Path
from .conftest import initialize,REPO


def test_pipe_multiple_lines_no_read_ahead_stall_or_raw_telemetry(tmp_path):
    home=tmp_path/'home';initialize(home,active=0)
    result=subprocess.run([sys.executable,'-m','nana_core.life','run','--home',str(home),'--seconds','3','--json'],input='/pause\n今天只是吐槽一下 CLI_PIPE_CANARY\n/resume\n/status\n/quit\n',text=True,capture_output=True,timeout=6,cwd=REPO,env={**os.environ,'PYTHONPATH':str(REPO/'src')})
    assert result.returncode==0,result.stderr
    rows=[json.loads(line) for line in result.stdout.splitlines()]
    assert any(x.get('autonomy')=='PAUSED' for x in rows) and any(x.get('autonomy')=='RUNNING' for x in rows)
    assert next(x for x in rows if 'dialogue' in x)['dialogue']['mode']=='VENT'
    assert rows[-1]['summary']['autonomy']=='RUNNING' and rows[-1]['wall_seconds']<2
    assert 'CLI_PIPE_CANARY' not in result.stdout


def test_second_process_cannot_acquire_same_runtime(app):
    before=app.runtime.lease.epoch
    result=subprocess.run([sys.executable,'-m','nana_core.life','run','--home',str(app.home),'--seconds','1','--headless','--json'],text=True,capture_output=True,timeout=4,cwd=REPO,env={**os.environ,'PYTHONPATH':str(REPO/'src')})
    assert result.returncode==2 and json.loads(result.stdout)['state']=='BLOCKED'
    assert app.runtime.lease.epoch==before and app.runtime.lease.assert_current()
