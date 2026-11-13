"""Sourced interaction assessment inside C. No classifier model or expression loop.

Signals are host interpretations, not facts about intent. Boundaries are exact
person/scope/topic observations; inferred disagreement cannot install a refusal.
"""
from typing import Literal
from pydantic import Field
from ...contracts import DTO
from ...storage import digest,canonical
from ..records import RecordService

# An existing delivery-boundary ledger topic, not a new availability authority.
# C can retain interests and continue work while spontaneous delivery waits.
REST_DELIVERY_TOPIC = 'presence.rest'

class InteractionSignal(DTO):
    kind: Literal['VENT','CHAT','HELP','SHARE','CORRECTION','DECLINE_DEPTH','DECLINE_DELIVERY','REOPEN','REOPEN_DELIVERY','FOCUS','UNCLEAR','IMPORTANT','PROJECT_STATUS']
    topic_key: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    basis: Literal['EXPLICIT','INTERPRETED','MODEL_PROPOSAL'] = 'EXPLICIT'
    proposal_record_id: str | None = None
    provenance: Literal['HOST_INTERPRETATION_NOT_TRUTH'] = 'HOST_INTERPRETATION_NOT_TRUTH'

class ContextFitAssessment(DTO):
    derived: Literal[True] = True
    entity_id: str
    topic_key: str
    mode: Literal['VENT','CHAT','HELP','SHARE','CORRECTION','DECLINE_DEPTH','DECLINE_DELIVERY','REOPEN','REOPEN_DELIVERY','FOCUS','UNCLEAR','IMPORTANT','RESPECT_BOUNDARY','INDEPENDENT','PROJECT_STATUS']
    allow_delivery: bool = True
    allow_deepening: bool
    allow_new_work: bool
    preserve_independent_activity: Literal[True] = True
    source_record_ids: tuple[str,...] = ()
    source_memory_ids: tuple[str,...] = ()
    reason: str
    state_token: str

def boundary_key(entity_id,scope,topic,*,purpose='COGNITION'):
    key='context-topic:'+digest([entity_id,scope,topic])
    return key if purpose=='COGNITION' else key+':delivery'

def depth_boundary(store,entity_id,scope,topic,privacy_classes,*,purpose="DELIVERY"):
    """Separate indexed ledgers: delivery traffic cannot hide processing limits.

    Legacy DECLINE_DEPTH/REOPEN retain their processing meaning. New ordinary
    conversation reopen affects only the delivery ledger, never processing.
    """
    if purpose not in {"DELIVERY","COGNITION"}:raise ValueError("unknown boundary purpose")
    if store.schema_target<9:return False,(),'CONTEXT_BOUNDARY_SCHEMA_NOT_AVAILABLE'
    records=RecordService(store)
    def ledger(axis):
        rows=store.db.execute("SELECT * FROM continuity_records WHERE record_kind='SUBJECT_EVENT' AND target_id=? ORDER BY rowid DESC LIMIT 33",(boundary_key(entity_id,scope,topic,purpose=axis),)).fetchall()
        for row in rows:
            if row['lifecycle']!='ACTIVE':continue
            if row['scope']!=scope or row['privacy_class'] not in privacy_classes:return True,(),'BOUNDARY_COVERAGE_UNKNOWN'
            if not records.current_support(row['record_id']):continue
            value=records.read(row['record_id'])['payload']['input'];signal=value.get('interaction_signal')
            if not signal or signal['basis']!='EXPLICIT' or value['origin']!='USER' or value['entity_id']!=entity_id:continue
            kinds={'DECLINE_DEPTH','REOPEN'} if axis=='COGNITION' else {'DECLINE_DELIVERY','REOPEN_DELIVERY'}
            if signal['kind'] in kinds:
                return signal['kind'].startswith('DECLINE'),(row['record_id'],),'EXPLICIT_TOPIC_'+signal['kind']
        return len(rows)>32,(),'BOUNDARY_COVERAGE_UNKNOWN' if len(rows)>32 else 'NO_EXPLICIT_REFUSAL'
    hard,refs,reason=ledger('COGNITION')
    if purpose=='COGNITION':return hard,refs,reason
    delivery,drefs,dreason=ledger('DELIVERY')
    return hard or delivery,tuple(dict.fromkeys((*refs,*drefs))),reason if hard else dreason

