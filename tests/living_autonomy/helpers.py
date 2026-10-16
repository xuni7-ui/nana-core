from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.contracts import LivingRuntimeConfig,RuntimeEvent,Cause
from nana_core.continuity.subject import SubjectInput
from nana_core.presence.authority import VirtualClock

def fresh(path,*,clock=None,model=None,living=None,**kwargs):
    clock=clock or VirtualClock()
    with ContinuityStore(path,clock,schema_target=11) as s:
        IdentityService(s,OperatorAuthority());MemoryService(s).entity('synthetic-person','PERSON')
    return NanaRuntime(path,RuntimeConfig(schema_target=11,scopes=('lab',),entity_id='synthetic-person',living=living or LivingRuntimeConfig(),model=model,**kwargs),clock=clock)

def event(r,key,*,background=False,**kwargs):
    inp=SubjectInput(source_key='synthetic.living.'+key,kind='WAKE' if background else 'INTERACTION',origin='SELF_WAKE' if background else 'USER',entity_id='synthetic-person',scope='lab',observed_at_us=r.clock.utc_now_us(),**kwargs)
    return RuntimeEvent(event_type='SELF_EVENT' if background else 'USER_EVENT',trigger='SELF_TRIGGER' if background else 'INCOMING_EVENT',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=r.store.identity['identity_id']),),due_at_us=r.clock.utc_now_us(),priority=0 if background else 3)
