import asyncio
from nana_core.contracts import CoreError
from nana_core.nanalink.management import AdapterManagement
from nana_core.nanalink.sdk import AdapterManifest
from nana_core.nanalink.contracts import Account,SessionHealth
from tests.nanalink.test_onebot_network import network
import pytest
from aiohttp import ClientSession


class Fake:
    def __init__(self,version='1.0.0',bad=False):
        self.manifest=AdapterManifest(adapter_id='fixture.adapter',version=version,platforms=('fixture',),license='Original fixture')
        self.account=Account(platform='fixture',adapter_id='fixture.adapter',account_id='42');self.bad=bad;self.connected=False
    async def connect(self):
        if self.bad:raise OSError('owned failure')
        self.connected=True
    async def disconnect(self):self.connected=False
    def health(self):return SessionHealth(connection='CONNECTED' if self.connected else 'DISCONNECTED')
    def capabilities(self):return ()


def test_offline_installed_versions_persist_rollback_and_isolate_failure(tmp_path):
    async def run():
        factories={'1.0.0':lambda:Fake(),'1.1.0':lambda:Fake('1.1.0'),'1.2.0':lambda:Fake('1.2.0',True)}
        catalogs={'primary':factories,'other':{'1.0.0':lambda:Fake()}}
        # Separate account identity for isolation (same plugin, different account).
        def other():
            f=Fake();f.account=f.account.model_copy(update={'account_id':'43'});return f
        catalogs['other']['1.0.0']=other
        state=tmp_path/'private'/'adapters.json'
        manager=AdapterManagement({'primary':Fake(),'other':other()},catalogs,state_path=state)
        async def op(operation,version=None):return await manager.command('primary',operation,version,manager.view('primary')['revision'])
        with pytest.raises(CoreError):await op('UPGRADE','1.1.0')
        await op('DISABLE');await op('UPGRADE','1.1.0')
        assert manager.view('primary')['current']=='1.1.0' and manager.view('primary')['previous']=='1.0.0'
        restored=AdapterManagement({'primary':Fake(),'other':other()},catalogs,state_path=state)
        assert restored.adapter('primary').manifest.version=='1.1.0' and not restored.enabled('primary')
        await op('ROLLBACK');assert manager.view('primary')['current']=='1.0.0'
        await op('UPGRADE','1.2.0');result=await op('ENABLE')
        assert result['state']=='UNKNOWN_NO_AUTORETRY' and not manager.enabled('primary')
        assert manager.enabled('other') and manager.view('other')['current']=='1.0.0'
        restored=AdapterManagement({'primary':Fake(),'other':other()},catalogs,state_path=state)
        assert not restored.enabled('primary') and restored.view('primary')['uncertain']
        await op('DISABLE');await op('ROLLBACK');await op('UNINSTALL')
        assert not manager.view('primary')['installed']
        await op('INSTALL','1.0.0');assert not manager.enabled('primary')
        with pytest.raises(CoreError):await op('UPGRADE','9.9.9')
        with pytest.raises(CoreError):await manager.command('primary','ENABLE',None,1)
    asyncio.run(run())


def test_failed_disconnect_is_uncertain_and_stays_paused_across_restart(tmp_path):
    class FailingDisconnect(Fake):
        fail = True
        calls = 0
        async def disconnect(self):
            self.calls += 1
            if self.fail:
                raise OSError('synthetic disconnect failure')
            self.connected = False

    async def run():
        first=FailingDisconnect();first.connected=True
        other=Fake();other.account=other.account.model_copy(update={'account_id':'43'})
        catalogs={'primary':{'1.0.0':FailingDisconnect}, 'other':{'1.0.0':lambda:other}}
        state=tmp_path/'private'/'adapters.json'
        manager=AdapterManagement({'primary':first,'other':other},catalogs,state_path=state)
        result=await manager.command('primary','DISABLE',None,manager.view('primary')['revision'])
        assert result['state']=='UNKNOWN_NO_AUTORETRY'
        assert result['uncertain'] and not result['enabled'] and first.connected
        assert first.calls==1 and manager.enabled('other')
        restored=AdapterManagement({'primary':FailingDisconnect(),'other':other},catalogs,state_path=state)
        assert restored.view('primary')['uncertain'] and not restored.enabled('primary')
        with pytest.raises(CoreError,match='NANALINK_UNCERTAIN_RECONCILIATION_REQUIRED'):
            await manager.command('primary','ENABLE',None,manager.view('primary')['revision'])
        first.fail=False
        result=await manager.command('primary','DISABLE',None,manager.view('primary')['revision'])
        assert result['state']=='APPLIED' and not result['uncertain'] and not first.connected
        assert first.calls==2 and manager.enabled('other')
    asyncio.run(run())


def test_failed_uninstall_disconnect_preserves_installed_version():
    class FailingDisconnect(Fake):
        async def disconnect(self):raise OSError('synthetic disconnect failure')
    async def run():
        first=FailingDisconnect()
        manager=AdapterManagement({'primary':first},{'primary':{'1.0.0':FailingDisconnect}})
        manager.registry.slots[manager.keys['primary']].enabled=False
        result=await manager.command('primary','UNINSTALL',None,manager.view('primary')['revision'])
        assert result['state']=='UNKNOWN_NO_AUTORETRY' and result['uncertain']
        assert result['installed'] and not result['enabled'] and result['current']=='1.0.0'
    asyncio.run(run())


