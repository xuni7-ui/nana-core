"""Real host probes plus explicit failure injection, without credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from nana_core.contracts import CoreError
from nana_core.host_requirements import sqlite_runtime_report, unix_socket_path
from nana_core.continuity import ContinuityStore
from nana_core.continuity.open_agency import code_skills


def test_real_supported_and_unsupported_interpreters(tmp_path):
    assert sqlite_runtime_report()['supported']
    with ContinuityStore(tmp_path/'ok/self.db',schema_target=13) as store:
        assert store.db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    # Real system binding, not a monkeypatched claimed old SQLite.
    code="import sys,json;sys.path.insert(0,sys.argv[1]);from nana_core.host_requirements import sqlite_runtime_report;print(json.dumps(sqlite_runtime_report()))"
    old=subprocess.run(['/usr/bin/python3','-I','-c',code,str(Path('src').resolve())],text=True,capture_output=True,check=True)
    result=json.loads(old.stdout)
    # Other developers may have a newer system Python; assert the contract,
    # not a hardcoded distro version. The current real old-host refusal is also
    # independently qualified through the built installer.
    if tuple(map(int,result['version'].split('.')))<(3,51,3):
        assert result['code']=='SQLITE_VERSION_UNSUPPORTED' and result['reason']=='WAL_RESET_CORRUPTION_FIX_REQUIRED'
    else:
        assert result['supported']==all(result['checks'].values())


def test_store_rejects_before_creating_files(tmp_path,monkeypatch):
    import sqlite3
    monkeypatch.setattr(sqlite3,'sqlite_version_info',(3,45,0))
    with pytest.raises(CoreError,match='SQLITE_VERSION_UNSUPPORTED'):
        ContinuityStore(tmp_path/'not-created/self.db',schema_target=13)
    assert not (tmp_path/'not-created').exists()


@pytest.mark.parametrize('mode',('missing','namespace-denied'))
def test_bwrap_unavailable_never_falls_back(mode,monkeypatch):
    calls=[]
    if mode=='missing':monkeypatch.setattr(code_skills.shutil,'which',lambda _:None)
    else:
        def denied(*args,**kwargs):
            calls.append(args[0]);return subprocess.CompletedProcess(args[0],1,b'',b'bwrap: namespace denied')
        monkeypatch.setattr(code_skills.subprocess,'run',denied)
    result=code_skills.IsolatedSkillRunner().qualify()
    assert result['state']=='UNAVAILABLE' and result['execution_authority'] is False
    assert len(calls)==(mode=='namespace-denied')


def test_real_bwrap_isolation_and_pure_skill():
    runner=code_skills.IsolatedSkillRunner();report=runner.qualify()
    assert report['state']=='AVAILABLE' and all(report['checks'].values())
    assert runner.run('def transform(data):\n return sum(data)\n',[1.25,2.5])==3.75
    with pytest.raises(CoreError,match='SKILL_STATIC_REJECTED'):
        runner.run('def transform(data):\n return open(data).read()\n','/etc/passwd')


def test_final_socket_bytes_and_no_subject_or_child_on_rejection(tmp_path,monkeypatch):
    assert len(os.fsencode(unix_socket_path('/'+'a'*106)))==107
    with pytest.raises(ValueError,match='UNIX_SOCKET_PATH_TOO_LONG'):unix_socket_path('/'+'a'*107)
    with pytest.raises(ValueError,match='UNIX_SOCKET_PATH_TOO_LONG'):unix_socket_path('/'+'界'*40)
    home=tmp_path/('x'*100)
    from nana_core.life.__main__ import run
    with pytest.raises(CoreError,match='UNIX_SOCKET_PATH_TOO_LONG'):run(home,1,control_enabled=True)
    from nana_core.continuity.hands.host import OwnedApplication
    with pytest.raises(CoreError,match='UNIX_SOCKET_PATH_TOO_LONG'):OwnedApplication(home)
    assert not home.exists()


@pytest.mark.parametrize('optimized',(False,True))
def test_subreaper_syscalls_execute_and_fail_in_both_modes(optimized):
    script='''import ctypes,json,sys
sys.path.insert(0,sys.argv[1])
from nana_core.presence.process_qualification import checked_prctl
libc=ctypes.CDLL(None,use_errno=True);old=ctypes.c_int();checked_prctl(libc,37,ctypes.byref(old),0,0,0)
try:
 checked_prctl(libc,36,1,0,0,0);now=ctypes.c_int();checked_prctl(libc,37,ctypes.byref(now),0,0,0)
 if now.value!=1:raise RuntimeError('SYSCALL_NOT_EXECUTED')
finally:checked_prctl(libc,36,old.value,0,0,0)
class Denied:
 def prctl(self,*args):return -1
try:checked_prctl(Denied(),36,1,0,0,0)
except OSError:denied=True
else:denied=False
print(json.dumps({'actual_subreaper':now.value,'failed_syscall_rejected':denied}))'''
    proc=subprocess.run([sys.executable,*(['-O'] if optimized else []),'-I','-c',script,str(Path('src').resolve())],check=True,text=True,capture_output=True)
    assert json.loads(proc.stdout)=={'actual_subreaper':1,'failed_syscall_rejected':True}


@pytest.mark.parametrize('optimized',(False,True))
def test_backup_quarantine_check_survives_optimization(tmp_path,optimized):
    code='''import sqlite3,sys,json
sys.path.insert(0,sys.argv[1])
from nana_core.life.cloud import backup
from nana_core.contracts import CoreError
class WrongBackup:
 def backup(self,path):
  with sqlite3.connect(path) as db:
   db.execute('create table core_meta(key,value_json)');db.execute("insert into core_meta values('recovery_quarantine','false')")
try:backup(WrongBackup(),sys.argv[2])
except CoreError as exc:print(exc.code)
else:raise RuntimeError('UNSAFE_BACKUP_ACCEPTED')'''
    proc=subprocess.run([sys.executable,*(['-O'] if optimized else []),'-I','-c',code,str(Path('src').resolve()),str(tmp_path/'bad.db')],check=True,text=True,capture_output=True)
    assert proc.stdout.strip()=='CLOUD_BACKUP_NOT_QUARANTINED'
