import json
import pytest
from nana_core.storage import Store
from nana_core.contracts import CoreError
from nana_core.integration.contracts import RuntimeIntegrationContext
from nana_core.integration.shadow import ShadowBridge,ShadowDecision,ProposedHostAction,reconcile
from test_host import event

def test_shadow_drafts_zero_actions_budget_restart(tmp_path):
    p=tmp_path/'core.db';e=event();d=ShadowDecision(interpretation='Synthetic conversation',goal_purpose='Consider response',
        planned_actions=(ProposedHostAction(capability='astrbot.message.send',resource='synthetic://chat',reason='fixture'),),rationale='Draft only')
    with Store(p) as s:
        context=RuntimeIntegrationContext(host_instance=e.host_instance,expected_identity_id=s.identity['identity_id'])
        b=ShadowBridge(s,context);r=b.observe(e,d);n=len(s.all('events'))
        assert b.observe(e,d)==r and len(s.all('events'))==n
        assert r['execution_state']=='SHADOW_BLOCKED' and r['goal_draft']
        for table in ['actions','attempts','budgets','grants','strategies','goals','plans']:assert not s.all(table)
        with pytest.raises(CoreError,match='SHADOW_BLOCKED'):b.execute('anything')
        with pytest.raises(CoreError,match='UNSUPPORTED'):b.observe(event(event_id='m2'),d.model_copy(update={'memory_ids':('absent',)}))
    with Store(p) as s:
        b=ShadowBridge(s,context);assert b.observe(e,d)==r
        report=reconcile(r['observation_event_id'],d,d,important_evidence=('synthetic-missing-history',))
        assert report['winner'] is None and not report['differences'] and report['paths']['core']['omitted_important_evidence']

def test_fake_real_model_cannot_claim_semantics(tmp_path):
    with Store(tmp_path/'s.db') as s:
        b=ShadowBridge(s,RuntimeIntegrationContext(host_instance='synthetic-host',expected_identity_id=s.identity['identity_id']))
        with pytest.raises(CoreError,match='CALL_LEDGER'):b.observe(event(),ShadowDecision(interpretation='x',rationale='x',model_kind='real_model'))
        assert not s.all('actions')

def test_export_to_evidence_rehearsal(tmp_path):
    from nana_core.integration.rehearsal import run
    r=run(tmp_path/'lab');assert r['status']=='PASS' and r['export_record_count']==14
    assert r['same_identity'] and r['duplicate_after_restart'] and not any(r['zero_execution_tables'].values())

def test_shadow_store_kernel_cannot_be_reenabled_by_operator(tmp_path):
    from nana_core.actions import ActionKernel,OperatorAuthority
    with Store(tmp_path/'s.db') as s:
        a=OperatorAuthority();b=ShadowBridge(s,RuntimeIntegrationContext(host_instance='synthetic-host',expected_identity_id=s.identity['identity_id']))
        k=ActionKernel(s,None,a)
        with pytest.raises(CoreError,match='SHADOW_BLOCKED'):k.propose('reading.source.read','source://synthetic/a',{'source_id':'source://synthetic/a'})
        with pytest.raises(CoreError,match='SHADOW_BLOCKED'):k.set_budgets({'write_attempts':10,'external_requests':10,'cost_micro_units':10},a)
        assert not s.all('budgets') and not s.all('actions') and not s.all('attempts')
