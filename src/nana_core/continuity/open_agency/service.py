"""Persistent multi-goal transitions; all intentions still committed by C.

This component adopts eligible proposals under a finite application policy and
executes ONE C-approved step via the existing governed Kernel. It is not a loop.
"""
import json
from ...contracts import CoreError
from ...storage import canonical,digest,uid
from ..records import RecordService
from ..agency import AgencyService
from ..agency_contracts import GoalStepRef,PlanStepView
from ..autonomy.realization import GovernedRealization
from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..learning import ExperienceService,ExperienceInput
from .contracts import Objective,PlannerInput
from .planning import BoundedPlanner,validate_plan
from .world import LocalWorldRegistry

class OpenGoalPolicy:
    def __init__(self,objectives,*,max_active=8,planner=None):
        if not 1<=len(objectives)<=64 or len({o.objective_id for o in objectives})!=len(objectives) or not 1<=max_active<=16:raise CoreError('OPEN_GOAL_POLICY_INVALID')
        self.objectives={o.objective_id:Objective.model_validate_json(o.model_dump_json()) for o in objectives}
        self.max_active=max_active;self.planner=planner or BoundedPlanner()
    def get(self,key):
        if key not in self.objectives:raise CoreError('OFFLINE_PROGRAM_NOT_REVIEWED')
        return self.objectives[key]


def open_step_view(store,reference,*,scope,privacy_classes):
    records=RecordService(store);work=store.one('jobs',reference.work_id)
    if not work or work['work_kind']!='GOAL' or work['revision']!=reference.revision or work['cursor']!=reference.cursor or work['state'] not in {'WAITING','RUNNING','UNKNOWN'}:raise CoreError('STALE_GOAL_STEP')
    head=store.one('continuity_records',work['record_id'])
    if not head or head['scope']!=scope or head['privacy_class'] not in privacy_classes or not records.current_support(head['record_id']):raise CoreError('GOAL_SOURCE_UNAVAILABLE')
    plan=records.read(head['record_id'])['payload'];goal=store.one('goals',plan['goal_id'])
    if not goal or goal['state'] not in {'ACTIVE','BLOCKED'} or reference.cursor>=len(plan['steps']):raise CoreError('GOAL_NOT_ACTIVE')
    from .contracts import Operator
    op=Operator.model_validate_json(canonical(plan['steps'][reference.cursor]))
    return PlanStepView(reference=reference,goal_id=goal['goal_id'],plan_id=plan['plan_id'],target=op.target(),record_id=head['record_id'],source_memory_ids=records.support(head['record_id']),task_class=plan['task_class'])

