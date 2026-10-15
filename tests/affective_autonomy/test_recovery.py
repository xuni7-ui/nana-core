from .recovery import run

def test_actual_sigkill_six_dangerous_cuts(tmp_path):
 report=run(tmp_path/'crash')
 assert len(report['cuts'])==6 and all(x['result']=='PASS' for x in report['cuts'])
