"""Fictional instance data. No expected decision is passed into Core."""
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import HOUR
from nana_core.continuity.subject import SubjectInput,PreferenceSignal
from nana_core.continuity.relational.bootstrap import SubjectBootstrapService,SubjectBootstrapAuthority
from nana_core.continuity.relational.contracts import RelationalAnchorSpec,SubjectPersonalitySeed


def fresh(path,*,clock=None):
 clock=clock or VirtualClock()
 with ContinuityStore(path,clock,schema_target=10) as s:
  IdentityService(s,OperatorAuthority())
  for entity in ('anchor-person','friend-person','stranger-person'):MemoryService(s).entity(entity,'PERSON')
 return NanaRuntime(path,RuntimeConfig(schema_target=10,scopes=('lab',),entity_id='anchor-person',lease_us=3*HOUR,heartbeat_us=HOUR),clock=clock)


def event(r,key,**fields):
 data=dict(source_key='synthetic.relational.'+key,kind='INTERACTION',origin='USER',entity_id='anchor-person',scope='lab',text='A fictional direct source',significance='RELEVANT',observed_at_us=r.clock.utc_now_us(),occurred_at_us=r.clock.utc_now_us())
 data.update(fields);return SubjectInput(**data)


def bootstrap(r,*,anchor=True,role='sibling-like',**seed):
 authority=SubjectBootstrapAuthority();service=SubjectBootstrapService(r.store,authority)
 if anchor:service.install(RelationalAnchorSpec(identity_id=r.store.identity['identity_id'],anchor_id='primary-bond',entity_id='anchor-person',role_label=role,scope='lab',revision=1,effective_from_us=r.clock.utc_now_us()),authority)
 service.install(SubjectPersonalitySeed(identity_id=r.store.identity['identity_id'],scope='lab',revision=1,**seed),authority)
 return service,authority


def signal(r,key,topic='social_exploration',kind='PREFERENCE',direction='SUPPORT'):
 return r.subject.run(event(r,key,kind='OUTCOME',origin='ENVIRONMENT',preference_signal=PreferenceSignal(kind=kind,topic=topic,direction=direction,interpretation='Independent external observation of a fictional outcome')))
