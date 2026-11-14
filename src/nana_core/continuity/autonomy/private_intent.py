"""Structured selective disclosure in the original C transaction, never raw thought.

Existing INTENTION records own revision/deletion lineage. This service
has no scheduler, model, execution kernel or authority to grant/revoke anything.
"""
import json
from typing import Literal
from pydantic import Field,model_serializer,model_validator
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


class PrivateThoughtEdit(DTO):
    """One bounded own edit in existing cognition, never an observation."""
    model_config={**DTO.model_config, "hide_input_in_errors":True}
    topic:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    related_private_record_ids:tuple[str,...]=Field(default=(),max_length=8)
    clear_related_private_records:bool=False
    revises_record_id:str|None=Field(default=None,pattern=r'^[A-Za-z0-9._:-]{1,128}$')

    @model_validator(mode='after')
    def unambiguous_association_choice(self):
        if self.clear_related_private_records and (self.revises_record_id is None or self.related_private_record_ids):
            raise ValueError('clearing associations requires one current revision and no replacement links')
        return self

    @model_serializer(mode='wrap')
    def compatible_wire(self,handler):
        value=handler(self)
        if self.revises_record_id is None:value.pop('revises_record_id',None)
        if not self.clear_related_private_records:value.pop('clear_related_private_records',None)
        return value


class PrivateQuestionProposal(PrivateThoughtEdit):
    question:str=Field(min_length=1,max_length=512)


class PrivatePlanProposal(PrivateThoughtEdit):
    plan:str=Field(min_length=1,max_length=512)


class PrivateTendencyProposal(PrivateThoughtEdit):
    tendency:str=Field(min_length=1,max_length=512)


class PrivateQuestion(PrivateActivity):
    contract:Literal['PRIVATE_QUESTION_V3']='PRIVATE_QUESTION_V3'
    category:Literal['PRIVATE_QUESTION']='PRIVATE_QUESTION'
    epistemic_status:Literal['OWN_QUESTION_NOT_WORLD_FACT']='OWN_QUESTION_NOT_WORLD_FACT'


class PrivateTendency(PrivateActivity):
    """A retained own orientation, not necessarily a question, plan or emotion."""
    contract:Literal['PRIVATE_TENDENCY_V4']='PRIVATE_TENDENCY_V4'
    category:Literal['PRIVATE_TENDENCY']='PRIVATE_TENDENCY'


def payload_model(data):
    return {'PRIVATE_INTENT_V1':PrivateIntent,'PRIVATE_ACTIVITY_V2':PrivateActivity,
        'PRIVATE_QUESTION_V3':PrivateQuestion,'PRIVATE_TENDENCY_V4':PrivateTendency}.get(data.get('contract'))


