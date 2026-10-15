"""Explicit synthetic input builders; never a decision policy or real importer."""
from ..storage import canonical
from ..continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..continuity.memory import MemoryService
from ..continuity.subject import SubjectInput
from ..continuity.subject.opportunities import ConcernCue
from .contracts import RuntimeEvent,Cause,HOUR


def memory(runtime,key,text,*,predicate=None,memory_type=MemoryType.EPISODIC,source_kind='DIRECT_OBSERVATION',derived_from=()):
    service=MemoryService(runtime.store)
    now=runtime.clock.utc_now_us()
    eid=service.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.runtime-fixture',source_reference=key,source_kind=source_kind),
        text=text,privacy_class='PERSONAL',event_time_us=now,observed_time_us=now))
    mid=service.add(MemoryCandidate(entity_id=runtime.config.entity_id,scope=runtime.config.scopes[0],memory_type=memory_type,
        epistemic_kind='INFERENCE' if source_kind=='MODEL_DERIVATION' else 'STATEMENT' if source_kind=='USER_STATEMENT' else 'OBSERVATION',source_evidence_id=eid,text=text,
        confidence=.8,predicate_key=predicate,derived_from=derived_from))
    runtime.refresh_attention()
    return mid


def concern(runtime,key,cue:ConcernCue,*,derived_from=()):
    prefix='concern.constraint.' if cue.cue_kind=='CONSTRAINT' else 'concern.open.'
    return memory(runtime,key,cue.model_dump_json(),predicate=prefix+key,memory_type=MemoryType.RELATIONAL if cue.motivation_source=='RELATIONSHIP' else MemoryType.SEMANTIC,
        source_kind='MODEL_DERIVATION' if derived_from else 'USER_STATEMENT',derived_from=derived_from)


def interaction(runtime,key,*,text='A fictional interaction',kind='SHARED_HISTORY'):
    now=runtime.clock.utc_now_us()
    inp=SubjectInput(source_key='synthetic.runtime-history.'+key,kind='INTERACTION',origin='USER',entity_id=runtime.config.entity_id,
        scope=runtime.config.scopes[0],text=text,relationship_kind=kind,significance='RELEVANT',observed_at_us=now,occurred_at_us=now)
    event=RuntimeEvent(event_type='RELATIONSHIP_EVENT',trigger='RELATIONSHIP_TRIGGER',input=inp,
        causes=(Cause(kind='CANONICAL_SELF',reference_id=runtime.store.identity['identity_id']),),due_at_us=now)
    runtime.submit(event)
    return runtime.drain()


def familiar_relationship(runtime):
    for i,kind in enumerate(('SHARED_HISTORY','SHARED_PROJECT','TRUST','SHARED_JOKE')):
        interaction(runtime,'relationship-'+str(i),kind=kind)


def advance(runtime,clock,duration_us,*,step_us=HOUR):
    results=[]
    remaining=duration_us
    while remaining:
        delta=min(step_us,remaining);clock.advance(delta)
        results.extend(runtime.drain());remaining-=delta
    return results
