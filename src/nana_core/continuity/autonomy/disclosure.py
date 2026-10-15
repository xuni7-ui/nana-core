"""Semantic disclosure/claim eligibility, within the existing subject cycle."""
import json
from ...contracts import CoreError
from ..memory import MemoryService
from ..records import RecordService
from .contracts import DisclosureDecision,SocialExpectationSpec

def expectation(store,*,scope,entity_id,topic,privacy_classes):
    rows=store.db.execute("SELECT memory_id FROM memories WHERE scope=? AND entity_id=? AND predicate_key LIKE 'social.expectation.%' AND lifecycle='ACTIVE' AND assessment IN ('CURRENT','UNASSESSED') ORDER BY created_at_us DESC,rowid DESC LIMIT 64",(scope,entity_id)).fetchall()
    found=[];memory=MemoryService(store)
    for r in rows:
        header=store.one('memories',r['memory_id'])
        if header['privacy_class'] not in privacy_classes:continue
        item=memory.read(r['memory_id'])
        if item['authority']!='DIRECT' or item['epistemic_kind'] not in {'STATEMENT','OBSERVATION'}:continue
        try:spec=SocialExpectationSpec.model_validate_json(item['text'])
        except ValueError:continue
        if spec.topic==topic:found.append((r['memory_id'],spec))
    if store.schema_target>=9 and privacy_classes:
        records=RecordService(store);marks=','.join('?' for _ in privacy_classes)
        for raw in store.db.execute("SELECT e.* FROM relationship_events e JOIN continuity_records r ON r.record_id=e.record_id WHERE e.to_entity_id=? AND r.scope=? AND r.privacy_class IN ("+marks+") AND r.lifecycle='ACTIVE' AND e.relation_kind IN ('BOUNDARY','NORM') ORDER BY e.occurred_at_us DESC,e.rowid DESC LIMIT 64",(entity_id,scope,*privacy_classes)):
            r=dict(raw)
            if not records.current_support(r['record_id']) or r['relation_effect']=='WITHDRAWN':continue
            if store.db.execute("SELECT 1 FROM relationship_events WHERE related_event_id=? AND relation_effect IN ('WITHDRAWN','SUPERSEDES') LIMIT 1",(r['relationship_event_id'],)).fetchone():continue
            body=records.read(r['record_id'])['payload'].get('details',{})
            if not body.get('social_expectation'):continue
            try:spec=SocialExpectationSpec.model_validate_json(json.dumps(body['social_expectation']))
            except ValueError:continue
            if spec.topic==topic:
                for mid in records.support(r['record_id']):found.append((mid,spec))
    return tuple(found)

def action_phase(store,action_id):
    row=store.one('actions',action_id)
    if not row:raise CoreError('DISCLOSURE_ACTION_MISSING')
    if row['state']=='SUCCEEDED':
        event=json.loads(row['body_json']).get('verification_event_id')
        if not event or store.event(event)['kind']!='action.verified':raise CoreError('DISCLOSURE_EFFECT_UNVERIFIED')
        return 'VERIFIED_EFFECT',(event,)
    if row['state']=='BLOCKED':return 'ACTION_BLOCKED',()
    if row['state'] in {'UNKNOWN','DISPATCHING'}:return 'UNKNOWN',()
    if row['state'] in {'PENDING_VERIFY','FAILED_EFFECT','NOT_APPLIED'}:return 'ATTEMPTED',()
    return 'PLANNED',()

def decide_disclosure(store,event,*,privacy_classes,relation=None):
    request=event.disclosure_request
    if request is None:return None
    phase,events='PLANNED',()
    records=[]
    if request.intention_id:
        i=store.one('subject_intentions',request.intention_id)
        if not i or i['scope']!=event.scope:raise CoreError('DISCLOSURE_SCOPE_DENIED')
        r=store.one('continuity_records',i['record_id'])
        if r['privacy_class'] not in privacy_classes:raise CoreError('DISCLOSURE_PRIVACY_DENIED')
        RecordService(store).read(i['record_id']);records.append(i['record_id'])
        if i['state']=='MANAGER_BLOCKED':phase='MANAGER_BLOCKED'
    if request.action_id:
        # Only actions linked by governed realization can enter a subject scope.
        link=store.db.execute("SELECT * FROM events WHERE kind='governance.action_linked' AND json_extract(data_json,'$.data.target_id')=? ORDER BY seq DESC LIMIT 1",(request.action_id,)).fetchone()
        if not link or json.loads(link['data_json'])['data']['scope']!=event.scope:raise CoreError('DISCLOSURE_ACTION_SCOPE_DENIED')
        phase,events=action_phase(store,request.action_id)
    facts=expectation(store,scope=event.scope,entity_id=event.entity_id,topic=request.topic,privacy_classes=privacy_classes)
    spec=facts[0][1] if facts else None
    now=store.clock.utc_now_us()
    mode='DISCLOSE_AFTER' if phase!='PLANNED' else 'DISCLOSE_BEFORE'
    if spec:
        if spec.expectation=='EXPLICITLY_FORBIDDEN':mode='DECLINE_TO_DISCLOSE'
        elif spec.timing=='DEFER_UNTIL' and (spec.reveal_at_us is None or now<spec.reveal_at_us):mode='WITHHOLD_UNTIL_REVEAL'
        elif spec.timing=='ON_REQUEST':mode='DISCLOSE_WHEN_ASKED' if not request.asked else 'DISCLOSE_AFTER' if phase!='PLANNED' else 'DISCLOSE_BEFORE'
        elif spec.timing=='AFTER' and phase=='PLANNED':mode='STAY_SILENT'
    if not request.asked and event.observed_availability=='BUSY':mode='STAY_SILENT'
    if spec and spec.expectation=='CONTEXT_SENSITIVE' and relation and relation.familiarity.assessment!='FAMILIAR' and mode=='DISCLOSE_BEFORE':
        mode='DECLINE_TO_DISCLOSE' if request.asked else 'DISCLOSE_WHEN_ASKED'
    return DisclosureDecision(mode=mode,phase=phase,topic=request.topic,source_memory_ids=tuple(x[0] for x in facts),
        source_record_ids=tuple(records),source_event_ids=events,reveal_at_us=spec.reveal_at_us if spec else None,
        reason='Choose disclosure timing without inventing effects or creating authority')

def eligible_assertion(store,memory_id,asserted_value,*,scope,privacy_classes):
    if type(asserted_value) is not bool:raise CoreError('SEMANTIC_ASSERTION_INVALID')
    head=store.one('memories',memory_id)
    if not head or head['scope']!=scope or head['privacy_class'] not in privacy_classes:raise CoreError('CLAIM_SCOPE_DENIED')
    memory=MemoryService(store);item=memory.read(memory_id);source=memory.evidence(item['source_evidence_id'])
    body=json.loads(item['text'])
    if source['source_kind']!='SYSTEM_VERIFICATION' or item['epistemic_kind']!='OBSERVATION' or type(body.get('value')) is not bool:
        raise CoreError('CLAIM_NOT_KNOWN')
    if body['value'] is not asserted_value:raise CoreError('KNOWING_FALSEHOOD_BLOCKED')
    return {'memory_id':memory_id,'asserted_value':asserted_value,'source_evidence_id':item['source_evidence_id']}