def candidates(store,scope,privacy_classes,*,topic=None,owner_identity_id=None,for_decision=False,for_continuation=False,continuation_entity_id=None):
    marks=','.join('?' for _ in privacy_classes)
    if not marks:return ()
    # Scope/privacy/current headers precede the bounded payload window. The
    # original Store installs a rebuildable partial lookup; revisions of one
    # idea must not displace another current idea behind retired headers.
    # A read-only Inspector may inspect a legacy DB before the new owner has
    # installed the lookup. It never creates an index or acquires writer power.
    from ..store import REBUILDABLE_LOOKUP_INDEXES
    index_rows=store.db.execute("SELECT name,sql FROM sqlite_master WHERE type='index' AND name IN ('private_intent_live_lookup','private_intent_topic_lookup_v1','private_intent_payload_lookup','private_intent_tendency_topic_v4')")
    normalize=lambda sql:' '.join((sql or '').replace(' IF NOT EXISTS','').split())
    installed={name for name,sql in index_rows if normalize(sql)==normalize(REBUILDABLE_LOOKUP_INDEXES[name])}
    indexed=topic is not None and owner_identity_id is not None and {'private_intent_topic_lookup_v1','private_intent_payload_lookup','private_intent_tendency_topic_v4'}<=installed
    if indexed:
        from ..store import PRIVATE_INTENT_JSON_FILTER,PRIVATE_TENDENCY_JSON_FILTER
        # The small purpose-specific artifact index narrows owner/topic, then
        # the original current header enforces scope/privacy/lifecycle. It is
        # a rebuildable lookup, never a second memory authority.
        queries=[]
        for index,predicate in (('private_intent_topic_lookup_v1',PRIVATE_INTENT_JSON_FILTER),('private_intent_tendency_topic_v4',PRIVATE_TENDENCY_JSON_FILTER)):
            query="SELECT r.record_id,r.scope,r.privacy_class,r.lifecycle,r.created_at_us,r.rowid AS ordering_row FROM artifacts a INDEXED BY "+index+" JOIN continuity_records r INDEXED BY private_intent_payload_lookup ON r.payload_artifact_id=a.artifact_id WHERE "+predicate.replace('payload','a.payload')+" AND json_extract(CAST(a.payload AS TEXT),'$.owner_identity_id')=? AND json_extract(CAST(a.payload AS TEXT),'$.topic')=? AND r.record_kind='INTENTION' AND r.target_id='private-intent.v1' AND r.lifecycle='ACTIVE' AND r.scope=? AND r.privacy_class IN ("+marks+")"
            if for_continuation:query+=" AND NOT EXISTS (SELECT 1 FROM runtime_schedules s WHERE s.dedupe_key='private-thought.'||r.record_id)"
            queries.append(query)
        # Disjoint format indexes: do not duplicate legacy entries or change
        # the partial predicate an older installed reader explicitly selects.
        sql=' UNION ALL '.join(queries)+' ORDER BY created_at_us DESC,ordering_row DESC LIMIT 64 OFFSET ?'
        args=(owner_identity_id,topic,scope,*privacy_classes)*2
    else:
        # Legacy/read-only/JSON-less engines retain correctness by paging
        # current permitted headers. They never install a cache on inspection.
        lookup=' INDEXED BY private_intent_live_lookup' if 'private_intent_live_lookup' in installed else ''
        sql="SELECT record_id,scope,privacy_class,lifecycle FROM continuity_records"+lookup+" WHERE record_kind='INTENTION' AND target_id='private-intent.v1' AND lifecycle='ACTIVE' AND scope=? AND privacy_class IN ("+marks+") ORDER BY created_at_us DESC LIMIT 64 OFFSET ?"
        args=(scope,*privacy_classes)
    if for_continuation and not indexed:
        alias='r' if 'FROM artifacts a ' in sql else 'continuity_records'
        sql=sql.replace(' ORDER BY '," AND NOT EXISTS (SELECT 1 FROM runtime_schedules s WHERE s.dedupe_key='private-thought.'||"+alias+".record_id) ORDER BY ",1)
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
            if for_continuation:
                formed=store.one('subject_intentions',value.intent_id)
                if (not isinstance(value,PrivateActivity) or value.activity_state!='ACTIVE'
                        or not formed or formed['kind']!='REFLECTION' or formed['state']!='COMPLETED'):continue
                if continuation_entity_id is not None:
                    from ..subject.context_fit import depth_boundary
                    # This C/data permission already governs actual cognition.
                    # Filter before the opportunity cap, without changing the
                    # retained wish. Delivery-only boundaries leave cognition eligible.
                    if depth_boundary(store,continuation_entity_id,scope,value.topic,privacy_classes,purpose='COGNITION')[0]:continue
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


def internal_projection(store,record_ids,*,scope,privacy_classes,include_associations=True):
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
    if include_associations:
        selected=tuple(out);by_id={item['record_id']:item for item in out}
        for item in selected:
            links=_association_record_ids(store,item['record_id'],owner_intent_id=item['intent_id'],scope=scope,privacy_classes=privacy_classes)
            if not links:continue
            item['related_private_record_ids']=links
            item['association_semantics']='OWN_ASSOCIATION_NOT_WORLD_CAUSATION_OR_PRIORITY'
            # One direct association step from a thought already selected by C.
            # Each extra block still competes in the complete context budget.
            for related in internal_projection(store,links,scope=scope,privacy_classes=privacy_classes,include_associations=False):
                if related['record_id'] in by_id:continue
                related['selection_basis']='DIRECT_ASSOCIATION_OF_C_SELECTED_THOUGHT'
                by_id[related['record_id']]=related;out.append(related)
    return tuple(out)


