import socket
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject import SubjectLoop
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import RuntimeConfig
from nana_core.presence.fixtures import memory,concern
from types import SimpleNamespace

@pytest.fixture(autouse=True)
def offline(monkeypatch):
 def deny(*a,**k):raise AssertionError('NO_REAL_NETWORK')
 monkeypatch.setattr(socket.socket,'connect',deny)
 monkeypatch.setattr(socket,'create_connection',deny)

@pytest.fixture
def subject(tmp_path):
 with ContinuityStore(tmp_path/'subject'/'self.db',VirtualClock(),schema_target=9) as s:
  a=OperatorAuthority('synthetic-controller');IdentityService(s,a);MemoryService(s).entity('person-a','PERSON')
  r=SimpleNamespace(store=s,authority=a,clock=s.clock,config=RuntimeConfig(scopes=('lab',),entity_id='person-a'),refresh_attention=lambda:None)
  r.subject=SubjectLoop(s,scopes=('lab',))
  yield r

def event(r,key,**updates):
 from nana_core.continuity.subject import SubjectInput
 data=dict(source_key='synthetic.autonomy.'+key,kind='INTERACTION',origin='USER',entity_id=r.config.entity_id,
  scope=r.config.scopes[0],observed_at_us=r.clock.utc_now_us(),text='A fictional source event',significance='RELEVANT')
 data.update(updates);return SubjectInput(**data)
