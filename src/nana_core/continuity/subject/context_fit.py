"""Sourced interaction assessment inside C. No classifier model or expression loop.

Signals are host interpretations, not facts about intent. Boundaries are exact
person/scope/topic observations; inferred disagreement cannot install a refusal.
"""
from typing import Literal
from pydantic import Field
from ...contracts import DTO
from ...storage import digest
from ..records import RecordService

class InteractionSignal(DTO):
    kind: Literal['VENT','HELP','SHARE','DECLINE_DEPTH','REOPEN','FOCUS','UNCLEAR','IMPORTANT']
    topic_key: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    basis: Literal['EXPLICIT','INTERPRETED'] = 'EXPLICIT'
    provenance: Literal['HOST_INTERPRETATION_NOT_TRUTH'] = 'HOST_INTERPRETATION_NOT_TRUTH'

class ContextFitAssessment(DTO):
    derived: Literal[True] = True
    entity_id: str
    topic_key: str
    mode: Literal['VENT','HELP','SHARE','DECLINE_DEPTH','REOPEN','FOCUS','UNCLEAR','IMPORTANT','RESPECT_BOUNDARY','INDEPENDENT']
    allow_deepening: bool
    allow_new_work: bool
    preserve_independent_activity: Literal[True] = True
    source_record_ids: tuple[str,...] = ()
    source_memory_ids: tuple[str,...] = ()
    reason: str
    state_token: str

def boundary_key(entity_id,scope,topic):return 'context-topic:'+digest([entity_id,scope,topic])

def depth_boundary(store,entity_id,scope,topic,privacy_classes):
    if store.schema_target<9:return False,(),'CONTEXT_BOUNDARY_SCHEMA_NOT_AVAILABLE'
    records=RecordService(store)
    rows=store.db.execute("SELECT * FROM continuity_records WHERE record_kind='SUBJECT_EVENT' AND target_id=? ORDER BY rowid DESC LIMIT 33",(boundary_key(entity_id,scope,topic),)).fetchall()
    for row in rows:
        if row['lifecycle']!='ACTIVE':continue
        if row['scope']!=scope or row['privacy_class'] not in privacy_classes:return True,(),'BOUNDARY_COVERAGE_UNKNOWN'
        if not records.current_support(row['record_id']):continue
        value=records.read(row['record_id'])['payload']['input'];signal=value.get('interaction_signal')
        if not signal or signal['basis']!='EXPLICIT' or value['origin']!='USER' or value['entity_id']!=entity_id:continue
        if signal['kind'] in {'DECLINE_DEPTH','REOPEN'}:
            return signal['kind']=='DECLINE_DEPTH',(row['record_id'],),'EXPLICIT_TOPIC_'+signal['kind']
    # The bounded horizon cannot establish absence if all33 candidates are stale.
    return len(rows)>32,(),'BOUNDARY_COVERAGE_UNKNOWN' if len(rows)>32 else 'NO_EXPLICIT_REFUSAL'

def assess(store,event,source,*,topic,privacy_classes):
    signal=event.interaction_signal
    topic=signal.topic_key if signal else topic
    if not topic:return None
    closed,refs,reason=depth_boundary(store,event.entity_id,event.scope,topic,privacy_classes)
    if signal and signal.kind=='DECLINE_DEPTH' and signal.basis=='EXPLICIT':closed=True
    mode=signal.kind if signal else 'INDEPENDENT'
    if signal and signal.basis!='EXPLICIT':mode='UNCLEAR'
    if closed:mode='RESPECT_BOUNDARY'
    allow=not closed and mode in {'HELP','IMPORTANT','REOPEN','INDEPENDENT'}
    if mode=='IMPORTANT' and not event.source_memory_ids:mode='UNCLEAR';allow=False
    refs=tuple(dict.fromkeys((*refs,*((source['record_id'],) if source['record_id'] else ()))))
    records=RecordService(store)
    memories=tuple(dict.fromkeys(m for r in refs for m in records.support(r)))
    return ContextFitAssessment(entity_id=event.entity_id,topic_key=topic,mode=mode,allow_deepening=allow,allow_new_work=allow,
        source_record_ids=refs,source_memory_ids=memories,reason=reason if closed else 'C interprets a sourced '+mode.lower()+' context without automatic task adoption',
        state_token=digest([mode,refs,topic,event.entity_id]))

def choose(event,situation):
    """Optional phase of the existing C judgment, never execution authorization."""
    fit=situation.context_fit
    if fit is None or fit.mode in {'INDEPENDENT','REOPEN'}:return None
    from .contracts import Judgment,Intention
    sources=situation.memory_ids;self_generated=event.origin=='SELF_WAKE'
    if fit.mode=='RESPECT_BOUNDARY':
        return 'DEFER',Judgment(stance='DEFER',reason='Respect the explicit topic refusal; do not privately restart research',source_ids=sources),Intention(kind='NO_ACTION',purpose='Leave this topic closed without deleting independent interests',slot_key='quiet',source_ids=sources,self_generated=self_generated,behavior='STAY_SILENT')
    if fit.mode=='FOCUS':
        return 'FOCUS_NOW',Judgment(stance='ASK',reason='Attend to the requested focus; preserve unrelated pending activity for later',source_ids=sources),Intention(kind='WAIT',purpose='Clarify the immediate need while background work yields',slot_key='context-focus',source_ids=sources,self_generated=False)
    if fit.mode in {'VENT','SHARE'}:
        return 'FOCUS_NOW',Judgment(stance='WATCH',reason='Attend to the interaction without turning it into unsolicited research',source_ids=sources),Intention(kind='SOCIAL_INTERACTION',purpose='Consider a context-appropriate response, not a new project',slot_key='interaction-'+fit.topic_key,source_ids=sources,self_generated=False)
    if fit.mode in {'UNCLEAR','DECLINE_DEPTH'}:
        return 'FOCUS_NOW',Judgment(stance='ASK',reason='Intent is uncertain; clarification is preferable to unsolicited analysis',source_ids=sources),Intention(kind='WAIT',purpose='Ask what kind of response is wanted',slot_key='context-clarify',source_ids=sources,self_generated=self_generated)
    return 'FOCUS_NOW',Judgment(stance='THINK_MORE',reason='Consider explicit help or sourced significance; no goal is adopted by the request',source_ids=sources),Intention(kind='GOAL_CANDIDATE',purpose='Consider a bounded helpful next step',slot_key='help-'+fit.topic_key,source_ids=sources,self_generated=self_generated)

def social_candidate(fit,*,style,source_ids,available=True):
    from .social import SocialInteractionProposal,propose_social
    if fit.mode in {'RESPECT_BOUNDARY','FOCUS'} or not available:return SocialInteractionProposal(act='STAY_SILENT',topic_key=fit.topic_key,approach='NO_INTERRUPTION',source_memory_ids=source_ids)
    if fit.mode=='SHARE':return propose_social(topic=fit.topic_key,style=style,available=available,source_ids=source_ids)
    return SocialInteractionProposal(act='CHECK_IN' if fit.mode=='VENT' else 'ASK',topic_key=fit.topic_key,approach='CHECK_RECEPTION',source_memory_ids=source_ids)

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