def deliberated_lesson_refs(store,thoughts,*,scope,privacy_classes):
    """Methods explicitly considered in these current thoughts' latest C choice.

    No topic inference, revision-chain search or implicit authority from ancestry.
    Original G still decides whether each referenced method remains qualified.
    """
    from ..cognition import CognitiveProposal
    records=RecordService(store);selected=[]
    for thought in thoughts:
        head=store.one('continuity_records',thought['record_id'])
        if (not head or head['record_kind']!='INTENTION' or head['target_id']!='private-intent.v1'
                or head['scope']!=scope or head['privacy_class'] not in privacy_classes
                or head['lifecycle']!='ACTIVE' or not records.current_support(head['record_id'])):continue
        data=records.read(head['record_id'])['payload'];model=payload_model(data)
        if model is None:continue
        item=model.model_validate_json(json.dumps(data))
        if (item.owner_identity_id!=store.identity['identity_id'] or item.status=='WITHDRAWN'
                or item.disclosure_policy=='WITHDRAWN' or getattr(item,'activity_state','ACTIVE')=='ABANDONED'):continue
        cycle=store.one('subject_cycles',getattr(item,'last_choice_cycle_id',item.cycle_id))
        parent=store.one('continuity_records',cycle['record_id']) if cycle and cycle['record_id'] else None
        if (not parent or parent['record_kind']!='SUBJECT_CYCLE' or parent['scope']!=scope or parent['privacy_class'] not in privacy_classes
                or parent['lifecycle']!='ACTIVE' or not records.current_support(parent['record_id'])):continue
        choice=records.read(parent['record_id'])['payload'];trace=choice.get('deliberation')
        if not trace or not choice['intention']['self_generated']:continue
        proposal=CognitiveProposal.model_validate_json(trace['raw_proposal_json'])
        if proposal.identity_id!=store.identity['identity_id']:continue
        selected.extend(proposal.lesson_refs)
    return tuple(dict.fromkeys(selected))


def _association_record_ids(store,record_id,*,owner_intent_id,scope,privacy_classes):
    # These are the existing explicit private support edges, not a similarity
    # graph, a full history walk, or the previous revision of this same idea.
    ids=tuple(row[0] for row in store.db.execute("SELECT d.parent_id FROM record_dependencies d JOIN continuity_records r ON r.record_id=d.parent_id WHERE d.record_id=? AND d.parent_kind='RECORD' AND d.relation_kind='SUPPORT' AND r.record_kind='INTENTION' AND r.target_id='private-intent.v1' AND r.lifecycle='ACTIVE' ORDER BY d.parent_id",(record_id,)))
    return tuple(item['record_id'] for item in internal_projection(store,ids,scope=scope,privacy_classes=privacy_classes,include_associations=False)
        if item['intent_id']!=owner_intent_id)


def review_target(store,reference,*,scope,privacy_classes,topic=None):
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
            or item.revision!=reference.revision or (topic is not None and item.topic!=topic) or item.status=='WITHDRAWN'
            or item.disclosure_policy=='WITHDRAWN'):
        raise CoreError('PRIVATE_INTENT_REVIEW_STALE_OR_UNBOUND')
    return reference.record_id,item


def continuation_target(store,reference,*,scope,privacy_classes):
    rid,item=review_target(store,reference,scope=scope,privacy_classes=privacy_classes)
    if not isinstance(item,PrivateActivity) or item.activity_state!='ACTIVE':raise CoreError('PRIVATE_CONTINUATION_INACTIVE')
    formed=store.one('subject_intentions',item.intent_id)
    if not formed or formed['kind']!='REFLECTION' or formed['state']!='COMPLETED':raise CoreError('PRIVATE_CONTINUATION_NOT_FORMED')
    return rid,item


