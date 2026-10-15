"""Bounded cognition resources, not another subject. Only offline fixture models."""
import json
import os
import subprocess
import sys
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
        self.model_kind=kind
        self._restore_resource_state()

    def choose(self,row,event,loop):
        if row['event_type']=='TIME_EVENT' and row['wake_trigger']=='TIME_TRIGGER':
            return 'NO_COGNITION','LOW_FREQUENCY_TIME_MAINTENANCE'
        source=self.store.one('subject_events',row['subject_event_id'])
        situation=loop.situation(event,source)
        from ..continuity.subject.policy import appraise
        appraisal=appraise(event,situation)
        if event.retention=='DO_NOT_REMEMBER':return 'LIGHT_COGNITION','NONRETENTION_NO_MODEL'
        need=appraisal.uncertainty in {'RELEVANT','HIGH'} and (appraisal.risk=='HIGH' or event.significance=='HIGH' or appraisal.novelty=='HIGH')
        if not need:return 'LIGHT_COGNITION','C_POLICY_SUFFICIENT'
        now=self.store.clock.utc_now_us()
        if self.model_kind is None or self.availability=='UNAVAILABLE':return 'LIGHT_COGNITION','MODEL_UNAVAILABLE_SELF_CONTINUES'
        if now<self.backoff_until:return 'LIGHT_COGNITION','MODEL_BACKOFF'
        previous=self.store.db.execute('SELECT * FROM runtime_cognition_calls WHERE queue_id=?',(row['queue_id'],)).fetchone()
        if previous:return 'LIGHT_COGNITION','MODEL_ATTEMPT_ALREADY_RESERVED'
        if self.store.db.execute("SELECT 1 FROM runtime_cognition_calls WHERE provider=? AND state IN ('RESERVED','UNKNOWN')",(self.model_kind,)).fetchone():
            return 'LIGHT_COGNITION','UNRESOLVED_PROVIDER_CALL'
        latest=self.store.db.execute('SELECT max(started_at_us) FROM runtime_cognition_calls').fetchone()[0]
        if latest is not None and now-latest<self.config.cognition_cooldown_us:return 'LIGHT_COGNITION','COGNITION_COOLDOWN'
        count=self.store.db.execute('SELECT count(*) FROM runtime_cognition_calls WHERE started_at_us>=?',(now//DAY*DAY,)).fetchone()[0]
        if count>=self.config.max_calls_per_day:return 'LIGHT_COGNITION','COGNITION_BUDGET_EXHAUSTED'
        if situation.pending_count>=6:return 'LIGHT_COGNITION','COGNITIVE_LOAD'
        return 'FULL_COGNITION','IMPORTANT_UNCERTAIN_SOURCE'

    def reserve(self,row):
        now=self.store.clock.utc_now_us()
        with self.store.transaction('runtime.cognition_reserved') as tx:
            call_id=uid()
            tx.put('runtime_cognition_calls',{'call_id':call_id,'queue_id':row['queue_id'],
                'provider':self.model_kind,'state':'RESERVED','owner_epoch':self.lease.epoch,'reserved_units':1,
                'input_bytes':None,'output_bytes':None,'actual_tokens':None,'actual_cost_micro':None,
                'started_at_us':now,'finished_at_us':None})
        return call_id

    def port(self,call_id):
        def usage(input_bytes,output_bytes):
            self.lease.assert_current()
            # Operational byte accounting must not change cognitive state stamp.
            self.store.db.execute('UPDATE runtime_cognition_calls SET input_bytes=?,output_bytes=? WHERE call_id=? AND state=?',
                (input_bytes,output_bytes,call_id,'RESERVED'))
        return SupervisedModelPort(self.model_kind,self.config.model_timeout_seconds,self.lease.heartbeat,usage)

    def finish(self,call_id,state):
        if state not in {'SUCCEEDED','FAILED','TIMED_OUT'}:raise CoreError('RUNTIME_CALL_TRANSITION_INVALID')
        row=self.store.one('runtime_cognition_calls',call_id)
        if not row or row['state']!='RESERVED':raise CoreError('RUNTIME_CALL_TERMINAL')
        with self.store.transaction('runtime.cognition_finished') as tx:
            tx.update('runtime_cognition_calls',call_id,state=state,finished_at_us=self.store.clock.utc_now_us(),
                actual_tokens=0,actual_cost_micro=0)  # registered fixtures ONLY, not provider billing
        if state!='SUCCEEDED':
            self.availability='DEGRADED'
            self.backoff_until=self.store.clock.utc_now_us()+self.config.cognition_backoff_us
        else:self.availability='AVAILABLE'
