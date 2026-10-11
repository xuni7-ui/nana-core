import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import time
import pytest
from test_r041_bridge import fixture,ready,send
from test_r041_crash import launch,wait_file
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.bridge_wire import load_config,project_raw,envelope,frame,process_fingerprint
from tools.nana_astrbot_shadow.bridge_cli import session_status,stop,stale_cleanup
import tools.nana_astrbot_shadow.bridge_cli as cli
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore,ReceiptLedger
from tools.nana_astrbot_shadow.one_shot_cli import ReadOnlyStoreView
from tools.nana_host_shadow.safety import private_file,canonical

@contextmanager
def fixture_view(directory):
    store=ReadOnlyStoreView(Path(directory)/'observer-shadow.db')
    try:yield ReceiptLedger(store,FixtureTrustStore())
    finally:store.close()


def test_foreign_local_pid_cannot_use_copied_session_capability(tmp_path):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=2,trust=FixtureTrustStore())
        task,c=await ready(w)
        data=frame(envelope(project_raw(raw,c),c))
        code='''import socket,sys
s=socket.socket(socket.AF_UNIX);s.settimeout(1);s.connect(sys.argv[1]);s.sendall(bytes.fromhex(sys.argv[2]))
try:reply=s.recv(8192);assert not reply
except ConnectionResetError:pass
s.close()
'''
        p=await asyncio.create_subprocess_exec(sys.executable,'-c',code,c['socket_path'],data.hex(),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        out,err=await p.communicate();assert p.returncode==0
        result=await send(c,project_raw(raw,c));assert result['status']=='SHADOW_BLOCKED';await task
        report=json.loads((ipc/'result.json').read_text());assert report['receipt']['uses']==1
    asyncio.run(run())


def test_absolute_deadline_no_daemon_and_live_stale_cleanup_blocked(tmp_path,monkeypatch):
    root,ipc,r,raw=fixture(tmp_path)
    monkeypatch.setattr(cli,'operator_ledger',fixture_view)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=.1,trust=FixtureTrustStore())
        before=time.monotonic();task,c=await ready(w)
        with pytest.raises(ValueError,match='LIVE_CLEANUP'):stale_cleanup(root,ipc)
        await task
        assert time.monotonic()-before<1.5
        assert not (ipc/'bridge.sock').exists() and not (ipc/'client.json').exists()
    asyncio.run(run())


def test_sigkill_stale_cleanup_exact_inode_and_receipt_not_rearmed(tmp_path,monkeypatch):
    root,ipc,r,raw=fixture(tmp_path);p=launch(root,ipc,r.receipt_id,'never',tmp_path/'none')
    try:
        wait_file(p,ipc/'client.json');p.kill();assert p.wait(5)==-9;p.communicate(timeout=5)
        monkeypatch.setattr(cli,'operator_ledger',fixture_view)
        assert (ipc/'bridge.sock').exists()
        result=stale_cleanup(root,ipc)
        assert result['receipt_rearmed'] is False and result['store_modified'] is False
        assert not (ipc/'bridge.sock').exists() and not (ipc/'client.json').exists()
        assert (ipc/'session.json').exists() and (root/'observer-shadow.db').exists()
    finally:
        if p.poll() is None:p.kill();p.wait(5)


def test_forged_pid_or_socket_sidecar_cannot_signal_or_unlink(tmp_path,monkeypatch):
    root,ipc,r,raw=fixture(tmp_path);p=launch(root,ipc,r.receipt_id,'never',tmp_path/'none')
    calls=[]
    monkeypatch.setattr(cli,'operator_ledger',fixture_view)
    monkeypatch.setattr(os,'pidfd_open',lambda pid:calls.append(pid))
    try:
        wait_file(p,ipc/'session.json');original=json.loads((ipc/'session.json').read_text())
        forged={**original,'pid':os.getpid(),'pid_fingerprint':process_fingerprint(os.getpid())}
        private_file(ipc/'session.json',forged,replace=True)
        with pytest.raises(ValueError,match='FENCE_DRIFT'):stop(root,ipc)
        assert calls==[]
        forged={**original,'socket_inode':original['socket_inode']+1}
        private_file(ipc/'session.json',forged,replace=True)
        with pytest.raises(ValueError,match='FENCE_DRIFT'):stale_cleanup(root,ipc)
        assert (ipc/'bridge.sock').exists()
    finally:
        p.kill();p.wait(5);p.communicate(timeout=5)


def test_reject_unsafe_directory_stale_socket_and_bad_window(tmp_path):
    root,ipc,r,raw=fixture(tmp_path)
    ipc.chmod(0o755)
    with pytest.raises(ValueError,match='DIRECTORY'):ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid())
    ipc.chmod(0o700)
    s=socket.socket(socket.AF_UNIX);s.bind(str(ipc/'bridge.sock'));s.close()
    with pytest.raises(ValueError,match='NEW_IPC_DIRECTORY'):asyncio.run(ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),trust=FixtureTrustStore()).serve())
    for seconds in (0,601,True):
        with pytest.raises(ValueError):ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=seconds)


def test_operator_errors_do_not_echo_values_or_admit_fixture(tmp_path,capsys):
    root,ipc,r,raw=fixture(tmp_path)
    assert cli.main(['preflight','--directory',str(root),'--ipc-directory',str(ipc),'--receipt-id',r.receipt_id,'--client-pid',str(os.getpid())])==2
    for command in ('preflight','start','stop','collect','verify','cleanup','status'):
        assert cli.main([command,'--ipc-directory',str(ipc),'--dry-run'])==0
    assert not list(ipc.iterdir())
    assert cli.main(['start','--ipc-directory',str(ipc),'--unsafe','PRIVATE-CANARY'])==2
    assert 'PRIVATE-CANARY' not in capsys.readouterr().out

def test_tampered_session_fields_never_echo_private_data(tmp_path,capsys):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=.1,trust=FixtureTrustStore())
        task,c=await ready(w);await task
    asyncio.run(run())
    row=json.loads((ipc/'session.json').read_text());row['phase']='PRIVATE-CANARY'
    private_file(ipc/'session.json',row,replace=True)
    assert cli.main(['status','--ipc-directory',str(ipc)])==2
    assert 'PRIVATE-CANARY' not in capsys.readouterr().out
