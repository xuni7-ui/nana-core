from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.open_agency.contracts import Objective,Operator
from nana_core.continuity.open_agency.service import OpenGoalPolicy
from nana_core.continuity.autonomy.fixture_effects import OfflineEffectPort
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.contracts import GrantSpec
from nana_core.storage import digest
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.contracts import LivingRuntimeConfig,RuntimeEvent,Cause,SECOND,HOUR
from nana_core.presence.authority import VirtualClock

def fresh(path,clock=None,*,schema_target=12):
    clock=clock or VirtualClock()
    with ContinuityStore(path,clock,schema_target=schema_target) as s:
        IdentityService(s,OperatorAuthority());MemoryService(s).entity('synthetic-person','PERSON')
    return NanaRuntime(path,RuntimeConfig(schema_target=schema_target,living=LivingRuntimeConfig(),scopes=('lab',),entity_id='synthetic-person',idle_recall_us=HOUR),clock=clock)

def capture(r,key,text,*,predicate=None,entity='synthetic-person',privacy='PERSONAL',derived=()):
    m=MemoryService(r.store);eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.open-fixture',source_reference=key,source_kind='DIRECT_OBSERVATION'),text=text,privacy_class=privacy,observed_time_us=r.clock.utc_now_us()))
    return m.add(MemoryCandidate(entity_id=entity,scope='lab',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,predicate_key=predicate,derived_from=derived))

def cue(r,obj):
    c=ConcernCue(cue_kind='OPEN_LOOP',motivation_source=obj.motivation_source,topic_key=obj.objective_id.replace('.','-'),program_id=obj.objective_id)
    return capture(r,obj.objective_id,c.model_dump_json(),predicate='concern.'+obj.objective_id)

def send(r,key,mids=(),**extra):
    inp=SubjectInput(source_key='synthetic.open.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='synthetic-person',scope='lab',source_memory_ids=mids,observed_at_us=r.clock.utc_now_us(),**extra)
    return r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=r.identity_id),),due_at_us=r.clock.utc_now_us()))

def objective(key='fixture.total',method='NUMERIC_SUM',expected=3.5,**kwargs):
    return Objective(objective_id=key,scope='lab',motivation_source=kwargs.pop('motivation_source','PROJECT_COMPLETION'),task_domain=kwargs.pop('task_domain','numbers'),desired=('published',),operators=(
        Operator(operator_id='inspect',capability='world.observe',resource='synthetic://input/'+key,produces=('observed',),args={}),
        Operator(operator_id='compute',capability='world.compute',resource='synthetic://compute/'+key,requires=('observed',),produces=('computed',),args={'method':method,'input_from':'inspect'},strategy_selectable=True,expected_digest=digest(expected)),
        Operator(operator_id='publish',capability='world.publish',resource='synthetic://output/'+key,requires=('computed',),produces=('published',),args={'input_from':'compute'},expected_digest=digest(expected))),**kwargs)

def configure(r,world,objectives,*,grant=True):
    p=OfflineEffectPort(r.identity_id,world);GovernanceController(r.store,r.authority).initialize(r.authority)
    r.work.configure_open_agency(OpenGoalPolicy(objectives),p)
    if grant:
        k=r.work.agency.realization.kernel;now=r.clock.utc_now_us()
        k.grant(GrantSpec(capabilities=tuple(k.capabilities)+(k.verify_capability,),resources=tuple({op.resource for o in objectives for op in o.operators}),not_before_us=now,expires_at_us=now+10*HOUR),r.authority)
        k.set_budgets({'write_attempts':100,'external_requests':500,'cost_micro_units':500},r.authority)
    return p

def advance(r,steps=16):
    for _ in range(steps):r.clock.source.advance(SECOND);r.step()
