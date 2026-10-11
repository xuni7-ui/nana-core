"""Evidence-backed initiative candidates; acceptance is not execution permission.

No communication adapter or keyword trigger. Numeric need assessments are supplied
by a ModelPort/engineering fixture, not claims that risk was semantically verified.
"""
import json
from typing import Literal
from pydantic import Field
from .contracts import DTO,CoreError,CAPABILITIES
from .runtime import Runtime
from .storage import canonical,digest


class GoalCandidate(DTO):
    purpose:str=Field(min_length=1,max_length=512)
    intent:Literal['dialogue','information','reading_card','external_task']
    evidence_event_ids:tuple[str,...]=Field(min_length=1,max_length=16)
    need:float=Field(ge=0,le=1)
    importance:float=Field(ge=0,le=1)
    urgency:float=Field(ge=0,le=1)
    confidence:float=Field(ge=0,le=1)
    disturbance:float=Field(ge=0,le=1)
    user_requests_discretion:bool=False
    required_capability:str|None=None
    resource:str|None=None


class Initiative:
    def __init__(self,store,kernel):self.store,self.kernel=store,kernel
    def _evidence(self,ids):
        refs=[]
        for eid in ids:
            e=self.store.event(eid)
            if e['identity_id']!=self.store.identity['identity_id']:raise CoreError('CANDIDATE_IDENTITY_MISMATCH')
            if e['artifact_id']:self.store.artifact(e['artifact_id'])
            refs.append({'event_id':eid,'artifact_id':e['artifact_id'],'coverage':'FULL'})
        return refs
    def propose(self,proposal):
        if not isinstance(proposal,GoalCandidate):raise CoreError('STRICT_CANDIDATE_REQUIRED')
        proposal=GoalCandidate.model_validate(proposal.model_dump());refs=self._evidence(proposal.evidence_event_ids)
        if proposal.intent in {'reading_card','external_task'} and (not proposal.required_capability or not proposal.resource):
            raise CoreError('CANDIDATE_CAPABILITY_SCOPE_REQUIRED')
        key=digest([self.store.identity['identity_id'],proposal.evidence_event_ids,proposal.purpose])
        existing=self.store.one('memory_items',key)
        if existing:
            if json.loads(existing['body_json'])['proposal']!=proposal.model_dump(mode='json'):raise CoreError('CANDIDATE_KEY_COLLISION')
            return key
        body={'type':'GOAL_CANDIDATE','identity_id':self.store.identity['identity_id'],'state':'PROPOSED',
            'identity_revision':self.store.identity['revision'],'charter':json.loads(self.store.identity['body_json'])['charter'],
            'proposal':proposal.model_dump(mode='json'),'source_refs':refs,'epistemic_kind':'MODEL_INFERENCE',
            'assessment':'UNASSESSED','goal_id':None,'reason':None,'job_id':None,'due_at_us':self.store.clock.utc_now_us()+60_000_000}
        with self.store.transaction('initiative.proposed',{'candidate_id':key}) as tx:
            tx.payload_id=tx.artifact(canonical(body).encode())
            tx.put('memory_items',{'memory_id':key,'kind':'CLAIM','status':'ACTIVE','body_json':canonical(body),'created_event_id':tx.event_id})
        return key
    def candidate(self,key):
        memory=self.store.one('memory_items',key)
        if not memory:raise CoreError('CANDIDATE_NOT_FOUND')
        body=json.loads(memory['body_json'])
        if body.get('type')!='GOAL_CANDIDATE' or body['identity_id']!=self.store.identity['identity_id']:raise CoreError('CANDIDATE_IDENTITY_MISMATCH')
        return body
    def evaluate(self,key,fault=None):
        body=self.candidate(key)
        if body['state'] in {'REJECTED','ACTIVATED'}:return body
        p=GoalCandidate.model_validate_json(canonical(body['proposal']));self._evidence(p.evidence_event_ids)
        priority=.4*p.need+.3*p.importance+.3*p.urgency-.25*p.disturbance
        if p.need<.1:state,reason='REJECTED','NO_SUFFICIENT_NEED'
        elif p.intent=='external_task' and p.confidence<.85:state,reason='DEFERRED','INSUFFICIENT_EVIDENCE_FOR_EXTERNAL_DISCLOSURE'
        elif priority<.45:state,reason='DEFERRED','LOW_PRIORITY_RESPECT_NON_INTERRUPTION'
        else:
            state,reason='ACCEPTED','EVIDENCE_REFERENCED_NEED_EXCEEDS_DISTURBANCE'
            if p.required_capability:
                if p.required_capability not in CAPABILITIES:state,reason='BLOCKED','CAPABILITY_NOT_AVAILABLE'
                else:
                    try:self.kernel._grant_for(p.required_capability,p.resource)
                    except CoreError as exc:state,reason='BLOCKED',exc.code
        new={**body,'state':state,'reason':reason,'priority':priority,
            'user_preference_considered':p.user_requests_discretion,'permission_source':'operator_grant_only',
            'independent_judgement':'discretion is considered; does not fabricate permission or suppress a candidate'}
        if state in {'ACCEPTED','DEFERRED'} and not new['job_id']:
            # Existing Scheduler wake is not an autonomous goal or an external action.
            due=body.get('due_at_us',self.store.event(self.store.one('memory_items',key)['created_event_id'])['recorded_at_us']+60_000_000)
            new['due_at_us']=due
            new['job_id']=Runtime(self.store,self.kernel,None).schedule_wake('initiative:'+key,due)
            if fault:fault('after_wake_commit')
        if new!=body:
            with self.store.transaction('initiative.evaluated',{'candidate_id':key,'state':state,'reason':reason}) as tx:
                tx.update('memory_items',key,body_json=canonical(new))
        return new
    def activate_reading(self,key,observation,model):
        body=self.evaluate(key)
        if body['state']!='ACCEPTED' or body['proposal']['intent']!='reading_card':raise CoreError('CANDIDATE_NOT_EXECUTABLE')
        event=self.store.ingest(observation)
        if event not in body['proposal']['evidence_event_ids'] or observation.source_id!=body['proposal']['resource']:
            raise CoreError('CANDIDATE_EVENT_SCOPE_MISMATCH')
        # Runtime validates plan and every action separately through the ActionKernel.
        goal=Runtime(self.store,self.kernel,model).process(observation)
        new={**body,'state':'ACTIVATED','goal_id':goal}
        with self.store.transaction('initiative.activated',{'candidate_id':key,'goal_id':goal}) as tx:
            tx.update('memory_items',key,body_json=canonical(new))
        return goal
