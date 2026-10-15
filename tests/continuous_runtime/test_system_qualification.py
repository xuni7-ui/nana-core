from nana_core.presence.qualification import run
from nana_core.presence.process_qualification import wall_soak,crash_matrix


def test_same_subject_many_behaviors_and_virtual_runtime_life(tmp_path):
    report=run(tmp_path/'life')
    assert all(report['checks'].values()),report['checks']
    assert len(report['scenario_matrix'])==10
    assert {'EXPLORE','CREATE','REST','STAY_SILENT','CONTINUE_PROJECT','SEEK_CAPABILITY'}<=set(report['distinct_behaviors'])
    assert report['72h']['new_user_events']==0 and report['72h']['calls']==0
    assert report['E12']=='NOT_RUN' and report['real_external_actions']==0


def test_actual_wall_process_soak_and_crash_recovery(tmp_path):
    soak=wall_soak(tmp_path/'wall')
    assert all(soak['checks'].values())
    assert soak['heartbeat_progressed'] and soak['double_start_blocked'] and soak['graceful_shutdown'] and soak['no_active_worker']
    assert soak['fd_growth']<=2
    matrix=crash_matrix(tmp_path/'crashes')
    assert len(matrix)==4 and all(x['identity_stable'] and x['integrity']=='ok' and x['zero_actions'] for x in matrix)
