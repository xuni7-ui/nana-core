import socket
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.presence.authority import VirtualClock

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('NO_REAL_NETWORK')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)

@pytest.fixture
def subject(tmp_path):
    authority = OperatorAuthority()
    with ContinuityStore(tmp_path/'source'/'self.db', VirtualClock(), schema_target=10) as store:
        IdentityService(store, authority)
        MemoryService(store, authority).entity('person-a','PERSON')
        MemoryService(store, authority).entity('person-b','PERSON')
        yield store, authority