def feedback_continuation(store,experience_id,*,scope,entity_id,privacy_classes,reference=None):
    """One exact method opinion may inform an own tendency, including its birth.

    Read only: the existing Experience remains the queue cause. This is an
    opportunity to reconsider, never a verdict about emotion or a learned trait.
    """
    if store.schema_target<13:return None
    row=store.one('experiences',experience_id);records=RecordService(store)
    if not row or row['task_class']!='interaction.expression':return None
    head=store.one('continuity_records',row['record_id'])
    if not head or head['scope']!=scope or head['privacy_class'] not in privacy_classes or head['lifecycle']!='ACTIVE' or not records.current_support(head['record_id']):return None
    verification=store.one('memories',row['verification_memory_id'])
    if not verification or verification['scope']!=scope or verification['privacy_class'] not in privacy_classes:return None
    from ..lived_language import ExpressionFeedbackCheck,communication_feedback
    try:check=ExpressionFeedbackCheck.model_validate_json(records.memory.read(row['verification_memory_id'])['text'])
    except ValueError:return None
    if check.result_memory_id!=row['result_memory_id']:return None
    review=store.one('continuity_records',check.sample_record_id)
    if not review or review['scope']!=scope or review['privacy_class'] not in privacy_classes or review['lifecycle']!='ACTIVE' or not records.current_support(review['record_id']):return None
    data=records.read(review['record_id'])['payload'];binding=data.get('communication_attribution')
    if data.get('person_kind')!='LIVED_LANGUAGE_SAMPLE' or not binding or binding['entity_id']!=entity_id:return None
    arguments=dict(scope=scope,entity_id=entity_id,topic=binding['topic'],recipient_context=binding['recipient_context'])
    opinion=communication_feedback(store,**arguments,privacy=privacy_classes)
    if not opinion:return None
    def opinion_meaning(payload):
        sample=payload['sample'];attribution=payload.get('communication_attribution')
        return [sample['review_target'],attribution['reviewed_choice'] if attribution else None,
            sample['human_judgment'],sample['reason_tags'],sample['exact_feedback'],sample['provenance']]
    latest=records.read(opinion['review_record_id'])['payload']
    if opinion_meaning(latest)!=opinion_meaning(data):return None
    from ..subject.context_fit import communication_strategy_projection
    from ...life.dialogue_contracts import CommunicationStrategy
    strategy=communication_strategy_projection(store,**arguments,privacy_classes=privacy_classes)
    if strategy is None:return None
    method=CommunicationStrategy.model_validate_json(json.dumps(records.read(strategy['record_id'])['payload']))
    target=None;support_id=strategy['record_id']
    for rid in method.basis_private_record_ids:
        if reference is not None and reference.record_id!=rid:continue
        selected=internal_projection(store,(rid,),scope=scope,privacy_classes=privacy_classes,include_associations=False)
        if not selected or selected[0]['category']!='PRIVATE_TENDENCY' or selected[0]['activity_state']!='ACTIVE':continue
        item=PrivateTendency.model_validate_json(json.dumps(records.read(rid)['payload']))
        from ..subject.opportunities import PrivateIntentRef
        candidate=PrivateIntentRef(record_id=rid,intent_id=item.intent_id,revision=item.revision)
        if reference is not None and reference!=candidate:continue
        continuation_target(store,candidate,scope=scope,privacy_classes=privacy_classes)
        target=candidate;support_id=rid
        break
    # An initial own method can matter before a lasting inner state exists.
    # A paused/retired/unavailable prior basis is never treated as a new birth.
    if method.basis_private_record_ids and target is None:return None
    if reference is not None and target is None:return None
    from ...storage import digest
    # Aliases of the same exact opinion on the same turn are not new
    # conditions. The record remains a dependency, not an identity key.
    key='private-feedback.'+digest([store.identity['identity_id'],support_id,*opinion_meaning(data)])
    return {'reference':target,'key':key,'record_ids':tuple(dict.fromkeys((head['record_id'],review['record_id'],opinion['review_record_id'],opinion['record_id'],strategy['record_id']))),
        'memory_ids':tuple(dict.fromkeys((*records.support(head['record_id']),*records.support(support_id),*records.support(opinion['review_record_id']))))}



def consider_question(event,situation,judgment,intention,proposal):
    return _consider_formation(event,situation,judgment,intention,proposal)


