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
    original=worker_module.private_file
    def fault(path,*args,**kwargs):
        if Path(path).name=='result.json':raise OSError('SYNTHETIC_WRITE_FAILURE')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(worker_module,'private_file',fault)
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
