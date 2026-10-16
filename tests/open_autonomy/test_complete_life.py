from nana_core.presence.open_demo import run_demo

def test_real_cross_domain_service_calls_and_learning_change_future_behavior(tmp_path):
    report=run_demo(tmp_path)
    assert all(value for value in report.values() if type(value) is bool)
    assert report['goal_states']==['COMPLETED']*3
    assert len(report['learning_comparison'])==2
    assert {c['cause'] for c in report['learning_comparison']}=={'VERIFIED_FAILURE','SOURCED_INTEREST_OR_GAP'}
    assert all(c['baseline_passed']==0 and c['transfer_passed']==1 for c in report['learning_comparison'])
    assert report['actions']==10 and report['model_calls']==0
