import json
import pytest
from nana_core.storage import Store
from nana_core.actions import OperatorAuthority,ActionKernel
from nana_core.fake_world import FakeWorld
from nana_core.contracts import CAPABILITIES,CoreError,Observation
from nana_core.migration.routing import CapabilityRouter
from nana_core.integration.authority import ExecutionProtocol,HandoffChecks,MemoryAuthorityProtocol

def test_synthetic_owner_protocol_and_memory_fences(tmp_path):
    with Store(tmp_path/'s.db') as s:
        a=OperatorAuthority();port=FakeWorld(tmp_path/'world.db');router=CapabilityRouter(s,{c:port for c in CAPABILITIES},a)
        p=ExecutionProtocol(router,a);old=router.bind('legacy_simulator',a)
        p.move('SHADOW_CORE',a);p.move('CORE_READY',a)
        aid=ActionKernel(s,None,a).propose('reading.source.read','source://synthetic/a',{'source_id':'source://synthetic/a'})
        p.move('HANDOFF_PENDING',a)
        with pytest.raises(CoreError,match='FENCED'):ActionKernel(s,None,a).propose('reading.source.read','source://synthetic/b',{'source_id':'source://synthetic/b'})
        with pytest.raises(CoreError,match='EVIDENCE'):p.move('CORE_ACTIVE',a)
        evidence=s.ingest(Observation(source_namespace='synthetic.checks',object_id='1',raw_text='Operator synthetic checks and snapshot'))
        checks=HandoffChecks(no_unresolved_legacy_action=True,no_unknown_action=True,no_pending_irreversible_work=True,
            state_snapshot_verified=True,grants_verified=True,budget_verified=True,evidence_event_ids=(evidence,))
        with pytest.raises(CoreError,match='BLOCKED'):p.move('CORE_ACTIVE',a,checks.model_copy(update={'budget_verified':False}))
        with pytest.raises(CoreError,match='UNRESOLVED'):p.move('CORE_ACTIVE',a,checks)
        ActionKernel(s,None,a).cancel(aid)
        live=p.move('CORE_ACTIVE',a,checks);assert live['epoch']==2 and old._epoch==1
        p.move('ROLLBACK_PENDING',a);restored=p.move('LEGACY_RESTORED',a,checks);assert restored['epoch']==3 and restored['rollback_record']
        memory=MemoryAuthorityProtocol(s,a);memory.move('M1',a)
        with pytest.raises(CoreError,match='RECONCILIATION'):memory.move('M2',a)
        memory.move('M2',a,reconciliation_event_id=evidence,writer_fenced=True)
        assert memory.move('M3',a,reconciliation_event_id=evidence,writer_fenced=True)['writer']=='core'
        assert memory.move('M2',a,reconciliation_event_id=evidence,writer_fenced=True)['writer']=='iris'
        assert not s.all('grants') and not s.all('strategies')
        port.close()
