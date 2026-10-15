"""Positive requests become subject decisions and proposals, never governance."""
import json
from ...contracts import CoreError
from ...storage import canonical
from ..records import RecordService
from ..commitments import CommitmentService,CommitmentCandidate
from .contracts import RequestDecision

def evaluate_request(event,situation,now,*,source_memory_id):
    request=event.positive_request
    if request is None:return None
    denied=situation.social_privacy and situation.social_privacy.assessment=='EXPLICITLY_FORBIDDEN'
    if denied:choice,reason='DECLINE','Decline an expectation conflicting with a current sourced boundary'
    elif situation.pending_count>=6 or situation.due_commitment_ids or request.task_class=='CONTACT' or (request.due_at_us is not None and request.due_at_us<=now):
        choice,reason='NEGOTIATE','Discuss scope/time or competing concerns before making a promise'
    else:choice,reason='ACCEPT','Propose a bounded commitment; adoption and action authority are separate'
    candidate=CommitmentCandidate(entity_id=event.entity_id,scope=event.scope,description=request.description,
        support_memory_ids=tuple(dict.fromkeys((source_memory_id,*situation.memory_ids)))[:32],due_at_us=request.due_at_us,recurrence=request.recurrence) if choice=='ACCEPT' and source_memory_id else None
    return RequestDecision(decision=choice,reason=reason,source_refs=situation.memory_ids,candidate=candidate)

class RequestCommitmentService:
    def __init__(self,store,authority):
        self.store,self.records=store,RecordService(store)
        self.commitments=CommitmentService(store,authority)

    def materialize(self,cycle_id):
        row=self.store.db.execute('SELECT * FROM subject_cycles WHERE cycle_id=?',(cycle_id,)).fetchone()
        if not row or not row['record_id'] or not self.records.current_support(row['record_id']):raise CoreError('REQUEST_DECISION_UNAVAILABLE')
        body=self.records.read(row['record_id'])['payload'].get('request_decision')
        if not body:raise CoreError('NO_COMMITMENT_REQUEST_DECISION')
        decision=RequestDecision.model_validate_json(canonical(body))
        if decision.decision!='ACCEPT' or not decision.candidate:return None
        return self.commitments.propose(decision.candidate,source_key=cycle_id)