def assess(store,event,source,*,topic,privacy_classes):
    signal=event.interaction_signal
    topic=signal.topic_key if signal else topic
    if not topic:return None
    closed,refs,reason=depth_boundary(store,event.entity_id,event.scope,topic,privacy_classes,purpose='COGNITION' if event.origin=='SELF_WAKE' else 'DELIVERY')
    if signal and signal.kind in {'DECLINE_DEPTH','DECLINE_DELIVERY'} and signal.basis=='EXPLICIT':closed=True
    mode=signal.kind if signal else 'INDEPENDENT'
    proposal_refs=()
    if signal and signal.basis=='MODEL_PROPOSAL':
        # The model can suggest meaning, never install an explicit user boundary.
        try:
            records=RecordService(store);head=store.one('continuity_records',signal.proposal_record_id)
            if not head or head['record_kind']!='COGNITION_PROPOSAL' or head['scope']!=event.scope or head['privacy_class'] not in privacy_classes or not records.current_support(head['record_id']):raise ValueError()
            reply=records.read(head['record_id'])['payload']['reply'];request=store.one('cognitive_requests',reply['request_id'])
            body=records.read(request['record_id'])['payload']['request']
            from .state import revision
            if request['state']!='PROPOSED' or request['subject_revision']!=revision(store) or body['cognitive_role']!='INTERPRET' or body['role_input']['dialogue']['message_memory_id'] not in event.source_memory_ids or body['role_input']['dialogue']['topic']!=topic or reply['proposal']['dialogue']['kind']!=signal.kind:raise ValueError()
            if body['subject_epoch']!=store.one('runtime_lease',store.identity['identity_id'])['epoch'] or store.clock.utc_now_us()>request['deadline_us']:raise ValueError()
            proposal_refs=(head['record_id'],)
            if signal.kind in {'DECLINE_DEPTH','DECLINE_DELIVERY','REOPEN','REOPEN_DELIVERY'}:mode='RESPECT_BOUNDARY' if signal.kind.startswith('DECLINE') else 'UNCLEAR'
        except (ValueError,KeyError,TypeError):mode='UNCLEAR'
    elif signal and signal.basis!='EXPLICIT':mode='UNCLEAR'
    delivery_closed,delivery_refs,_=depth_boundary(store,event.entity_id,event.scope,topic,privacy_classes)
    refs=tuple(dict.fromkeys((*refs,*delivery_refs)))
    if closed:mode='RESPECT_BOUNDARY'
    allow=not closed and mode in {'HELP','IMPORTANT','REOPEN','REOPEN_DELIVERY','INDEPENDENT'}
    if mode=='IMPORTANT' and not event.source_memory_ids:mode='UNCLEAR';allow=False
    refs=tuple(dict.fromkeys((*refs,*proposal_refs,*((source['record_id'],) if source['record_id'] else ()))))
    records=RecordService(store)
    memories=tuple(dict.fromkeys(m for r in refs for m in records.support(r)))
    return ContextFitAssessment(entity_id=event.entity_id,topic_key=topic,mode=mode,allow_delivery=not delivery_closed and not (signal and signal.kind in {'DECLINE_DEPTH','DECLINE_DELIVERY'}),allow_deepening=allow,allow_new_work=allow,
        source_record_ids=refs,source_memory_ids=memories,reason=reason if closed else 'C interprets a sourced '+mode.lower()+' context without automatic task adoption',
        state_token=digest([mode,refs,topic,event.entity_id]))