def consider_plan(event,situation,judgment,intention,proposal):
    return _consider_formation(event,situation,judgment,intention,proposal)


def consider_tendency(event,situation,judgment,intention,proposal):
    return _consider_formation(event,situation,judgment,intention,proposal)


def is_private_consideration(event):
    """Existing internal opportunities, not public questions or work requests."""
    return event.origin=='SELF_WAKE' and (event.private_thought_ref is not None
        or event.communication_method_record_id is not None or event.growth_assessment_id is not None
        or event.task_class=='private.feedback.review')


def can_consider_private_formation(event,situation,judgment,intention):
    """The original C's pre-choice, reused by D only to allocate its method."""
    if (event.origin!='SELF_WAKE' or event.retention=='DO_NOT_REMEMBER'
            or judgment.stance not in {'WATCH','THINK_MORE','REMEMBER','REFLECT'}
            or (judgment.lesson_ids and intention.kind not in {'NO_ACTION','REFLECTION'})
            or intention.kind in {'SOCIAL_INTERACTION','DISAGREE','ACTION_PROPOSAL'}
            or intention.behavior in {'REST','WITHDRAW','STAY_SILENT','IGNORE','DO_NOTHING','DEFER'}
            or any((event.realization_target,event.goal_step,event.goal_review,event.memory_review_id,
                event.governance_review_id,event.disposition_reflection_id))
            or 'REFLECT' in situation.prohibited_behaviors
            or (situation.context_fit and not situation.context_fit.allow_deepening)
            or (situation.cue and (situation.cue.resource_ref or situation.cue.program_id))):
        return False
    return True


def _consider_formation(event,situation,judgment,intention,proposal):
    if proposal is None or not can_consider_private_formation(event,situation,judgment,intention):return None
    return proposal


def anchor_own_occurrence(store,event,*,authority):
    """Retain actual validated cognition occurrence, not the thought as fact.

    Only the original C controller calls this after proposal validation and its
    tentative choice. The private contents stay solely in the deletable private
    record. A stable source cannot resurrect a forgotten occurrence.
    """
    from ...storage import digest
    from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType,SELF_COGNITION_OCCURRENCE_TEXT
    from ..memory import MemoryService
    reference='self.'+digest([store.identity['identity_id'],event.scope,event.source_key])
    previous=store.db.execute("SELECT * FROM continuity_evidence WHERE source_namespace=? AND source_reference=?",('recorded.subject.cognition-occurrence',reference)).fetchone()
    if previous and previous['state']=='DELETED':raise CoreError('SOURCE_DELETED')
    when=previous['observed_time_us'] if previous else store.clock.utc_now_us()
    memory=MemoryService(store,authority)
    eid=memory.capture(EvidenceInput(provenance=Provenance(domain='SELF_COGNITION',
        source_namespace='recorded.subject.cognition-occurrence',source_reference=reference,source_kind='SYSTEM_VERIFICATION'),
        text=SELF_COGNITION_OCCURRENCE_TEXT,privacy_class=event.privacy_class,event_time_us=when,observed_time_us=when))
    mid=memory.add(MemoryCandidate(entity_id=store.identity['identity_id'],scope=event.scope,
        memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,
        text=SELF_COGNITION_OCCURRENCE_TEXT,importance=0,significance=0))
    return event.model_copy(update={'source_memory_ids':(mid,)})


def _complete_question_formation(store,tx,intention_id):
    """The C consideration was recorded; its ongoing question/plan is still active.

    This never completes a goal, learning job, delivery or external action.
    """
    row=store.one('subject_intentions',intention_id)
    if not row or row['kind']!='REFLECTION':raise CoreError('PRIVATE_QUESTION_FORMATION_BINDING_MISMATCH')
    if row['state']=='PENDING':
        tx.update('subject_intentions',intention_id,state='COMPLETED',revision=row['revision']+1)