class OpenAgencyService(AgencyService):
    def __init__(self,store,subject,authority,policy,port,*,step_interval_us=1000000):
        if store.schema_target<12 or type(policy) is not OpenGoalPolicy or subject.store is not store:raise CoreError('OPEN_AGENCY_SCHEMA_REQUIRED')
        self.store,self.subject,self._authority,self.policy=store,subject,authority,policy
        self.records=RecordService(store);self.registry=LocalWorldRegistry()
        self.realization=GovernedRealization(store,port,authority,registry=self.registry);self.interval=step_interval_us
        self.learning=None;self.delivery=None

    def _plan(self,obj,rid):
        # A reviewed learned strategy changes method choice, not capabilities/Grant.
        strategy_ids=[]
        if self.learning:
            strategy=self.learning.strategy(obj.task_domain,obj.scope)
            if strategy:
                obj=obj.model_copy(update={'operators':tuple(op.model_copy(update={'args':{**op.args,'method':strategy[1]}}) if op.strategy_selectable and op.capability=='world.compute' else op for op in obj.operators)})
                strategy_ids.append(strategy[0])
        world_revision=digest(obj.model_dump(mode='json'))
        request=PlannerInput(objective=obj,source_record_id=rid,world_revision=world_revision)
        proposal=self.policy.planner.plan(request)
        steps=validate_plan(request,proposal,self.registry)
        if not steps:raise CoreError('GOAL_ALREADY_SATISFIED')
        return obj,steps,strategy_ids

    def adopt(self,cycle):
        if not cycle.goal_candidate_id or not cycle.proposed_program_id or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED':return None
        old=self.store.db.execute('SELECT goal_id FROM goals WHERE goal_key=?',(cycle.goal_candidate_id,)).fetchone()
        if old:return old[0]
        candidate=self.store.one('subject_goal_candidates',cycle.goal_candidate_id)
        obj=self.policy.get(cycle.proposed_program_id);source=self.store.one('subject_events',cycle.event_id)
        if not candidate or candidate['state']!='PROPOSED' or source['scope']!=obj.scope or obj.motivation_source not in {m.source for m in cycle.motivations}:raise CoreError('GOAL_ADOPTION_SOURCE_MISMATCH')
        if not self.subject.visible(candidate['record_id'],obj.scope):raise CoreError('GOAL_SOURCE_UNAVAILABLE')
        from ..subject.opportunities import cues_from
        cues=cues_from(self.store,self.records.support(candidate['record_id']),scope=obj.scope,privacy_classes=self.subject.privacy_classes)
        if not any(c.program_id==obj.objective_id for _,c in cues):raise CoreError('GOAL_PROGRAM_SOURCE_REQUIRED')
        if self.store.db.execute("SELECT count(*) FROM goals WHERE state IN ('ACTIVE','BLOCKED','SUSPENDED')").fetchone()[0]>=self.policy.max_active:return None
        for dep in (*obj.depends_on,*((obj.parent_id,) if obj.parent_id else ())):
            g=self.store.one('goals',dep)
            if not g:raise CoreError('GOAL_DEPENDENCY_UNKNOWN')
            parent=self.store.one('continuity_records',json.loads(g['body_json'])['record_id'])
            if parent['scope']!=obj.scope:raise CoreError('CROSS_SCOPE_GOAL_DEPENDENCY')
        obj,steps,strategies=self._plan(obj,candidate['record_id'])
        gid,pid,wid=uid(),uid(),uid();now=self.store.clock.utc_now_us()
        with self.store.transaction('open.goal_adopted',{'goal_id':gid,'candidate_id':cycle.goal_candidate_id}) as tx:
            rid=self.records.create(tx,kind='ADOPTED_GOAL',scope=obj.scope,payload={'purpose':cycle.intention.purpose,'objective':obj.model_dump(mode='json'),'candidate_id':cycle.goal_candidate_id},records=(candidate['record_id'],))
            plan=self._plan_record(tx,gid,pid,obj,steps,rid,strategies)
            tx.put('goals',{'goal_id':gid,'goal_key':cycle.goal_candidate_id,'event_id':self.store.one('continuity_records',cycle.record_id)['event_id'],'template':obj.task_domain,'state':'ACTIVE','version':1,
                'body_json':canonical({'record_id':rid,'plan_record_id':plan,'work_id':wid}),'priority':obj.priority,'deadline_us':obj.deadline_us,'parent_id':obj.parent_id,'depends_json':canonical(obj.depends_on),'last_served_us':0})
            tx.put('plans',{'plan_id':pid,'goal_id':gid,'body_json':canonical({'record_id':plan})})
            tx.put('jobs',{'job_id':wid,'occurrence_key':'goal:'+gid,'due_at_us':now,'state':'WAITING','body_json':canonical({'goal_id':gid,'plan_id':pid}),'work_kind':'GOAL','record_id':plan,'revision':1,'cursor':0,'owner_epoch':None,'updated_at_us':now})
            tx.update('subject_goal_candidates',cycle.goal_candidate_id,state='ADOPTED');self._complete(tx,cycle.intention_id)
        return gid

    def _plan_record(self,tx,gid,pid,obj,steps,parent,strategies=(),supersedes=None):
        return self.records.create(tx,kind='AUTONOMOUS_PLAN',scope=obj.scope,payload={'format':'OPEN_PLAN_V1','goal_id':gid,'plan_id':pid,'program':{'program_id':obj.objective_id},'objective':obj.model_dump(mode='json'),
            'steps':[s.model_dump(mode='json') for s in steps],'task_class':obj.task_domain,'strategy_ids':strategies,'policy_digest':digest(self.policy.get(obj.objective_id).model_dump(mode='json'))},records=(parent,*strategies),supersedes=supersedes)
    def _complete(self,tx,iid):
        i=self.store.one('subject_intentions',iid) if iid else None
        if i and i['state']=='PENDING':tx.update('subject_intentions',iid,state='COMPLETED',revision=i['revision']+1)

    def next_reference(self):
        now=self.store.clock.utc_now_us()
        rows=self.store.db.execute("SELECT j.*,g.depends_json,g.deadline_us,g.priority,g.last_served_us FROM jobs j JOIN goals g ON json_extract(j.body_json,'$.goal_id')=g.goal_id WHERE j.work_kind='GOAL' AND j.state IN ('WAITING','RUNNING','UNKNOWN') AND g.state IN ('ACTIVE','BLOCKED') AND j.due_at_us<=? ORDER BY CASE WHEN g.deadline_us<=? THEN 0 ELSE 1 END,g.priority DESC,g.last_served_us,j.due_at_us LIMIT 32",(now,now)).fetchall()
        # At most one committed step at a time; round-robin within priority and
        # bounded aging means low-priority goals are not silently lost.
        for row in rows:
            deps=[self.store.one('goals',x) for x in json.loads(row['depends_json'])]
            if any(d is None or d['state']!='COMPLETED' for d in deps):continue
            return GoalStepRef(work_id=row['job_id'],revision=row['revision'],cursor=row['cursor'])
        return None

    def advance(self,reference,cycle):
        work=self.store.one('jobs',reference.work_id)
        if not work or work['revision']!=reference.revision:return None
        head=self.store.one('continuity_records',work['record_id'])
        view=open_step_view(self.store,reference,scope=head['scope'],privacy_classes=self.subject.privacy_classes)
        plan=self.records.read(work['record_id'])['payload']
        if digest(self.policy.get(plan['program']['program_id']).model_dump(mode='json'))!=plan['policy_digest']:return self._park(work,view,'POLICY_CHANGED')
        source=self.store.one('subject_events',cycle.event_id)
        if self.records.read(source['record_id'])['payload']['input'].get('goal_step')!=reference.model_dump(mode='json'):raise CoreError('GOAL_STEP_CYCLE_MISMATCH')
        if not cycle.intention_id or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED' or cycle.realization_target!=view.target:return self._park(work,view,'SUBJECT_DEFERRED')
        op=plan['steps'][reference.cursor];args=dict(op['args'])
        if args.get('input_from'):
            prior=self._outputs(view.goal_id)
            match=next((o for o in reversed(prior) if o.get('operator_id')==args['input_from']),None)
            if not match:return self._park(work,view,'VERIFIED_INPUT_REQUIRED')
            args['data']=json.loads(self.records.memory.read(match['memory_id'])['text'])['data']
        if op['capability']=='world.contact':
            if not self.delivery:return self._park(work,view,'DELIVERY_ADMISSION_REQUIRED')
            admission=self.delivery.assess(cycle,view.target.resource)
            if admission['result']!='ELIGIBLE':
                # Preserve original social desire/intention and defer this step;
                # a new observed availability/window is needed before retry.
                return self._park(work,view,'DELIVERY_'+admission['result'])
            args['admission_id']=admission['record_id']
        action=self.store.db.execute('SELECT action_id FROM actions WHERE effect_slot=?',('subject:'+cycle.intention_id,)).fetchone()
        try:
            if action:aid=action[0]
            else:
                outcome,aid=self.realization.propose(cycle.intention_id,expected_revision=1,args=args)
                if not aid:return self._park(work,view,'MANAGER_'+outcome.result)
                with self.store.transaction('open.action_bound',{'goal_id':view.goal_id,'work_id':work['job_id']}) as tx:tx.update('actions',aid,goal_id=view.goal_id,plan_id=view.plan_id)
            state=self.realization.dispatch(cycle.intention_id,aid,expected_revision=1)
        except CoreError as exc:return self._park(work,view,'REALIZATION_'+exc.code)
        if state!='SUCCEEDED':return self._park(work,view,'EFFECT_'+state,unknown=state=='UNKNOWN')
        action=self.store.one('actions',aid);memory=self.records.memory
        # Evidence capture is idempotent on action; no external effect is retried
        # if a crash happens between this observation and progress commit.
        result=self.realization.kernel.payload(action,'result_json');now=self.store.clock.utc_now_us()
        existing=self.store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON m.source_evidence_id=e.evidence_id WHERE e.source_namespace='synthetic.open-action' AND e.source_reference=? AND m.lifecycle='ACTIVE' LIMIT 1",(aid,)).fetchone()
        if existing:mid=existing[0]
        else:
            eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.open-action',source_reference=aid,source_kind='SYSTEM_VERIFICATION'),text=result,privacy_class=head['privacy_class'],observed_time_us=now))
            mid=memory.add(MemoryCandidate(entity_id=source['entity_id'],scope=head['scope'],memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=result,derived_from=view.source_memory_ids,confidence=1.))
        quality=True;exp=None
        if op.get('expected_digest'):
            quality=digest(json.loads(result).get('data'))==op['expected_digest']
            service=ExperienceService(self.store,self._authority)
            prior=self.store.db.execute('SELECT experience_id FROM experiences WHERE result_memory_id=?',(mid,)).fetchone()
            if prior:exp=prior[0]
            else:
                checked=service.verify_structured_result(mid,op['expected_digest'],self._authority)
                exp=service.record(ExperienceInput(context_memory_ids=view.source_memory_ids[:32],scope=head['scope'],task_class=plan['task_class'],decision=cycle.judgment.reason,result_memory_id=mid,verification_memory_id=checked))
        final=reference.cursor+1==len(plan['steps']);data={'goal_id':view.goal_id,'work_id':work['job_id'],'operator_id':op['operator_id'],'cursor':reference.cursor,'action_id':aid,'memory_id':mid,'experience_id':exp,'quality':quality}
        with self.store.transaction('living.goal_step_completed',data,source_namespace='living.goal-step',source_key=work['job_id']+':'+str(reference.revision)+':'+str(reference.cursor)) as tx:
            fresh=self.store.one('jobs',work['job_id'])
            if fresh['revision']!=reference.revision:raise CoreError('STALE_GOAL_STEP')
            tx.update('jobs',work['job_id'],cursor=reference.cursor+1,revision=reference.revision+1,state='DONE' if final and quality else 'BLOCKED' if not quality else 'WAITING',due_at_us=now+self.interval,owner_epoch=None,updated_at_us=now)
            goal=self.store.one('goals',view.goal_id)
            tx.update('goals',view.goal_id,state='FAILED' if not quality else 'COMPLETED' if final else 'ACTIVE',version=goal['version']+1,last_served_us=now)
            self._complete(tx,cycle.intention_id)
        return data

    def transition(self,goal_id,state,*,expected_version,authority,cause_memory_id):
        if authority is not self._authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        goal=self.store.one('goals',goal_id)
        allowed={'ACTIVE':{'SUSPENDED','ABANDONED'},'SUSPENDED':{'ACTIVE','ABANDONED'},'BLOCKED':{'ABANDONED'},'FAILED':{'ABANDONED'}}
        if not goal or goal['version']!=expected_version or state not in allowed.get(goal['state'],set()):raise CoreError('STALE_GOAL_TRANSITION')
        meta=json.loads(goal['body_json']);head=self.records.read(meta['record_id']);cause=self.records.memory.read(cause_memory_id)
        if cause['scope']!=head['scope'] or cause['authority']!='DIRECT':raise CoreError('GOAL_TRANSITION_SOURCE_REQUIRED')
        if self.store.db.execute("SELECT 1 FROM actions WHERE goal_id=? AND state IN ('READY','DISPATCHING','UNKNOWN','PENDING_VERIFY')",(goal_id,)).fetchone():raise CoreError('VERIFY_UNKNOWN_EFFECT_FIRST')
        work=self.store.one('jobs',meta['work_id'])
        with self.store.transaction('open.goal_transition',{'goal_id':goal_id,'state':state,'cause_memory_id':cause_memory_id}) as tx:
            tx.update('goals',goal_id,state=state,version=goal['version']+1)
            tx.update('jobs',work['job_id'],state='PAUSED' if state=='SUSPENDED' else 'WAITING' if state=='ACTIVE' else 'CANCELLED',revision=work['revision']+1,updated_at_us=self.store.clock.utc_now_us())

    def revise(self,goal_id,*,expected_version,cause_memory_id,authority):
        """Fresh supported world/strategy change: new plan, never a retry of UNKNOWN."""
        if authority is not self._authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        goal=self.store.one('goals',goal_id)
        if not goal or goal['version']!=expected_version or goal['state'] not in {'FAILED','BLOCKED','ACTIVE','SUSPENDED'}:raise CoreError('STALE_GOAL_TRANSITION')
        if self.store.db.execute("SELECT 1 FROM actions WHERE goal_id=? AND state IN ('READY','DISPATCHING','UNKNOWN','PENDING_VERIFY')",(goal_id,)).fetchone():raise CoreError('VERIFY_UNKNOWN_EFFECT_FIRST')
        meta=json.loads(goal['body_json']);work=self.store.one('jobs',meta['work_id']);old=self.records.read(work['record_id']);cause=self.records.memory.read(cause_memory_id)
        if cause['scope']!=old['scope'] or cause['authority']!='DIRECT' or cause['observed_time_us']<work['updated_at_us']:raise CoreError('FRESH_RECONSIDERATION_SOURCE_REQUIRED')
        obj=self.policy.get(old['payload']['program']['program_id']);obj,steps,strategies=self._plan(obj,work['record_id'])
        with self.store.transaction('open.goal_replanned',{'goal_id':goal_id,'cause_memory_id':cause_memory_id}) as tx:
            cause_rid=self.records.create(tx,kind='AUTONOMOUS_PLAN',scope=obj.scope,payload={'cause':cause_memory_id},records=(meta['record_id'],),memories=(cause_memory_id,))
            rid=self._plan_record(tx,goal_id,old['payload']['plan_id'],obj,steps,cause_rid,strategies,supersedes=work['record_id'])
            tx.update('goals',goal_id,state='ACTIVE',version=goal['version']+1,body_json=canonical({**meta,'plan_record_id':rid}))
            tx.update('plans',old['payload']['plan_id'],body_json=canonical({'record_id':rid}))
            tx.update('jobs',work['job_id'],record_id=rid,cursor=0,state='WAITING',revision=work['revision']+1,due_at_us=self.store.clock.utc_now_us(),updated_at_us=self.store.clock.utc_now_us(),body_json=canonical({'goal_id':goal_id,'plan_id':old['payload']['plan_id']}))
        return goal_id
