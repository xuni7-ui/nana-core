"""Operator-only synthetic rehearsal of existing S6 owner/epoch handoff.

No host stop/start or production lease implemented. These protocol records do
not themselves stop a legacy process; real handoff remains separately authorized.
"""
import json
from typing import Literal
from pydantic import Field
from ..contracts import DTO,CoreError
from ..storage import canonical

EXEC_KEY='cloud.execution_protocol'
EXEC_LEGAL={'LEGACY_ACTIVE':{'SHADOW_CORE'},'SHADOW_CORE':{'CORE_READY','LEGACY_RESTORED'},
    'CORE_READY':{'HANDOFF_PENDING','LEGACY_RESTORED'},'HANDOFF_PENDING':{'CORE_ACTIVE','LEGACY_RESTORED'},
    'CORE_ACTIVE':{'ROLLBACK_PENDING'},'ROLLBACK_PENDING':{'LEGACY_RESTORED'},'LEGACY_RESTORED':{'SHADOW_CORE'}}

class HandoffChecks(DTO):
    no_unresolved_legacy_action: bool
    no_unknown_action: bool
    no_pending_irreversible_work: bool
    state_snapshot_verified: bool
    grants_verified: bool
    budget_verified: bool
    evidence_event_ids: tuple[str,...] = Field(min_length=1,max_length=16)

class ExecutionProtocol:
    def __init__(self,router,authority,*,simulation_only:Literal[True]=True):
        if simulation_only is not True:raise CoreError('PRODUCTION_HANDOFF_NOT_ENABLED')
        router._operator(authority)
        self.router,self.store,self._authority=router,router.store,authority
        if not self.store.one('core_meta',EXEC_KEY):
            owner=router.select_owner('legacy_simulator',authority)
            with self.store.transaction('cloud.execution_protocol_initialized') as tx:
                tx.put('core_meta',{'key':EXEC_KEY,'value_json':canonical({'state':'LEGACY_ACTIVE','epoch':owner['epoch'],'simulation_only':True})})
    @property
    def state(self):return json.loads(self.store.one('core_meta',EXEC_KEY)['value_json'])
    def move(self,target,authority,checks=None):
        self.router._operator(authority)
        prior=self.state
        if target not in EXEC_LEGAL[prior['state']]:raise CoreError('ILLEGAL_HANDOFF_TRANSITION')
        if target in {'CORE_ACTIVE','LEGACY_RESTORED'}:
            if not isinstance(checks,HandoffChecks):raise CoreError('HANDOFF_EVIDENCE_REQUIRED')
            checks=HandoffChecks.model_validate(checks.model_dump())
            if not all(v for k,v in checks.model_dump().items() if k!='evidence_event_ids'):raise CoreError('HANDOFF_CHECKS_BLOCKED')
            for ref in checks.evidence_event_ids:
                e=self.store.event(ref)
                if e['identity_id']!=self.store.identity['identity_id'] or not e['artifact_id']:raise CoreError('HANDOFF_EVIDENCE_REQUIRED')
                self.store.artifact(e['artifact_id'])
            owner=self.router.select_owner('core_simulator' if target=='CORE_ACTIVE' else 'legacy_simulator',authority)
        else:owner=self.router.owner
        result={'state':target,'epoch':owner['epoch'],'simulation_only':True,'previous_state':prior['state'],
            'checks':checks.model_dump(mode='json') if checks else None,'rollback_record':target in {'ROLLBACK_PENDING','LEGACY_RESTORED'}}
        # Crash after owner selection before this commit leaves epoch mismatch;
        # Router blocks execution and this transition can safely be resumed.
        with self.store.transaction('cloud.execution_protocol_transition',result) as tx:
            tx.put('core_meta',{'key':EXEC_KEY,'value_json':canonical(result)})
        return result

MEMORY_LEGAL={'M0':{'M1'},'M1':{'M2','M0'},'M2':{'M3','M0'},'M3':{'M4','M2'},'M4':{'M3'}}
MEMORY_WRITER={'M0':'iris','M1':'iris','M2':'iris','M3':'core','M4':'core'}
class MemoryAuthorityProtocol:
    def __init__(self,store,authority):self.store,self._authority=store,authority
    @property
    def state(self):
        row=self.store.one('core_meta','cloud.memory_authority')
        return json.loads(row['value_json']) if row else {'stage':'M0','writer':'iris','simulation_only':True}
    def move(self,target,authority,*,reconciliation_event_id=None,writer_fenced=False):
        if authority is not self._authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        prior=self.state
        if target not in MEMORY_LEGAL[prior['stage']]:raise CoreError('ILLEGAL_MEMORY_AUTHORITY_TRANSITION')
        changing=MEMORY_WRITER[target]!=prior['writer']
        if changing or target in {'M2','M4'}:
            if not writer_fenced or not reconciliation_event_id:raise CoreError('MEMORY_RECONCILIATION_REQUIRED')
            e=self.store.event(reconciliation_event_id)
            if e['identity_id']!=self.store.identity['identity_id'] or not e['artifact_id']:raise CoreError('MEMORY_RECONCILIATION_REQUIRED')
            self.store.artifact(e['artifact_id'])
        result={'stage':target,'writer':MEMORY_WRITER[target],'simulation_only':True,'previous_stage':prior['stage'],
            'source_evidence_never_deleted':True,'reconciliation_event_id':reconciliation_event_id,
            'writer_fenced_attestation':writer_fenced,'rollback_catchup':'required; never discard post-handoff evidence'}
        with self.store.transaction('cloud.memory_authority_transition',result) as tx:
            tx.put('core_meta',{'key':'cloud.memory_authority','value_json':canonical(result)})
        return result