def provider_consideration_memory(store,event):
    """Read an existing program occurrence; admission never invents a source."""
    from ...storage import digest
    from ..memory import MemoryService
    reference='self.request.'+digest([store.identity['identity_id'],event.scope,event.source_key])
    evidence=store.db.execute('SELECT * FROM continuity_evidence WHERE source_namespace=? AND source_reference=?',
        ('recorded.subject.provider-consideration',reference)).fetchone()
    if evidence is None:return None
    if evidence['state']=='DELETED':raise CoreError('SOURCE_DELETED')
    row=store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=? AND entity_id=? AND scope=?',
        (evidence['evidence_id'],store.identity['identity_id'],event.scope)).fetchone()
    if row is None:return None
    memory=MemoryService(store).read(row['memory_id'])
    if memory['privacy_class']!=event.privacy_class:raise CoreError('SOURCE_COLLISION')
    return row['memory_id']


def anchor_provider_consideration(store,event,*,authority):
    """C's actual pre-inference consideration, not a validated model proposal.

    Only a source-less provider resource needs this minimal audit root; no
    thought/input/response body is copied into it. Forgotten roots cannot revive.
    """
    from ...storage import digest
    from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType,SELF_PROVIDER_CONSIDERATION_TEXT
    from ..memory import MemoryService
    reference='self.request.'+digest([store.identity['identity_id'],event.scope,event.source_key])
    previous=store.db.execute('SELECT * FROM continuity_evidence WHERE source_namespace=? AND source_reference=?',
        ('recorded.subject.provider-consideration',reference)).fetchone()
    if previous and previous['state']=='DELETED':raise CoreError('SOURCE_DELETED')
    when=previous['observed_time_us'] if previous else store.clock.utc_now_us();memory=MemoryService(store,authority)
    eid=memory.capture(EvidenceInput(provenance=Provenance(domain='SELF_COGNITION',source_namespace='recorded.subject.provider-consideration',
        source_reference=reference,source_kind='SYSTEM_VERIFICATION'),text=SELF_PROVIDER_CONSIDERATION_TEXT,
        privacy_class=event.privacy_class,event_time_us=when,observed_time_us=when))
    mid=memory.add(MemoryCandidate(entity_id=store.identity['identity_id'],scope=event.scope,memory_type=MemoryType.EPISODIC,
        epistemic_kind='OBSERVATION',source_evidence_id=eid,text=SELF_PROVIDER_CONSIDERATION_TEXT,importance=0,significance=0))
    return event.model_copy(update={'source_memory_ids':(mid,)})


