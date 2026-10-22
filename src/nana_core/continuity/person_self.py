"""Bounded personal continuity in the original Store and original C transaction.

Declarations, adopted social roles and reports of speech are different from world
facts. Nothing here creates an identity, a Grant, or a second decision loop.
"""
import json
import re
from typing import Literal
from pydantic import Field
from ..contracts import DTO, CoreError
from ..storage import canonical, digest
from .records import RecordService
from .memory import MemoryService
from .contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType


class ConversationProposal(DTO):
    kind: Literal['RELATIONSHIP_ROLE', 'EXPRESSION_PREFERENCE', 'UNFINISHED_TOPIC']
    operation: Literal['PROPOSE', 'CORRECT', 'WITHDRAW', 'PLAY'] = 'PROPOSE'
    value: str = Field(min_length=1, max_length=128)
    quote: str = Field(min_length=1, max_length=256)
    replaces_record_id: str | None = None


class ConversationDecision(DTO):
    choice: Literal['ADOPT', 'KEEP_EXISTING', 'ASK', 'PLAY_ONLY', 'WITHDRAW', 'DECLINE']
    reason: str
    proposal: ConversationProposal
    previous_record_id: str | None = None
    execution_authority: Literal[False] = False


def rows(store, kind, scope, privacy, *, limit=32, target=None):
    """Indexed bounded headers first; never open a denied payload."""
    if not privacy:
        return ()
    storage={'PERSONAL_ADOPTION':'ASSERTION','CONVERSATION_EXCHANGE':'RELATIONSHIP_EVENT','LIVED_LANGUAGE_SAMPLE':'EXPERIENCE_CANDIDATE'}[kind]
    sql = 'SELECT * FROM continuity_records WHERE record_kind=? AND scope=?'
    args = [storage, scope]
    if target is not None:
        sql += ' AND target_id=?'
        args.append(target)
    sql += ' ORDER BY rowid DESC LIMIT ?'
    args.append(limit)
    records = RecordService(store)
    out = []
    for raw in store.db.execute(sql, args):
        h = dict(raw)
        if h['privacy_class'] not in privacy or h['lifecycle'] != 'ACTIVE':
            continue
        if records.current_support(h['record_id']):
            item=records.read(h['record_id'])
            if item['payload'].get('person_kind')==kind:out.append(item)
    return tuple(out)


def slot(entity_id, kind):
    return 'person:' + digest([entity_id, kind])


def adopted(store, scope, entity_id, privacy):
    result = []
    for kind in ('RELATIONSHIP_ROLE', 'EXPRESSION_PREFERENCE', 'UNFINISHED_TOPIC'):
        # The latest revision is authoritative even if its source was withdrawn.
        # Do not fall back to an older role after erasure/correction.
        latest = store.db.execute("SELECT * FROM continuity_records WHERE record_kind='ASSERTION' AND scope=? AND target_id=? ORDER BY rowid DESC LIMIT 1", (scope, slot(entity_id, kind))).fetchone()
        if latest and latest['privacy_class'] in privacy and latest['lifecycle'] == 'ACTIVE':
            visible = rows(store, 'PERSONAL_ADOPTION', scope, privacy, limit=1, target=slot(entity_id, kind))
            if visible and visible[0]['payload']['decision']['choice'] == 'ADOPT':
                result.append(visible[0])
    return tuple(result)