def choose(event,situation):
    """Optional phase of the existing C judgment, never execution authorization."""
    fit=situation.context_fit
    if fit is None or fit.mode in {'INDEPENDENT','REOPEN','REOPEN_DELIVERY'}:return None
    from .contracts import Judgment,Intention
    sources=situation.memory_ids;self_generated=event.origin=='SELF_WAKE'
    if fit.mode=='RESPECT_BOUNDARY':
        return 'DEFER',Judgment(stance='DEFER',reason='Respect the sourced boundary at its declared scope',source_ids=sources),Intention(kind='NO_ACTION',purpose='Withhold this interaction; preserve desires and independent cognition unless processing is forbidden',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='STAY_SILENT')
    if fit.mode=='FOCUS':
        return 'FOCUS_NOW',Judgment(stance='THINK_MORE',reason='Attend to the requested focus; preserve unrelated pending activity for later',source_ids=sources),Intention(kind='SOCIAL_INTERACTION',purpose='Respond to the current focus using supplied details; clarify only missing specifics while background work yields',slot_key='context-focus',source_ids=sources,self_generated=False)
    if fit.mode=='PROJECT_STATUS':
        return 'FOCUS_NOW',Judgment(stance='WATCH',reason='Attend to an explicit project-status question using current sourced state, not clarification of an unclear intent',source_ids=sources),Intention(kind='SOCIAL_INTERACTION',purpose='Discuss sourced current project status and a supported assessment, not adopt work or invent personal experiences',slot_key='project-status-'+fit.topic_key,source_ids=sources,self_generated=False)
    if fit.mode=='CORRECTION':
        return 'FOCUS_NOW',Judgment(stance='WATCH',reason='Attend to the correction as a sourced report; it does not by itself verify or rewrite a fact',source_ids=sources),Intention(kind='SOCIAL_INTERACTION',purpose='Acknowledge the correction and distinguish established details from uncertainty; clarify only missing details',slot_key='correction-'+fit.topic_key,source_ids=sources,self_generated=False)
    if fit.mode in {'VENT','SHARE','CHAT'}:
        return 'FOCUS_NOW',Judgment(stance='WATCH',reason='Attend to the interaction without turning it into unsolicited research',source_ids=sources),Intention(kind='SOCIAL_INTERACTION',purpose='Consider a context-appropriate response, not a new project',slot_key='interaction-'+fit.topic_key,source_ids=sources,self_generated=False)
    if fit.mode in {'UNCLEAR','DECLINE_DEPTH'}:
        return 'FOCUS_NOW',Judgment(stance='ASK',reason='Intent is uncertain; clarification is preferable to unsolicited analysis',source_ids=sources),Intention(kind='WAIT',purpose='Ask what kind of response is wanted',slot_key='context-clarify',source_ids=sources,self_generated=self_generated)
    return 'FOCUS_NOW',Judgment(stance='THINK_MORE',reason='Consider explicit help or sourced significance; no goal is adopted by the request',source_ids=sources),Intention(kind='GOAL_CANDIDATE',purpose='Consider a bounded helpful next step',slot_key='help-'+fit.topic_key,source_ids=sources,self_generated=self_generated)

def social_candidate(fit,*,style,source_ids,available=True):
    from .social import SocialInteractionProposal,propose_social
    if not fit.allow_delivery or fit.mode in {'RESPECT_BOUNDARY','FOCUS'} or not available:return SocialInteractionProposal(act='STAY_SILENT',topic_key=fit.topic_key,approach='NO_INTERRUPTION',source_memory_ids=source_ids)
    if fit.mode=='PROJECT_STATUS':return SocialInteractionProposal(act='EXPRESS_OPINION',topic_key=fit.topic_key,approach='CHECK_RECEPTION',source_memory_ids=source_ids)
    if fit.mode=='SHARE':return propose_social(topic=fit.topic_key,style=style,available=available,source_ids=source_ids)
    return SocialInteractionProposal(act='CHECK_IN' if fit.mode=='VENT' else 'ASK',topic_key=fit.topic_key,approach='CHECK_RECEPTION',source_memory_ids=source_ids)


