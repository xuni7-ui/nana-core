"""Final artifacts must prove more than elapsed wall time; no live staging access."""
import copy
import pytest
from tools.nana_foundation_closure.staging_verify import PIN_HEAD,validate_final


def fixture():
    actions=[{'idempotency_key':str(i)} for i in range(42)]
    final={'actions':actions,'goals':[{'state':'COMPLETED'}]*12,'queue_depth':0,'cognition_calls':0,'fk_violations':[],'identity_id':'synthetic'}
    result={'source_head':PIN_HEAD,'actual_residency_seconds':86405,'selected_source_unchanged':True,'source_hashes_start':{'x':'digest'},'source_hashes_end':{'x':'digest'},'new_provider_calls':0,'real_social_sends':0,'production_changes':0,'human_review':'NOT_RUN','final':final,'at_work_complete':copy.deepcopy(final),'before_stop':copy.deepcopy(final),'final_life':{'unknown_actions':[]},'actual_sigkill_restart':{'same_identity':True,'no_action_replay':True,'no_new_grant':True,'new_epoch':3,'old_epoch':2},'actual_external_effects':14,'backup_delete_propagation':True,'restored_subject':{'identity_id':'synthetic','grants_all_revoked':True,'same_history':True,'provider_configuration_transferred':False},'samples':[{'elapsed_seconds':i,'model_calls':0,'queue':0,'pending_intentions':4,'actions':42} for i in range(0,86401,60)]}
    return {'state':'PASS_24H_DEV','exit_code':0},result


def test_complete_artifact_accepted():
    progress,result=fixture()
    assert validate_final(progress,result)['duration_seconds']==86405


@pytest.mark.parametrize('fault,expected',[
    ('short','INSUFFICIENT_ACTUAL_DURATION'),('failed_exit','FINAL_EXIT_NOT_QUALIFIED'),
    ('pin','WRONG_PIN'),('replay','ACTION_REPLAY'),('unknown','UNKNOWN_EFFECT'),
    ('resource_gap','RESOURCE_SAMPLE_GAP'),('restore_grant','RESTORE_AUTHORITY_FAILED'),
])
def test_duration_cannot_hide_missing_final_evidence(fault,expected):
    progress,result=fixture()
    if fault=='short':result['actual_residency_seconds']=86399
    elif fault=='failed_exit':progress['exit_code']=1
    elif fault=='pin':result['source_head']='different'
    elif fault=='replay':result['final']['actions'].append({'idempotency_key':'extra'})
    elif fault=='unknown':result['final_life']['unknown_actions']=['unverified']
    elif fault=='resource_gap':del result['samples'][10:20]
    elif fault=='restore_grant':result['restored_subject']['grants_all_revoked']=False
    with pytest.raises(ValueError,match=expected):validate_final(progress,result)
