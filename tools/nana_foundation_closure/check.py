"""Frozen criteria, current closure evidence and sanitized change manifest checks."""
import hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path
from tools.nana_foundation_audit.check import check as check_definitions
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'docs/nana_foundation_closure_v1_evidence'


def check():
    frozen=check_definitions()
    audit=json.loads((ROOT/'docs/nana_master_framework_foundation_audit_v1_evidence/audit.json').read_text())
    statuses={c['id']:c['status'] for d in audit['domains'] for c in d['criteria']}
    assert len(statuses)==63
    assert statuses['S3-C09']==statuses['S6-C07']=='FOUNDATION_QUALIFIED'
    assert statuses['S4-C06']=='FOUNDATION_QUALIFIED'
    assert statuses['S5-C06']=='FOUNDATION_QUALIFIED'
    assert not subprocess.check_output(['git','diff','edda7d08','--','src/nana_core/storage','pyproject.toml'],cwd=ROOT)
    manifest=json.loads((E/'manifest.json').read_text())
    assert 'PROJECT_BRAIN/09_STATE.md' not in manifest['files']
    for name,value in manifest['files'].items():
        assert name!='docs/nana_foundation_closure_v1_evidence/manifest.json'
        raw=(ROOT/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==value,name
        assert not re.search(rb'sk-[A-Za-z0-9_-]{16,}',raw),name
    q=json.loads((E/'qualification.json').read_text())
    assert q['new_paid_provider_calls']==1 and q['status']=='FOUNDATION_CLOSURE_COMPLETE'
    live=json.loads((E/'semantic_chain_live.json').read_text())
    assert live['new_provider_calls']==1 and live['retry']==live['fallback']==0
    assert live['qualification']=='CONTROLLED_TEXT_SEMANTIC_CHAIN_PASS'
    assert live['evidence_level']=='REAL_PROVIDER_CURRENT_LINEAGE_CONTROLLED_PROJECT_SOURCE'
    assert live['http']['response_http_status']==200
    assert 0<live['http']['latency_ms']<=15000
    assert live['route']['effective']['timeout_ms']<=15000
    assert live['reservation_usd_micro']<=50000
    assert live['semantic_source_kind']=='MODEL_DERIVATION'
    assert live['world_before']=='SUPPORTED_BELIEF' and live['world_after']=='UNKNOWN'
    assert not live['concern_after_withdrawal'] and live['after_intention']=='NO_ACTION'
    assert live['effect_counts_unchanged'] and live['exact_secret_match_count']==0
    assert live['identity_id']==live['reopen']['identity_id']
    assert live['reopen']['cognitive_requests']==live['prior']['cognitive_requests']+1==20
    assert live['reopen']['request_rows_for_this_request']==live['reopen']['cycle_rows_for_this_cycle']==1
    assert live['reopen']['new_dispatch_after_reopen']==live['reopen']['foreign_key_violations']==0
    assert q['s1_to_s9_foundation_qualified'] and q['foundation_closure_complete']
    assert q['ready_for_first_life_integration_qualification']
    assert all(d['foundation_status']=='FOUNDATION_QUALIFIED' and all(c['status']=='FOUNDATION_QUALIFIED' for c in d['criteria']) for d in audit['domains'] if d['id']!='S10')
    assert q['human_review']=='NOT_RUN' and q['first_life_experience_ready']=='NOT_READY'
    final=json.loads((E/'staging_final_verification.json').read_text())
    assert final['result']=='PASS_S4_C06_FROZEN_DEV_24H'
    assert final['duration_seconds']>=86400 and final['exit_code']==0
    assert final['source_pin']['head']=='645899b32220e66a702e75d59a279a3a9685693f'
    assert final['source_pin']['start_end_current_git_matches'] and final['source_pin']['attested_files']==205
    assert final['source_pin']['supervisor_checked_separately']
    assert final['samples']>=1440 and final['max_sample_gap_seconds']<120
    assert final['actions']==42 and final['owned_dev_effects']==14 and final['final_queue']==final['unknown_effects']==0
    assert final['actual_sigkill_restart']['no_action_replay'] and final['actual_sigkill_restart']['no_new_grant']
    assert all(d['quick_check']=='ok' and d['foreign_key_violations']==0 for d in final['database'].values())
    assert final['source_retired'] and final['restored_grants_revoked'] and final['database']['backup']['quarantined_review_copy']
    assert final['backup_delete_propagation'] and final['new_provider_calls']==0 and not final['staging_modified']
    assert final['human_review']=='NOT_RUN' and not final['production']
    assert q['schema_version']==13 and q['business_tables']==43
    assert q['new_business_tables']==q['new_dependencies']==0
    assert q['full_regression']['failures']==q['full_regression']['errors']==0
    return {'result':'PASS','criteria':dict(Counter(statuses.values())),'framework_bytes_unchanged':frozen['framework_bytes_unchanged'],'fixed_criteria_unchanged':True,'fingerprinted_files':len(manifest['files']),'new_paid_provider_calls':1,'foundation_closure':'COMPLETE_IN_DECLARED_SCOPE'}

if __name__=='__main__':print(json.dumps(check(),indent=2))
