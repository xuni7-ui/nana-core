"""Actual child readiness deadlines, separate from execution authority."""
import subprocess
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.hands import host


@pytest.mark.parametrize('deadline,ready',((.05,False),(10,True)))
def test_delayed_child_is_bounded_and_reaped(tmp_path,monkeypatch,deadline,ready):
    original=subprocess.Popen
    children=[]
    def delayed(args,**kwargs):
        args=list(args);args[3]='import time;time.sleep(.2);'+args[3]
        child=original(args,**kwargs);children.append(child);return child
    monkeypatch.setattr(host.subprocess,'Popen',delayed)
    if ready:
        with host.OwnedApplication(tmp_path/'app',startup_timeout_seconds=deadline) as app:
            assert app.startup_diagnostics['status']=='READY'
            assert app.target.pid==children[0].pid
    else:
        with pytest.raises(CoreError,match='OWNED_APPLICATION_START_TIMED_OUT') as failed:
            host.OwnedApplication(tmp_path/'app',startup_timeout_seconds=deadline)
        assert failed.value.startup_diagnostics['exit_code'] is None
        assert failed.value.startup_diagnostics['timeout_seconds']==deadline
    assert len(children)==1 and children[0].poll() is not None


def test_early_exit_is_distinct_and_invalid_deadline_starts_nothing(tmp_path,monkeypatch):
    original=subprocess.Popen
    children=[]
    def exits(args,**kwargs):
        args=list(args);args[3]='raise SystemExit(7)'
        child=original(args,**kwargs);children.append(child);return child
    monkeypatch.setattr(host.subprocess,'Popen',exits)
    for invalid in (0,-1,31,float('inf'),float('nan'),True,'15'):
        with pytest.raises(CoreError,match='OWNED_APPLICATION_START_TIMEOUT_INVALID'):
            host.OwnedApplication(tmp_path/'invalid',startup_timeout_seconds=invalid)
    assert not children and not (tmp_path/'invalid').exists()
    with pytest.raises(CoreError,match='OWNED_APPLICATION_START_EXITED') as failed:
        host.OwnedApplication(tmp_path/'app')
    assert failed.value.startup_diagnostics['exit_code']==7
    assert children[0].returncode==7
