"""Post-judgment governed handoff to the existing Kernel; no new executor."""
from contextlib import contextmanager
import json
from ...actions import ActionKernel
from ...contracts import CoreError
from .governance import ManagerConstraintGate
from .fixture_effects import OfflineEffectPort

class GovernedRealization:
    def __init__(self,store,port,authority):
        if store.schema_target<9 or type(port) is not OfflineEffectPort:raise CoreError('OFFLINE_REALIZATION_ONLY')
        self.store,self.gate=store,ManagerConstraintGate(store)
        self.kernel=ActionKernel(store,port,authority)

    @contextmanager
    def _guard(self,outcome):
        if getattr(self.store,'_governed_action_guard',None):raise CoreError('NESTED_REALIZATION_FORBIDDEN')
        self.gate.require_current(outcome)
        self.store._governed_action_guard=lambda:self.gate.require_current(outcome)
        try:yield
        finally:del self.store._governed_action_guard

    def propose(self,intention_id,*,expected_revision,args):
        outcome=self.gate.gate(intention_id,expected_revision=expected_revision)
        if outcome.result!='PASS':return outcome,None
        if outcome.target.resource_class!='ORDINARY':raise CoreError('REALIZATION_RESOURCE_HARD_DENY')
        operation='WRITE' if outcome.target.capability=='reading.card.create' else 'READ'
        if outcome.target.operation!=operation:raise CoreError('REALIZATION_OPERATION_MISMATCH')
        try:
            with self._guard(outcome):
                action_id=self.kernel.propose(outcome.target.capability,outcome.target.resource,args,effect_slot='subject:'+intention_id)
        except CoreError as exc:
            if exc.code!='STALE_MANAGER_PASS':raise
            return self.gate.gate(intention_id,expected_revision=expected_revision),None
        old=self.store.db.execute("SELECT 1 FROM events WHERE kind='governance.action_linked' AND json_extract(data_json,'$.data.target_id')=?",(action_id,)).fetchone()
        if not old:
            with self.store.transaction('governance.action_linked',{'target_id':action_id,'intention_id':intention_id,'outcome_record_id':outcome.record_id,'scope':outcome.scope}):pass
        return outcome,action_id

    def dispatch(self,intention_id,action_id,*,expected_revision,fault=None):
        action=self.store.one('actions',action_id)
        if not action or action['effect_slot']!='subject:'+intention_id:raise CoreError('ACTION_INTENTION_MISMATCH')
        # UNKNOWN/effects are verified, never dispatched again even after a veto.
        if action['state'] in {'DISPATCHING','UNKNOWN','PENDING_VERIFY','SUCCEEDED','NOT_APPLIED','FAILED_EFFECT'}:
            if action['state']=='DISPATCHING':self.kernel.recover()
            return self.kernel.verify(action_id) if self.store.one('actions',action_id)['state'] in {'UNKNOWN','PENDING_VERIFY'} else self.store.one('actions',action_id)['state']
        outcome=self.gate.gate(intention_id,expected_revision=expected_revision)
        if outcome.result!='PASS':
            if action['state'] in {'PROPOSED','READY','BLOCKED'}:self.kernel.cancel(action_id)
            return 'INTENTION_BLOCKED_MANAGER'
        try:
            with self._guard(outcome):
                if action['state'] in {'PROPOSED','BLOCKED'}:self.kernel.prepare(action_id)
                if self.store.one('actions',action_id)['state']=='READY':self.kernel.dispatch(action_id,fault=fault)
        except CoreError as exc:
            if exc.code!='STALE_MANAGER_PASS':raise
            refreshed=self.gate.gate(intention_id,expected_revision=expected_revision)
            if refreshed.result!='PASS' and self.store.one('actions',action_id)['state'] in {'PROPOSED','READY','BLOCKED'}:
                self.kernel.cancel(action_id)
            return 'INTENTION_BLOCKED_MANAGER' if refreshed.result!='PASS' else 'REALIZATION_NEEDS_REVIEW'
        return self.kernel.verify(action_id) if self.store.one('actions',action_id)['state'] in {'UNKNOWN','PENDING_VERIFY'} else self.store.one('actions',action_id)['state']
