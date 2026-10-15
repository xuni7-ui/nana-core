import socket
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.presence.authority import RuntimeClock,RuntimeLease,VirtualClock
from nana_core.presence.contracts import RuntimeConfig

@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    def denied(*a,**kw):raise AssertionError('D runtime tests do not access network')
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr(socket,'create_connection',denied)

@pytest.fixture
def active(tmp_path):
    clock=VirtualClock()
    config=RuntimeConfig(scopes=('life',),entity_id='synthetic-person')
    with ContinuityStore(tmp_path/'self.db',clock,schema_target=8) as store:
        authority=OperatorAuthority();IdentityService(store,authority)
        MemoryService(store).entity('synthetic-person','PERSON')
        store.clock=RuntimeClock(clock)
        lease=RuntimeLease(store,config);lease.acquire()
        yield store,config,lease,clock
        lease.release()