def consider_communication(store,event,situation,intention,evaluation,*,privacy_classes):
    """Original C may adopt a method only after its independent choice.

    The interpretation binding has already been validated by assess(). Private
    reasons stay in their original records; the public choice has only enums.
    """
    fit=situation.context_fit;signal=event.interaction_signal
    if (not fit or not signal or signal.basis!='MODEL_PROPOSAL' or not signal.proposal_record_id
            or signal.proposal_record_id not in fit.source_record_ids
            or fit.mode=='UNCLEAR'):
        return None,None
    from ...life.dialogue_contracts import CommunicationProposal,CommunicationChoice
    from ..autonomy.private_intent import internal_projection
    import json
    records=RecordService(store)
    data=records.read(signal.proposal_record_id)['payload']['reply']['proposal']['dialogue'].get('communication_proposal')
    if data is None:return None,None
    proposal=CommunicationProposal.model_validate_json(json.dumps(data))
    current={v['record_id'] for v in internal_projection(store,situation.private_interest_records,
        scope=event.scope,privacy_classes=privacy_classes)}
    if not set(proposal.basis_private_record_ids)<=current:return None,None
    if (fit.mode=='RESPECT_BOUNDARY' and intention.kind=='NO_ACTION' and proposal.end_previous_strategy):
        # C may stop its own method in this context without manufacturing an
        # explicit, permanent user boundary from a model interpretation.
        return None,proposal
    if (fit.mode=='RESPECT_BOUNDARY' or not fit.allow_delivery
            or intention.kind not in {'SOCIAL_INTERACTION','DISAGREE'}
            or not evaluation or evaluation.normative!='ENDORSED'):
        return None,None
    return CommunicationChoice(approach=proposal.approach,detail=proposal.detail,follow_up=proposal.follow_up),proposal


def _strategy_key(store,scope,entity_id,topic,recipient):
    if hasattr(recipient,'model_dump'):recipient=recipient.model_dump(mode='json')
    return 'communication-strategy.'+digest([store.identity['identity_id'],scope,entity_id,topic,recipient])


def _strategy_latest(store,scope,entity_id,topic,recipient):
    # Read the latest header even if retired/withheld. Never fall back to an
    # older strategy after a correction, stop, withdrawal or privacy change.
    return store.db.execute("SELECT * FROM continuity_records WHERE record_kind='INTENTION' AND scope=? AND target_id=? ORDER BY created_at_us DESC,rowid DESC LIMIT 1",
        (scope,_strategy_key(store,scope,entity_id,topic,recipient))).fetchone()


def communication_strategy_projection(store,*,scope,entity_id,topic,recipient_context,privacy_classes):
    if store.schema_target<13:return None
    head=_strategy_latest(store,scope,entity_id,topic,recipient_context)
    if not head or head['lifecycle']!='ACTIVE' or head['privacy_class'] not in privacy_classes:return None
    records=RecordService(store)
    if not records.current_support(head['record_id']):return None
    from ...life.dialogue_contracts import CommunicationStrategy
    from ..autonomy.private_intent import internal_projection
    value=CommunicationStrategy.model_validate_json(canonical(records.read(head['record_id'])['payload']))
    expected_recipient=recipient_context.model_dump(mode='json') if hasattr(recipient_context,'model_dump') else recipient_context
    if (value.owner_identity_id!=store.identity['identity_id'] or value.entity_id!=entity_id or value.topic!=topic
            or (value.recipient_context.model_dump(mode='json') if value.recipient_context else None)!=expected_recipient
            or value.state!='ACTIVE' or value.expires_at_us<=store.clock.utc_now_us()):return None
    current={item['record_id'] for item in internal_projection(store,value.basis_private_record_ids,
        scope=scope,privacy_classes=privacy_classes,include_associations=False)}
    if not set(value.basis_private_record_ids)<=current:return None
    # Only a compact prior own method, never the previous user words, private
    # reasons, a claim of effectiveness or a command to follow it unchanged.
    return {'record_id':head['record_id'],'choice':value.choice.model_dump(mode='json'),
        'created_at_us':value.created_at_us,'expires_at_us':value.expires_at_us,
        'effect_status':value.effect_status,'semantics':'PRIOR_OWN_METHOD_HYPOTHESIS_RECONSIDER_NOW',
        'execution_authority':False}


