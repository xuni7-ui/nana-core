"""Owned environment opportunities into original C/D/F/G. No decision loop here."""
import json,time
from ...contracts import CoreError,GrantSpec
from ...storage import digest
from ..project_work.service import capture,post
from ..subject.opportunities import ConcernCue
from ..open_agency.contracts import Objective,Operator
from ..open_agency.service import OpenGoalPolicy
from ..open_agency.learning import LearningSpec,LearningCase,IndependentEvaluator
from ..autonomy.governance import GovernanceController
from ..records import RecordService
from .contracts import ApplicationTask,HandsEffectContext,command_plan,load_target
from .port import OwnedApplicationPort


def expected(task):
    if task.kind in {'DOCUMENT','CONTENT'}:return task.wanted
    if task.kind=='FILES':return {'values':{dst:task.initial+':'+src for src,dst in task.wanted.items()},'submitted':False}
    return {'values':{k:task.wanted.get(k,'') for k in task.fields},'submitted':True}

def independent_commands(data):
    """Evaluator-only full desired workflow, not candidate output or effect receipt."""
    t=data['task']
    commands=([{'op':'REPLACE','value':t['wanted']}] if t['kind']=='DOCUMENT' else [{'op':'SET_FIELD','field':k,'value':''} for k in t['fields']]+[{'op':'SET_FIELD','field':k,'value':v} for k,v in sorted(t['wanted'].items())]+[{'op':'SUBMIT'}])
    return {'task_id':t['task_id'],'revision':data['revision'],'commands':commands}

class PracticeProposer:
    def propose_method(self,problem):
        evaluator=IndependentEvaluator()
        for method in problem.hypotheses:
            if evaluator.evaluate(method,problem.practice)['all_passed']:return method
        return problem.baseline_method

def specifications():
    def case(key,kind,context,value):
        t=ApplicationTask(task_id=key,kind=kind,initial='old draft ',wanted=value,fields=('other','label') if kind=='FORM' else (),context=context)
        data={'task':t.model_dump(mode='json'),'revision':1}
        return LearningCase(case_id=key,context=context,data=data,expected=independent_commands(data))
    return (LearningSpec(learning_key='learn.owned-document',domain='owned-document',baseline_method='HANDS_APPEND',hypotheses=('HANDS_REPLACE',),practice=(case('doc-practice','DOCUMENT','notes','a note'),),evaluation=(case('doc-heldout','DOCUMENT','notes','a different line'),),transfer=(case('doc-transfer','DOCUMENT','drafts','meeting title'),)),
            LearningSpec(learning_key='learn.owned-form',domain='owned-form',baseline_method='HANDS_POSITIONAL',hypotheses=('HANDS_NAMED',),practice=(case('form-practice','FORM','settings',{'label':'blue'}),),evaluation=(case('form-heldout','FORM','settings',{'label':'green'}),),transfer=(case('form-transfer','FORM','search',{'label':'amber'}),)))

