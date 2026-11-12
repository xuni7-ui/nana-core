"""Structured selective disclosure in the original C transaction, never raw thought.

Existing INTENTION records own revision/deletion lineage. This service
has no scheduler, model, execution kernel or authority to grant/revoke anything.
"""
import json
from typing import Literal
from pydantic import Field,model_serializer
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


class PrivateActivity(PrivateIntent):
    """Versioned life of the same private idea, never a task execution receipt.

    Old readers ignore this contract in the existing record family. No schema,
    second history or event/SubjectInput format is introduced.
    """
    contract:Literal['PRIVATE_ACTIVITY_V2']='PRIVATE_ACTIVITY_V2'
    activity_state:Literal['ACTIVE','PAUSED','ABANDONED']='ACTIVE'
    created_at_us:int=Field(ge=0)
    updated_at_us:int=Field(ge=0)
    last_choice_cycle_id:str
    epistemic_status:Literal['OWN_TENDENCY_NOT_WORLD_FACT']='OWN_TENDENCY_NOT_WORLD_FACT'
    execution_state:Literal['NOT_INFERRED_FROM_ACTIVITY_STATE']='NOT_INFERRED_FROM_ACTIVITY_STATE'


class PrivateQuestionProposal(DTO):
    """An own question proposed in existing cognition, never an observation."""
    topic:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    question:str=Field(min_length=1,max_length=512)
    related_private_record_ids:tuple[str,...]=Field(default=(),max_length=8)
    revises_record_id:str|None=Field(default=None,pattern=r'^[A-Za-z0-9._:-]{1,128}$')

    @model_serializer(mode='wrap')
    def compatible_wire(self,handler):
        value=handler(self)
        if self.revises_record_id is None:value.pop('revises_record_id',None)
        return value


class PrivateQuestion(PrivateActivity):
    contract:Literal['PRIVATE_QUESTION_V3']='PRIVATE_QUESTION_V3'
    category:Literal['PRIVATE_QUESTION']='PRIVATE_QUESTION'
    epistemic_status:Literal['OWN_QUESTION_NOT_WORLD_FACT']='OWN_QUESTION_NOT_WORLD_FACT'


def payload_model(data):
    return {'PRIVATE_INTENT_V1':PrivateIntent,'PRIVATE_ACTIVITY_V2':PrivateActivity,
        'PRIVATE_QUESTION_V3':PrivateQuestion}.get(data.get('contract'))


