from .migrations import run

def test_all_prior_development_schema_migrations_and_restore_quarantine(tmp_path):
 report=run(tmp_path/'migration')
 assert len(report['checks'])==5 and report['result']=='PASS'
