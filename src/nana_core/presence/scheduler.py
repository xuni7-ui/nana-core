"""Source-bound checks, never motives. Missed periodic ticks coalesce."""
from ..contracts import CoreError
from ..storage import canonical,uid,digest
from .contracts import ScheduleSpec,RuntimeEvent


class Scheduler:
    def __init__(self,store,config,queue):self.store,self.config,self.queue=store,config,queue

    def add(self,spec:ScheduleSpec):
        self.queue.lease.assert_current()
        old=self.store.db.execute('SELECT * FROM runtime_schedules WHERE dedupe_key=?',(spec.dedupe_key,)).fetchone()
        template=spec.event.model_dump(mode='json')
        if spec.calendar:
            if self.store.schema_target<9:raise CoreError('AUTONOMY_SCHEMA_REQUIRED')
            template={'event':template,'calendar':spec.calendar.model_dump(mode='json')}
        # Scheduler templates contain no plaintext or mutable free-form objects.
        if old:
            if old['template_json']!=canonical(template) or old['schedule_kind']!=spec.kind:
                raise CoreError('RUNTIME_SCHEDULE_COLLISION')
            return old['schedule_id']
        if self.store.db.execute("SELECT count(*) FROM runtime_schedules WHERE state='ACTIVE'").fetchone()[0]>=self.config.schedule_capacity:
            raise CoreError('RUNTIME_SCHEDULE_BACKPRESSURE')
        self.queue.cause_memories(spec.event.causes,spec.event.input.scope)
        with self.store.transaction('runtime.schedule_created') as tx:
            sid=uid()
            tx.put('runtime_schedules',{'schedule_id':sid,'dedupe_key':spec.dedupe_key,'state':'ACTIVE',
                'schedule_kind':spec.kind,'due_at_us':spec.due_at_us,'interval_us':spec.interval_us,
                'template_json':canonical(template),'last_queue_id':None,'occurrence':0,'created_at_us':self.store.clock.utc_now_us()})
        return sid

    def due(self):
        now=self.store.clock.utc_now_us()
        rows=self.store.db.execute("SELECT * FROM runtime_schedules WHERE state='ACTIVE' AND due_at_us<=? ORDER BY due_at_us,schedule_id LIMIT 16",(now,)).fetchall()
        for raw in rows:
            row=dict(raw)
            import json
            payload=json.loads(row['template_json'])
            calendar=None;due_at=row['due_at_us']
            if row['schedule_kind']=='CALENDAR':
                from ..continuity.recurrence import RecurrenceSpec
                calendar=RecurrenceSpec.model_validate_json(canonical(payload['calendar']));payload=payload['event']
                due_at=calendar.latest_due(now)
                if due_at<row['due_at_us'] or now-due_at>calendar.grace_us:
                    with self.store.transaction('runtime.calendar_missed',{'schedule_id':row['schedule_id']}) as tx:
                        tx.update('runtime_schedules',row['schedule_id'],due_at_us=calendar.next_after(now))
                    continue
            payload['input']['source_key']='synthetic.runtime.'+digest([row['schedule_id'],calendar.occurrence_key(due_at) if calendar else row['occurrence']])
            # Preserve this scheduled occurrence across enqueue-before-ACK
            # crashes; never rewrite the time of its source experience.
            payload['input']['observed_at_us']=due_at;payload['input']['occurred_at_us']=due_at
            payload['due_at_us']=due_at
            try:
                event=RuntimeEvent.model_validate_json(canonical(payload))
                qid=self.queue.enqueue(event)
            except CoreError as exc:
                if str(exc) in {'RUNTIME_QUEUE_BACKPRESSURE'}:break
                if str(exc) in {'RUNTIME_CAUSE_UNAVAILABLE','RUNTIME_CAUSE_STALE','MEMORY_UNAVAILABLE','RECORD_UNAVAILABLE'}:
                    with self.store.transaction('runtime.schedule_retired') as tx:tx.update('runtime_schedules',row['schedule_id'],state='CANCELLED')
                    continue
                raise
            with self.store.transaction('runtime.schedule_fired') as tx:
                tx.update('runtime_schedules',row['schedule_id'],state='ACTIVE' if row['schedule_kind'] in {'PERIODIC','CALENDAR'} else 'FIRED',
                    due_at_us=calendar.next_after(now) if calendar else now+row['interval_us'] if row['interval_us'] else row['due_at_us'],
                    last_queue_id=qid,occurrence=row['occurrence']+1)

    def reschedule_periodic(self,schedule_id,*,expected_interval_us,interval_us):
        """Host cadence change, not a Subject motive. Preserve occurrence identity."""
        if type(interval_us)!=int or not 1_000_000<=interval_us<=86_400_000_000:raise CoreError('RUNTIME_INTERVAL_INVALID')
        self.queue.lease.assert_current()
        with self.store.transaction('runtime.periodic_cadence_changed',{'schedule_id':schedule_id,'interval_us':interval_us}) as tx:
            row=self.store.one('runtime_schedules',schedule_id)
            if not row or row['state']!='ACTIVE' or row['schedule_kind']!='PERIODIC' or row['interval_us']!=expected_interval_us:raise CoreError('STALE_RUNTIME_SCHEDULE')
            tx.update('runtime_schedules',schedule_id,interval_us=interval_us,due_at_us=self.store.clock.utc_now_us()+interval_us)

    def cancel(self,schedule_id):
        with self.store.transaction('runtime.schedule_cancelled') as tx:
            row=self.store.one('runtime_schedules',schedule_id)
            if not row or row['state']!='ACTIVE':raise CoreError('RUNTIME_SCHEDULE_TERMINAL')
            tx.update('runtime_schedules',schedule_id,state='CANCELLED')
