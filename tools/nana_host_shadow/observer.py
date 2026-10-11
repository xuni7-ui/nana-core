"""Only an operator-created local probe can enter this temporary observer.

This is an adapter-local lifecycle, NOT a claim of an AstrBot hook registration.
No host message stream is attached. A future dynamic SDK hook needs separate proof
of probe isolation and registration/unregistration without a restart.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import secrets


@dataclass(frozen=True)
class LocalProbe:
    event_id: str
    timestamp: str
    synthetic: bool = True
    private: bool = False
    source: str = 'operator_probe'
    external_delivery: bool = False


class ProbeObserver:
    def __init__(self, callback):
        self._callback = callback
        self._token = secrets.token_hex(16)
        self.active = False
        self.lifecycle = []

    def install(self):
        if self.active:
            raise ValueError('OBSERVER_ALREADY_ACTIVE')
        self.active = True
        self.lifecycle.append('install')
        return self._token

    def emit(self, probe, token):
        if not self.active or token != self._token or type(probe) is not LocalProbe:
            raise ValueError('PROBE_ONLY_OBSERVER')
        if (probe.synthetic is not True or probe.private is not False or probe.external_delivery is not False
                or probe.source != 'operator_probe' or probe.event_id != 'first-shadow-probe-v1'):
            raise ValueError('PROBE_SCOPE_BLOCKED')
        self.lifecycle.append('probe_received')
        return self._callback(probe)

    def uninstall(self):
        if self.active:
            self.active = False
            self.lifecycle.append('uninstall')
        self._callback = None


def new_probe():
    return LocalProbe(event_id='first-shadow-probe-v1', timestamp=datetime.now(timezone.utc).isoformat())
