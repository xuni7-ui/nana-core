"""Recoverable learning stages with independent evaluation and held-out transfer.

Uses existing jobs, experiences, lessons, records and the same privacy graph.
No model response or summary counts as a successful trial.
"""
import json
from typing import Literal,Any,Protocol
from pydantic import Field,model_validator
from ...contracts import DTO,CoreError
from ...storage import canonical,digest,uid
from ..records import RecordService
from ..learning import ExperienceService
from .world import ComputeArgs,transform,bounded_data

STAGES=('OBSERVE','VALUE','HYPOTHESIZE','BASELINE','PRACTICE','EVALUATE','TRANSFER','CONSOLIDATE','MONITOR')
class LearningCase(DTO):
    case_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    context: str = Field(min_length=1,max_length=96)
    data: Any
    expected: Any
class LearningSpec(DTO):
    learning_key: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,31}\.[a-z][a-z0-9._-]{0,95}$')
    domain: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    baseline_method: str
    hypotheses: tuple[str,...] = Field(min_length=1,max_length=8)
    practice: tuple[LearningCase,...] = Field(min_length=1,max_length=8)
    evaluation: tuple[LearningCase,...] = Field(min_length=1,max_length=8)
    transfer: tuple[LearningCase,...] = Field(min_length=1,max_length=8)
    estimated_cost_micro: int = Field(default=0,ge=0,le=10000)
    @model_validator(mode='after')
    def distinct_splits(self):
        cases=(*self.practice,*self.evaluation,*self.transfer)
        if len({c.case_id for c in cases})!=len(cases):raise ValueError('independent case IDs required')
        splits=[{digest(c.data) for c in group} for group in (self.practice,self.evaluation,self.transfer)]
        if any(splits[a]&splits[b] for a,b in ((0,1),(0,2),(1,2))):raise ValueError('held-out inputs required')
        if {c.context for c in self.transfer}&{c.context for c in (*self.practice,*self.evaluation)}:raise ValueError('transfer needs new context')
        for c in cases:bounded_data(c.data);bounded_data(c.expected)
        for method in (self.baseline_method,*self.hypotheses):ComputeArgs(method=method)
        return self

class MethodStrategyRule(DTO):
    kind: Literal['METHOD_SELECTION'] = 'METHOD_SELECTION'
    scope: str
    method: str
    trial_record_id: str
    grants_authority: Literal[False] = False

class LearningProposerPort(Protocol):
    def propose_method(self,spec:LearningSpec) -> str: ...
class FixtureLearningProposer:
    def propose_method(self,spec):return spec.hypotheses[0]

class IndependentEvaluator:
    """Application-owned oracle and real candidate computation, not candidate prose."""
    def evaluate(self,method,cases):
        rows=[]
        for c in cases:
            actual=transform(method,c.data)
            rows.append({'case_id':c.case_id,'context':c.context,'input_digest':digest(c.data),'actual':actual,'expected_digest':digest(c.expected),'passed':digest(actual)==digest(c.expected)})
        return {'checked':len(rows),'passed':sum(r['passed'] for r in rows),'cases':rows,'all_passed':all(r['passed'] for r in rows)}