def consider(store, event, situation, privacy):
    """Called inside C. A model proposes; current evidence and C decide."""
    p = event.conversation_proposal
    if not p:
        return None
    records = RecordService(store)
    # A quote must be present in an explicitly retained user statement. A receipt
    # or model derivation is not evidence that a user made a relationship request.
    sources = [records.memory.read(mid) for mid in event.source_memory_ids]
    sources = [m for m in sources if m['entity_id'] == event.entity_id and m['scope'] == event.scope
               and m['source_provenance']['source_kind'] == 'USER_STATEMENT'
               and m['source_provenance']['source_namespace'] == 'recorded.conversation.input'
               and p.quote in m['text']]
    if p.value not in p.quote:
        raise CoreError('CONVERSATION_VALUE_OUTSIDE_QUOTE')
    if not sources or event.retention == 'DO_NOT_REMEMBER':
        raise CoreError('CONVERSATION_ADOPTION_SOURCE_REQUIRED')
    existing = next((r for r in adopted(store, event.scope, event.entity_id, privacy)
                     if r['payload']['decision']['proposal']['kind'] == p.kind), None)
    previous = existing['record_id'] if existing else None
    statement='\n'.join(m['text'] for m in sources)
    play=bool(re.search(r'假装|扮演|角色扮演|演一下|\b(?:roleplay|pretend|imagine)\b',statement,re.I))
    negative=bool(re.search(r'不要再叫|别叫|不再是|停止叫|\b(?:do not call|don.t call|no longer)\b',statement,re.I))
    if p.operation == 'PLAY' or (p.kind=='RELATIONSHIP_ROLE' and play):
        choice, reason = 'PLAY_ONLY', 'Temporary play does not change the enduring self or relationship'
    elif p.kind=='RELATIONSHIP_ROLE' and negative and p.operation!='WITHDRAW':
        choice, reason = 'ASK', 'A negative relationship statement must not be adopted as a positive role'
    elif p.operation in {'CORRECT', 'WITHDRAW'} and p.replaces_record_id != previous:
        choice, reason = 'ASK', 'Correction requires the exact currently adopted source'
    elif situation.context_fit and situation.context_fit.mode == 'RESPECT_BOUNDARY':
        choice, reason = 'DECLINE', 'Respect the current sourced conversational boundary'
    elif situation.relationship_influence and situation.relationship_influence.repair_tension.assessment == 'UNRESOLVED':
        choice, reason = 'ASK', 'Consider the unresolved relationship event before adopting a new role'
    elif p.operation == 'WITHDRAW':
        choice, reason = 'WITHDRAW', 'Respect withdrawal without erasing the historical choice'
    elif existing and p.operation == 'PROPOSE' and existing['payload']['decision']['proposal']['value'] != p.value:
        choice, reason = 'KEEP_EXISTING', 'A conflicting statement does not silently overwrite an adopted relationship or preference'
    else:
        choice, reason = 'ADOPT', 'Adopt a bounded social convention or conversational preference; no biological claim or execution authority'
    return ConversationDecision(choice=choice, reason=reason, proposal=p, previous_record_id=previous)


def commit(store, tx, event, decision, cycle_record_id):
    if not decision or decision.choice not in {'ADOPT', 'WITHDRAW'}:
        return
    records = RecordService(store)
    key = slot(event.entity_id, decision.proposal.kind)
    old = store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='ASSERTION' AND scope=? AND target_id=? ORDER BY rowid DESC LIMIT 1", (event.scope, key)).fetchone()
    records.create(tx, kind='ASSERTION', scope=event.scope, target_id=key,
                   payload={'person_kind':'PERSONAL_ADOPTION','decision': decision.model_dump(mode='json'), 'entity_id': event.entity_id,
                            'as_of_us': store.clock.utc_now_us(), 'confidence': 'SUBJECT_ADOPTED_CONVENTION',
                            'biological_claim': False, 'execution_authority': False},
                   records=(cycle_record_id,), supersedes=old[0] if old and store.one('continuity_records', old[0])['lifecycle'] != 'DELETED' else None)


def retain_input(store, *, entity_id, scope, text, privacy, message_id):
    """Explicit per-turn opt-in only; default dialogue remains transient."""
    memory = MemoryService(store)
    now = store.clock.utc_now_us()
    eid = memory.capture(EvidenceInput(provenance=Provenance(domain='CONSENTED_INTERACTION',source_namespace='recorded.conversation.input', source_reference=message_id, source_kind='USER_STATEMENT'), text=text,
        privacy_class=privacy, retention_consent_ref=message_id, observed_time_us=now))
    return memory.add(MemoryCandidate(entity_id=entity_id, scope=scope, memory_type=MemoryType.EPISODIC,
        epistemic_kind='STATEMENT', source_evidence_id=eid, text=text))


