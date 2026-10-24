"""Read-only validation of committed controlled-world qualification evidence.

Historical test/residency pins remain explicit; this cannot turn later source
changes into a past runtime result. No DB opening, network or authority tokens.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'docs/nana_real_world_controlled_expansion_v1_evidence'
MASTER='fe6efe121a05145b44178d5ec26b99430a28e873fca8d1b80f16671c65e5133c'
GATES=set('CONTROLLED_WORLD_LAB GENERALIZED_BROWSER_HAND_V1 REALISTIC_RESEARCH LONG_HORIZON_AUTONOMOUS_PROJECT MULTI_HAND_PLANNING INDEPENDENT_VERIFY_EXPANDED FAILURE_RICH_RECOVERY UNKNOWN_DISCIPLINE REALISTIC_NOISY_LEARNING LEARNING_VALUE_SELECTION SELF_EXTENSION_V2 SKILL_LIFECYCLE PROACTIVE_SHARED_LIFE INDEPENDENT_LIFE_DEPTH ANTI_LOOP_RHYTHM MEMORY_AT_SCALE_V1 MEMORY_RETRIEVAL_SALIENCE RESOURCE_GROWTH_CONTROL LONG_REAL_RESIDENCY CRASH_CAMPAIGN ACTIVE_LIFE_MIGRATION MODEL_RESOURCE_SWAP MULTI_SURFACE_CONTINUITY SURFACE_CONCURRENCY GOVERNANCE_STRESS RESOURCE_ECONOMICS ADVERSARIAL_OPEN_LIFE'.split())


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_residency(result):
    assert result['exit_code']==0 and result['status']=='PASS_PINNED_OWNED_RESIDENCY'
    assert result['duration_seconds']>=result['requested_seconds']>=18000
    assert result['source_head_start']==result['source_head_end']
    required={'duration','foreign_keys_clean','no_action_replay','one_identity','quick_check','same_identity_restart','source_bytes_unchanged','source_head_unchanged','zero_provider'}
    assert required<=result['checks'].keys() and all(result['checks'][key] is True for key in required)
    samples=result['samples'];assert len(samples)>=2
    assert all(a['elapsed_seconds']<b['elapsed_seconds'] for a,b in zip(samples,samples[1:]))
    assert samples[-1]['elapsed_seconds']>=18000-90
    assert all(x['services_alive'] and x['provider_calls']==0 for x in samples)
    assert all(x['queue']<=32 and x['pending_opportunities']<=16 and x['pending_intentions']<=32 and x['fds']<=32 and x['threads']<=4 and x['max_rss_kib']<=131072 for x in samples)
    return True


def validate_interruption(proof):
    """Validate an explicitly incomplete observation, never qualify residency."""
    assert proof['status']=='PARTIAL_EXTERNAL_LIMIT' and proof['final_result_exists'] is False
    assert proof['old_pid_exists'] is False and proof['old_boot_id']!=proof['current_boot_id']
    assert proof['source_pin_unchanged'] is True and not proof['changed_source_files']
    assert proof['requested_seconds']>=18000 and proof['last_observed_elapsed_seconds_lower_bound']>=0
    assert proof['exact_exit_time_and_status']=='UNKNOWN'
    assert proof['original_final_fabricated'] is False and proof['time_stitched'] is False
    assert proof['replacement_soak_created'] is False
    assert proof['foreign_key_violations']==0 and proof['quick_check']=='ok'
    return True


def check(*,raw_residency=None,raw_progress=None,archive=None):
    manifest=json.loads((EVIDENCE/'manifest.json').read_text())
    files=manifest['files'];assert 'manifest.json' not in files
    assert set(files)=={p.name for p in EVIDENCE.iterdir() if p.is_file() and p.name!='manifest.json'}
    for name,digest in files.items():
        assert Path(name).name==name and sha(EVIDENCE/name)==digest
    qualification=json.loads((EVIDENCE/'qualification.json').read_text())
    assert qualification['scope']=='OWNED_DEV_AND_SYNTHETIC_SEMANTICS'
    gates=qualification['gates'];assert set(gates)==GATES
    partial=qualification['status']=='PARTIAL_EXTERNAL_LIMIT'
    assert all(value==('PARTIAL' if partial and key=='LONG_REAL_RESIDENCY' else 'PASS') for key,value in gates.items())
    assert qualification['human_review']=='NOT_RUN' and qualification['first_life_ready'] is False and qualification['beta_ready'] is False
    assert qualification['new_paid_provider_calls']==qualification['real_social_sends']==0
    assert qualification['private_data_accessed'] is False and qualification['production_changed'] is False
    assert sha(ROOT/'PROJECT_BRAIN/00_MASTER_FRAMEWORK.md')==MASTER
    fingerprints=json.loads((EVIDENCE/'source_fingerprints.json').read_text())
    assert fingerprints['source_commit']==qualification['runtime_source_commit']
    for name,digest in fingerprints['files'].items():
        path=ROOT/name
        assert name.startswith('src/nana_core/') and '..' not in Path(name).parts and not path.is_symlink()
        assert sha(path)==digest,'CURRENT_RUNTIME_DIFFERS_FROM_TESTED_PIN'
    for pin in (qualification['base_commit'],qualification['runtime_source_commit'],qualification['residency_source_commit']):
        subprocess.run(['git','cat-file','-e',pin+'^{commit}'],cwd=ROOT,check=True,capture_output=True)
    subprocess.run(['git','merge-base','--is-ancestor',qualification['base_commit'],'HEAD'],cwd=ROOT,check=True,capture_output=True)
    regression=json.loads((EVIDENCE/'regression.json').read_text())
    assert regression['full']['failed']==regression['full']['errors']==0 and regression['full']['passed']>0
    assert regression['new_focused']['failed']==regression['new_focused']['errors']==0
    residency=json.loads((EVIDENCE/'residency.json').read_text())
    assert residency['source_head_start']==qualification['residency_source_commit']
    if partial:
        proof=json.loads((EVIDENCE/'interruption.json').read_text());validate_interruption(proof)
        assert residency['status']=='PARTIAL_EXTERNAL_LIMIT' and residency['qualified'] is False
        assert residency['exit_code'] is None and residency['duration_seconds'] is None
        assert residency['last_observed_elapsed_seconds_lower_bound']==proof['last_observed_elapsed_seconds_lower_bound']
        assert not raw_residency,'MISSING_FINAL_RESULT_CANNOT_BE_REPLACED'
        if raw_progress:
            assert sha(raw_progress)==proof['raw_progress_sha256']
            progress=json.loads(raw_progress.read_text())
            assert progress['sample']['elapsed_seconds']==proof['last_observed_elapsed_seconds_lower_bound']
            assert progress['status']=='RUNNING_NOT_QUALIFIED' and progress['source_head']==qualification['residency_source_commit']
    else:
        assert qualification['status']=='OWNED_DEV_CANDIDATE_READY'
        assert residency['status']=='PASS_PINNED_OWNED_RESIDENCY'
        assert residency['duration_seconds']>=18000 and all(residency['checks'].values())
        assert not raw_progress
    assert residency['latest_release_exact_five_hours']=='NOT_RUN_SEPARATELY_QUALIFIED_DELTA'
    if raw_residency:
        assert sha(raw_residency)==residency['raw_result_sha256'];validate_residency(json.loads(raw_residency.read_text()))
    if archive:
        release=json.loads((EVIDENCE/'portable_release.json').read_text());assert sha(archive)==release['sha256']
    return {'status':'PASS_EVIDENCE_CONSISTENCY_PARTIAL_NOT_RESIDENCY_QUALIFIED' if partial else 'PASS_COMMITTED_CONTROLLED_WORLD_EVIDENCE','residency_qualified':not partial,'runtime_pin':qualification['runtime_source_commit'],'residency_pin':qualification['residency_source_commit'],'evidence_files':len(files),'current_runtime_bytes_equal_tested_pin':True,'raw_residency_revalidated':bool(raw_residency),'raw_interrupted_progress_revalidated':bool(raw_progress),'archive_rehashed':bool(archive),'new_provider_calls':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw-residency',type=Path);p.add_argument('--raw-progress',type=Path);p.add_argument('--archive',type=Path);a=p.parse_args();print(json.dumps(check(raw_residency=a.raw_residency,raw_progress=a.raw_progress,archive=a.archive),indent=2))
if __name__=='__main__':main()