class LearningService:
    def __init__(self,store,authority,specs,*,privacy_classes,scopes,proposer=None,evaluator=None,max_pending=4,cost_ceiling_micro=10000):
        if store.schema_target<12:raise CoreError('OPEN_AGENCY_SCHEMA_REQUIRED')
        self.store,self.authority=store,authority;self.records=RecordService(store)
        self.specs={s.learning_key:LearningSpec.model_validate_json(s.model_dump_json()) for s in specs}
        if len(self.specs)>16 or not 1<=max_pending<=8:raise CoreError('LEARNING_POLICY_BOUND')
        self.proposer=proposer or FixtureLearningProposer();self.evaluator=evaluator or IndependentEvaluator()
        self.scopes=tuple(scopes)
        if not self.scopes:raise CoreError('LEARNING_SCOPE_REQUIRED')
        self.privacy=tuple(privacy_classes);self.max_pending=max_pending;self.ceiling=cost_ceiling_micro
    def after_cycle(self,runtime,cycle,event):
        if event.scope not in self.scopes:raise CoreError('LEARNING_SCOPE_DENIED')
        if not cycle.evaluation or cycle.evaluation.normative!='ENDORSED':return None
        spec=self.specs.get(cycle.proposed_program_id)
        experience=None
        if cycle.intention.kind=='REFLECTION' and event.reflection_experience_id:
            experience=self.store.one('experiences',event.reflection_experience_id)
            if experience:
                spec=next((s for s in self.specs.values() if s.domain==experience['task_class']),None)
        if not spec:return None
        key=digest([cycle.cycle_id,spec.learning_key,event.reflection_experience_id])
        old=self.store.db.execute("SELECT * FROM jobs WHERE occurrence_key=?",('learning:'+key,)).fetchone()
        if old:return old['job_id']
        # One work item per supported learning problem; a wake/replay cannot
        # recreate completed work or indefinitely train on its own outputs.
        previous=self.store.db.execute("SELECT j.* FROM jobs j JOIN continuity_records r ON r.record_id=j.record_id WHERE j.work_kind='LEARNING' AND r.target_id=? AND r.scope=? AND r.lifecycle='ACTIVE' LIMIT 1",(spec.learning_key,event.scope)).fetchone()
        if previous:
            i=self.store.one('subject_intentions',cycle.intention_id)
            if i and i['state']=='PENDING':
                with self.store.transaction('open.learning_already_selected',{'work_id':previous['job_id']}) as tx:tx.update('subject_intentions',i['intention_id'],state='COMPLETED',revision=i['revision']+1)
            return previous['job_id']
        if self.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LEARNING' AND state IN ('WAITING','RUNNING','UNKNOWN')").fetchone()[0]>=self.max_pending:return None
        parents=(cycle.record_id,*((experience['record_id'],) if experience else ()))
        now=self.store.clock.utc_now_us();wid=uid()
        with self.store.transaction('open.learning_selected',{'work_id':wid,'cycle_id':cycle.cycle_id}) as tx:
            rid=self.records.create(tx,kind='OPEN_LEARNING',scope=event.scope,payload={'stage':'OBSERVE','spec':spec.model_dump(mode='json'),'results':{},'cause':'VERIFIED_FAILURE' if experience and experience['outcome']=='FAILURE' else 'SOURCED_INTEREST_OR_GAP','selected_method':None,'trial_record_id':None,'lesson_id':None},records=parents,target_id=spec.learning_key)
            tx.put('jobs',{'job_id':wid,'occurrence_key':'learning:'+key,'due_at_us':now,'state':'WAITING','body_json':'{}','work_kind':'LEARNING','record_id':rid,'revision':1,'cursor':0,'owner_epoch':None,'updated_at_us':now})
            i=self.store.one('subject_intentions',cycle.intention_id)
            if i and i['state']=='PENDING':tx.update('subject_intentions',i['intention_id'],state='COMPLETED',revision=i['revision']+1)
            if cycle.goal_candidate_id:tx.update('subject_goal_candidates',cycle.goal_candidate_id,state='ADOPTED')
        return wid

    def next_job(self):
        scopes=','.join('?' for _ in self.scopes);privacy=','.join('?' for _ in self.privacy)
        return self.store.db.execute(f"SELECT j.* FROM jobs j JOIN continuity_records r ON r.record_id=j.record_id WHERE r.scope IN ({scopes}) AND r.privacy_class IN ({privacy}) AND j.work_kind='LEARNING' AND j.state='WAITING' AND j.due_at_us<=? ORDER BY j.due_at_us LIMIT 1",(*self.scopes,*self.privacy,self.store.clock.utc_now_us())).fetchone()
    def slice(self):
        job=self.next_job()
        if not job:return None
        rid=job['record_id'];head=self.store.one('continuity_records',rid)
        if not self.records.current_support(rid) or head['lifecycle']!='ACTIVE':return self._terminal(job,'CANCELLED','SOURCE_RETIRED')
        body=self.records.read(rid)['payload'];spec=LearningSpec.model_validate_json(canonical(body['spec']))
        if spec.learning_key not in self.specs or self.specs[spec.learning_key]!=spec:return self._terminal(job,'BLOCKED','LEARNING_POLICY_CHANGED')
        stage=STAGES[job['cursor']];new=json.loads(canonical(body));next_cursor=job['cursor']+1
        # Computation/validation happens BEFORE advancing cursor. An exception,
        # timeout or killed process leaves this exact stage pending on reopen.
        if stage=='VALUE' and spec.estimated_cost_micro>self.ceiling:return self._terminal(job,'BLOCKED','LEARNING_COST_CEILING')
        if stage=='HYPOTHESIZE':
            method=self.proposer.propose_method(spec)
            if method not in spec.hypotheses:raise CoreError('LEARNING_HYPOTHESIS_REJECTED')
            new['selected_method']=method
            parent=getattr(self.proposer,'last_record_id',None)
            if parent:
                record=self.records.read(parent)
                if record['record_kind']!='COGNITION_PROPOSAL' or record['scope']!=head['scope'] or record['privacy_class'] not in self.privacy or not self.records.current_support(parent) or record['payload']['reply']['proposal']['method']!=method:raise CoreError('LEARNING_COGNITION_SOURCE_MISMATCH')
                new['hypothesis_source']=parent
        if stage in {'BASELINE','PRACTICE','EVALUATE','TRANSFER'}:
            method=spec.baseline_method if stage=='BASELINE' else body['selected_method']
            cases=spec.evaluation if stage in {'BASELINE','EVALUATE'} else spec.practice if stage=='PRACTICE' else spec.transfer
            new['results'][stage]=self.evaluator.evaluate(method,cases)
            result=new['results'][stage]
            if result['checked']!=len(cases) or len(result['cases'])!=len(cases):raise CoreError('LEARNING_EVALUATION_INCOMPLETE')
            for case,row in zip(cases,result['cases']):
                if row['case_id']!=case.case_id or row['input_digest']!=digest(case.data) or row['expected_digest']!=digest(case.expected) or row['passed']!=(digest(row['actual'])==digest(case.expected)):raise CoreError('LEARNING_EVALUATION_INVALID')
            if result['passed']!=sum(x['passed'] for x in result['cases']) or result['all_passed']!=all(x['passed'] for x in result['cases']):raise CoreError('LEARNING_EVALUATION_INVALID')
        if stage=='CONSOLIDATE':
            results=body['results']
            if not results['EVALUATE']['all_passed'] or not results['TRANSFER']['all_passed'] or results['EVALUATE']['passed']<=results['BASELINE']['passed']:return self._terminal(job,'BLOCKED','LEARNING_NOT_TRANSFERRED_OR_NO_IMPROVEMENT')
            exp=None
            for parent in self.store.db.execute("SELECT parent_id FROM record_dependencies WHERE record_id=? AND parent_kind='RECORD'",(rid,)):
                row=self.store.db.execute('SELECT experience_id FROM experiences WHERE record_id=?',(parent[0],)).fetchone()
                if row:exp=row[0]
            # The learning test itself is an independently verified outcome. The
            # original goal failure remains distinct, not overwritten by success.
            memory=self.records.memory;now=head['created_at_us'];text=canonical({'data':results['TRANSFER']})
            from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
            eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.learning-transfer',source_reference=job['job_id'],source_kind='SYSTEM_VERIFICATION'),text=text,privacy_class=head['privacy_class'],observed_time_us=now))
            existing=self.store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=? AND lifecycle=\'ACTIVE\' LIMIT 1',(eid,)).fetchone()
            mid=existing[0] if existing else memory.add(MemoryCandidate(entity_id=self.store.identity['identity_id'],scope=head['scope'],memory_type=MemoryType.PROCEDURAL,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,derived_from=self.records.support(rid),confidence=1.))
            service=ExperienceService(self.store,self.authority);old=self.store.db.execute('SELECT experience_id FROM experiences WHERE result_memory_id=?',(mid,)).fetchone()
            if old:exp=old[0]
            else:
                check=service.verify_structured_result(mid,digest(results['TRANSFER']),self.authority)
                from ..learning import ExperienceInput
                exp=service.record(ExperienceInput(context_memory_ids=self.records.support(rid)[:32],scope=head['scope'],task_class=spec.domain,decision='Checked transfer, not a self-report',result_memory_id=mid,verification_memory_id=check))
            old_lesson=self.store.db.execute('SELECT lesson_id FROM lessons WHERE experience_id=?',(exp,)).fetchone()
            if old_lesson:lesson_id=old_lesson[0]
            else:
                lesson_id=uid()
                with self.store.transaction('open.method_trial_verified',{'work_id':job['job_id']}) as tx:
                    trial=self.records.create(tx,kind='LEARNING_TRIAL',scope=head['scope'],payload={'work_id':job['job_id'],'method':body['selected_method'],'domain':spec.domain,'results':results,'origin':'INDEPENDENT_EXECUTED_TRIALS'},records=(rid,))
                    rule=MethodStrategyRule(scope=spec.domain,method=body['selected_method'],trial_record_id=trial)
                    lesson=self.records.create(tx,kind='LESSON',scope=head['scope'],payload={'rule':rule.model_dump(mode='json')},records=(trial,))
                    tx.put('lessons',{'lesson_id':lesson_id,'experience_id':exp,'record_id':lesson,'task_class':spec.domain,'revision':1,'state':'CANDIDATE','tested_rule_hash':None,'test_event_id':None})
            state=self.store.one('lessons',lesson_id)['state']
            if state=='CANDIDATE':service.test_lesson(lesson_id);state=self.store.one('lessons',lesson_id)['state']
            if state=='TESTED':service.activate(lesson_id,self.authority);state='ACTIVE'
            if state!='ACTIVE':return self._terminal(job,'BLOCKED','LESSON_REVIEW_FAILED')
            new['lesson_id']=lesson_id
        new['stage']=STAGES[min(next_cursor,len(STAGES)-1)]
        with self.store.transaction('open.learning_stage_committed',{'work_id':job['job_id'],'stage':stage}) as tx:
            current=self.store.one('jobs',job['job_id'])
            if current['revision']!=job['revision']:raise CoreError('STALE_LEARNING_WORK')
            newrid=self.records.create(tx,kind='OPEN_LEARNING',scope=head['scope'],payload=new,records=(rid,*((new['hypothesis_source'],) if new.get('hypothesis_source') else ())),supersedes=rid,target_id=spec.learning_key)
            tx.update('jobs',job['job_id'],record_id=newrid,cursor=next_cursor,state='DONE' if stage=='MONITOR' else 'WAITING',revision=job['revision']+1,updated_at_us=self.store.clock.utc_now_us())
        return {'work_id':job['job_id'],'stage':stage,'next_stage':new['stage'],'lesson_id':new.get('lesson_id')}
    def _terminal(self,job,state,reason):
        with self.store.transaction('open.learning_parked',{'work_id':job['job_id'],'reason':reason}) as tx:tx.update('jobs',job['job_id'],state=state,revision=job['revision']+1)
        return {'work_id':job['job_id'],'reason':reason}
    def resume(self,work_id,*,expected_revision,cause_memory_id,authority):
        if authority is not self.authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        job=self.store.one('jobs',work_id)
        if not job or job['work_kind']!='LEARNING' or job['state']!='UNKNOWN' or job['revision']!=expected_revision:raise CoreError('STALE_LEARNING_WORK')
        parent=self.records.read(job['record_id']);cause=self.records.memory.read(cause_memory_id)
        if parent['scope'] not in self.scopes or not self.records.current_support(job['record_id']) or cause['scope']!=parent['scope'] or cause['authority']!='DIRECT':raise CoreError('LEARNING_RECOVERY_SOURCE_REQUIRED')
        with self.store.transaction('open.learning_reconsidered',{'work_id':work_id,'cause_memory_id':cause_memory_id}) as tx:tx.update('jobs',work_id,state='WAITING',revision=job['revision']+1)
    def strategy(self,domain,scope):
        if scope not in self.scopes:raise CoreError('LEARNING_SCOPE_DENIED')
        for row in self.store.db.execute("SELECT * FROM lessons WHERE task_class=? AND state='ACTIVE' ORDER BY rowid DESC LIMIT 16",(domain,)):
            head=self.store.one('continuity_records',row['record_id'])
            if head['scope']!=scope or head['privacy_class'] not in self.privacy or head['lifecycle']!='ACTIVE' or not self.records.current_support(head['record_id']):continue
            rule=ExperienceService(self.store,self.authority)._rule(row)
            if isinstance(rule,MethodStrategyRule):return row['record_id'],rule.method
        return None
    def monitor(self,lesson_id,cases,*,authority):
        if authority is not self.authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        service=ExperienceService(self.store,self.authority);row=self.store.one('lessons',lesson_id)
        if not row or row['state']!='ACTIVE':raise CoreError('ACTIVE_LESSON_REQUIRED')
        rule=service._rule(row);result=self.evaluator.evaluate(rule.method,cases)
        if not result['all_passed']:service.suspend(lesson_id,self.authority)
        with self.store.transaction('open.learning_monitored',{'lesson_id':lesson_id,'passed':result['all_passed']}):pass
        return result