class HandsWork:
    def __init__(self,runtime,profile,*,grant=False,allow_skills=False,browser_endpoint=None):
        self.runtime=runtime;self.port=OwnedApplicationPort(runtime.identity_id,load_target(profile),host_enabled=True);self.next_at=0;self.interval=500_000
        if browser_endpoint is not None:
            from .browser import OwnedBrowserPort
            self.port=OwnedBrowserPort(runtime.identity_id,self.port.target,browser_endpoint,host_enabled=True)
        self.objects={t.task_id:self.objective(t) for t in self.port.tasks.values()}
        self.policy=OpenGoalPolicy(tuple(self.objects.values()),dynamic_resources=tuple(op.resource for o in self.objects.values() for op in o.operators))
        GovernanceController(runtime.store,runtime.authority).initialize(runtime.authority)
        runtime.work.configure_open_agency(self.policy,self.port)
        self.port.context_provider=self._effect_context
        specs=specifications()
        # Training cases share one support bundle. An erased root retires that
        # host binding; construction must not recapture it or resurrect a skill.
        keys=tuple('owned-learning-input:'+digest(c.data) for s in specs for group in (s.practice,s.evaluation,s.transfer) for c in group)
        if any(runtime.store.db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace='recorded.project.material' AND source_reference=? AND state='DELETED'",(key,)).fetchone() for key in keys):specs=()
        self.training_sources=tuple(capture(runtime,'owned-learning-input:'+digest(c.data),{'origin':'DEVELOPMENT_PROJECT','prepared_command_trial':c.data}) for s in specs for group in (s.practice,s.evaluation,s.transfer) for c in group)
        runtime.work.configure_open_learning(specs,source_memory_ids=self.training_sources,proposer=PracticeProposer())
        runtime.work.activity_source=self
        self.skills=None
        if allow_skills:
            from .skills import HandsSkills
            self.skills=HandsSkills(self);runtime.work.skill_development=self.skills
        if grant:
            k=runtime.work.agency.realization.kernel;now=runtime.clock.utc_now_us()
            k.grant(GrantSpec(capabilities=('world.observe','world.compute','world.publish',k.verify_capability,*(('world.skill',) if allow_skills else ())),resources=tuple(op.resource for obj in self.objects.values() for op in obj.operators),not_before_us=now,expires_at_us=now+4*3600_000_000),runtime.authority)
            k.set_budgets({'write_attempts':64,'external_requests':512,'cost_micro_units':512},runtime.authority)
    def _effect_context(self,inv):
        r=self.runtime;a=r.store.one('actions',inv.action_id);attempt=r.store.one('attempts',inv.attempt_id)
        if not a or not attempt or not a['goal_id'] or not a['plan_id'] or not attempt['started_at_us']:raise CoreError('HANDS_FORMAL_ACTION_BINDING_REQUIRED')
        key=inv.resource.rsplit('/',2)[-2];task=self.port.tasks[key]
        holds=tuple(x[0] for x in r.store.db.execute('SELECT hold_id FROM budget_holds WHERE owner_id=? ORDER BY hold_id',(inv.attempt_id,)))
        return HandsEffectContext(action_id=inv.action_id,subject_id=r.identity_id,goal_id=a['goal_id'],plan_id=a['plan_id'],plan_step_id=a['effect_slot'],target_identity=self.port.target.instance_id,target_ownership_evidence=self.port.target.binding,
            allowed_effect=tuple(c['op'] for c in inv.args['data']['commands']),expected_outcome_digest=digest(expected(task)),grant_reference=attempt['grant_id'],budget_reference=holds,created_at_us=attempt['started_at_us'],deadline_us=attempt['started_at_us']+5_000_000,idempotency_key=inv.idempotency_key)
    def objective(self,task,skill=None):
        key=task.task_id;resource='hands://'+self.port.target.instance_id+'/'+key+'/'
        domains={'DOCUMENT':'owned-document','FORM':'owned-form','FILES':'owned-files','CONTENT':'owned-content'}
        methods={'DOCUMENT':'HANDS_APPEND','FORM':'HANDS_POSITIONAL','FILES':'HANDS_MOVE_DECLARED','CONTENT':'HANDS_UNIQUE_LINES'}
        return Objective(objective_id='hands.'+key+('-batch' if skill else ''),scope='project-work',motivation_source='PROJECT_COMPLETION',task_domain=domains[task.kind],desired=('applied',),operators=(
            Operator(operator_id='inspect',capability='world.observe',resource=resource+'source',produces=('seen',),args={}),
            Operator(operator_id='prepare',capability='world.skill' if skill else 'world.compute',resource=resource+'commands',requires=('seen',),produces=('prepared',),args={'input_from':'inspect','data_privacy':'PROJECT',**({'skill_record_id':skill} if skill else {'method':methods[task.kind]})},strategy_selectable=not skill),
            Operator(operator_id='apply',capability='world.publish',resource=resource+'effect',requires=('prepared',),produces=('applied',),args={'input_from':'prepare','data_privacy':'PROJECT'},expected_digest=digest(expected(task)))))
    def goal_for_object(self,obj):
        row=self.runtime.store.db.execute("SELECT g.* FROM goals g JOIN continuity_records r ON r.record_id=json_extract(g.body_json,'$.record_id') JOIN artifacts a ON a.artifact_id=r.payload_artifact_id WHERE json_extract(CAST(a.payload AS TEXT),'$.objective.objective_id')=? ORDER BY g.rowid DESC LIMIT 1",(obj.objective_id,)).fetchone()
        return dict(row) if row else None
    def goal_for(self,key):return self.goal_for_object(self.objects[key])
    def offer(self,obj,*,parents=()):
        r=self.runtime;task=self.port.tasks[obj.operators[0].resource.rsplit('/',2)[-2]]
        observation=self.port.peek(task.task_id)
        root=capture(r,'owned-source:'+obj.objective_id,{'origin':'REAL_OS_CONTROLLED_APPLICATION','binding':self.port.target.binding,'task':observation['task'],'initial_state':observation['state']},parents=parents)
        cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key=obj.objective_id,program_id=obj.objective_id,motivation_source=obj.motivation_source)
        mid=capture(r,'owned-opportunity:'+obj.objective_id,cue.model_dump(mode='json'),kind='MODEL_DERIVATION',parents=(root,),predicate='concern.'+obj.objective_id)
        post(r,'owned.'+obj.objective_id,(mid,),task_class=obj.task_domain)
        return {'source':'OWNED_APPLICATION_OPPORTUNITY_NOT_COMMAND','source_memory_id':root}
    def assess_later_use(self):
        r=self.runtime;learning=r.work.open_learning
        from ..world_loop.learning import EpisodeLearning
        for row in r.store.db.execute("SELECT * FROM lessons WHERE state='ACTIVE' AND task_class IN ('owned-document','owned-form') ORDER BY rowid LIMIT 4"):
            rule=RecordService(r.store).read(row['record_id'])['payload']['rule'];method=rule['method']
            for t in self.port.tasks.values():
                obj=self.objects[t.task_id];goal=self.goal_for(t.task_id)
                if obj.task_domain!=row['task_class'] or not goal or goal['state'] not in {'COMPLETED','FAILED'}:continue
                actions=r.store.db.execute("SELECT * FROM actions WHERE goal_id=? AND capability='world.compute' AND state='SUCCEEDED' ORDER BY rowid",(goal['goal_id'],)).fetchall()
                if not actions:continue
                k=r.work.agency.realization.kernel
                results=[(a,json.loads(k.payload(a,'result_json'))) for a in actions]
                if any(result.get('method')!=method for a,result in results):continue # exclude baseline/repaired task
                a,result=results[-1]
                apply=r.store.db.execute("SELECT data_json FROM events WHERE kind='living.goal_step_completed' AND json_extract(data_json,'$.data.goal_id')=? AND json_extract(data_json,'$.data.operator_id')='apply' ORDER BY seq DESC LIMIT 1",(goal['goal_id'],)).fetchone()
                if not apply:continue
                effect=json.loads(apply[0])['data'];mid=effect['memory_id'];key='owned-'+digest([row['lesson_id'],a['action_id']])[:40]
                if r.store.db.execute('SELECT 1 FROM strategy_assessments WHERE lesson_id=? AND episode_key=?',(row['lesson_id'],key)).fetchone():continue
                source=json.loads(k.payload(a,'args_json'))['data'];case=LearningCase(case_id='real-later-owned-task',context=t.context,data=source,expected=independent_commands(source))
                episode={'episode_key':key,'lesson_id':row['lesson_id'],'case':case.model_dump(mode='json'),'actual_effect_memory_id':mid,'actual_effect_quality':effect['quality'],'action_id':effect['action_id'],'attribution':'REAL_EXTERNAL_TASK_WITH_INDEPENDENT_VERIFY_PLUS_PREPARATION_TRIAL'}
                observed=capture(r,'owned-use:'+key,{'strategy_episode':episode},kind='SYSTEM_VERIFICATION',parents=(mid,))
                aid=EpisodeLearning(r.store,r.authority,scopes=r.config.scopes,privacy_classes=r.config.privacy_classes).assess(row['lesson_id'],observed,authority=r.authority)
                return {'strategy_assessment_id':aid,'actual_external_task':t.task_id}
        return None
    def opportunity(self):
        r=self.runtime;now=r.clock.utc_now_us()
        if now<self.next_at:return None
        self.next_at=now+self.interval
        checked=self.assess_later_use()
        if checked:return checked
        if self.skills:
            offered=self.skills.opportunity()
            if offered:return offered
        if r.store.db.execute("SELECT 1 FROM goals WHERE state IN ('ACTIVE','BLOCKED') LIMIT 1").fetchone():return None
        for goal in r.store.db.execute("SELECT template FROM goals WHERE state='FAILED'"):
            if not r.store.db.execute("SELECT 1 FROM jobs j JOIN continuity_records c ON c.record_id=j.record_id WHERE j.work_kind='LEARNING' AND c.target_id=? LIMIT 1",('learn.'+goal['template'],)).fetchone():return None
        if r.store.db.execute("SELECT 1 FROM jobs WHERE work_kind IN ('LEARNING','CODE_DEVELOPMENT') AND state IN ('WAITING','RUNNING') LIMIT 1").fetchone():return None
        for t in self.port.tasks.values():
            obj=self.objects[t.task_id]
            if self.goal_for(t.task_id):continue
            # Offered/adopted task identity survives erasure and a retired skill.
            # Never reinterpret an already completed skill-only task as a fresh
            # unskilled base task. Tombstones, not cached views, close this path.
            if r.store.db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace='recorded.project.material' AND source_reference IN (?,?) LIMIT 1",('owned-source:'+obj.objective_id,'owned-source:'+obj.objective_id+'-batch')).fetchone():continue
            if t.kind=='FORM' and len(t.wanted)>1 and self.skills:
                active=self.skills.active_skill()
                if active:
                    skill_obj=self.objective(t,active);self.policy.offer(skill_obj)
                    if not self.goal_for_object(skill_obj):return self.offer(skill_obj,parents=RecordService(r.store).support(active))
                    continue
            return self.offer(obj)
        return None
