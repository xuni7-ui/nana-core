from .migrations import run

def test_v7_v8_upgrade_restore_and_privacy_journal(tmp_path):
 report=run(tmp_path/'migration')
 assert all(x['result']=='PASS' for x in report['checks'])
 assert report['v9_new_business_tables']==0
