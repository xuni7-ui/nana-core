"""Regressions found before fixing support code. No Approved Core changes."""
import asyncio
import json
from pathlib import Path
import pytest
from test_r041_bridge import fixture,ready
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
import tools.nana_astrbot_shadow.bridge_worker as worker_module
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore
from nana_core.storage import Store
import os


def test_result_write_failure_still_closes_store_socket_and_executor(tmp_path,monkeypatch):
    root,ipc,r,raw=fixture(tmp_path)
    original=ShortLivedWorker._write_sidecar
    def fault(self,name,*args,**kwargs):
        if name=='result.json':raise OSError('SYNTHETIC_WRITE_FAILURE')
        return original(self,name,*args,**kwargs)
    monkeypatch.setattr(ShortLivedWorker,'_write_sidecar',fault)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=.1,trust=FixtureTrustStore())
        task,_=await ready(w)
        try:
            try:await task
            except OSError:pass
            assert not w.observer.active
            assert not (ipc/'bridge.sock').exists()
            assert not (ipc/'client.json').exists()
            with Store(root/'observer-shadow.db') as s:assert not s.all('actions')
        finally:
            # Test teardown only; never disguise the failing assertions above.
            if w.observer and w.observer.active:await w.observer.close()
    asyncio.run(run())


def test_ipc_directory_replacement_before_start_is_blocked(tmp_path):
    root,ipc,r,raw=fixture(tmp_path)
    w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=.05,trust=FixtureTrustStore())
    original=ipc.with_name('original-ipc');ipc.rename(original);ipc.mkdir(mode=0o700)
    with pytest.raises(ValueError,match='DIRECTORY.*DRIFT|DIRECTORY.*REPLACED'):
        asyncio.run(w.serve())
    assert not list(ipc.iterdir())


def test_client_capability_is_published_only_after_session_metadata(tmp_path,monkeypatch):
    root,ipc,r,raw=fixture(tmp_path)
    original=ShortLivedWorker._write_sidecar
    seen=[]
    def write(self,name,*args,**kwargs):
        if name=='client.json':
            seen.append((ipc/'session.json').is_file())
            assert seen[-1], 'CLIENT_CAPABILITY_BEFORE_SESSION_PROOF'
        return original(self,name,*args,**kwargs)
    monkeypatch.setattr(ShortLivedWorker,'_write_sidecar',write)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=.03,trust=FixtureTrustStore())
        await w.serve()
    asyncio.run(run())
    assert seen==[True]