def after_choice(store,tx,event,result,*,privacy_classes,selected_topic=None,private_intent_ref=None,private_question=None,private_plan=None,private_tendency=None):
    """Called only by original SubjectLoop after its independent judgment commit data.

    A wall clock only permits reconsideration in another ordinary C cycle. Even a
    DISCLOSED state is eligibility, never an assertion of delivery or of an effect.
    """
    records=RecordService(store)
    formation=private_question or private_plan or private_tendency
    continued=continuation_target(store,event.private_thought_ref,scope=event.scope,privacy_classes=privacy_classes) if event.private_thought_ref else None
    current=candidates(store,event.scope,privacy_classes)
    if continued and not any(rid==continued[0] for rid,_ in current):current=(*current,continued)
    for topic in dict.fromkeys(t for t in (selected_topic,formation.topic if formation else None) if t is not None):
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
            if desired=='ACTIVE' and item.category not in {'PRIVATE_QUESTION','PRIVATE_PLAN','PRIVATE_TENDENCY'} and item.content_summary!=result.intention.purpose[:512]:
                changes['content_summary']=result.intention.purpose[:512]
        if changes:
            data={**item.model_dump(mode='json'),**changes,'revision':item.revision+1}
            if 'activity_state' in changes or isinstance(item,PrivateActivity):
                model=type(item) if isinstance(item,PrivateActivity) else PrivateActivity
                data.update(contract=model.model_fields['contract'].default,
                    activity_state=changes.get('activity_state',getattr(item,'activity_state','ACTIVE')),
                    created_at_us=getattr(item,'created_at_us',store.one('continuity_records',rid)['created_at_us']),
                    updated_at_us=store.clock.utc_now_us(),last_choice_cycle_id=result.cycle_id)
                revised=model.model_validate_json(json.dumps(data))
            else:revised=PrivateIntent.model_validate_json(json.dumps(data))
            associations=_association_record_ids(store,rid,owner_intent_id=item.intent_id,scope=event.scope,privacy_classes=privacy_classes)
            parents=(rid,result.record_id,*associations) if 'activity_state' in changes or 'content_summary' in changes else (rid,*associations)
            records.create(tx,kind='INTENTION',scope=event.scope,payload=revised.model_dump(mode='json'),records=parents,
                supersedes=rid,target_id='private-intent.v1')
    if (formation is not None and result.intention_id and result.record_id
            and result.intention.behavior=='REFLECT' and result.evaluation and result.evaluation.normative=='ENDORSED'):
        category='PRIVATE_QUESTION' if private_question is not None else 'PRIVATE_PLAN' if private_plan is not None else 'PRIVATE_TENDENCY'
        model=PrivateQuestion if private_question is not None else PrivateActivity if private_plan is not None else PrivateTendency
        contents=formation.question if private_question is not None else formation.plan if private_plan is not None else formation.tendency
        if formation.revises_record_id is not None:
            old=next(((rid,item) for rid,item in current if rid==formation.revises_record_id),None)
            if (old is None or not isinstance(old[1],model) or old[1].category!=category or old[1].owner_identity_id!=store.identity['identity_id']
                    or old[1].status=='WITHDRAWN' or old[1].disclosure_policy=='WITHDRAWN'):raise CoreError(category+'_REVISION_UNAVAILABLE')
            rid,item=old
            reframed=item.content_summary!=contents or item.topic!=formation.topic
            previous_associations=_association_record_ids(store,rid,owner_intent_id=item.intent_id,scope=event.scope,privacy_classes=privacy_classes)
            # Clear the current association projection, not the related ideas
            # or their original source/erasure lineage. Omission keeps old wire
            # semantics; it is never silently interpreted as abandonment.
            associations=() if formation.clear_related_private_records else (
                tuple(dict.fromkeys(x for x in formation.related_private_record_ids if x!=rid)) or previous_associations)
            association_changed=set(associations)!=set(previous_associations)
            if reframed or association_changed or item.activity_state!='ACTIVE':
                changes={'content_summary':contents,'topic':formation.topic,'activity_state':'ACTIVE',
                    'revision':item.revision+1,'updated_at_us':store.clock.utc_now_us(),'last_choice_cycle_id':result.cycle_id,
                    'source_memory_ids':result.intention.source_ids}
                if reframed or association_changed:
                    # Old eligibility/timing never discloses new private contents.
                    changes.update(disclosure_policy='MANAGER_AUDIT_ONLY' if item.disclosure_policy=='MANAGER_AUDIT_ONLY' else 'PRIVATE_FOR_NOW',
                        status='CONSIDERED',trigger_at_us=None)
                revised=item.model_copy(update=changes)
                records.create(tx,kind='INTENTION',scope=event.scope,payload=revised.model_dump(mode='json'),
                    records=tuple(dict.fromkeys((rid,result.record_id,*associations))),
                    supersedes=rid,target_id='private-intent.v1')
            _complete_question_formation(store,tx,result.intention_id)
            return
        if not any(item.owner_identity_id==store.identity['identity_id'] and item.topic==formation.topic
                and item.category==category and item.content_summary==contents
                and getattr(item,'activity_state','ACTIVE')!='ABANDONED' for _,item in current):
            now=store.clock.utc_now_us()
            value=model(category=category,intent_id=result.intention_id,owner_identity_id=store.identity['identity_id'],cycle_id=result.cycle_id,
                topic=formation.topic,content_summary=contents,disclosure_policy='PRIVATE_FOR_NOW',
                source_memory_ids=result.intention.source_ids,risk_class=event.risk,created_at_us=now,updated_at_us=now,last_choice_cycle_id=result.cycle_id)
            records.create(tx,kind='INTENTION',scope=event.scope,payload=value.model_dump(mode='json'),
                records=tuple(dict.fromkeys((result.record_id,*formation.related_private_record_ids))),target_id='private-intent.v1')
        _complete_question_formation(store,tx,result.intention_id)
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
