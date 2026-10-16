import json,subprocess,sys
from pathlib import Path
from nana_core.presence.living_demo import run_demo
from nana_core.presence.contracts import RuntimeConfig,LivingRuntimeConfig


def test_complete_no_input_life_causal_learning_and_relationship_boundaries(tmp_path):
    report=run_demo(tmp_path)
    checks=('primary_user_influences_choice','social_desire_preserved','relationship_did_not_grant','rest_is_valid','no_input_goal','wanted_but_manager_blocked','revocation_did_not_execute','quality_failure_observed','learned_replanning_succeeded','offline_skill_extension','surfaces_same_identity','no_input_runtime_present','restart_identity_stable','restart_fresh_epoch','no_authority_recreated','maintenance_yields_to_user','maintenance_resumes')
    assert all(report[k] for k in checks),report
    assert report['pending_intentions']<=8 and report['model_calls']==0


def test_bounded_real_process_run_heartbeats_and_shutdown(tmp_path):
    path=tmp_path/'subject'/'self.db';config=RuntimeConfig(schema_target=11,living=LivingRuntimeConfig(),scopes=('lab',),entity_id='synthetic-person',lease_us=200000,heartbeat_us=20000,review_interval_us=100000)
    conf=tmp_path/'config.json';conf.write_text(config.model_dump_json())
    env={'PYTHONPATH':str(Path('src').resolve())}
    common=[sys.executable,'-m','nana_core.presence.cli']
    subprocess.run([*common,'init-synthetic','--db',str(path),'--config',str(conf)],check=True,env=env,capture_output=True,timeout=5)
    run=subprocess.run([*common,'run','--db',str(path),'--config',str(conf),'--max-seconds','0.35'],check=True,env=env,capture_output=True,timeout=5)
    assert json.loads(run.stdout)['status']=='STOPPED'
    import sqlite3
    with sqlite3.connect(path) as db:
        state,acquired,heartbeat=db.execute('SELECT state,acquired_at_us,heartbeat_at_us FROM runtime_lease').fetchone()
        assert state=='STOPPED' and heartbeat>acquired
