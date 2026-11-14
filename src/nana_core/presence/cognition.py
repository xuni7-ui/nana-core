"""Bounded cognition resources, not another subject. Only offline fixture models."""
import json
import os
import subprocess
import sys
import time
from ..contracts import CoreError
from ..clock import Clock
from ..storage import uid
from .contracts import DAY

KINDS={'analytical','cautious','unavailable','timeout'}


class SupervisedModelPort:
    def __init__(self,kind,timeout_seconds,progress,on_usage,resource_clock=None):
        if kind not in KINDS:raise CoreError('RUNTIME_MODEL_NOT_REGISTERED')
        self.kind,self.timeout,self.progress,self.on_usage=kind,timeout_seconds,progress,on_usage
        self.descriptor='isolated-offline-fixture-'+kind
        self.resource_clock=resource_clock or Clock()

    def propose(self,request):
        payload=request.model_dump_json().encode()
        if len(payload)>196608:raise CoreError('RUNTIME_MODEL_CONTEXT_LIMIT')
        self.on_usage(len(payload),None)
        process=subprocess.Popen([sys.executable,'-m','nana_core.presence.model_worker',self.kind,str(os.getpid())],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.process_pid=process.pid
        deadline=self.resource_clock.monotonic_ns()+int(self.timeout*1_000_000_000)
        first=True
        try:
            while True:
                self.progress()
                remaining=(deadline-self.resource_clock.monotonic_ns())/1_000_000_000
                if remaining<=0:raise TimeoutError('RUNTIME_MODEL_TIMEOUT')
                try:
                    out,_=process.communicate(input=payload if first else None,timeout=min(.05,remaining))
                    break
                except subprocess.TimeoutExpired:
                    first=False
            if process.returncode!=0 or len(out)>32768:raise CoreError('RUNTIME_MODEL_FAILED')
            envelope=json.loads(out)
            if set(envelope)!={'proposal'} or type(envelope['proposal']) is not str:raise CoreError('RUNTIME_MODEL_REPLY_INVALID')
            self.on_usage(len(payload),len(out))
            return envelope['proposal']
        finally:
            if process.poll() is None:process.kill()
            process.communicate(timeout=2)  # reap even timeout/cancel/lease loss
            self.process_pid=None


class CognitionCoordinator:
    def __init__(self,store,config,lease):
        self.store,self.config,self.lease=store,config,lease
        self.model_kind=config.model
        self.provider_factory=None;self.provider_preview=None
        self._started={}
        self._restore_resource_state()

    def _restore_resource_state(self):
        self.availability='UNCONFIGURED' if self.model_kind is None else 'UNAVAILABLE' if self.model_kind=='unavailable' else 'AVAILABLE'
        last=self.store.db.execute("SELECT * FROM runtime_cognition_calls WHERE provider=? AND state IN ('FAILED','TIMED_OUT') ORDER BY started_at_us DESC LIMIT 1",(self.model_kind,)).fetchone()
        self.backoff_until=(last['finished_at_us']+self.config.cognition_backoff_us) if last else 0
        if last and self.store.clock.utc_now_us()<self.backoff_until:self.availability='DEGRADED'
        if self.store.db.execute("SELECT 1 FROM runtime_cognition_calls WHERE provider=? AND state IN ('RESERVED','UNKNOWN')",(self.model_kind,)).fetchone():self.availability='DEGRADED'

    def set_model(self,kind):
        if kind is not None and kind not in KINDS:raise CoreError('RUNTIME_MODEL_NOT_REGISTERED')
        if kind==self.model_kind:return
        self.provider_factory=None;self.provider_preview=None
        self.model_kind=kind
        self._restore_resource_state()

    def bind_provider(self,factory,preview):
        """Explicit owner binding; callbacks reuse original provider admission.

        This is not persisted model output or a new model loop. The host rebinds
        it on startup; old fixture mode/defaults remain unchanged until requested.
        Preview must be read-only and apply the host's route/hour/profile limits.
        """
        self.lease.assert_current()
        if self.store.schema_target<13 or not callable(factory) or not callable(preview):raise CoreError('PROVIDER_RESOURCE_BINDING_REQUIRED')
        self.provider_factory,self.provider_preview=factory,preview
        self.model_kind='provider';self.availability='AVAILABLE';self.backoff_until=0

    def _provider_choice(self,row,event,loop,source,situation,appraisal,*,preview=True):
        if source and source.get('subject_event_id'):
            key='subject-cognition.'+source['subject_event_id']
            if self.store.db.execute('SELECT 1 FROM cognitive_requests WHERE request_key=?',(key,)).fetchone():
                return 'NO_COGNITION','MODEL_ATTEMPT_ALREADY_RESERVED'
        if self.store.db.execute("SELECT 1 FROM cognitive_requests WHERE state='CALLING' UNION ALL SELECT 1 FROM runtime_cognition_calls WHERE state='RESERVED' LIMIT 1").fetchone():
            return 'LIGHT_COGNITION','UNRESOLVED_PROVIDER_CALL'
        now=self.store.clock.utc_now_us();day=now//DAY*DAY
        old=self.store.db.execute('SELECT count(*),max(started_at_us) FROM runtime_cognition_calls WHERE started_at_us>=?',(day,)).fetchone()
        new=self.store.db.execute('SELECT count(*),max(created_at_us) FROM cognitive_requests WHERE created_at_us>=?',(day,)).fetchone()
        if old[0]+new[0]>=self.config.max_calls_per_day:return 'LIGHT_COGNITION','COGNITION_BUDGET_EXHAUSTED'
        latest=max(old[1] or 0,new[1] or 0)
        if latest and now-latest<self.config.cognition_cooldown_us:return 'LIGHT_COGNITION','COGNITION_COOLDOWN'
        unknown=self.store.db.execute("SELECT count(*) FROM cognitive_requests WHERE state='UNKNOWN' AND created_at_us>=?",(day,)).fetchone()[0]
        unknown+=self.store.db.execute("SELECT count(*) FROM runtime_cognition_calls WHERE state='UNKNOWN' AND started_at_us>=?",(day,)).fetchone()[0]
        if row['event_type']!='USER_EVENT' and self.config.provider_unknown_calls_per_day and unknown>=self.config.provider_unknown_calls_per_day:
            return 'LIGHT_COGNITION','UNKNOWN_BILLING_BACKGROUND_PAUSED'
        if not situation.memory_ids and not situation.support_record_ids:
            from ..continuity.autonomy.private_intent import provider_consideration_memory
            from ..continuity.subject.policy import appraise
            root=provider_consideration_memory(self.store,event)
            if root:
                situation=situation.model_copy(update={'memory_ids':(root,)})
                appraisal=appraise(event,situation)
        # Admission already previewed the complete request. Dispatch constructs
        # and rechecks it, so do not assemble a duplicate preview after claim.
        if not preview:return 'FULL_COGNITION','IMPORTANT_UNCERTAIN_SOURCE'
        from ..continuity.subject.policy import motivate,decide,deliberation_frame
        frame=None
        if source and source.get('subject_event_id'):
            motives=motivate(event,situation,appraisal)
            frame=deliberation_frame(source['subject_event_id'],situation,appraisal,motives,decide(event,situation,appraisal,motives)[0])
        try:self.provider_preview(event,frame)
        except CoreError as exc:
            if exc.code in {'RUNTIME_LEASE_LOST','PRIVACY_ANCHOR_INVALID','PRIVACY_ANCHOR_UNAVAILABLE'}:raise
            return 'LIGHT_COGNITION',exc.code
        return 'FULL_COGNITION','IMPORTANT_UNCERTAIN_SOURCE'

    def choose(self,row,event,loop,*,preview=True):
        if row['event_type']=='TIME_EVENT' and row['wake_trigger']=='TIME_TRIGGER':
            return 'NO_COGNITION','LOW_FREQUENCY_TIME_MAINTENANCE'
        return self._choose(row,event,loop,self.store.one('subject_events',row['subject_event_id']),preview=preview)

    def preview_private(self,event,loop):
        """Read-only C/resource assessment before recording a D opportunity."""
        if event.private_thought_ref is None and event.task_class!='private.feedback.review':raise CoreError('PRIVATE_CONTINUATION_REFERENCE_REQUIRED')
        row={'event_type':'SELF_EVENT','wake_trigger':'SELF_TRIGGER','queue_id':None}
        return self._choose(row,event,loop,{'record_id':None})

    def _choose(self,row,event,loop,source,*,preview=True):
        situation=loop.situation(event,source)
        from ..continuity.subject.policy import appraise
        appraisal=appraise(event,situation)
        if event.retention=='DO_NOT_REMEMBER':return 'LIGHT_COGNITION','NONRETENTION_NO_MODEL'
        need=appraisal.uncertainty in {'RELEVANT','HIGH'} and (appraisal.risk=='HIGH' or event.significance=='HIGH' or appraisal.novelty=='HIGH')
        private_opportunity=event.private_thought_ref is not None or event.task_class=='private.feedback.review'
        if private_opportunity:
            from ..continuity.subject.policy import motivate,decide
            from ..continuity.autonomy.private_intent import can_consider_private_formation
            _,judgment,intention=decide(event,situation,appraisal,motivate(event,situation,appraisal))
            need=bool(can_consider_private_formation(event,situation,judgment,intention))
        if not need:return 'LIGHT_COGNITION','C_POLICY_SUFFICIENT'
        if self.provider_factory is not None:return self._provider_choice(row,event,loop,source,situation,appraisal,preview=preview)
        now=self.store.clock.utc_now_us()
        if self.model_kind is None or self.availability=='UNAVAILABLE':return 'LIGHT_COGNITION','MODEL_UNAVAILABLE_SELF_CONTINUES'
        if now<self.backoff_until:return 'LIGHT_COGNITION','MODEL_BACKOFF'
        previous=self.store.db.execute('SELECT * FROM runtime_cognition_calls WHERE queue_id=?',(row['queue_id'],)).fetchone()
        if previous:return 'LIGHT_COGNITION','MODEL_ATTEMPT_ALREADY_RESERVED'
        if self.store.db.execute("SELECT 1 FROM runtime_cognition_calls WHERE provider=? AND state='RESERVED'",(self.model_kind,)).fetchone():
            return 'LIGHT_COGNITION','UNRESOLVED_PROVIDER_CALL'
        latest=self.store.db.execute('SELECT max(started_at_us) FROM runtime_cognition_calls').fetchone()[0]
        if latest is not None and now-latest<self.config.cognition_cooldown_us:return 'LIGHT_COGNITION','COGNITION_COOLDOWN'
        count=self.store.db.execute('SELECT count(*) FROM runtime_cognition_calls WHERE started_at_us>=?',(now//DAY*DAY,)).fetchone()[0]
        if count>=self.config.max_calls_per_day:return 'LIGHT_COGNITION','COGNITION_BUDGET_EXHAUSTED'
        # A private formation completes in C and does not allocate an external
        # work slot. Provider/concurrency/budget and foreground guards above
        # still govern the method; pending tasks are not a ban on own thought.
        if situation.pending_count>=6 and not private_opportunity:return 'LIGHT_COGNITION','COGNITIVE_LOAD'
        if self.config.living:
            from .resources import allocation_reason
            reason=allocation_reason(self.store,self.config,row)
            if reason:return 'LIGHT_COGNITION',reason
        return 'FULL_COGNITION','IMPORTANT_UNCERTAIN_SOURCE'

    def reserve(self,row):
        now=self.store.clock.utc_now_us()
        with self.store.transaction('runtime.cognition_reserved') as tx:
            if self.config.living:
                from .resources import allocation_reason
                if allocation_reason(self.store,self.config,row):raise CoreError('COGNITION_RESERVATION_EXHAUSTED')
            call_id=uid()
            tx.put('runtime_cognition_calls',{'call_id':call_id,'queue_id':row['queue_id'],
                'provider':self.model_kind,'state':'RESERVED','owner_epoch':self.lease.epoch,'reserved_units':1,
                'input_bytes':None,'output_bytes':None,'actual_tokens':None,'actual_cost_micro':None,
                'started_at_us':now,'finished_at_us':None,**({'lane':'FOREGROUND' if row['event_type']=='USER_EVENT' else 'BACKGROUND',
                    'reserved_bytes':self.config.living.call_reserved_bytes if self.config.living else 0,
                    'reserved_cost_micro':self.config.living.call_estimated_cost_micro if self.config.living else 0,
                    'accounting':'ESTIMATED_UPPER_BOUND','wall_latency_us':None} if self.store.schema_target>=11 else {})})
        if self.store.schema_target>=11:self._started[call_id]=time.monotonic_ns()
        return call_id

    def port(self,call_id):
        def usage(input_bytes,output_bytes):
            self.lease.assert_current()
            row=self.store.one('runtime_cognition_calls',call_id)
            if self.config.living and input_bytes+(output_bytes if output_bytes is not None else 32768)>row['reserved_bytes']:
                raise CoreError('COGNITION_BYTE_RESERVATION_EXCEEDED')
            # Operational byte accounting must not change cognitive state stamp.
            self.store.db.execute('UPDATE runtime_cognition_calls SET input_bytes=?,output_bytes=? WHERE call_id=? AND state=?',
                (input_bytes,output_bytes,call_id,'RESERVED'))
        return SupervisedModelPort(self.model_kind,self.config.model_timeout_seconds,getattr(self,'progress',self.lease.heartbeat),usage)

    def finish(self,call_id,state):
        if state not in ({'SUCCEEDED','FAILED','TIMED_OUT','CANCELLED'} if self.store.schema_target>=11 else {'SUCCEEDED','FAILED','TIMED_OUT'}):raise CoreError('RUNTIME_CALL_TRANSITION_INVALID')
        row=self.store.one('runtime_cognition_calls',call_id)
        if not row or row['state']!='RESERVED':raise CoreError('RUNTIME_CALL_TERMINAL')
        with self.store.transaction('runtime.cognition_finished') as tx:
            tx.update('runtime_cognition_calls',call_id,state=state,finished_at_us=self.store.clock.utc_now_us(),
                actual_tokens=0,actual_cost_micro=0,**({'wall_latency_us':max(0,(time.monotonic_ns()-self._started.pop(call_id,time.monotonic_ns()))//1000)} if self.store.schema_target>=11 else {}))  # registered fixtures ONLY
        if state not in {'SUCCEEDED','CANCELLED'}:
            self.availability='DEGRADED'
            self.backoff_until=self.store.clock.utc_now_us()+self.config.cognition_backoff_us
        else:self.availability='AVAILABLE'
