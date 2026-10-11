import copy
from datetime import datetime,timezone
import pytest
from tools.nana_astrbot_shadow.proof import BindingRecorder,verify,TRUSTED_NANA_RECEIPTS

def proof():
    r=BindingRecorder('a'*64,'b'*64)
    r.add('registry_before',{'callback_present':False,'registry_digest':'c'*64})
    r.add('registry_after_register',{'callback_present':True,'registry_digest':'d'*64})
    dispatch={'probe_id':'nana-probe-development-v1','event_id':'e'*64,'event_timestamp':None,'event_source':'operator_probe'}
    r.add('dispatch',{**dispatch,'synthetic':True,'external_delivery':False})
    r.add('callback',{**dispatch,'observer_received_at':datetime.now(timezone.utc).isoformat()})
    r.add('core',dict(core_evidence_id='f'*64,observation_id='11111111-1111-4111-8111-111111111111',goal_candidate_id='1'*64,
                      shadow_plan_id='cloud.shadow:'+'2'*64+'#plan_draft',shadow_decision_id='cloud.shadow:'+'2'*64,metadata_hash='3'*64))
    r.add('dedup',{'dedup_result':'DUPLICATE','observation_id':'11111111-1111-4111-8111-111111111111'})
    r.add('barrier',{'barrier_result':'SHADOW_BLOCKED','zero_execution_counts':dict.fromkeys(('actions','attempts','grants','budgets','strategies'),0)})
    r.add('registry_after_unregister',{'callback_present':False,'registry_digest':'c'*64})
    return r.export()

def test_simulation_cannot_promote_by_origin_field_or_dispatch_class():
    p=proof();assert verify(p)['status']=='SIMULATED_BINDING_PROOF_PASS'
    p['evidence_origin']='real_astrbot_runtime';p['probe_class']='A'
    assert verify(p)['host_binding']=='UNVERIFIED' and verify(p)['status']=='HOST_ORIGIN_UNTRUSTED'
    assert not TRUSTED_NANA_RECEIPTS
    with pytest.raises(ValueError,match='REVIEWED_NANA'):BindingRecorder('a'*64,'b'*64,evidence_origin='real_astrbot_runtime',probe_class='A')

@pytest.mark.parametrize('index',range(8))
def test_each_chain_gate_required(index):
    p=proof();del p['stages'][index]
    assert verify(p)['host_binding']=='UNVERIFIED' and verify(p)['missing']

def test_extra_private_field_and_changed_links_are_rejected():
    p=proof();p['stages'][3]['content']='synthetic-private-canary'
    assert verify(p)['missing'] and verify(p)['host_binding']=='UNVERIFIED'
    p=proof();p['stages'][3]['event_id']='9'*64
    assert 'CALLBACK_event_id' in verify(p)['missing']
    p=proof();p['stages'][7]['callback_present']=True
    assert 'registry_after_unregister' in verify(p)['missing']
