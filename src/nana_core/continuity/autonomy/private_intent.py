"""Structured selective disclosure in the original C transaction, never raw thought.

Existing INTENTION records own revision/deletion lineage. This service
has no scheduler, model, execution kernel or authority to grant/revoke anything.
"""
import json
from typing import Literal
from pydantic import Field
from ...contracts import DTO,CoreError
from ..records import RecordService
from .disclosure import expectation

Policy=Literal['PUBLIC','PRIVATE_FOR_NOW','PRIVATE_UNTIL_TRIGGER','SURPRISE','MANAGER_AUDIT_ONLY','DISCLOSED','WITHDRAWN']
class PrivateIntent(DTO):
    contract:Literal['PRIVATE_INTENT_V1']='PRIVATE_INTENT_V1'
    intent_id:str
    owner_identity_id:str
    cycle_id:str
    topic:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    category:Literal['CREATIVE_IDEA','PRIVATE_PLAN']='CREATIVE_IDEA'
    status:Literal['CONSIDERED','DISCLOSURE_ELIGIBLE','WITHDRAWN']='CONSIDERED'
    content_summary:str=Field(min_length=1,max_length=512)
    disclosure_policy:Policy
    trigger_at_us:int|None=Field(default=None,ge=0)
    revision:int=Field(default=1,ge=1)
    source_memory_ids:tuple[str,...]
    goal_candidate_id:str|None=None
    risk_class:Literal['NONE','LOW','RELEVANT','HIGH']
    authority_need:Literal['FRESH_REALIZATION_GATES']='FRESH_REALIZATION_GATES'
    external_effect:Literal[False]=False
    budget_required:Literal[True]=True
    third_party:Literal[False]=False
    execution_authority:Literal[False]=False


def candidates(store,scope,privacy_classes):
    marks=','.join('?' for _ in privacy_classes)
    if not marks:return ()
    # Reserved target key uses existing (record_kind,target_id,time) index.
    # Bound headers BEFORE filtering lifecycle/privacy or reading any artifact;
    # old retired history cannot turn a normal C cycle into an unbounded scan.
    rows=store.db.execute("SELECT record_id,scope,privacy_class,lifecycle FROM continuity_records INDEXED BY autonomy_record_target WHERE record_kind='INTENTION' AND target_id='private-intent.v1' ORDER BY created_at_us DESC LIMIT 64").fetchall()
    records=RecordService(store);out=[]
    for row in rows:
        if row['scope']!=scope or row['privacy_class'] not in privacy_classes or row['lifecycle']!='ACTIVE':continue
        if not records.current_support(row[0]):continue
        data=records.read(row[0])['payload']
        if data.get('contract')=='PRIVATE_INTENT_V1':out.append((row[0],PrivateIntent.model_validate_json(json.dumps(data))))
    return tuple(out)


def decision_support(store,scope,privacy_classes,*,topic):
    """Original C's relevant own interests, not recipient disclosure content.

    The original record remains the source of identity/lifecycle/privacy and
    withdrawal. Returning only references cannot turn a thought into a fact or
    mint permission, and adds no model request or private-context plaintext.
    """
    if topic is None:return ()
    return tuple(rid for rid,item in candidates(store,scope,privacy_classes)
        if item.owner_identity_id==store.identity['identity_id'] and item.topic==topic
        and item.status!='WITHDRAWN' and item.disclosure_policy!='WITHDRAWN')


