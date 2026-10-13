import json
import pytest
from nana_core.contracts import CoreError
from nana_core.semantic.contracts import Endpoint, EvaluationCase, ModelBudget
from nana_core.semantic.model_port import CallLedger
from nana_core.semantic.evaluation import aggregate
from nana_core.semantic.snapshot import verify_snapshot
from nana_core.storage import canonical, digest
from tools.nana_next_stage.semantic import prepare, verify, run_cell, evaluate


class FixturePlanningTransport:
    """Only reads supplied context; never a real model or test-answer oracle."""
    is_real_transport=False
    def __init__(self, mutate=None, omit_step=False):
        self.mutate,self.omit_step=mutate,omit_step
        self.payloads=[]
    def send(self,endpoint,payload):
        self.payloads.append(payload)
        user=json.loads(json.loads(payload)['messages'][1]['content'])
        req,ctx=user['request'],user['continuity']
        next_stage=ctx['next_stage'];r,c,p=next_stage['relationship'],next_stage['commitment'],next_stage['preference']
        active=ctx['active_experiences'] if user['observation_kind']=='reading' else []
        understanding={'person_id':r['person_id'],'address_term':r['address_term'],
            'relationship_memory_refs':r['supporting_memory_ids'],'commitment_id':c['commitment_id'],
            'commitment_status':c['status'],'commitment_due_at':c['due_at'],
            'current_preference':p['current'],'preference_memory_refs':p['supporting_memory_ids'],
            'observation_coverage':next_stage['observation_coverage']['completeness'],
            'authorizes_new_permissions':False}
        if self.mutate:self.mutate(understanding)
        steps=[{'capability':'reading.source.read','resource':req['source_id']}]
        if active and not self.omit_step:steps.append({'capability':'reading.source.locate','resource':req['source_id']})
        steps.append({'capability':'reading.card.create','resource':req['card_resource']})
        reply={'identity':{'identity_id':req['identity_id'],'revision':req['identity_revision'],
            'identity_snapshot':req['identity_snapshot'],'charter':req['identity_snapshot']['charter'],
            'permission_source':'operator_grant','history_refs':[ctx['memories'][0]['created_event_id']]},
            'experience':{'rule_refs':[s['ref'] for s in active],'scope':'reading_card' if active else 'none',
                'required_output':'locator' if active else 'none',
                'support_refs':list(dict.fromkeys(r for s in active for r in s['support_refs'])),
                'authorizes_new_permissions':False},
            'proposal':{'purpose':'Synthetic protocol plan, not real inference.','steps':steps}
                if user['observation_kind']=='reading' else None,
            'rationale':canonical(understanding)}
        return canonical({'id':'synthetic-response','model':'fixture-'+endpoint.alias,
            'usage':{'prompt_tokens':100,'completion_tokens':100},
            'choices':[{'finish_reason':'stop','message':{'content':canonical(reply)}}]}).encode()


@pytest.fixture
def frozen(tmp_path):
    root=tmp_path/'snapshot';prepare(root,seed=109);return root


def endpoint(alias='first'):
    return Endpoint(alias=alias,base_url='http://127.0.0.1:9999/v1',model='fixture-'+alias,
        account_scope='local_offline',funding='local_offline',service_kind='protocol_simulator')


def test_frozen_relationship_identity_experience_and_heldout_isolation(frozen):
    _,s=verify(frozen);_,base=verify_snapshot(frozen)
    assert s['identity_id']==base['identity']['identity_id']
    assert s['commitment']['status']=='OFFERED'
    assert s['observation_coverage']['completeness']=='PARTIAL'
    assert all(s['identity_id'] in e['identity_id'] for e in base['event_prefix'] if e['identity_id'])
    assert not any(c['raw_text'] in canonical(s) for c in base['cases'])
    assert len(base['strategies'])==1 and base['strategies'][0]['status']=='ACTIVE'


def test_extra_context_tamper_rejected(frozen):
    (frozen/'next_stage_context.json').write_text('{}')
    with pytest.raises(CoreError,match='NEXT_STAGE_FROZEN_CONTEXT_REJECTED'):verify(frozen)


def test_one_command_no_config_reports_not_run_without_network(frozen,tmp_path):
    before=verify(frozen)[0]
    result=evaluate(frozen,tmp_path/'report')
    assert result['E12']=='NOT_RUN' and result['real_model_attempts']==0
    assert result['phase_a_semantics']=='NOT_RUN_REAL_DEPENDENCY'
    assert not result['model_switch_comparisons']
    assert result['fees']['actual_external_cost']==0 and verify(frozen)[0]==before