def test_sdk_uninstall_keeps_slot_if_disconnect_fails():
    from nana_core.nanalink.sdk import AdapterRegistry
    class FailingDisconnect(Fake):
        async def disconnect(self):raise OSError('synthetic disconnect failure')
    async def run():
        registry=AdapterRegistry();adapter=FailingDisconnect();key=registry.install(adapter)
        assert await registry.enable(key)
        with pytest.raises(CoreError,match='NANALINK_SHUTDOWN_INCOMPLETE'):
            await registry.uninstall(key)
        assert key in registry.slots and not registry.slots[key].enabled
        assert registry.slots[key].fault=='SHUTDOWN_INCOMPLETE'
    asyncio.run(run())


def test_uncertain_install_can_be_explicitly_reconciled_while_uninstalled():
    async def run():
        def bad_factory():raise OSError('synthetic factory failure')
        manager=AdapterManagement({'primary':Fake()},{'primary':{'1.0.0':Fake,'1.1.0':bad_factory}})
        async def op(name,version=None):
            return await manager.command('primary',name,version,manager.view('primary')['revision'])
        await op('DISABLE');await op('UNINSTALL')
        result=await op('INSTALL','1.1.0')
        assert result['state']=='UNKNOWN_NO_AUTORETRY' and result['uncertain'] and not result['installed']
        result=await op('DISABLE')
        assert result['state']=='APPLIED' and not result['uncertain'] and not result['installed']
        assert (await op('INSTALL','1.0.0'))['state']=='APPLIED'
    asyncio.run(run())


def test_actual_management_http_auth_revision_no_platform_send():
    with network(mode='http') as (net,state,resolver,loop):
        async def run():
            url=net['endpoint']+'/nanalink/manage'
            headers={'Authorization':'Bearer FIXTURE_ONLY_CORE_NOT_A_REAL_SECRET'}
            async with ClientSession() as client:
                assert (await client.get(url)).status==403
                view=await (await client.get(url,headers=headers)).json()
                body={'operation':'DISABLE','version':None,'revision':view['revision']}
                result=await (await client.post(url,headers=headers,json=body)).json()
                assert result['state']=='APPLIED' and not result['enabled']
                assert (await client.post(url,headers=headers,json=body)).status==502
                body.update(operation='UNINSTALL',revision=result['revision'])
                result=await (await client.post(url,headers=headers,json=body)).json()
                assert not result['installed']
                assert not state['sent']
        asyncio.run_coroutine_threadsafe(run(),loop).result(5)


def test_http_disable_failure_reports_unknown_and_cancels_pending_input():
    from tests.nanalink.test_onebot_network import message
    with network(mode='http') as (net,state,resolver,loop):
        async def run():
            sidecar=net['sidecar'];adapter=net['adapter']
            original=adapter.disconnect
            async def fail():raise OSError('synthetic disconnect failure')
            adapter.disconnect=fail
            try:
                assert adapter.offer(message(11))=='QUEUED'
                headers={'Authorization':'Bearer FIXTURE_ONLY_CORE_NOT_A_REAL_SECRET'}
                async with ClientSession() as client:
                    url=net['endpoint']+'/nanalink/manage'
                    view=await (await client.get(url,headers=headers)).json()
                    response=await client.post(url,headers=headers,json={
                        'operation':'DISABLE','version':None,'revision':view['revision']})
                    result=await response.json()
                    assert response.status==200 and result['state']=='UNKNOWN_NO_AUTORETRY'
                    assert result['uncertain'] and not result['enabled']
                    assert result['cancelled_queued_events']==1 and adapter.events.empty()
                    assert not state['sent']
            finally:
                adapter.disconnect=original
        asyncio.run_coroutine_threadsafe(run(),loop).result(5)


def test_http_disable_cancels_queued_input_before_reenable():
    from nana_core.nanalink.onebot import normalize
    from tests.nanalink.test_onebot_network import message
    with network(mode='http') as (net,state,resolver,loop):
        async def run():
            sidecar=net['sidecar']; adapter=net['adapter']
            assert adapter.offer(message(11)) == 'QUEUED'
            assert sidecar.transport.offer(normalize(adapter.account,message(12))) == 'QUEUED'
            url=net['endpoint']+'/nanalink/manage'
            headers={'Authorization':'Bearer FIXTURE_ONLY_CORE_NOT_A_REAL_SECRET'}
            async with ClientSession() as client:
                view=await (await client.get(url,headers=headers)).json()
                body={'operation':'DISABLE','version':None,'revision':view['revision']}
                result=await (await client.post(url,headers=headers,json=body)).json()
                assert result['state']=='APPLIED' and not result['enabled']
                assert result['cancelled_queued_events']==2
                assert adapter.events.empty() and sidecar.transport.size==0
                body.update(operation='ENABLE',revision=result['revision'])
                result=await (await client.post(url,headers=headers,json=body)).json()
                assert result['state']=='APPLIED' and adapter.events.empty() and sidecar.transport.size==0
                assert not state['sent']
        asyncio.run_coroutine_threadsafe(run(),loop).result(5)