def after_choice(store,tx,event,result,*,privacy_classes):
    """Called only by original SubjectLoop after its independent judgment commit data.

    A wall clock only permits reconsideration in another ordinary C cycle. Even a
    DISCLOSED state is eligibility, never an assertion of delivery or of an effect.
    """
    records=RecordService(store)
    current=candidates(store,event.scope,privacy_classes)
    from ..subject.context_fit import depth_boundary
    for rid,item in current:
        if event.observed_availability=='BUSY' or depth_boundary(store,event.entity_id,event.scope,item.topic,privacy_classes)[0]:continue
        live_facts=expectation(store,scope=event.scope,entity_id=event.entity_id,topic=item.topic,privacy_classes=privacy_classes)
        if any(spec.expectation in {'EXPLICITLY_FORBIDDEN','EXPLICITLY_PRIVATE'} for _,spec in live_facts):continue
        if item.disclosure_policy in {'SURPRISE','PRIVATE_UNTIL_TRIGGER'} and item.trigger_at_us is not None and store.clock.utc_now_us()>=item.trigger_at_us:
            revised=item.model_copy(update={'disclosure_policy':'DISCLOSED','status':'DISCLOSURE_ELIGIBLE','revision':item.revision+1})
            records.create(tx,kind='INTENTION',scope=event.scope,payload=revised.model_dump(mode='json'),records=(rid,),supersedes=rid,target_id='private-intent.v1')
    if (not result.intention_id or not result.record_id or not result.intention.self_generated
        or result.intention.behavior!='CREATE' or not result.evaluation or result.evaluation.normative!='ENDORSED'
        or not any(m.source=='CREATIVE_INTEREST' for m in result.motivations) or len(current)>=32):return
    if any(item.intent_id==result.intention_id for _,item in current):return
    # No model can submit a private-intent DTO; only the recorded C choice qualifies.
    topic=result.intention.slot_key.removeprefix('concern-')
    if any(item.owner_identity_id==store.identity['identity_id'] and item.topic==topic
            and item.status!='WITHDRAWN' and item.disclosure_policy!='WITHDRAWN'
            and item.content_summary==result.intention.purpose[:512] for _,item in current):return
    facts=expectation(store,scope=event.scope,entity_id=event.entity_id,topic=topic,privacy_classes=privacy_classes)
    mode='PRIVATE_FOR_NOW';trigger=None
    for _,spec in facts:
        if spec.expectation=='EXPLICITLY_FORBIDDEN':mode='MANAGER_AUDIT_ONLY';trigger=None;break
        if spec.timing=='DEFER_UNTIL' and spec.reveal_at_us is not None:
            mode='SURPRISE';trigger=spec.reveal_at_us
        elif spec.expectation=='OPEN' and mode=='PRIVATE_FOR_NOW':mode='PUBLIC'
    value=PrivateIntent(intent_id=result.intention_id,owner_identity_id=store.identity['identity_id'],cycle_id=result.cycle_id,topic=topic,
        content_summary=result.intention.purpose[:512],disclosure_policy=mode,trigger_at_us=trigger,
        source_memory_ids=result.intention.source_ids,goal_candidate_id=result.goal_candidate_id,risk_class=event.risk)
    records.create(tx,kind='INTENTION',scope=event.scope,payload=value.model_dump(mode='json'),records=(result.record_id,),memories=tuple(mid for mid,_ in facts),target_id='private-intent.v1')



def metadata(store,scope,privacy_classes):
    # Allowlisted metadata, intentionally no content, raw reasoning or credentials.
    return tuple({'record_id':rid,'intent_id':v.intent_id,'category':v.category,'status':v.status,
        'disclosure_policy':v.disclosure_policy,'revision':v.revision,'risk_class':v.risk_class,
        'authority_need':v.authority_need,'execution_authority':False,'external_effect':False,
        'budget_required':True,'third_party':False,'cycle_id':v.cycle_id,'source_memory_ids':v.source_memory_ids}
        for rid,v in candidates(store,scope,privacy_classes))


def eligible_content(store,intent_id,*,scope,privacy_classes):
    """Explicit recipient eligibility; caller still needs legal delivery admission."""
    for rid,value in candidates(store,scope,privacy_classes):
        if value.intent_id==intent_id:
            if value.disclosure_policy not in {'PUBLIC','DISCLOSED'}:raise CoreError('PRIVATE_INTENT_WITHHELD')
            return {'content_summary':value.content_summary,'source_record_ids':(rid,),'delivery_authority':False,'effect_phase':'PLANNED'}
    raise CoreError('PRIVATE_INTENT_UNAVAILABLE')
