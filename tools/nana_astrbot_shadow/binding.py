"""Registry lifecycle contract; actual AstrBot shim is blocked without source audit.

No host SDK import, core monkey-patch, Dashboard access, module guess or reload.
This neutral port is explicitly a B/C development harness, not a real registration.
"""
from dataclasses import dataclass
from typing import Protocol
from tools.nana_host_shadow.safety import digest

class RegistryPort(Protocol):
    def register(self, registration_id: str, callback): ...
    def unregister(self, registration_id: str): ...
    def contains(self, registration_id: str) -> bool: ...
    def fingerprint(self) -> str: ...

class RegistryLifecycle:
    def __init__(self, port, registration_id, *, probe_class='C'):
        if probe_class not in {'B','C'}: raise ValueError('REAL_DISPATCH_REQUIRES_SOURCE_EVIDENCE')
        self._port,self.registration_id,self.probe_class=port,registration_id,probe_class
        self.active=False
    def registry_probe(self):
        result=self._port.contains(self.registration_id)
        fingerprint=self._port.fingerprint()
        import re
        if type(result) is not bool or type(fingerprint) is not str or not re.fullmatch('[0-9a-f]{64}',fingerprint):
            raise ValueError('REGISTRY_METADATA_CONTRACT')
        return {'callback_present':result,'registry_digest':fingerprint}
    def register(self, callback):
        if self.active or self.registry_probe()['callback_present']: raise ValueError('REGISTRATION_ALREADY_PRESENT')
        try:
            self._port.register(self.registration_id,callback)
            if not self.registry_probe()['callback_present']: raise ValueError('REGISTRATION_NOT_OBSERVED')
            self.active=True
        except BaseException:
            # Registry API could have mutated and then raised: best effort exact
            # unbind only our registration; no broad registry clearing.
            self._port.unregister(self.registration_id)
            raise
        return self.registry_probe()
    def unregister(self):
        self._port.unregister(self.registration_id)
        after=self.registry_probe()
        self.active=after['callback_present']
        if self.active: raise ValueError('OBSERVER_UNLOAD_NOT_PROVEN')
        return after

class RealAstrBotBinding:
    """Source-gated placeholder, intentionally cannot guess private hook symbols.

    Nana must provide exact 4.28.0 file/symbol/hash, registration/unregistration,
    neutral return semantics, dispatcher entry and synthetic isolation evidence.
    The subsequent reviewed implementation replaces this block, not a config bit.
    """
    def register(self,*args,**kwargs): raise ValueError('BLOCKED_API_EVIDENCE')
    def unregister(self,*args,**kwargs): raise ValueError('BLOCKED_API_EVIDENCE')
    def registry_probe(self):
        return {'status':'BLOCKED_API_EVIDENCE','callback_present':'UNKNOWN','astrbot_version_boundary':'4.28.0',
                'dynamic_register':'UNKNOWN','dynamic_unregister':'UNKNOWN','restart_required':'UNKNOWN'}

@dataclass(frozen=True)
class ProbePath:
    level: str
    meaning: str
    implemented: bool
    real_dispatcher_proven: bool = False

PROBE_PATHS=(ProbePath('A','Real AstrBot internal dispatcher; exact source/host proof needed',False),
             ProbePath('B','Framework development/test-event port contract only; not host runtime proof',False),
             ProbePath('C','API-neutral plugin/lifecycle callback development harness',True))
