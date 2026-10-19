"""Persistent multi-goal transitions; all intentions still committed by C.

This component adopts eligible proposals under a finite application policy and
executes ONE C-approved step via the existing governed Kernel. It is not a loop.
"""
import json
from ...contracts import CoreError
from ...storage import canonical,digest,uid
from ..records import RecordService
from ..memory import PRIVACY_RANK
from ..agency import AgencyService
from ..agency_contracts import GoalStepRef,PlanStepView
from ..autonomy.realization import GovernedRealization
from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..learning import ExperienceService,ExperienceInput
from .contracts import Objective,PlannerInput
from .planning import BoundedPlanner,validate_plan
from .world import LocalWorldRegistry

class OpenGoalPolicy:
    def __init__(self,objectives,*,max_active=8,planner=None,dynamic_resources=()):
        if not (1<=len(objectives)<=64 or (not objectives and dynamic_resources)) or len({o.objective_id for o in objectives})!=len(objectives) or not 1<=max_active<=16:raise CoreError('OPEN_GOAL_POLICY_INVALID')
        self.objectives={o.objective_id:Objective.model_validate_json(o.model_dump_json()) for o in objectives}
        self.max_active=max_active;self.planner=planner or BoundedPlanner();self.dynamic_resources=frozenset(dynamic_resources)
    def offer(self,objective):
        if not self.dynamic_resources:raise CoreError('DYNAMIC_GOALS_NOT_CONFIGURED')
        obj=Objective.model_validate_json(objective.model_dump_json())
        if any(op.resource not in self.dynamic_resources for op in obj.operators):raise CoreError('GOAL_RESOURCE_NOT_DESCRIBED')
        for op in obj.operators:LocalWorldRegistry().validate(op.capability,op.resource,op.args)
        prior=self.objectives.get(obj.objective_id)
        if prior and prior!=obj:raise CoreError('GOAL_DESCRIPTION_CONFLICT')
        if not prior and len(self.objectives)>=64:raise CoreError('DYNAMIC_GOAL_BOUND')
        self.objectives[obj.objective_id]=obj

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
        for rid in proposal.source_record_ids:
            head=self.records.read(rid)
            if head['record_kind']!='COGNITION_PROPOSAL' or head['scope']!=obj.scope or head['privacy_class'] not in self.subject.privacy_classes or not self.records.current_support(rid) or tuple(head['payload']['reply']['proposal']['plan_operator_ids'])!=proposal.operator_ids:raise CoreError('PLAN_COGNITION_SOURCE_MISMATCH')
            strategy_ids.append(rid)
        if not steps:raise CoreError('GOAL_ALREADY_SATISFIED')
        for step in steps:
            if step.capability=='world.skill':
                rid=step.args['skill_record_id'];head=self.records.read(rid)
                if head['record_kind']!='CODE_SKILL' or head['scope']!=obj.scope or head['privacy_class'] not in self.subject.privacy_classes or head['payload']['state']!='ACTIVE' or not self.records.current_support(rid):raise CoreError('SKILL_SOURCE_RETIRED')
                strategy_ids.append(rid)
        return obj,steps,strategy_ids

    def adopt(self,cycle):
        if not cycle.goal_candidate_id or not cycle.proposed_program_id or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED':return None
        old=self.store.db.execute('SELECT goal_id FROM goals WHERE goal_key=?',(cycle.goal_candidate_id,)).fetchone()
        if old:return old[0]
        candidate=self.store.one('subject_goal_candidates',cycle.goal_candidate_id)
        if self.store.schema_target>=13 and candidate and candidate['state']=='ADOPTED':
            represented=self.store.db.execute("SELECT g.goal_id FROM goals g JOIN continuity_records r ON r.record_id=json_extract(g.body_json,'$.record_id') JOIN artifacts a ON a.artifact_id=r.payload_artifact_id WHERE r.record_kind='ADOPTED_GOAL' AND r.lifecycle='ACTIVE' AND json_extract(CAST(a.payload AS TEXT),'$.candidate_id')=? LIMIT 1",(cycle.goal_candidate_id,)).fetchone()
            if represented:return represented[0]
        obj=self.policy.get(cycle.proposed_program_id);source=self.store.one('subject_events',cycle.event_id)
        if not candidate or candidate['state']!='PROPOSED' or source['scope']!=obj.scope or obj.motivation_source not in {m.source for m in cycle.motivations}:raise CoreError('GOAL_ADOPTION_SOURCE_MISMATCH')
        if not self.subject.visible(candidate['record_id'],obj.scope):raise CoreError('GOAL_SOURCE_UNAVAILABLE')
        from ..subject.opportunities import cues_from
        cues=cues_from(self.store,self.records.support(candidate['record_id']),scope=obj.scope,privacy_classes=self.subject.privacy_classes)
        cause_ids=tuple(sorted(mid for mid,c in cues if c.program_id==obj.objective_id))
        if not cause_ids:raise CoreError('GOAL_PROGRAM_SOURCE_REQUIRED')
        goal_key='open:'+digest([obj.objective_id,cause_ids])
        represented=self.store.db.execute('SELECT goal_id FROM goals WHERE goal_key=?',(goal_key,)).fetchone()
        if represented:
            with self.store.transaction('open.concern_already_represented',{'goal_id':represented[0],'candidate_id':cycle.goal_candidate_id}) as tx:
                tx.update('subject_goal_candidates',cycle.goal_candidate_id,state='WITHDRAWN');self._complete(tx,cycle.intention_id)
            return represented[0]
        if self.store.db.execute("SELECT count(*) FROM goals WHERE state IN ('ACTIVE','BLOCKED','SUSPENDED')").fetchone()[0]>=self.policy.max_active:return None
        dependency_records=[]
        for dep in (*obj.depends_on,*((obj.parent_id,) if obj.parent_id else ())):
            g=self.store.one('goals',dep)
            if not g:raise CoreError('GOAL_DEPENDENCY_UNKNOWN')
            parent=self.store.one('continuity_records',json.loads(g['body_json'])['record_id'])
            if parent['scope']!=obj.scope:raise CoreError('CROSS_SCOPE_GOAL_DEPENDENCY')
            if not self.subject.visible(parent['record_id'],obj.scope):raise CoreError('GOAL_DEPENDENCY_UNAVAILABLE')
            dependency_records.append(parent['record_id'])
        obj,steps,strategies=self._plan(obj,candidate['record_id'])
        gid,pid,wid=uid(),uid(),uid();now=self.store.clock.utc_now_us()
        with self.store.transaction('open.goal_adopted',{'goal_id':gid,'candidate_id':cycle.goal_candidate_id}) as tx:
            rid=self.records.create(tx,kind='ADOPTED_GOAL',scope=obj.scope,payload={'purpose':cycle.intention.purpose,'objective':obj.model_dump(mode='json'),'candidate_id':cycle.goal_candidate_id},records=(candidate['record_id'],*dependency_records))
            plan=self._plan_record(tx,gid,pid,obj,steps,rid,strategies)
            tx.put('goals',{'goal_id':gid,'goal_key':goal_key,'event_id':self.store.one('continuity_records',cycle.record_id)['event_id'],'template':obj.task_domain,'state':'ACTIVE','version':1,
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
        scopes=','.join('?' for _ in self.subject.scopes);privacy=','.join('?' for _ in self.subject.privacy_classes)
        rows=self.store.db.execute(f"SELECT j.*,g.depends_json,g.deadline_us,g.priority,g.last_served_us FROM jobs j JOIN goals g ON json_extract(j.body_json,'$.goal_id')=g.goal_id JOIN continuity_records cr ON cr.record_id=j.record_id WHERE cr.scope IN ({scopes}) AND cr.privacy_class IN ({privacy}) AND j.work_kind='GOAL' AND j.state IN ('WAITING','RUNNING','UNKNOWN') AND g.state IN ('ACTIVE','BLOCKED') AND j.due_at_us<=? ORDER BY CASE WHEN g.deadline_us<=? THEN 0 ELSE 1 END,min(3,g.priority+cast((?-j.due_at_us)/60000000 AS INTEGER)) DESC,g.last_served_us,j.due_at_us LIMIT 32",(*self.subject.scopes,*self.subject.privacy_classes,now,now,now)).fetchall()
        # At most one committed step at a time; round-robin within priority and
        # bounded aging means low-priority goals are not silently lost.
        for row in rows:
            deps=[self.store.one('goals',x) for x in json.loads(row['depends_json'])]
            if any(d is None or d['state']!='COMPLETED' for d in deps):continue
            return GoalStepRef(work_id=row['job_id'],revision=row['revision'],cursor=row['cursor'])
        return None

    def learning_opportunity(self,entity_id):
        if not self.learning:return None
        from ...presence.contracts import RuntimeEvent,Cause
        from ..subject.contracts import SubjectInput
        from ..agency_contracts import GoalReviewRef
        for goal in self.store.db.execute("SELECT * FROM goals WHERE state IN ('FAILED','BLOCKED') ORDER BY priority DESC,last_served_us LIMIT 16"):
            meta=json.loads(goal['body_json']);head=self.store.one('continuity_records',meta.get('plan_record_id'))
            if not head or head['scope'] not in self.subject.scopes or not self.subject.visible(head['record_id'],head['scope']):continue
            strategy=self.learning.strategy(goal['template'],head['scope'])
            if not strategy:continue
            plan=self.records.read(head['record_id'])['payload']
            if plan.get('format')!='OPEN_PLAN_V1' or strategy[0] in plan['strategy_ids']:continue
            lesson=self.store.db.execute('SELECT * FROM lessons WHERE record_id=?',(strategy[0],)).fetchone()
            exp=self.store.one('experiences',lesson['experience_id']);mid=exp['result_memory_id']
            m=self.records.memory.read(mid);work=self.store.one('jobs',meta['work_id'])
            if m['observed_time_us']<work['updated_at_us']:continue
            if self.store.db.execute("SELECT 1 FROM actions WHERE goal_id=? AND state IN ('READY','DISPATCHING','UNKNOWN','PENDING_VERIFY')",(goal['goal_id'],)).fetchone():continue
            project=any(op['resource'].startswith('project://') for op in plan['steps'])
            key=('development.open.review.' if project else 'synthetic.open.review.')+digest([goal['goal_id'],goal['version'],strategy[0]])
            if self.store.db.execute('SELECT 1 FROM subject_events WHERE source_key=?',(key,)).fetchone():continue
            ref=GoalReviewRef(goal_id=goal['goal_id'],version=goal['version'],cause_memory_id=mid)
            inp=SubjectInput(domain='DEVELOPMENT_MATERIAL' if project else 'SYNTHETIC_ONLY',source_key=key,kind='WAKE',origin='SELF_WAKE',entity_id=entity_id,scope=head['scope'],observed_at_us=self.store.clock.utc_now_us(),source_memory_ids=(mid,),task_class=goal['template'],privacy_class=head['privacy_class'],goal_review=ref)
            return RuntimeEvent(event_type='GOAL_EVENT',trigger='GOAL_TRIGGER',input=inp,causes=(Cause(kind='EXPERIENCE',reference_id=exp['experience_id']),),due_at_us=self.store.clock.utc_now_us(),priority=2)
        return None

    def advance(self,reference,cycle):
        work=self.store.one('jobs',reference.work_id)
        if not work or work['revision']!=reference.revision:
            old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='living.goal-step' AND source_key=?",(reference.work_id+':'+str(reference.revision)+':'+str(reference.cursor),)).fetchone()
            return json.loads(old[0])['data'] if old else None
        head=self.store.one('continuity_records',work['record_id'])
        view=open_step_view(self.store,reference,scope=head['scope'],privacy_classes=self.subject.privacy_classes)
        plan=self.records.read(work['record_id'])['payload']
        if digest(self.policy.get(plan['program']['program_id']).model_dump(mode='json'))!=plan['policy_digest']:return self._park(work,view,'POLICY_CHANGED')
        source=self.store.one('subject_events',cycle.event_id)
        if self.records.read(source['record_id'])['payload']['input'].get('goal_step')!=reference.model_dump(mode='json'):raise CoreError('GOAL_STEP_CYCLE_MISMATCH')
        if not cycle.intention_id or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED' or cycle.realization_target!=view.target:return self._park(work,view,'SUBJECT_DEFERRED')
        for rid in plan['strategy_ids']:
            head=self.store.one('continuity_records',rid)
            if not head or head['lifecycle']!='ACTIVE' or not self.records.current_support(rid):return self._park(work,view,'STRATEGY_SUPPORT_RETIRED')
            if head['record_kind']=='LESSON':
                lesson=self.store.db.execute('SELECT state FROM lessons WHERE record_id=?',(rid,)).fetchone()
                if not lesson or lesson[0]!='ACTIVE':return self._park(work,view,'STRATEGY_SUSPENDED')
            if head['record_kind']=='CODE_SKILL':
                controller=getattr(self.realization.kernel.capability,'code_skills',None)
                try:
                    if not controller:raise CoreError('CURRENT_REALM_REVIEW_REQUIRED')
                    controller.require_current(rid)
                except CoreError:return self._park(work,view,'CODE_REALM_REVIEW_REQUIRED')
        op=plan['steps'][reference.cursor];args=dict(op['args']);input_mids=()
        if args.get('input_from'):
            prior=[o for o in self._outputs(view.goal_id) if o.get('plan_record_id')==work['record_id']]
            match=next((o for o in reversed(prior) if o.get('operator_id')==args['input_from']),None)
            if not match:return self._park(work,view,'VERIFIED_INPUT_REQUIRED')
            observed=self.records.memory.read(match['memory_id'])
            args['data']=json.loads(observed['text'])['data'];args['data_privacy']=observed['privacy_class'];input_mids=(match['memory_id'],)
        if op['capability']=='world.contact':
            if not self.delivery:return self._park(work,view,'DELIVERY_ADMISSION_REQUIRED')
            admission=self.delivery.assess(cycle,view.target.resource,payload=args.get('data'),source_memory_ids=input_mids)
            if admission['result']!='ELIGIBLE':
                # Preserve original social desire/intention and defer this step;
                # a new observed availability/window is needed before retry.
                return self._park(work,view,'DELIVERY_'+admission['result'])
            args['admission_id']=admission['record_id']
        action=self.store.db.execute('SELECT action_id FROM actions WHERE effect_slot=?',('subject:'+cycle.intention_id,)).fetchone()
        try:
            if action:aid=action[0]
            else:
                outcome,aid=self.realization.propose(cycle.intention_id,expected_revision=1,args=args,input_memory_ids=input_mids)
                if not aid:return self._park(work,view,'MANAGER_'+outcome.result)
                with self.store.transaction('open.action_bound',{'goal_id':view.goal_id,'work_id':work['job_id']}) as tx:tx.update('actions',aid,goal_id=view.goal_id,plan_id=view.plan_id)
            state=self.realization.dispatch(cycle.intention_id,aid,expected_revision=1)
        except CoreError as exc:return self._park(work,view,'REALIZATION_'+exc.code)
        if state!='SUCCEEDED':return self._park(work,view,'EFFECT_'+state,unknown=state=='UNKNOWN')
        action=self.store.one('actions',aid);memory=self.records.memory
        # Evidence capture is idempotent on action; no external effect is retried
        # if a crash happens between this observation and progress commit.
        result=self.realization.kernel.payload(action,'result_json');now=self.store.clock.utc_now_us()
        verified_at=self.store.event(json.loads(action['body_json'])['verification_event_id'])['recorded_at_us']
        namespace=getattr(self.realization.kernel.capability,'evidence_namespace','synthetic.open-action')
        existing=self.store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON m.source_evidence_id=e.evidence_id WHERE e.source_namespace=? AND e.source_reference=? AND m.lifecycle='ACTIVE' LIMIT 1",(namespace,aid)).fetchone()
        if existing:mid=existing[0]
        else:
            eid=memory.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT' if namespace.startswith('recorded.project.') else 'SYNTHETIC_ONLY',source_namespace=namespace,source_reference=aid,source_kind='SYSTEM_VERIFICATION'),text=result,privacy_class=max((head['privacy_class'],self.registry.payload_privacy(json.loads(result))),key=PRIVACY_RANK.get),observed_time_us=verified_at))
            mid=memory.add(MemoryCandidate(entity_id=source['entity_id'],scope=head['scope'],memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=result,derived_from=tuple(dict.fromkeys((*view.source_memory_ids,*input_mids))),confidence=1.))
        quality=True;exp=None
        if op.get('expected_digest'):
            quality=digest(json.loads(result).get('data'))==op['expected_digest']
            service=ExperienceService(self.store,self._authority)
            prior=self.store.db.execute('SELECT experience_id FROM experiences WHERE result_memory_id=?',(mid,)).fetchone()
            if prior:exp=prior[0]
            else:
                checked=service.verify_structured_result(mid,op['expected_digest'],self._authority)
                exp=service.record(ExperienceInput(context_memory_ids=view.source_memory_ids[:32],scope=head['scope'],task_class=plan['task_class'],decision=cycle.judgment.reason,result_memory_id=mid,verification_memory_id=checked))
        final=reference.cursor+1==len(plan['steps']);data={'goal_id':view.goal_id,'work_id':work['job_id'],'plan_record_id':work['record_id'],'operator_id':op['operator_id'],'cursor':reference.cursor,'action_id':aid,'memory_id':mid,'experience_id':exp,'quality':quality}
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