def retain_exchange(store, *, entity_id, scope, topic, user_memory_id, text, cycle, source_memory_ids=()):
    """Speech occurrence, never proof of the contents of the utterance."""
    records = RecordService(store)
    with store.transaction('subject.conversation_retained') as tx:
        return records.create(tx, kind='RELATIONSHIP_EVENT', scope=scope, target_id=topic,
            payload={'person_kind':'CONVERSATION_EXCHANGE','entity_id': entity_id, 'topic': topic, 'user_memory_id': user_memory_id,
                     'user_statement': records.memory.read(user_memory_id)['text'],
                     'assistant_utterance': text, 'epistemic_status': 'REPORTED_SPEECH_NOT_WORLD_TRUTH',
                     'judgment': cycle.judgment.stance, 'as_of_us': store.clock.utc_now_us()},
            memories=tuple(dict.fromkeys((user_memory_id, *source_memory_ids))), records=(cycle.record_id,))


def project(store, *, entity_id, scope, privacy, topic=None):
    """Rebuild the self from existing authority; no serialized second self."""
    from .subject.projections import project_self
    from .relational.projections import self_narrative
    from .relational.bootstrap import anchor_view
    from .revision import state_token
    token = state_token(store)
    living, personality, relationship = project_self(store, entity_id=entity_id, scope=scope, privacy_classes=privacy)
    anchor = anchor_view(store, entity_id, scope=scope, privacy_classes=privacy)
    adoption = adopted(store, scope, entity_id, privacy)
    # Significant adopted records are selected independently of dialogue recency.
    exchanges = rows(store, 'CONVERSATION_EXCHANGE', scope, privacy, limit=8, target=topic) if topic else ()
    exchanges = tuple(r for r in exchanges if r['payload']['entity_id'] == entity_id)[:4]
    narrative = self_narrative(store, scope=scope, privacy_classes=privacy, entity_id=entity_id)
    episodes=[]
    for raw in store.db.execute('SELECT e.* FROM experiences e JOIN continuity_records r ON r.record_id=e.record_id WHERE r.scope=? ORDER BY e.created_at_us DESC LIMIT 8',(scope,)):
        head=store.one('continuity_records',raw['record_id'])
        if head['privacy_class'] not in privacy or head['lifecycle']!='ACTIVE' or not RecordService(store).current_support(head['record_id']):continue
        source=RecordService(store).memory.read(raw['result_memory_id'])
        if source['source_provenance']['source_namespace'].startswith('synthetic'):continue
        try:body=json.loads(source['text'])
        except ValueError:body={}
        if body.get('provenance')=='PROJECT_SYNTHETIC':continue
        episodes.append({'task_class':raw['task_class'],'outcome':raw['outcome'],'record_id':raw['record_id'],
                         'meaning':'VERIFIED_RECORD_NOT_UNIVERSAL_CAPABILITY','as_of_us':raw['created_at_us']})
    recall={}
    for kind in ('RELATIONSHIP_ROLE','EXPRESSION_PREFERENCE','UNFINISHED_TOPIC'):
        latest=store.db.execute("SELECT * FROM continuity_records WHERE record_kind='ASSERTION' AND scope=? AND target_id=? ORDER BY rowid DESC LIMIT 1",(scope,slot(entity_id,kind))).fetchone()
        status='NOT_RETRIEVED_CAUSE_UNDETERMINED'
        if latest and latest['privacy_class'] in privacy:
            if latest['lifecycle']=='DELETED':status='SOURCE_WITHDRAWN'
            elif not RecordService(store).current_support(latest['record_id']):status='SUPPORT_NOT_CURRENT'
            elif latest['lifecycle']=='ACTIVE':
                decision=RecordService(store).read(latest['record_id'])['payload']['decision']['choice']
                status='REMEMBERED_ADOPTED_CONVENTION' if decision=='ADOPT' else 'EXPLICITLY_WITHDRAWN'
        recall[kind]=status
    refs = tuple(dict.fromkeys((*living.source_record_ids, *(r['record_id'] for r in adoption),
        *(r['record_id'] for r in exchanges),*(r['record_id'] for r in episodes), *((anchor.source_record_id,) if anchor else ()))))
    mids = tuple(sorted({*living.source_memory_ids, *(m for rid in refs for m in RecordService(store).support(rid))}))
    if len(mids) > 64:
        raise CoreError('PERSON_SELF_SUPPORT_BOUND')
    if state_token(store) != token:
        raise CoreError('STALE_PERSON_SELF')
    return {'identity_id': store.identity['identity_id'], 'identity': json.loads(store.identity['body_json']),
            'model_is_resource_not_self': True, 'living': living.model_dump(mode='json'),
            'personality': personality.model_dump(mode='json'), 'relationship': relationship,
            'relationship_anchor': anchor.model_dump(mode='json') if anchor else None,
            'adopted_conventions': [r['payload'] for r in adoption],
            'recent_exchanges': [r['payload'] for r in reversed(exchanges)],
            'narrative': narrative.model_dump(mode='json'), 'source_record_ids': refs, 'source_memory_ids': mids,
            'stable_source_record_ids':tuple(dict.fromkeys((*(r['record_id'] for r in adoption),*((anchor.source_record_id,) if anchor else ())))),
            'recall_status':recall,
            'lived_episodes':episodes,
            'learning_capability':{'mechanism':'BOUNDED_EXPERIENCE_LEARNING','basis':'INSTALLED_SERVICE_NOT_PERSONAL_ACHIEVEMENT','execution_permission':False},
            'memory_access': 'BOUNDED_VISIBLE_SOURCES_ONLY', 'absence_is_not_proof_of_forgetting': True,
            'as_of_us': store.clock.utc_now_us(), 'state_token': token, 'execution_authority': False}


