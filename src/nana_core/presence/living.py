"""D provides opportunities and safe points; C/Agency own their semantics."""
import json
from ..storage import canonical,digest
from ..contracts import CoreError
from ..continuity.agency import AgencyService,step_view
from ..continuity.subject.contracts import SubjectInput
from .contracts import RuntimeEvent,Cause

class LivingWork:
    def __init__(self,runtime):
        self.runtime=runtime;self.agency=None
    def configure_agency(self,policy,port):
        r=self.runtime
        self.agency=AgencyService(r.store,r.subject,r.authority,policy,port,step_interval_us=r.config.living.step_interval_us)
    def after_cycle(self,cycle,event):
        if not self.agency or not cycle:return None
        if event.goal_step:return self.agency.advance(event.goal_step,cycle)
        if cycle.proposed_program_id:
            try:return self.agency.adopt(cycle)
            except CoreError as exc:
                if exc.code=='OFFLINE_PROGRAM_NOT_REVIEWED':return None
                raise
    def opportunity(self):
        if not self.agency:return None
        r=self.runtime;ref=self.agency.next_reference()
        if not ref:return None
        work=r.store.one('jobs',ref.work_id);head=r.store.one('continuity_records',work['record_id'])
        try:view=step_view(r.store,ref,scope=head['scope'],privacy_classes=r.config.privacy_classes)
        except CoreError:
            with r.store.transaction('living.work_source_retired') as tx:
                tx.update('jobs',work['job_id'],state='CANCELLED',owner_epoch=None,revision=work['revision']+1)
                goal_id=json.loads(work['body_json'])['goal_id'];goal=r.store.one('goals',goal_id)
                if goal and goal['state'] in {'ACTIVE','BLOCKED'}:tx.update('goals',goal_id,state='ABANDONED',version=goal['version']+1)
            return None
        key='synthetic.living.step.'+digest(ref.model_dump(mode='json'))
        prior=r.store.db.execute('SELECT * FROM subject_events WHERE source_key=?',(key,)).fetchone()
        if prior:
            cycle=r.store.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=?',(prior['subject_event_id'],)).fetchone()
            if cycle:
                return {'recovered':self.agency.advance(ref,r.subject.result(dict(cycle))), 'work_id':ref.work_id}
        inp=SubjectInput(source_key=key,kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,
            scope=head['scope'],observed_at_us=work['due_at_us'],source_memory_ids=view.source_memory_ids[:32],
            task_class=view.task_class,realization_target=view.target,goal_step=ref)
        event=RuntimeEvent(event_type='GOAL_EVENT',trigger='GOAL_TRIGGER',input=inp,
            causes=tuple(Cause(kind='MEMORY',reference_id=mid) for mid in view.source_memory_ids[:32]),due_at_us=work['due_at_us'],priority=1)
        return {'queue_id':r.submit(event),'work_id':ref.work_id}
