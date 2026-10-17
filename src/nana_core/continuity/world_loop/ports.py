"""Transport-backed adapters for existing proposer ports, not another brain."""
from ...contracts import CoreError
from ...storage import digest
from ..open_agency.contracts import PlanCandidate
from ..open_agency.code_skills import CodeCandidate

class CognitionPlannerPort:
    def __init__(self,session):self.session=session
    def plan(self,request):
        refs=self.session.records.support(request.source_record_id)
        key='planner:'+digest(request.model_dump(mode='json'))
        cid=self.session.prepare(key,'PLAN',refs[:16],role_input=request.model_dump(mode='json'))
        reply=_run(self.session,cid)
        return PlanCandidate(operator_ids=reply.proposal.plan_operator_ids,source_record_id=request.source_record_id,world_revision=request.world_revision)

class CognitionLearningProposer:
    def __init__(self,session,source_ids):self.session,self.source_ids=session,tuple(source_ids)
    def propose_method(self,spec):
        cid=self.session.prepare('hypothesis:'+digest([spec.model_dump(mode='json'),self.source_ids]),'LEARN',self.source_ids,role_input=spec.model_dump(mode='json'))
        reply=_run(self.session,cid)
        if reply.proposal.method not in spec.hypotheses:raise CoreError('LEARNING_HYPOTHESIS_REJECTED')
        return reply.proposal.method

class CognitionCodeProposer:
    def __init__(self,session,source_ids):self.session,self.source_ids=session,tuple(source_ids)
    def implement(self,spec,diagnostic=None):
        role_input={'spec':spec.model_dump(mode='json'),'diagnostic':diagnostic}
        cid=self.session.prepare('code:'+digest([role_input,self.source_ids]),'SKILL',self.source_ids,role_input=role_input)
        reply=_run(self.session,cid)
        if not reply.proposal.skill_source:raise CoreError('SKILL_PROPOSAL_INVALID')
        return CodeCandidate(source=reply.proposal.skill_source)

def _run(session,cid):
    outcome=session.execute(cid)
    if outcome['state']!='PROPOSED':raise CoreError('COGNITION_PROPOSAL_UNAVAILABLE')
    rid=outcome.get('record_id')
    if not rid:
        row=session.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL' AND target_id=?",(cid,)).fetchone();rid=row[0] if row else None
    if not rid:raise CoreError('COGNITION_PROPOSAL_UNAVAILABLE')
    return session.proposal(rid)
