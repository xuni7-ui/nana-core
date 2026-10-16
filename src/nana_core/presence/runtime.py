"""One standalone event-driven runtime schedules the existing C SubjectLoop."""
import json
from pathlib import Path
from ..actions import OperatorAuthority
from ..clock import Clock
from ..contracts import CoreError
from ..storage import canonical,digest
from ..continuity import ContinuityStore,IdentityService
from ..continuity.context import ContextPolicy
from ..continuity.subject import SubjectLoop,SubjectInput
from ..continuity.subject.projections import project_self,Environment
from .contracts import RuntimeConfig,RuntimeEvent,RuntimeHealth,ScheduleSpec,Cause
from .authority import RuntimeClock,RuntimeLease
from .queue import EventQueue
from .scheduler import Scheduler
from .cognition import CognitionCoordinator
from .cadence import Cadence,CognitionPreempted


class NanaRuntime:
    def __init__(self,path,config:RuntimeConfig,*,clock=None):
        self.config,self.stopped,self.stop_requested=config,False,False
        self.cadence=Cadence(config.queue_capacity,config.living.max_idle_seconds if config.living else config.poll_seconds)
        self._processing=None
        self.store=ContinuityStore(path,clock or Clock(),schema_target=config.schema_target)
        try:
            old=self.store.one('runtime_lease',self.store.identity['identity_id'])
            history_floor=self.store.db.execute('SELECT coalesce(max(recorded_at_us),0) FROM events').fetchone()[0]
            self.clock=RuntimeClock(clock or self.store.clock,max(history_floor,old['clock_high_water_us'] if old else 0))
            self.store.clock=self.clock
            self.lease=RuntimeLease(self.store,config);self.lease.acquire()
            self.authority=OperatorAuthority()
            IdentityService(self.store,self.authority)
            if not self.store.one('entities',config.entity_id):raise CoreError('RUNTIME_ENTITY_BINDING_REQUIRED')
            self.subject=SubjectLoop(self.store,scopes=config.scopes,privacy_classes=config.privacy_classes)
            self.queue=EventQueue(self.store,config,self.lease)
            self.scheduler=Scheduler(self.store,config,self.queue)
            self.cognition=CognitionCoordinator(self.store,config,self.lease)
            self.cognition.progress=self._model_progress
            self.queue.recover()
            persisted=self.store.one('core_meta','runtime.health')
            self.oper=json.loads(persisted['value_json']) if persisted else {
                'last_event':None,'last_wake_us':None,'last_cognition_us':None,'last_successful_checkpoint_us':None,
                'last_interaction_us':None,'last_activity_us':self.clock.utc_now_us()}
            if self.oper['last_interaction_us'] is None:
                self.oper['last_interaction_us']=self.store.db.execute("SELECT max(observed_at_us) FROM subject_events WHERE origin='USER'").fetchone()[0]
            self.next_scan_us=0
            self._install_review()
            self._save_oper()
        except BaseException:
            if hasattr(self,'lease') and self.lease.epoch is not None:self.lease.release()
            self.store.close();raise

    def _save_oper(self):
        self.lease.assert_current()
        value=canonical(self.oper)
        old=self.store.one('core_meta','runtime.health')
        if not old or old['value_json']!=value:
            self.store.db.execute('BEGIN IMMEDIATE')
            try:
                self.lease.assert_current()
                self.store._put('core_meta',{'key':'runtime.health','value_json':value})
                self.lease.assert_current()
                self.store.db.execute('COMMIT')
            except BaseException:
                self.store.db.execute('ROLLBACK');raise

    def _install_review(self):
        now=self.clock.utc_now_us()
        for scope in self.config.scopes:
            key='runtime-review-'+digest(scope)[:24]
            if self.store.db.execute('SELECT 1 FROM runtime_schedules WHERE dedupe_key=?',(key,)).fetchone():continue
            inp=SubjectInput(source_key='synthetic.runtime.review-template',kind='WAKE',origin='SELF_WAKE',
                entity_id=self.config.entity_id,scope=scope,observed_at_us=now)
            event=RuntimeEvent(event_type='TIME_EVENT',trigger='TIME_TRIGGER',input=inp,
                causes=(Cause(kind='CANONICAL_SELF',reference_id=self.store.identity['identity_id']),),due_at_us=now+self.config.review_interval_us)
            self.scheduler.add(ScheduleSpec(dedupe_key=key,kind='PERIODIC',due_at_us=event.due_at_us,
                interval_us=self.config.review_interval_us,event=event))

    def submit(self,event:RuntimeEvent):
        self.cadence.assert_owner()
        result=self.queue.enqueue(event)
        self.next_scan_us=0
        self.cadence.notify()
        return result

    def post(self,event:RuntimeEvent):
        """Thread-safe producer API; receipt is durable only after wait() succeeds."""
        return self.cadence.post(event)

    def request_stop(self):
        self.stop_requested=True;self.cadence.notify()

    def _model_progress(self):
        self.lease.heartbeat();self.cadence.drain(self.submit)
        row=self._processing
        if self.stop_requested or (self.config.living and row and row['event_type']!='USER_EVENT' and self.queue.has_reactive()):
            raise CognitionPreempted()

    def next_wait_seconds(self):
        now=self.clock.utc_now_us()
        deadlines=[now+self.cadence.max_wait*1_000_000,now+self.config.heartbeat_us]
        for table in ('runtime_queue','runtime_schedules'):
            states="('READY','DEFERRED')" if table=='runtime_queue' else "('ACTIVE')"
            due=self.store.db.execute(f'SELECT min(due_at_us) FROM {table} WHERE state IN {states}').fetchone()[0]
            if due is not None:deadlines.append(max(now+10000,due))
        idle=min(self.cadence.max_wait,self.config.poll_seconds*(2**min(self.cadence.idle_rounds,8)))
        return max(.001,min(idle,(min(deadlines)-now)/1_000_000))

    def refresh_attention(self):
        self.lease.assert_current()
        self.next_scan_us=0

    def _watch_sources(self):
        """D installs source-bound checks. C decides relevance and intentions."""
        now=self.clock.utc_now_us()
        if now<self.next_scan_us:return
        self.next_scan_us=now+min(self.config.review_interval_us,self.config.idle_recall_us)
        # The generic C opportunity collector is added by the C integration
        # milestone. This compatibility check keeps clock/deadline infrastructure
        # useful independently; it is not a hidden second judgment engine.
        collector=getattr(self.subject,'background_opportunities',None)
        if collector:
            opportunities=collector(entity_id=self.config.entity_id,now_us=now,
                quiet_since_us=self.oper['last_activity_us'],quiet_window_us=self.config.idle_recall_us)
            for opportunity in opportunities:
                inp=SubjectInput(source_key='synthetic.runtime.attention-template',kind='WAKE',origin='SELF_WAKE',
                    entity_id=opportunity.entity_id,scope=opportunity.scope,observed_at_us=now,
                    source_memory_ids=opportunity.memory_ids[:32],task_class=opportunity.task_class,
                    reflection_experience_id=opportunity.reflection_experience_id,commitment_check_id=opportunity.commitment_check_id)
                event=RuntimeEvent(event_type=opportunity.event_type,trigger=opportunity.wake_trigger,input=inp,
                    causes=(Cause(kind=opportunity.source_kind,reference_id=opportunity.source_id,revision=opportunity.source_revision),),
                    due_at_us=opportunity.due_at_us,priority=opportunity.priority)
                spec=ScheduleSpec(dedupe_key=opportunity.key,kind='CALENDAR' if opportunity.calendar else 'CONDITION',due_at_us=opportunity.due_at_us,event=event,calendar=opportunity.calendar)
                if self.store.db.execute('SELECT 1 FROM runtime_schedules WHERE dedupe_key=?',(opportunity.key,)).fetchone():continue
                try:self.scheduler.add(spec)
                except CoreError as exc:
                    if str(exc)=='RUNTIME_SCHEDULE_BACKPRESSURE':break
                    raise

    def step(self):
        self.cadence.assert_owner();self.cadence.drain(self.submit)
        self.lease.heartbeat()
        self._watch_sources();self.scheduler.due()
        row=self.queue.claim()
        if row is None:
            self.cadence.idle_rounds=min(8,self.cadence.idle_rounds+1)
            self._save_oper();return None
        self.cadence.idle_rounds=0;self._processing=row
        self.oper['last_event']=row['queue_id'];self.oper['last_wake_us']=self.clock.utc_now_us()
        try:
            event=self.queue.input(row)
            self.queue.cause_memories(tuple(Cause.model_validate_json(canonical(x)) for x in json.loads(row['cause_json'])),event.scope)
            if event.origin=='USER':self.oper['last_interaction_us']=event.observed_at_us
            mode,reason=self.cognition.choose(row,event,self.subject)
            result=None
            if mode=='NO_COGNITION':
                maintenance=getattr(self.subject,'maintain',None)
                if maintenance:maintenance()
            elif mode=='FULL_COGNITION':
                call=self.cognition.reserve(row)
                try:
                    policy=ContextPolicy(policy_id='runtime-local-fixture',allowed_scopes=self.config.scopes,
                        readable_privacy=self.config.privacy_classes)
                    result=self.subject.cognize(event,model=self.cognition.port(call),authority=self.authority,policy=policy,
                        capabilities=self.config.capability_snapshot.capabilities,limitations=('NO_EXTERNAL_EXECUTION_IN_C_D',))
                    self.cognition.finish(call,'SUCCEEDED')
                except CognitionPreempted:
                    self.cognition.finish(call,'CANCELLED' if self.store.schema_target>=11 else 'FAILED')
                    self.queue.finish(row,'DEFERRED','PREEMPTED_AT_NO_EFFECT_SAFE_POINT')
                    return {'queue_id':row['queue_id'],'mode':'NO_COGNITION','reason':'PREEMPTED','cycle':None}
                except TimeoutError:
                    self.cognition.finish(call,'TIMED_OUT')
                    result=self.subject.run(event)
                    reason='MODEL_TIMEOUT_LIGHT_FALLBACK'
                except Exception as exc:
                    if isinstance(exc,CoreError) and str(exc)=='RUNTIME_LEASE_LOST':raise
                    self.cognition.finish(call,'FAILED')
                    result=self.subject.run(event)
                    reason='MODEL_FAILED_LIGHT_FALLBACK'
                self.oper['last_cognition_us']=self.clock.utc_now_us()
            else:result=self.subject.run(event)
            if result and result.intention.kind=='REFLECTION' and event.reflection_experience_id:
                self.subject.reflect(event.reflection_experience_id,authority=self.authority,apply=False)
            if result and result.intention.kind!='NO_ACTION':self.oper['last_activity_us']=self.clock.utc_now_us()
            self.queue.finish(row,'DONE',reason,result.cycle_id if result else None)
            checkpoint=self.store.db.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
            if checkpoint[0]==0:self.oper['last_successful_checkpoint_us']=self.clock.utc_now_us()
            self._save_oper()
            return {'queue_id':row['queue_id'],'mode':mode,'reason':reason,'cycle':result}
        except CoreError as exc:
            if str(exc)=='RUNTIME_LEASE_LOST':raise
            # Retired/deleted sources and malformed semantic proposals do not
            # become new history, external replies or unlimited retries.
            self.queue.finish(row,'IGNORED','SOURCE_RETIRED_OR_INVALID')
            self._save_oper()
            return {'queue_id':row['queue_id'],'mode':'NO_COGNITION','reason':'SOURCE_RETIRED_OR_INVALID','cycle':None}
        finally:self._processing=None

    def drain(self,limit=256):
        results=[]
        for _ in range(limit):
            result=self.step()
            if result is None:break
            results.append(result)
        return results

    def living(self,scope=None):
        return project_self(self.store,entity_id=self.config.entity_id,scope=scope or self.config.scopes[0],
            privacy_classes=self.config.privacy_classes,environment=Environment(capabilities=self.config.capability_snapshot.capabilities,
                devices=self.config.capability_snapshot.devices,platforms=self.config.capability_snapshot.platforms,
                cognition_available=False if self.cognition.availability in {'DEGRADED','UNAVAILABLE'} else None))

    def health(self):
        now=self.clock.utc_now_us()
        lease=self.store.one('runtime_lease',self.store.identity['identity_id'])
        lost=False
        try:self.lease.assert_current()
        except CoreError:lost=True
        status='STOPPED' if self.stopped else 'LOST' if lost else 'DEGRADED' if self.cognition.availability in {'DEGRADED','UNAVAILABLE'} else 'WATCHING'
        return RuntimeHealth(status=status,runtime_instance_id=self.lease.instance_id,epoch=self.lease.epoch,
            lease_status='LOST' if lost and not self.stopped else lease['state'],identity_id=self.store.identity['identity_id'],
            last_event=self.oper['last_event'],last_wake_us=self.oper['last_wake_us'],last_cognition_us=self.oper['last_cognition_us'],
            queue_depth=self.queue.depth(),deferred_count=self.store.db.execute("SELECT count(*) FROM runtime_queue WHERE state='DEFERRED'").fetchone()[0],
            model_availability=self.cognition.availability,subject_revision=self.subject.revision,
            last_successful_checkpoint_us=self.oper['last_successful_checkpoint_us'],clock_us=now,
            time_since_interaction_us=None if self.oper['last_interaction_us'] is None else max(0,now-self.oper['last_interaction_us']),
            time_since_activity_us=max(0,now-self.oper['last_activity_us']))

    def run(self,max_seconds=30):
        deadline=None if max_seconds==0 else self.clock.monotonic_ns()+int(max_seconds*1_000_000_000)
        try:
            while not self.stop_requested and (deadline is None or self.clock.monotonic_ns()<deadline):
                stamp=self.cadence.stamp()
                result=self.step()
                if result is None:
                    wait=self.next_wait_seconds()
                    if deadline is not None:wait=min(wait,max(0,(deadline-self.clock.monotonic_ns())/1_000_000_000))
                    self.cadence.wait(wait,stamp)
        finally:self.stop()

    def stop(self):
        if self.stopped:return
        self.stopped=True
        self.cadence.close()
        try:
            try:self._save_oper()
            except CoreError:pass
            self.lease.release()
        finally:self.store.close()

    def __enter__(self):return self
    def __exit__(self,*args):self.stop()