@pytest.mark.parametrize('case_index',[0,1,2,3])
def test_two_fixture_ports_same_identity_both_arms_and_proposals(frozen,tmp_path,case_index):
    manifest,_=verify(frozen);_,base=verify_snapshot(frozen)
    case=EvaluationCase.model_validate_json(canonical(base['cases'][case_index]))
    results=[]
    ledger=CallLedger(tmp_path/'calls.db',ModelBudget(max_calls=32),{'snapshot':digest(manifest)})
    try:
        for alias in ('first','second'):
            for arm in ('with','without'):
                r=run_cell(frozen,tmp_path/(alias+'-'+arm),case,arm,endpoint(alias),ledger,transport=FixturePlanningTransport())
                assert r['semantic']['passed'] and r['behavior']['passed']
                assert r['phase_a_semantic']['passed'] and r['provenance']=='transport_fixture'
                assert 'raw_proposal' in r and 'compiled_plan' in r['behavior']
                results.append(r)
        assert all(r['request_identity']==results[0]['request_identity'] for r in results)
        if case_index in (0,2):
            assert results[0]['behavior']['world_counts']['locate_calls']==1
            assert results[1]['behavior']['world_counts']['locate_calls']==0
        if case_index==1:assert results[0]['behavior']['goal_state']=='BLOCKED'
        report=aggregate(results,ledger.summary(),[],digest(manifest),4,2)
        assert report['E12']=='NOT_RUN' and report['real_model_attempts']==0
        assert verify(frozen)[0]==manifest
    finally:ledger.close()

@pytest.mark.parametrize('field,value', [
    ('person_id','synthetic:imposter'),('address_term','fictional changed name'),
    ('commitment_due_at','2026-09-09T10:00:00+00:00'),('current_preference','long'),
    ('relationship_memory_refs',['made-up-reference']),('preference_memory_refs',['made-up-reference']),
    ('observation_coverage','FULL_FOR_DECLARED_SCOPE')])
def test_semantic_drift_fails_without_rewriting_core(frozen,tmp_path,field,value):
    _,base=verify_snapshot(frozen);case=EvaluationCase.model_validate_json(canonical(base['cases'][0]))
    ledger=CallLedger(tmp_path/'calls.db',ModelBudget(),{})
    try:
        r=run_cell(frozen,tmp_path/'cell',case,'with',endpoint(),ledger,
            transport=FixturePlanningTransport(mutate=lambda d:d.update({field:value})))
        assert r['behavior']['passed'] and r['base_semantic']['passed']
        assert not r['phase_a_semantic']['passed'] and not r['semantic']['passed']
    finally:ledger.close()


def test_compiler_cannot_hide_raw_plan_failure(frozen,tmp_path):
    _,base=verify_snapshot(frozen);case=EvaluationCase.model_validate_json(canonical(base['cases'][0]))
    ledger=CallLedger(tmp_path/'calls.db',ModelBudget(),{})
    try:
        r=run_cell(frozen,tmp_path/'cell',case,'with',endpoint(),ledger,
            transport=FixturePlanningTransport(omit_step=True))
        assert r['behavior']['passed'] and r['phase_a_semantic']['passed']
        assert not r['base_semantic']['passed'] and not r['semantic']['passed']
    finally:ledger.close()


def test_simulator_config_cannot_be_run_as_real(frozen,tmp_path):
    cfg=tmp_path/'config.json';cfg.write_text(canonical({'endpoints':[endpoint().model_dump(mode='json')]}))
    report=evaluate(frozen,tmp_path/'report',cfg)
    assert report['ledger']['attempts']==0 and report['E12']=='NOT_RUN'


def test_missing_binding_remains_not_run(frozen,tmp_path,monkeypatch):
    monkeypatch.delenv('NANA_S5_DEV_UNAVAILABLE',raising=False)
    cfg=tmp_path/'config.json';cfg.write_text(canonical({'endpoints':[{'alias':'a','base_url':'https://example.invalid/v1',
        'model':'declared-dev','account_scope':'development','funding':'existing_quota','service_kind':'real_model',
        'credential_env':'NANA_S5_DEV_UNAVAILABLE'}]}))
    report=evaluate(frozen,tmp_path/'report',cfg)
    assert report['ledger']['attempts']==0 and report['E12']=='NOT_RUN'
