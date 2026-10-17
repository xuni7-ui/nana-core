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
        cid=self.session.prepare(key,'PLAN',bounded_sources(self.session,refs),role_input=request.model_dump(mode='json'))
        reply=_run(self.session,cid)
        return PlanCandidate(source_record_ids=(self.session.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL' AND target_id=?",(cid,)).fetchone()[0],),operator_ids=reply.proposal.plan_operator_ids,source_record_id=request.source_record_id,world_revision=request.world_revision)

class CognitionLearningProposer:
    def __init__(self,session,source_ids):self.session,self.source_ids=session,tuple(source_ids)
    def propose_method(self,spec):
        cid=self.session.prepare('hypothesis:'+digest([spec.model_dump(mode='json'),self.source_ids]),'LEARN',self.source_ids,role_input=spec.model_dump(mode='json'))
        reply=_run(self.session,cid)
        if reply.proposal.method not in spec.hypotheses:raise CoreError('LEARNING_HYPOTHESIS_REJECTED')
        self.last_record_id=self.session.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL' AND target_id=?",(cid,)).fetchone()[0]
        return reply.proposal.method

class CognitionCodeProposer:
    def __init__(self,session,source_ids):self.session,self.source_ids=session,tuple(source_ids)
    def implement(self,spec,diagnostic=None):
        role_input={'spec':spec.model_dump(mode='json'),'diagnostic':diagnostic}
        cid=self.session.prepare('code:'+digest([role_input,self.source_ids]),'SKILL',self.source_ids,role_input=role_input)
        reply=_run(self.session,cid)
        if not reply.proposal.skill_source:raise CoreError('SKILL_PROPOSAL_INVALID')
        return CodeCandidate(source=reply.proposal.skill_source,source_record_ids=(self.session.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL' AND target_id=?",(cid,)).fetchone()[0],))

def _run(session,cid):
    outcome=session.execute(cid)
    if outcome['state']!='PROPOSED':raise CoreError('COGNITION_PROPOSAL_UNAVAILABLE')
    rid=outcome.get('record_id')
    if not rid:
        row=session.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='COGNITION_PROPOSAL' AND target_id=?",(cid,)).fetchone();rid=row[0] if row else None
    if not rid:raise CoreError('COGNITION_PROPOSAL_UNAVAILABLE')
    return session.proposal(rid)


def bounded_sources(session, refs):
    """Pin concise relevant evidence, not the whole transitive provenance graph.

    The role's source record remains a dependency of the request. Omitted support
    is not presented as model-visible evidence and cannot be cited by the model.
    ContextAssembler still owns privacy, contradiction completeness and budget.
    """
    ranked=[]
    for mid in refs:
        memory=session.records.memory.read(mid)
        if memory['entity_id'] not in {session.runtime.config.entity_id,session.runtime.identity_id}:continue
        text=memory['text']
        relevant='"opportunities"' in text or '"cue_kind"' in text
        ranked.append((not relevant,len(text.encode('utf-8')),mid))
    ranked.sort()
    if not ranked:raise CoreError('COGNITION_SOURCES_REQUIRED')
    return tuple(item[2] for item in ranked[:2])
