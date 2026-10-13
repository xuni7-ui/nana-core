import socket
import pytest
from nana_core.clock import ManualClock
from nana_core.storage import Store
from tools.nana_next_stage.memory import PhaseAPrototype
from tools.nana_next_stage.fixtures import seed_phase_a

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Next-stage offline qualification attempted network')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.setattr(socket, 'create_connection', blocked)

@pytest.fixture
def seeded(tmp_path):
    with Store(tmp_path/'memory.db', ManualClock()) as store:
        proto = PhaseAPrototype(store)
        report, ids = seed_phase_a(proto)
        yield store, proto, report, ids