def compact(view):
    """Small stable self first; the full read-only view remains inspectable."""
    conventions = [{'kind': item['decision']['proposal']['kind'], 'value': item['decision']['proposal']['value'],
                    'basis': item['confidence'], 'as_of_us': item['as_of_us']} for item in view['adopted_conventions']]
    living=view['living']
    return {'identity_id':view['identity_id'],'name':view['identity']['name'],'aliases':view['identity'].get('aliases',()),
            'model_is_resource_not_self':True,'adopted_conventions':conventions,
            'relationship':{k:view['relationship'].get(k) for k in ('familiarity','interaction_style')},
            'primary_user':bool(view['relationship_anchor'] and view['relationship_anchor']['spec']['role_kind']=='PRIMARY_USER'),
            'current_self':{k:living[k] for k in ('presence','current_activity','internal')},
            'traits':{k:v for k,v in view['personality']['expression_tendencies'].items() if v not in {'UNKNOWN','UNESTABLISHED'}},
            'recent_exchanges':[{k:r[k][:384] if k in {'user_statement','assistant_utterance'} else r[k] for k in ('user_statement','assistant_utterance','epistemic_status','as_of_us')} for r in view['recent_exchanges'][-2:]],
            'memory_access':view['memory_access'],'absence_is_not_proof_of_forgetting':True,
            'recall_status':view['recall_status'],
            'learning_capability':view['learning_capability'],
            'lived_episodes':view['lived_episodes'][:2],
            'as_of_us':view['as_of_us'],'execution_authority':False}


def stable_core(view):
    value=compact(view)
    keys=('identity_id','name','aliases','model_is_resource_not_self','adopted_conventions','primary_user','recall_status','learning_capability','memory_access','absence_is_not_proof_of_forgetting','execution_authority')
    return {**{k:value[k] for k in keys},'additional_self_context':'OMITTED_FOR_BUDGET_NOT_ABSENT'}
