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


def test_stale_cleanup_rejects_changed_capability_not_just_same_session(tmp_path,monkeypatch):
    from test_r041_crash import launch,wait_file
    from r044_helpers import fixture_view
    from tools.nana_astrbot_shadow.bridge_wire import load_config
    import tools.nana_astrbot_shadow.bridge_cli as cli
    from tools.nana_host_shadow.safety import private_file
    root,ipc,r,raw=fixture(tmp_path);p=launch(root,ipc,r.receipt_id,'never',tmp_path/'none')
    try:
        wait_file(p,ipc/'client.json');p.kill();p.wait(5);p.communicate(timeout=5)
        c=load_config(ipc/'client.json');c['hash_key']='0'*64
        private_file(ipc/'client.json',c,replace=True)
        monkeypatch.setattr(cli,'operator_ledger',fixture_view)
        with pytest.raises(ValueError,match='CLIENT.*DRIFT'):cli.stale_cleanup(root,ipc)
        assert (ipc/'client.json').exists()
    finally:
        if p.poll() is None:p.kill();p.wait(5)
        p.communicate(timeout=5)


def test_atomic_publication_never_exposes_two_link_configuration(tmp_path,monkeypatch):
    from tools.nana_astrbot_shadow.bridge_wire import DirectoryFence
    d=tmp_path/'private';d.mkdir(mode=0o700)
    with DirectoryFence(d) as fence:
        original=fence.entry
        def inspect(name):
            st=original(name)
            if name=='client.json':assert st.st_nlink==1,'PUBLISHED_CONFIGURATION_HAS_TWO_LINKS'
            return st
        monkeypatch.setattr(fence,'entry',inspect)
        fence.write('client.json',{'synthetic':True})
        assert (d/'client.json').stat().st_nlink==1


@pytest.mark.parametrize('case',['verify_only','expired'])
def test_preflight_never_reports_ready_for_readonly_or_expired_authorization(tmp_path,monkeypatch,case):
    from r044_helpers import fixture_view
    from tools.nana_astrbot_shadow import sealed_trust
    import tools.nana_astrbot_shadow.bridge_cli as cli
    from datetime import datetime,timezone,timedelta
    root,ipc,r,raw=fixture(tmp_path)
    # Counterfactual trusted snapshot only: no production pin is injected.
    monkeypatch.setattr(cli,'operator_ledger',fixture_view)
    monkeypatch.setattr(sealed_trust,'SEAL_MODE','VERIFY_ONLY' if case=='verify_only' else 'ONE_SHOT')
    if case=='expired':
        class FutureClock:
            @staticmethod
            def now(tz):return datetime.fromisoformat(r.expires_at)+timedelta(microseconds=1)
        monkeypatch.setattr(cli,'datetime',FutureClock)
    result=cli.preflight(root,r.receipt_id,os.getpid())
    assert result['status']=='BLOCKED'
