"""R04 package/source-entry checks without actual AstrBot installation."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import asyncio
import pytest
from test_r04_receipt import setup,arm,RAW,FixtureTrustStore,OneShotSanitizer,OneShotCoreSink,OneShotObserver
from tools.nana_astrbot_shadow.one_shot_harness import run
from tools.nana_astrbot_shadow.package import verify_package


def test_foreground_harness_proof_and_restart(tmp_path):
    report=run(tmp_path/'shadow')
    assert report['status']=='SIMULATED_REAL_SHADOW_PROOF_PASS'
    assert report['receipt_status']['uses']==1 and report['identity_continuous']
    assert report['host_binding']=='UNVERIFIED' and report['observer_closed']
    assert report['real_message']=='NOT_RUN'


def test_dormant_plugin_no_body_no_yield_and_fixture_bind_blocked(tmp_path,monkeypatch):
    from test_message_hook_adapter import FakeEvent
    plugin=Path('src/plugins/astrbot_plugin_nana_shadow_observer')
    package='r04_offline_plugin';module=types.ModuleType(package);module.__path__=[str(plugin.resolve())]
    monkeypatch.setitem(sys.modules,package,module)
    def decorator(*a,**k):return lambda f:f
    api_event=types.ModuleType('astrbot.api.event');api_event.filter=types.SimpleNamespace(on_decorating_result=decorator)
    api_star=types.ModuleType('astrbot.api.star');api_star.Star=object;api_star.register=decorator
    for name,value in [('astrbot',types.ModuleType('astrbot')),('astrbot.api',types.ModuleType('astrbot.api')),('astrbot.api.event',api_event),('astrbot.api.star',api_star)]:
        monkeypatch.setitem(sys.modules,name,value)
    spec=importlib.util.spec_from_file_location(package+'.main',plugin/'r04_main.py')
    main=importlib.util.module_from_spec(spec);spec.loader.exec_module(main)
    assert asyncio.run(main.nana_shadow_r04_on_decorating_result(FakeEvent())) is None
    assert main._ADAPTER is None
    from importlib import import_module
    cls=import_module(package+'.message_hook_adapter').OneShotMessageHookAdapter
    sink,l,r=setup(tmp_path/'shadow');arm(l,r);sink.close()
    s=OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=r.receipt_id)
    observer=OneShotObserver(s,OneShotCoreSink(tmp_path/'shadow',s,r.receipt_id,trust=FixtureTrustStore()))
    with pytest.raises(ValueError,match='TRUSTED_PRODUCTION'):main.bind_reviewed_adapter(cls(observer=observer))
    assert main.bind_reviewed_adapter(None) is None
    asyncio.run(observer.close())
    # No generator/result/event mutation even when adapter raises cancellation.
    class Broken:
        async def on_decorating_result(self,e):raise asyncio.CancelledError()
        async def close(self):raise RuntimeError('synthetic-private-canary')
    main._ADAPTER=Broken()
    assert asyncio.run(main.nana_shadow_r04_on_decorating_result(FakeEvent())) is None
    assert asyncio.run(main.NanaShadowOneShotObserver().terminate()) is None
    assert main._ADAPTER is None
