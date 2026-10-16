from .recovery import run


def test_actual_sigkill_and_restart_seven_checkpoints(tmp_path):
 result=run(tmp_path/'crash')
 assert len(result['cuts'])==7 and result['result']=='PASS'
