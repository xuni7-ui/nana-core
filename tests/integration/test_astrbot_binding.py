import pytest
from tools.nana_astrbot_shadow.binding import RegistryLifecycle,RealAstrBotBinding,PROBE_PATHS
from tools.nana_host_shadow.safety import digest

class FixtureRegistry:
    def __init__(self): self.callbacks={}
    def register(self,key,callback): self.callbacks[key]=callback
    def unregister(self,key): self.callbacks.pop(key,None)
    def contains(self,key): return key in self.callbacks
    def fingerprint(self): return digest(sorted(self.callbacks))

def test_registration_and_exact_unload_restore_registry():
    port=FixtureRegistry();port.callbacks['unrelated-fixture']=lambda:None
    lifecycle=RegistryLifecycle(port,'a'*64)
    before=lifecycle.registry_probe()
    assert lifecycle.register(lambda:None)['callback_present']
    assert lifecycle.unregister()==before and 'unrelated-fixture' in port.callbacks
    assert lifecycle.unregister()==before

def test_unload_and_registration_failure_cannot_claim_success():
    class Broken(FixtureRegistry):
        def register(self,k,c): super().register(k,c);raise RuntimeError('fixture error')
    p=Broken();l=RegistryLifecycle(p,'a'*64)
    with pytest.raises(RuntimeError):l.register(lambda:None)
    assert not l.registry_probe()['callback_present']
    p=FixtureRegistry();l=RegistryLifecycle(p,'a'*64);l.register(lambda:None)
    p.unregister=lambda k:None
    with pytest.raises(ValueError,match='UNLOAD_NOT_PROVEN'):l.unregister()
    assert l.active

def test_no_evidence_cannot_access_guessed_real_sdk():
    real=RealAstrBotBinding();assert real.registry_probe()['callback_present']=='UNKNOWN'
    with pytest.raises(ValueError,match='BLOCKED_API_EVIDENCE'):real.register(object())
    with pytest.raises(ValueError,match='BLOCKED_API_EVIDENCE'):real.unregister()
    with pytest.raises(ValueError,match='REAL_DISPATCH'):RegistryLifecycle(FixtureRegistry(),'a'*64,probe_class='A')
    assert [p.level for p in PROBE_PATHS if p.implemented]==['C']
    assert not any(p.real_dispatcher_proven for p in PROBE_PATHS)
