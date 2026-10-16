"""Explicit application materialization of a committed Subject choice.

No timer grants adoption/action, and no new restraint daemon exists. The same
SubjectLoop decides every review; existing CommitmentService owns persistence.
"""
from ...contracts import CoreError
from ...storage import canonical
from ..records import RecordService
from .contracts import VoluntaryTerms,RelationalDecision,RelationalRequest,DAY
from .deliberation import deliberate
from .projections import personality_tendencies


def review(store,event,situation,*,privacy_classes):
    if event.task_class!='relational.accommodation.review' or not event.commitment_check_id:return None
    row=store.one('commitments',event.commitment_check_id);records=RecordService(store)
    if not row or row['state'] not in {'ADOPTED','ACTIVE'} or row['scope']!=event.scope or row['entity_id']!=event.entity_id:raise CoreError('VOLUNTARY_REVIEW_TARGET_INVALID')
    body=records.read(row['record_id'])['payload']
    if not body.get('voluntary'):raise CoreError('NOT_VOLUNTARY_COMMITMENT')
    terms=VoluntaryTerms.model_validate_json(canonical(body['voluntary']))
    if store.clock.utc_now_us()<terms.review_at_us:raise CoreError('VOLUNTARY_REVIEW_NOT_DUE')
    source=store.db.execute('SELECT * FROM subject_cycles WHERE cycle_id=?',(terms.source_cycle_id,)).fetchone()
    old=records.read(source['record_id'])['payload']['relational_decision']
    req=RelationalRequest.model_validate_json(canonical(old['request']))
    context=situation.model_copy(update={'commitment_ids':tuple(c for c in situation.commitment_ids if c!=row['commitment_id'])})
    current=deliberate(store,event.model_copy(update={'relational_request':req}),context,source_record_id=row['record_id'],privacy_classes=privacy_classes)
    now=store.clock.utc_now_us();traits={f.name:f.assessment for f in personality_tendencies(store,scope=event.scope,privacy_classes=privacy_classes).facets}
    choice='END' if now>=terms.end_us or current.response.decision=='DECLINE' or not situation.social_appetite.available else 'MODIFY' if traits['self_direction_sensitivity']=='HIGH' and situation.social_appetite.state=='SEEKING' else 'CONTINUE'
    duration=None if choice=='END' else min(terms.end_us-now,DAY) if choice=='MODIFY' else terms.end_us-now
    return current.model_copy(update={'phase':'REVIEW','review_commitment_id':row['commitment_id'],'review_revision':row['revision'],'review_choice':choice,
        'accepted_duration_us':duration,'review_at_us':now+duration if duration else None})


class VoluntaryAccommodationService:
    def __init__(self,store,authority):
        from ..commitments import CommitmentService
        if store.schema_target<10:raise CoreError('RELATIONAL_SCHEMA_REQUIRED')
        self.store,self.authority,self.records=store,authority,RecordService(store)
        self.commitments=CommitmentService(store,authority)

    def materialize(self,cycle_id,authority):
        if authority is not self.authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        row=self.store.db.execute('SELECT * FROM subject_cycles WHERE cycle_id=?',(cycle_id,)).fetchone()
        if not row or not row['record_id'] or not self.records.current_support(row['record_id']):raise CoreError('RELATIONAL_DECISION_UNAVAILABLE')
        body=self.records.read(row['record_id'])['payload'];raw=body.get('relational_decision')
        if not raw:return None
        decision=RelationalDecision.model_validate_json(canonical(raw))
        if decision.phase=='REVIEW':
            if body['judgment']['stance'] not in {'AGREE','ALTERNATIVE'} or body['evaluation']['normative']!='ENDORSED':return None
            return self.commitments.review_voluntary(cycle_id,authority=authority)
        if decision.response.decision!='ACCEPT' or body['judgment']['stance']!='AGREE' or body['evaluation']['normative']!='ENDORSED':return None
        for rid in (*decision.deference.relationship_refs,*decision.deference.personality_refs):
            head=self.store.one('continuity_records',rid)
            if not head or head['lifecycle']!='ACTIVE' or not self.records.current_support(rid):raise CoreError('RELATIONAL_SOURCE_REQUIRES_REVIEW')
        # Replaying a materialized choice returns its own commitment, never a new
        # promise or a renewal of an expired temporary restraint.
        old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='commitment.request' AND source_key=?",('relational:'+cycle_id,)).fetchone()
        if old:
            import json
            cid=json.loads(old[0])['data']['commitment_id']
            state=self.commitments.get(cid)
            if state.state not in {'PROPOSED','ADOPTED'}:return cid
        start=row['created_at_us'];end=start+decision.accepted_duration_us
        terms=VoluntaryTerms(request_id=decision.request.request_id,source_cycle_id=cycle_id,behavior_domain=decision.request.behavior_domain,
            operation=decision.request.operation,accepted_scope=decision.request.scope,start_us=start,end_us=end,review_at_us=decision.review_at_us or end)
        if self.store.clock.utc_now_us()>=terms.review_at_us:raise CoreError('VOLUNTARY_CHOICE_REVIEW_REQUIRED')
        from ..commitments import CommitmentCandidate
        candidate=CommitmentCandidate(entity_id=decision.request.requesting_entity,scope=self.records.read(row['record_id'])['scope'],description='Subject-chosen bounded relational accommodation',
            support_memory_ids=self.records.support(row['record_id'])[:32],due_at_us=terms.review_at_us,voluntary=terms,decision_record_id=row['record_id'])
        cid=self.commitments.propose(candidate,source_key='relational:'+cycle_id)
        state=self.commitments.get(cid)
        if state.state=='PROPOSED':state=self.commitments.transition(cid,'ADOPTED',expected_revision=state.revision,authority=authority)
        if state.state=='ADOPTED':self.commitments.transition(cid,'ACTIVE',expected_revision=state.revision,authority=authority)
        return cid
