import asyncio
from dataclasses import dataclass
import pytest
from tools.nana_astrbot_shadow.astrbot_shim import AstrBotLifecycleBinding,MODULE
from tools.nana_astrbot_shadow.observer import ShadowObserver
from test_astrbot_sanitizer import sanitizer,event,Sink,SecretRepr

@dataclass
class Handler:
    handler: object
class Registry:
    def __init__(self):self.handlers=[]
    def get_handlers_by_module_name(self,module):return [h for h in self.handlers if h.handler.__module__==module]
    def remove(self,h):self.handlers.remove(h)
class Filters:
    def __init__(self,registry):self.registry=registry
    def on_plugin_loaded(self):return self.decorate
    def on_plugin_unloaded(self):return self.decorate
    def decorate(self,f):self.registry.handlers.append(Handler(f));return f


def test_source_audited_lifecycle_shim_ignores_metadata_and_unbinds_exact_callbacks():
    async def run():
        r=Registry();filters=Filters(r)
        async def unrelated(metadata):return None
        unrelated.__module__=MODULE;r.handlers.append(Handler(unrelated))
        o=ShadowObserver(sanitizer(),Sink())
        b=AstrBotLifecycleBinding(filter_api=filters,registry=r,observed_version='4.28.0',observer=o,metadata=event(content='synthetic-private-canary'))
        assert 'content' not in b.metadata
        before=b.registry_probe();assert not before['callback_present']
        assert b.register()['callback_count']==2
        owned=b._owned()
        assert await owned[0].handler(SecretRepr()) is None and o.last_result['status']=='IDLE'
        b.arm_operator_probe();assert await owned[0].handler(SecretRepr()) is None
        assert o.last_result['status']=='RECORDED'
        assert not b.registry_probe()['dispatcher_proven'] and b.registry_probe()['probe_class']=='C'
        assert (await b.unregister())==before
        assert r.handlers==[Handler(unrelated)]
    asyncio.run(run())


def test_version_and_api_drift_block_before_any_registry_mutation():
    r=Registry();o=ShadowObserver(sanitizer(),Sink())
    try:
        with pytest.raises(ValueError,match='API_DRIFT'):AstrBotLifecycleBinding(filter_api=Filters(r),registry=r,observed_version='4.29.0',observer=o,metadata=event())
        with pytest.raises(ValueError,match='API_DRIFT'):AstrBotLifecycleBinding(filter_api=object(),registry=r,observed_version='4.28.0',observer=o,metadata=event())
        assert not r.handlers
    finally:asyncio.run(o.close())
