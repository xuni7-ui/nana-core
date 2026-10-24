"""D provides opportunities and safe points; C/Agency own their semantics."""
import json
from ..storage import canonical,digest
from ..contracts import CoreError
from ..continuity.agency import AgencyService,step_view
from ..continuity.subject.contracts import SubjectInput
from .contracts import RuntimeEvent,Cause

class LivingWork:
    def __init__(self,runtime):
        self.runtime=runtime;self.agency=None;self.learning_policy=None;self.accommodation_policy=None;self.open_learning=None;self.exploration=None;self.world=None;self.paused=False;self.activity_source=None;self.skill_development=None
        from ..continuity.maintenance import MaintenanceService
        self.maintenance=MaintenanceService(runtime.store,scopes=runtime.config.scopes,entity_id=runtime.config.entity_id,
            privacy_classes=runtime.config.privacy_classes,slice_items=runtime.config.living.slice_items,interval_us=runtime.config.living.maintenance_interval_us)
    def configure_agency(self,policy,port):
        r=self.runtime
        self.agency=AgencyService(r.store,r.subject,r.authority,policy,port,step_interval_us=r.config.living.step_interval_us)
    def configure_open_agency(self,policy,port):
        from ..continuity.open_agency.service import OpenAgencyService
        r=self.runtime
        self.agency=OpenAgencyService(r.store,r.subject,r.authority,policy,port,step_interval_us=r.config.living.step_interval_us)
        self.agency.learning=self.open_learning
        port.permitted_privacy=r.config.privacy_classes
    def configure_open_learning(self,specs,**kwargs):
        from ..continuity.open_agency.learning import LearningService
        r=self.runtime
        self.open_learning=LearningService(r.store,r.authority,specs,privacy_classes=r.config.privacy_classes,scopes=r.config.scopes,**kwargs)
        if self.agency:self.agency.learning=self.open_learning
    def configure_world(self,transport,policy,*,resources,skill_development=None):
        from ..continuity.world_loop.coordinator import WorldLoopWork
        self.world=WorldLoopWork(self.runtime,transport,policy,resources=resources,skill_development=skill_development)
    def after_cycle(self,cycle,event):
        result=self._after_cycle(cycle,event)
        if self.world and cycle:self.world.after_cycle(cycle,event,result)
        return result
    def _after_cycle(self,cycle,event):
        if not cycle:return None
        if self.skill_development:
            selected=self.skill_development.after_cycle(cycle,event)
            if selected:return selected
        if cycle.relational_decision and self.accommodation_policy:
            self.accommodation_policy.apply(self.runtime,cycle)
        if event.goal_review and self.agency:
            if event.goal_review.purpose=='LIFECYCLE':
                ref=event.goal_review;goal=self.runtime.store.one('goals',ref.goal_id)
                selected={'REST':'SUSPENDED','WITHDRAW':'ABANDONED','CONTINUE_PROJECT':'ACTIVE'}.get(cycle.intention.behavior)
                allowed={'ACTIVE':{'SUSPENDED','ABANDONED'},'SUSPENDED':{'ACTIVE','ABANDONED'},'BLOCKED':{'ABANDONED'},'FAILED':{'ABANDONED'}}
                if selected and goal and selected in allowed.get(goal['state'],set()):
                    self.agency.transition(ref.goal_id,selected,expected_version=ref.version,authority=self.runtime.authority,cause_memory_id=ref.cause_memory_id)
                if cycle.intention_id:
                    current=self.runtime.store.one('subject_intentions',cycle.intention_id)
                    if current and current['state']=='PENDING':self.runtime.subject.transition_intention(cycle.intention_id,expected_revision=current['revision'],state='COMPLETED')
                return {'goal_id':ref.goal_id,'lifecycle_review':selected,'not_plan_replay':True}
            if cycle.evaluation and cycle.evaluation.normative=='ENDORSED' and cycle.intention.kind=='GOAL_CANDIDATE':
                ref=event.goal_review
                if self.runtime.store.db.execute("SELECT 1 FROM events WHERE source_namespace='open.plan-review-deferred' AND source_key=?",(cycle.cycle_id,)).fetchone():return {'goal_id':ref.goal_id,'replan':'CURRENT_STATE_REVIEW_REQUIRED'}
                try:self.agency.revise(ref.goal_id,expected_version=ref.version,cause_memory_id=ref.cause_memory_id,authority=self.runtime.authority)
                except CoreError as exc:
                    if exc.code not in {'CHECKPOINT_CURRENT_EFFECT_UNCERTAIN','CHECKPOINT_DESCRIPTION_CHANGED','CHECKPOINT_EFFECT_REVIEW_REQUIRED','CHECKPOINT_SUPPORT_UNAVAILABLE'}:raise
                    # A changed independent check is an expected plan boundary,
                    # not an owner crash or permission to repeat old effects.
                    with self.runtime.store.transaction('open.plan_review_deferred',{'goal_id':ref.goal_id,'cycle_id':cycle.cycle_id,'reason':exc.code,'judgment_unchanged':True},source_namespace='open.plan-review-deferred',source_key=cycle.cycle_id) as tx:
                        current=self.runtime.store.one('subject_intentions',cycle.intention_id)
                        if current and current['state']=='PENDING':tx.update('subject_intentions',current['intention_id'],state='DEFERRED',revision=current['revision']+1)
                    return {'goal_id':ref.goal_id,'replan':'CURRENT_STATE_REVIEW_REQUIRED','reason':exc.code}
                with self.runtime.store.transaction('open.plan_review_adopted',{'goal_id':ref.goal_id}) as tx:
                    self.agency._complete(tx,cycle.intention_id)
                    if cycle.goal_candidate_id:tx.update('subject_goal_candidates',cycle.goal_candidate_id,state='ADOPTED')
            return None
        if self.open_learning:
            learned=self.open_learning.after_cycle(self.runtime,cycle,event)
            if learned:return {'learning_work_id':learned}
        if event.memory_review_id:return self.review_memory(event.memory_review_id,cycle)
        if event.reflection_experience_id and cycle.intention.kind=='REFLECTION' and self.learning_policy:
            self.learning_policy.apply(self.runtime,event.reflection_experience_id)
            self._learning_opportunity(event.reflection_experience_id)
            intention=self.runtime.store.one('subject_intentions',cycle.intention_id) if cycle.intention_id else None
            if intention and intention['state']=='PENDING':self.runtime.subject.transition_intention(cycle.intention_id,expected_revision=intention['revision'],state='COMPLETED')
        if event.reflection_experience_id and cycle.intention.kind=='REFLECTION' and not self.learning_policy:
            # Original C chose review; absence of a configured learning path is
            # not an unfinished job forever, nor permission to invent a Lesson.
            from ..continuity.records import RecordService
            records=RecordService(self.runtime.store);experience=self.runtime.store.one('experiences',event.reflection_experience_id)
            if experience and records.current_support(experience['record_id']):
                key='bounded-experience-review:'+cycle.cycle_id
                if not self.runtime.store.db.execute("SELECT 1 FROM continuity_records WHERE record_kind='RUNTIME_WORK' AND target_id=?",(key,)).fetchone():
                    with self.runtime.store.transaction('living.experience_review_no_lesson',{'cycle_id':cycle.cycle_id}) as tx:
                        records.create(tx,kind='RUNTIME_WORK',scope=event.scope,payload={'kind':'EXPERIENCE_REVIEW','experience_id':event.reflection_experience_id,'cycle_id':cycle.cycle_id,'result':'NO_APPLICABLE_LEARNING_PATH','lesson_created':False,'outcome_not_rewritten':True},records=(cycle.record_id,experience['record_id']),target_id=key)
                if cycle.intention_id:
                    intention=self.runtime.store.one('subject_intentions',cycle.intention_id)
                    if intention and intention['state']=='PENDING':self.runtime.subject.transition_intention(cycle.intention_id,expected_revision=intention['revision'],state='COMPLETED')
                return {'experience_id':event.reflection_experience_id,'reviewed':True,'lesson_created':False}
        if not self.agency:return None
        if event.goal_step:
            result=self.agency.advance(event.goal_step,cycle)
            if self.exploration and result and result.get('memory_id'):
                self.exploration.observe(self.runtime,result['memory_id'])
            return result
        if cycle.proposed_program_id:
            try:return self.agency.adopt(cycle)
            except CoreError as exc:
                if exc.code=='OFFLINE_PROGRAM_NOT_REVIEWED':return None
                raise

    def _learning_opportunity(self,experience_id):
        """A checked new method is a chance to reconsider, not an adopted retry."""
        r=self.runtime
        lesson=r.store.db.execute("SELECT * FROM lessons WHERE experience_id=? AND state='ACTIVE'",(experience_id,)).fetchone()
        if not lesson:return
        from ..continuity.learning import ExperienceService
        experience=ExperienceService(r.store,r.authority).get(experience_id)
        if experience.outcome!='FAILURE':return
        source=r.store.one('continuity_records',lesson['record_id'])
        when=r.store.event(lesson['test_event_id'])['recorded_at_us']
        inp=SubjectInput(source_key='synthetic.living.learned.'+lesson['lesson_id'],kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope=source['scope'],
            observed_at_us=when,source_memory_ids=experience.context_memory_ids[:32],task_class=experience.task_class)
        r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='EXPERIENCE',reference_id=experience_id),),due_at_us=when,priority=0))

    def review_memory(self,rid,cycle):
        old=self.runtime.store.db.execute("SELECT 1 FROM events WHERE source_namespace='living.review' AND source_key=?",(rid,)).fetchone()
        if old:return None
        mid=self.maintenance.adopt(rid,cycle)
        with self.runtime.store.transaction('living.memory_reviewed',{'candidate_record_id':rid,'memory_id':mid},source_namespace='living.review',source_key=rid):pass
        return mid

    def maintenance_slice(self):
        if self.paused:return None
        r=self.runtime
        if self.skill_development:
            activity=self.skill_development.slice()
            if activity:return activity
        if self.world:
            activity=self.world.maintenance_slice()
            if activity:return activity
        if self.open_learning:
            try:activity=self.open_learning.slice()
            except (CoreError,TimeoutError) as exc:
                if isinstance(exc,CoreError) and exc.code in {'RUNTIME_LEASE_LOST','PRIVACY_ANCHOR_INVALID','PRIVACY_ANCHOR_UNAVAILABLE'}:raise
                job=self.open_learning.next_job()
                if not job:raise
                with r.store.transaction('open.learning_unknown',{'work_id':job['job_id'],'error_type':type(exc).__name__}) as tx:tx.update('jobs',job['job_id'],state='UNKNOWN',revision=job['revision']+1)
                return {'work_id':job['job_id'],'reason':'LEARNING_UNKNOWN_REVIEW_REQUIRED'}
            if activity:return activity
        background=getattr(self.activity_source,'maintenance_slice',None)
        if background:
            activity=background()
            if activity:return activity
        for head in r.store.db.execute("SELECT * FROM continuity_records c WHERE record_kind='MAINTENANCE_CANDIDATE' AND lifecycle='ACTIVE' AND NOT EXISTS (SELECT 1 FROM events e WHERE e.source_namespace='living.review' AND e.source_key=c.record_id) ORDER BY created_at_us LIMIT 16"):
            try:_,body=self.maintenance.candidate(head['record_id'])
            except CoreError:continue
            key='synthetic.living.review.'+head['record_id']
            source=r.store.db.execute('SELECT * FROM subject_events WHERE source_key=?',(key,)).fetchone()
            if source:
                cycle=r.store.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=?',(source['subject_event_id'],)).fetchone()
                if cycle:self.review_memory(head['record_id'],r.subject.result(dict(cycle)))
                continue
            inp=SubjectInput(source_key=key,kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope=head['scope'],observed_at_us=head['created_at_us'],source_memory_ids=tuple(body['memory_ids']),memory_review_id=head['record_id'])
            r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=tuple(Cause(kind='MEMORY',reference_id=m) for m in body['memory_ids']),due_at_us=head['created_at_us'],priority=0))
            return {'review_enqueued':head['record_id']}
        return self.maintenance.slice()
    def opportunity(self):
        if self.paused:return None
        if self.world:
            event=self.world.opportunity()
            if event:return {'queue_id':self.runtime.submit(event),'source':'WORLD_CONCERN'}
        if not self.agency:return None
        r=self.runtime
        provider=getattr(self.agency,'learning_opportunity',None)
        if provider:
            event=provider(r.config.entity_id)
            if event:return {'queue_id':r.submit(event),'learning_reconsideration':True}
        ref=self.agency.next_reference()
        if not ref:return self.activity_source.opportunity() if self.activity_source else None
        work=r.store.one('jobs',ref.work_id);head=r.store.one('continuity_records',work['record_id'])
        try:view=step_view(r.store,ref,scope=head['scope'],privacy_classes=r.config.privacy_classes)
        except CoreError:
            with r.store.transaction('living.work_source_retired') as tx:
                tx.update('jobs',work['job_id'],state='CANCELLED',owner_epoch=None,revision=work['revision']+1)
                goal_id=json.loads(work['body_json'])['goal_id'];goal=r.store.one('goals',goal_id)
                if goal and goal['state'] in {'ACTIVE','BLOCKED'}:tx.update('goals',goal_id,state='ABANDONED',version=goal['version']+1)
            return None
        project=view.target.resource.startswith(('project://','hands://'))
        key=('development.living.step.' if project else 'synthetic.living.step.')+digest(ref.model_dump(mode='json'))
        prior=r.store.db.execute('SELECT * FROM subject_events WHERE source_key=?',(key,)).fetchone()
        if prior:
            cycle=r.store.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=?',(prior['subject_event_id'],)).fetchone()
            if cycle:
                try:recovered=self.agency.advance(ref,r.subject.result(dict(cycle)))
                except CoreError:recovered=self.agency._park(work,view,'SOURCE_OR_PROGRAM_REQUIRES_REVIEW')
                return {'recovered':recovered,'work_id':ref.work_id}
            queued=r.store.db.execute('SELECT state FROM runtime_queue WHERE subject_event_id=?',(prior['subject_event_id'],)).fetchone()
            if queued and queued['state'] in {'IGNORED','EXPIRED'}:
                return {'blocked':self.agency._park(work,view,'CORE_STEP_DROPPED')}
        inp=SubjectInput(domain='DEVELOPMENT_MATERIAL' if project else 'SYNTHETIC_ONLY',source_key=key,kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,
            scope=head['scope'],observed_at_us=work['due_at_us'],source_memory_ids=view.source_memory_ids[:32],
            task_class=view.task_class,privacy_class=head['privacy_class'],realization_target=view.target,goal_step=ref)
        event=RuntimeEvent(event_type='GOAL_EVENT',trigger='GOAL_TRIGGER',input=inp,
            causes=tuple(Cause(kind='MEMORY',reference_id=mid) for mid in view.source_memory_ids[:32]),due_at_us=work['due_at_us'],priority=2)
        return {'queue_id':r.submit(event),'work_id':ref.work_id}