def record_communication_strategy(store,tx,event,result,proposal,*,privacy_classes):
    if not result.record_id or event.retention=='DO_NOT_REMEMBER' or not event.interaction_signal:return
    from ...life.dialogue_contracts import CommunicationStrategy
    signal=event.interaction_signal;recipient=None
    if event.surface:recipient={'platform':event.surface.platform,'binding_id':event.surface.session_id,'conversation_id':event.surface.conversation_id}
    head=_strategy_latest(store,event.scope,event.entity_id,signal.topic_key,recipient)
    explicit_stop=signal.basis=='EXPLICIT' and signal.kind in {'DECLINE_DEPTH','DECLINE_DELIVERY'}
    stop=explicit_stop or bool(proposal and proposal.end_previous_strategy)
    duration=proposal.strategy_duration_seconds if proposal else None
    if (not stop and (duration is None or result.communication_choice is None)) or (stop and head is None):return
    records=RecordService(store)
    previous=communication_strategy_projection(store,scope=event.scope,entity_id=event.entity_id,topic=signal.topic_key,
        recipient_context=recipient,privacy_classes=privacy_classes)
    if stop and previous is None:return
    if previous and not stop and previous['choice']==result.communication_choice.model_dump(mode='json'):
        old=CommunicationStrategy.model_validate_json(canonical(records.read(head['record_id'])['payload']))
        if not proposal.basis_private_record_ids or set(proposal.basis_private_record_ids)==set(old.basis_private_record_ids):
            return  # Same method/conditions: no repeated writes or sliding expiry.
    now=store.clock.utc_now_us()
    value=CommunicationStrategy(owner_identity_id=store.identity['identity_id'],entity_id=event.entity_id,topic=signal.topic_key,
        recipient_context=recipient,choice=None if stop else result.communication_choice,
        basis_private_record_ids=() if stop else proposal.basis_private_record_ids,state='STOPPED' if stop else 'ACTIVE',
        source_cycle_id=result.cycle_id,created_at_us=now,expires_at_us=now if stop else now+duration*1_000_000)
    prior=head['record_id'] if head and head['lifecycle']=='ACTIVE' else None
    records.create(tx,kind='INTENTION',scope=event.scope,payload=value.model_dump(mode='json'),records=(result.record_id,),
        supersedes=prior,target_id=_strategy_key(store,event.scope,event.entity_id,signal.topic_key,recipient),
        privacy_floor=head['privacy_class'] if prior else None)

def plan_binding(store,reference,*,scope,privacy_classes,goal_id=None):
    """Follow existing adopted-goal lineage, not a model-named private topic."""
    from ..agency import step_view
    records=RecordService(store)
    if reference:
        view=step_view(store,reference,scope=scope,privacy_classes=privacy_classes);goal_id=view.goal_id
    goal=store.one('goals',goal_id)
    if not goal:return None
    import json
    rid=json.loads(goal['body_json']).get('record_id')
    if not rid:return None
    head=store.one('continuity_records',rid)
    if head['scope']!=scope or head['privacy_class'] not in privacy_classes:return None
    candidate_id=records.read(rid)['payload'].get('candidate_id')
    candidate=store.one('subject_goal_candidates',candidate_id) if candidate_id else None
    if not candidate:return None
    intention=store.one('subject_intentions',candidate['intention_id'])
    cycle=store.db.execute('SELECT record_id FROM subject_cycles WHERE subject_event_id=?',(intention['subject_event_id'],)).fetchone()
    if not cycle or not cycle[0]:return None
    head=store.one('continuity_records',cycle[0])
    if head['scope']!=scope or head['privacy_class'] not in privacy_classes:return None
    return records.read(cycle[0])['payload'].get('context_fit')
