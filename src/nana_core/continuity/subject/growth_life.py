"""Rebuildable opportunities from independently checked capability reuse.

No new fact, preference or adopted goal is written here. A current method lesson
and a distinct later verified use may become C attention, not mandatory sharing.
"""
import json
from typing import Literal
from pydantic import Field,model_serializer
from ...contracts import DTO,CoreError
from ...storage import digest
from ..records import RecordService

class GrowthChangeView(DTO):
    basis_private_record_ids:tuple[str,...]=Field(default=(),max_length=1)
    derived: Literal[True] = True
    assessment_id: str
    lesson_id: str
    experience_id: str
    topic: str
    scope: str
    method: str
    source_record_ids: tuple[str,...]
    source_memory_ids: tuple[str,...]
    as_of_us: int
    state_token: str

    @model_serializer(mode='wrap')
    def compatible_origin(self,handler):
        value=handler(self)
        if not self.basis_private_record_ids:value.pop('basis_private_record_ids',None)
        return value

def project(store,assessment_id,*,scope,privacy_classes):
    if store.schema_target<13:return None
    row=store.one('strategy_assessments',assessment_id)
    if not row or row['verdict']!='SUCCESS':return None
    lesson=store.one('lessons',row['lesson_id']);records=RecordService(store)
    if not lesson or lesson['state']!='ACTIVE':return None
    for rid in (row['record_id'],lesson['record_id']):
        head=store.one('continuity_records',rid)
        if not head or head['scope']!=scope or head['privacy_class'] not in privacy_classes or head['lifecycle']!='ACTIVE' or not records.current_support(rid):return None
    review=records.read(row['record_id'])['payload'];rule=records.read(lesson['record_id'])['payload']['rule']
    if rule.get('kind')!='METHOD_SELECTION':return None
    trial=records.read(rule['trial_record_id'])['payload'];case=review['episode']['case']
    training={x['input_digest'] for stage in trial['results'].values() for x in stage['cases']}
    if digest(case['data']) in training or not review['result']['all_passed']:return None
    # The published reuse observation must be independently verified, not a user
    # or model asserting that something worked. The original assessment recomputes.
    source_ids=records.support(row['record_id'])
    verified=[]
    for mid in source_ids:
        m=records.memory.read(mid)
        if m['source_provenance']['source_kind']!='SYSTEM_VERIFICATION' or m['authority']!='DIRECT' or m['epistemic_kind']!='OBSERVATION':continue
        try:body=json.loads(m['text'])
        except ValueError:continue
        if body.get('strategy_episode')==review['episode']:verified.append(mid)
    if not verified:return None
    refs=(row['record_id'],lesson['record_id'])
    basis=()
    work=store.one('jobs',trial.get('work_id')) if trial.get('work_id') else None
    if work and work['work_kind']=='LEARNING':
        head=store.one('continuity_records',work['record_id'])
        if (head and head['scope']==scope and head['privacy_class'] in privacy_classes
                and head['lifecycle']=='ACTIVE' and records.current_support(head['record_id'])):
            body=records.read(head['record_id'])['payload'];origin=body.get('origin_private_thought_ref')
            binding=body.get('context_binding')
            if (body.get('lesson_id')==lesson['lesson_id'] and type(origin) is dict and type(binding) is dict
                    and type(binding.get('entity_id')) is str and type(binding.get('topic')) is str):
                from .opportunities import PrivateIntentRef
                from ..autonomy.private_intent import internal_projection,growth_origin_target
                from .context_fit import depth_boundary
                try:reference=PrivateIntentRef.model_validate_json(json.dumps(origin))
                except ValueError:reference=None
                current=growth_origin_target(store,reference,scope=scope,privacy_classes=privacy_classes,topic=binding['topic']) if reference else None
                selected=internal_projection(store,(current[0],),scope=scope,privacy_classes=privacy_classes,include_associations=False) if current else ()
                if (selected and not depth_boundary(store,binding['entity_id'],scope,binding['topic'],privacy_classes,purpose='COGNITION')[0]):
                    basis=(current[0],)
    # Opportunity identity follows the checked outcome, never its current
    # private projection; revising the thought must not repeat this same wake.
    state_token=digest([refs,lesson['revision']])
    refs=(*refs,*basis)
    mids=tuple(dict.fromkeys(m for r in refs for m in records.support(r)))
    if len(mids)>32:return None
    return GrowthChangeView(basis_private_record_ids=basis,assessment_id=assessment_id,lesson_id=lesson['lesson_id'],experience_id=lesson['experience_id'],topic='growth.'+digest(lesson['task_class'])[:24],scope=scope,method=rule['method'],source_record_ids=refs,source_memory_ids=mids,as_of_us=store.clock.utc_now_us(),state_token=state_token)

def opportunities(store,*,scope,privacy_classes):
    if store.schema_target<13:return ()
    rows=store.db.execute("SELECT a.assessment_id FROM strategy_assessments a JOIN lessons l ON l.lesson_id=a.lesson_id WHERE a.verdict='SUCCESS' AND l.state='ACTIVE' ORDER BY a.created_at_us DESC,a.rowid DESC LIMIT 32").fetchall()
    result=[];lessons=set()
    for row in rows:
        view=project(store,row[0],scope=scope,privacy_classes=privacy_classes)
        if view and view.lesson_id not in lessons:result.append(view);lessons.add(view.lesson_id)
    return tuple(result)

def context_projection(store,subject_event_id,*,scope,entity_id,privacy_classes,selected_record_ids):
    """Only the actual C-selected, independently qualified growth occurrence.

    No history scan and no inferred mood, interest, adopted goal or permission.
    Ordinary expression contexts have no subject frame and never call this.
    """
    if store.schema_target<13:return None
    source=store.one('subject_events',subject_event_id)
    if not source or source['scope']!=scope or source['entity_id']!=entity_id or not source['record_id']:return None
    head=store.one('continuity_records',source['record_id']);records=RecordService(store)
    if not head or head['privacy_class'] not in privacy_classes or not records.current_support(head['record_id']):return None
    event=records.read(head['record_id'])['payload']['input']
    if event['origin']!='SELF_WAKE' or not event.get('growth_assessment_id'):return None
    value=project(store,event['growth_assessment_id'],scope=scope,privacy_classes=privacy_classes)
    if value and set(value.source_record_ids)<=set(selected_record_ids):return value
    return None

def availability(store,entity_id,*,scope,privacy_classes):
    """Use existing recipient observations. Silence is not low social appetite."""
    from ..open_agency.delivery import RecipientState
    records=RecordService(store);now=store.clock.utc_now_us();states=[]
    rows=store.db.execute("SELECT * FROM memories WHERE scope=? AND entity_id=? AND predicate_key LIKE 'recipient.%' AND lifecycle='ACTIVE' AND assessment IN ('CURRENT','UNASSESSED') ORDER BY created_at_us DESC,rowid DESC LIMIT 17",(scope,entity_id)).fetchall()
    if len(rows)>16:return 'UNKNOWN',()
    seen=set();support=[]
    for row in rows:
        if row['privacy_class'] not in privacy_classes:return 'UNKNOWN',()
        try:m=records.memory.read(row['memory_id']);state=RecipientState.model_validate_json(m['text'])
        except (CoreError,ValueError):continue
        if state.entity_id!=entity_id or m['authority']!='DIRECT' or state.resource in seen:continue
        seen.add(state.resource)
        if state.observed_at_us>now or state.expires_at_us<=now:continue
        states.append(state.availability);support.append(row['memory_id'])
    value=next(iter(set(states))) if len(set(states))==1 else 'UNKNOWN'
    return value,tuple(support)
