import asyncio
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import types
import pytest
from test_r041_bridge import fixture,ready,send
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore
from tools.nana_astrbot_shadow.bridge_wire import load_config,project_raw,frame,envelope
from tools.nana_host_shadow.safety import private_file
from test_message_hook_adapter import FakeEvent,HostileRepr,CANARY
from src.plugins.astrbot_plugin_nana_shadow_observer.bridge_client import OneShotBridgeClient


def client_config_for_adversarial_test(ipc):
    c=load_config(ipc/'client.json')
    # Deliberate fixture->real string forgery. Worker authority remains FIXTURE;
    # useful to exercise actual production client while proving no promotion.
    c['trust_domain']='PRODUCTION';p=ipc/'forged-config.json';private_file(p,c)
    return p,c

@pytest.mark.parametrize('fault',['none','timeout','cancel','death','unavailable','logger','malformed'])
def test_actual_client_pipeline_contract_and_no_automatic_retry(tmp_path,fault):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=2,trust=FixtureTrustStore())
        task,c=await ready(w)
        config,c=client_config_for_adversarial_test(ipc)
        client=OneShotBridgeClient(config,timeout=.02,logger=lambda code:(_ for _ in ()).throw(RuntimeError(CANARY)))
        e=FakeEvent(platform=raw['platform'],sender=raw['sender_id'],umo=raw['conversation_id'],
                    message_id=raw['event_id'],timestamp=raw['timestamp'])
        before=dict(vars(e));before_m=dict(vars(e.message_obj))
        seen=[];asyncio.get_running_loop().set_exception_handler(lambda l,ctx:seen.append(ctx))
        if fault in ('timeout','cancel','logger'):
            original=w._sink.accept_public
            def delayed(m):time.sleep(.06);return original(m)
            w._sink.accept_public=delayed
        if fault in ('death','unavailable'):
            # Stop test server rather than kill our pytest process; real kill test
            # in crash module exercises OS-level worker death independently.
            w.server.close();await w.server.wait_closed();w.stop_event.set()
        t=asyncio.create_task(client.on_decorating_result(HostileRepr() if fault=='malformed' else e))
        if fault=='cancel':await asyncio.sleep(.005);t.cancel()
        assert await t is None
        if fault!='malformed':
            assert await client.on_decorating_result(e) is None
            assert client.last_status=='DROP_SESSION_ATTEMPTED'
        assert vars(e)==before and vars(e.message_obj)==before_m
        await client.close();w.stop_event.set();await task
        assert seen==[]
        result=json.loads((ipc/'result.json').read_text())
        assert result['host_binding']=='UNVERIFIED' and result['real_host_bridge']=='NOT_RUN'
        if result.get('receipt',{}).get('uses')==1:
            assert result['receipt']['trust_domain']=='FIXTURE'
    asyncio.run(run())


def test_client_refuses_fixture_tag_stale_socket_and_wrong_process(tmp_path):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=2,trust=FixtureTrustStore())
        task,c=await ready(w)
        with pytest.raises(ValueError,match='FIXTURE'):OneShotBridgeClient(ipc/'client.json')
        config,c=client_config_for_adversarial_test(ipc);c['socket_inode']+=1
        forged=ipc/'drift-config.json';private_file(forged,c)
        client=OneShotBridgeClient(forged)
        e=FakeEvent(platform=raw['platform'],sender=raw['sender_id'],umo=raw['conversation_id'],message_id=raw['event_id'],timestamp=raw['timestamp'])
        assert await client.on_decorating_result(e) is None and client.last_status=='DROP_IPC_UNKNOWN'
        await client.close();w.stop_event.set();await task
        assert json.loads((ipc/'result.json').read_text())['receipt']['uses']==0
    asyncio.run(run())


def test_forbidden_dependencies_in_actual_old_sqlite_process(tmp_path,old_sqlite_python):
    code='''import sys,json,sqlite3,importlib.abc
sys.path.insert(0,sys.argv[1])
before=sqlite3.sqlite_version
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self,name,*args):
  if name.startswith(('nana_core','pydantic','tools.nana_astrbot_shadow','nana_host_shadow')):raise AssertionError('PRIVATE_RUNTIME_IMPORT')
sys.meta_path.insert(0,Guard())
from src.plugins.astrbot_plugin_nana_shadow_observer.bridge_client import OneShotBridgeClient
from src.plugins.astrbot_plugin_nana_shadow_observer.message_hook_adapter import extract_scalar_metadata
print(json.dumps({'before':before,'after':sqlite3.sqlite_version,'private_imports':[n for n in sys.modules if n.startswith(('nana_core','pydantic','tools.nana_astrbot_shadow'))]}))
'''
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC'}
    p=subprocess.run([old_sqlite_python,'-I','-c',code,str(Path('.').resolve())],env=env,capture_output=True,text=True,check=True,timeout=5)
    report=json.loads(p.stdout)
    assert report=={'before':'3.46.1','after':'3.46.1','private_imports':[]}


def test_socket_is_unix_only_no_dns_tcp(tmp_path,monkeypatch):
    root,ipc,r,raw=fixture(tmp_path)
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:(_ for _ in ()).throw(AssertionError('DNS_FORBIDDEN')))
    real=socket.socket
    def only_unix(family=socket.AF_INET,*args,**kwargs):
        assert family==socket.AF_UNIX
        return real(family,*args,**kwargs)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=2,trust=FixtureTrustStore())
        task,c=await ready(w)
        with monkeypatch.context() as m:
            m.setattr(socket,'socket',only_unix)
            result=await send(c,project_raw(raw,c));assert result['status']=='SHADOW_BLOCKED'
        await task
    asyncio.run(run())