def candidates(store,scope,privacy_classes,*,topic=None,owner_identity_id=None,for_decision=False):
    marks=','.join('?' for _ in privacy_classes)
    if not marks:return ()
    # Scope/privacy/current headers precede the bounded payload window. The
    # original Store installs a rebuildable partial lookup; revisions of one
    # idea must not displace another current idea behind retired headers.
    # A read-only Inspector may inspect a legacy DB before the new owner has
    # installed the lookup. It never creates an index or acquires writer power.
    installed={row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name IN ('private_intent_live_lookup','private_intent_topic_lookup_v1','private_intent_payload_lookup')")}
    if topic is not None and owner_identity_id is not None and {'private_intent_topic_lookup_v1','private_intent_payload_lookup'}<=installed:
        from ..store import PRIVATE_INTENT_JSON_FILTER
        # The small purpose-specific artifact index narrows owner/topic, then
        # the original current header enforces scope/privacy/lifecycle. It is
        # a rebuildable lookup, never a second memory authority.
        sql="SELECT r.record_id,r.scope,r.privacy_class,r.lifecycle FROM artifacts a INDEXED BY private_intent_topic_lookup_v1 JOIN continuity_records r INDEXED BY private_intent_payload_lookup ON r.payload_artifact_id=a.artifact_id WHERE "+PRIVATE_INTENT_JSON_FILTER.replace('payload','a.payload')+" AND json_extract(CAST(a.payload AS TEXT),'$.owner_identity_id')=? AND json_extract(CAST(a.payload AS TEXT),'$.topic')=? AND r.record_kind='INTENTION' AND r.target_id='private-intent.v1' AND r.lifecycle='ACTIVE' AND r.scope=? AND r.privacy_class IN ("+marks+") ORDER BY r.created_at_us DESC LIMIT 64 OFFSET ?"
        args=(owner_identity_id,topic,scope,*privacy_classes)
    else:
        # Legacy/read-only/JSON-less engines retain correctness by paging
        # current permitted headers. They never install a cache on inspection.
        lookup=' INDEXED BY private_intent_live_lookup' if 'private_intent_live_lookup' in installed else ''
        sql="SELECT record_id,scope,privacy_class,lifecycle FROM continuity_records"+lookup+" WHERE record_kind='INTENTION' AND target_id='private-intent.v1' AND lifecycle='ACTIVE' AND scope=? AND privacy_class IN ("+marks+") ORDER BY created_at_us DESC LIMIT 64 OFFSET ?"
        args=(scope,*privacy_classes)
    records=RecordService(store);out=[]
    offset=0
    while len(out)<64:
        rows=store.db.execute(sql,(*args,offset)).fetchall()
        for row in rows:
            if row['scope']!=scope or row['privacy_class'] not in privacy_classes or row['lifecycle']!='ACTIVE':continue
            if not records.current_support(row[0]):continue
            data=records.read(row[0])['payload'];model=payload_model(data)
            if model is None:continue
            value=model.model_validate_json(json.dumps(data))
            if topic is not None and value.topic!=topic:continue
            if owner_identity_id is not None and value.owner_identity_id!=owner_identity_id:continue
            if for_decision and (value.status=='WITHDRAWN' or value.disclosure_policy=='WITHDRAWN'
                    or getattr(value,'activity_state','ACTIVE')=='ABANDONED'):continue
            out.append((row[0],value))
            if len(out)==64:break
        if len(rows)<64:break
        offset+=64
    return tuple(out)


def decision_support(store,scope,privacy_classes,*,topic):
    """Original C's relevant own interests, not recipient disclosure content.

    The original record remains the source of identity/lifecycle/privacy and
    withdrawal. Returning only references cannot turn a thought into a fact or
    mint permission, and adds no model request or private-context plaintext.
    """
    if topic is None:return ()
    return tuple(rid for rid,item in candidates(store,scope,privacy_classes,topic=topic,owner_identity_id=store.identity['identity_id'],for_decision=True)
        if item.owner_identity_id==store.identity['identity_id'] and item.topic==topic
        and item.status!='WITHDRAWN' and item.disclosure_policy!='WITHDRAWN'
        and getattr(item,'activity_state','ACTIVE')!='ABANDONED')


def internal_projection(store,record_ids,*,scope,privacy_classes):
    """Only C-selected own current thoughts, for its existing deliberation.

    This is not recipient disclosure. The caller's original context assembler
    budgets each item and checks the sources again around inference.
    """
    records=RecordService(store);out=[]
    for rid in dict.fromkeys(record_ids):
        head=store.one('continuity_records',rid)
        if (not head or head['record_kind']!='INTENTION' or head['target_id']!='private-intent.v1'
                or head['scope']!=scope or head['privacy_class'] not in privacy_classes or head['lifecycle']!='ACTIVE'
                or not records.current_support(rid)):continue
        data=records.read(rid)['payload']
        model=payload_model(data)
        if model is None:continue
        item=model.model_validate_json(json.dumps(data))
        if (item.owner_identity_id!=store.identity['identity_id'] or item.status=='WITHDRAWN'
                or item.disclosure_policy=='WITHDRAWN' or getattr(item,'activity_state','ACTIVE')=='ABANDONED'):continue
        out.append({'record_id':rid,'intent_id':item.intent_id,'revision':item.revision,'topic':item.topic,
            'category':item.category,'content_summary':item.content_summary,
            'activity_state':getattr(item,'activity_state','ACTIVE'),
            'created_at_us':getattr(item,'created_at_us',head['created_at_us']),
            'updated_at_us':getattr(item,'updated_at_us',head['created_at_us']),
            'epistemic_status':getattr(item,'epistemic_status','OWN_TENDENCY_NOT_WORLD_FACT'),'disclosure_policy':item.disclosure_policy,
            'recipient_disclosure':False,'execution_authority':False})
    return tuple(out)


def review_target(store,reference,*,scope,privacy_classes,topic):
    """Validate the exact current version before the original C considers it."""
    head=store.one('continuity_records',reference.record_id)
    if (not head or head['record_kind']!='INTENTION' or head['target_id']!='private-intent.v1'
            or head['scope']!=scope or head['privacy_class'] not in privacy_classes or head['lifecycle']!='ACTIVE'):
        raise CoreError('PRIVATE_INTENT_REVIEW_UNAVAILABLE')
    records=RecordService(store)
    if not records.current_support(reference.record_id):raise CoreError('PRIVATE_INTENT_REVIEW_UNAVAILABLE')
    data=records.read(reference.record_id)['payload']
    model=payload_model(data)
    if model is None:raise CoreError('PRIVATE_INTENT_REVIEW_UNAVAILABLE')
    item=model.model_validate_json(json.dumps(data))
    if (item.owner_identity_id!=store.identity['identity_id'] or item.intent_id!=reference.intent_id
            or item.revision!=reference.revision or item.topic!=topic or item.status=='WITHDRAWN'
            or item.disclosure_policy=='WITHDRAWN'):
        raise CoreError('PRIVATE_INTENT_REVIEW_STALE_OR_UNBOUND')
    return reference.record_id,item


def consider_question(event,situation,judgment,intention,proposal):
    """Original C may consider an own new question without an external event.

    The model does not adopt a goal, replace a specific review or obtain an
    execution binding. Rest, disagreement, sourced norms and current boundaries
    retain their original choice; no source assertion is inferred from a question.
    """
    if (proposal is None or event.origin!='SELF_WAKE' or event.retention=='DO_NOT_REMEMBER'
            or judgment.stance not in {'WATCH','THINK_MORE','REMEMBER','REFLECT'}
            or (judgment.lesson_ids and intention.kind not in {'NO_ACTION','REFLECTION'})
            or intention.kind in {'SOCIAL_INTERACTION','DISAGREE','ACTION_PROPOSAL'}
            or intention.behavior in {'REST','WITHDRAW','STAY_SILENT','IGNORE','DO_NOTHING','DEFER'}
            or any((event.realization_target,event.goal_step,event.goal_review,event.memory_review_id,
                event.governance_review_id,event.disposition_reflection_id,event.growth_assessment_id))
            or 'REFLECT' in situation.prohibited_behaviors
            or (situation.context_fit and not situation.context_fit.allow_deepening)
            or (situation.cue and (situation.cue.resource_ref or situation.cue.program_id))):
        return None
    # A focus label is not an authorization boundary: an own question may open
    # a new direction. Owner/scope/privacy/current-source checks remain separate.
    return proposal


def after_choice(store,tx,event,result,*,privacy_classes,selected_topic=None,private_intent_ref=None,private_question=None):
    """Called only by original SubjectLoop after its independent judgment commit data.

    A wall clock only permits reconsideration in another ordinary C cycle. Even a
    DISCLOSED state is eligibility, never an assertion of delivery or of an effect.
    """
    records=RecordService(store)
    current=candidates(store,event.scope,privacy_classes)
    for topic in dict.fromkeys(t for t in (selected_topic,private_question.topic if private_question else None) if t is not None):
        relevant=candidates(store,event.scope,privacy_classes,topic=topic,owner_identity_id=store.identity['identity_id'],for_decision=True)
        current=tuple({rid:(rid,item) for rid,item in (*current,*relevant)}.values())
    from ..subject.context_fit import depth_boundary
    owned=[]
    if private_intent_ref is not None and event.origin=='SELF_WAKE' and event.retention!='DO_NOT_REMEMBER':
        owned=[review_target(store,private_intent_ref,scope=event.scope,privacy_classes=privacy_classes,topic=selected_topic)]
        if not any(rid==owned[0][0] for rid,_ in current):current=(*current,owned[0])
    desired={'CREATE':'ACTIVE','REST':'PAUSED','WITHDRAW':'ABANDONED'}.get(result.intention.behavior)
    review=bool(len(owned)==1 and event.retention!='DO_NOT_REMEMBER'
        and result.record_id and result.intention.self_generated and desired
        and result.evaluation and (result.evaluation.normative=='ENDORSED'
            or (desired in {'PAUSED','ABANDONED'} and result.evaluation.normative=='UNDECIDED'
                and result.evaluation.considered)))
    for rid,item in current:
        if item.owner_identity_id!=store.identity['identity_id']:continue
        changes={}
        if (item.disclosure_policy in {'SURPRISE','PRIVATE_UNTIL_TRIGGER'} and item.trigger_at_us is not None
                and store.clock.utc_now_us()>=item.trigger_at_us and event.observed_availability!='BUSY'
                and getattr(item,'activity_state','ACTIVE')!='ABANDONED'
                and not depth_boundary(store,event.entity_id,event.scope,item.topic,privacy_classes)[0]):
            live_facts=expectation(store,scope=event.scope,entity_id=event.entity_id,topic=item.topic,privacy_classes=privacy_classes)
            if not any(spec.expectation in {'EXPLICITLY_FORBIDDEN','EXPLICITLY_PRIVATE'} for _,spec in live_facts):
                changes.update(disclosure_policy='DISCLOSED',status='DISCLOSURE_ELIGIBLE')
        if review and rid==owned[0][0]:
            if getattr(item,'activity_state','ACTIVE')!=desired:
                changes['activity_state']=desired
            if desired=='ACTIVE' and not isinstance(item,PrivateQuestion) and item.content_summary!=result.intention.purpose[:512]:
                changes['content_summary']=result.intention.purpose[:512]
        if changes:
            data={**item.model_dump(mode='json'),**changes,'revision':item.revision+1}
            if 'activity_state' in changes or isinstance(item,PrivateActivity):
                data.update(contract='PRIVATE_QUESTION_V3' if isinstance(item,PrivateQuestion) else 'PRIVATE_ACTIVITY_V2',
                    activity_state=changes.get('activity_state',getattr(item,'activity_state','ACTIVE')),
                    created_at_us=getattr(item,'created_at_us',store.one('continuity_records',rid)['created_at_us']),
                    updated_at_us=store.clock.utc_now_us(),last_choice_cycle_id=result.cycle_id)
                revised=(PrivateQuestion if isinstance(item,PrivateQuestion) else PrivateActivity).model_validate_json(json.dumps(data))
            else:revised=PrivateIntent.model_validate_json(json.dumps(data))
            parents=(rid,result.record_id) if 'activity_state' in changes or 'content_summary' in changes else (rid,)
            records.create(tx,kind='INTENTION',scope=event.scope,payload=revised.model_dump(mode='json'),records=parents,
                supersedes=rid,target_id='private-intent.v1')
    if (private_question is not None and result.intention_id and result.record_id
            and result.intention.behavior=='REFLECT' and result.evaluation and result.evaluation.normative=='ENDORSED'):
        if private_question.revises_record_id is not None:
            old=next(((rid,item) for rid,item in current if rid==private_question.revises_record_id),None)
            if (old is None or not isinstance(old[1],PrivateQuestion) or old[1].owner_identity_id!=store.identity['identity_id']
                    or old[1].status=='WITHDRAWN' or old[1].disclosure_policy=='WITHDRAWN'):raise CoreError('PRIVATE_QUESTION_REVISION_UNAVAILABLE')
            rid,item=old
            reframed=item.content_summary!=private_question.question or item.topic!=private_question.topic
            if reframed or item.activity_state!='ACTIVE':
                changes={'content_summary':private_question.question,'topic':private_question.topic,'activity_state':'ACTIVE',
                    'revision':item.revision+1,'updated_at_us':store.clock.utc_now_us(),'last_choice_cycle_id':result.cycle_id,
                    'source_memory_ids':result.intention.source_ids}
                if reframed:
                    # Old eligibility/timing never discloses new private contents.
                    changes.update(disclosure_policy='MANAGER_AUDIT_ONLY' if item.disclosure_policy=='MANAGER_AUDIT_ONLY' else 'PRIVATE_FOR_NOW',
                        status='CONSIDERED',trigger_at_us=None)
                revised=item.model_copy(update=changes)
                records.create(tx,kind='INTENTION',scope=event.scope,payload=revised.model_dump(mode='json'),
                    records=tuple(dict.fromkeys((rid,result.record_id,*private_question.related_private_record_ids))),
                    supersedes=rid,target_id='private-intent.v1')
            return
        if not any(item.owner_identity_id==store.identity['identity_id'] and item.topic==private_question.topic
                and item.category=='PRIVATE_QUESTION' and item.content_summary==private_question.question
                and getattr(item,'activity_state','ACTIVE')!='ABANDONED' for _,item in current):
            now=store.clock.utc_now_us()
            value=PrivateQuestion(intent_id=result.intention_id,owner_identity_id=store.identity['identity_id'],cycle_id=result.cycle_id,
                topic=private_question.topic,content_summary=private_question.question,disclosure_policy='PRIVATE_FOR_NOW',
                source_memory_ids=result.intention.source_ids,risk_class=event.risk,created_at_us=now,updated_at_us=now,last_choice_cycle_id=result.cycle_id)
            records.create(tx,kind='INTENTION',scope=event.scope,payload=value.model_dump(mode='json'),
                records=tuple(dict.fromkeys((result.record_id,*private_question.related_private_record_ids))),target_id='private-intent.v1')
        return
    if review and desired=='ACTIVE':return  # Revise the existing idea, never duplicate it on resumption.
    if (not result.intention_id or not result.record_id or not result.intention.self_generated
        or result.intention.behavior!='CREATE' or not result.evaluation or result.evaluation.normative!='ENDORSED'
        or not any(m.source=='CREATIVE_INTEREST' for m in result.motivations)):return
    if any(item.intent_id==result.intention_id for _,item in current):return
    # No model can submit a private-intent DTO; only the recorded C choice qualifies.
    topic=result.intention.slot_key.removeprefix('concern-')
    if any(item.owner_identity_id==store.identity['identity_id'] and item.topic==topic
            and item.status!='WITHDRAWN' and item.disclosure_policy!='WITHDRAWN'
            and getattr(item,'activity_state','ACTIVE')!='ABANDONED'
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
        'activity_state':getattr(v,'activity_state','ACTIVE'),
        'disclosure_policy':v.disclosure_policy,'revision':v.revision,'risk_class':v.risk_class,
        'authority_need':v.authority_need,'execution_authority':False,'external_effect':False,
        'budget_required':True,'third_party':False,'cycle_id':v.cycle_id,'source_memory_ids':v.source_memory_ids}
        for rid,v in candidates(store,scope,privacy_classes))


def eligible_content(store,intent_id,*,scope,privacy_classes):
    """Explicit recipient eligibility; caller still needs legal delivery admission."""
    for rid,value in candidates(store,scope,privacy_classes):
        if value.intent_id==intent_id:
            if value.disclosure_policy not in {'PUBLIC','DISCLOSED'} or getattr(value,'activity_state','ACTIVE')=='ABANDONED':raise CoreError('PRIVATE_INTENT_WITHHELD')
            return {'content_summary':value.content_summary,'source_record_ids':(rid,),'delivery_authority':False,'effect_phase':'PLANNED'}
    raise CoreError('PRIVATE_INTENT_UNAVAILABLE')
