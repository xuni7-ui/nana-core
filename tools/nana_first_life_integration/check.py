"""Historical 0c6 checkpoint consistency, not the current readiness decision.

Current ONE_SHOT handoff: tools.nana_first_life_live_response.check. Historical
failure payloads stay unchanged; a later successful call cannot rewrite them.
"""
import hashlib,json,subprocess
from pathlib import Path
from tools.nana_foundation_audit.check import check as framework_check
R=Path(__file__).resolve().parents[2]
E=R/'docs/nana_first_life_integration_v1_evidence'


def check():
    framework=framework_check();q=json.loads((E/'qualification.json').read_text())
    assert q['base']=='8a1e2cfba3c71d7f397ac8486e4565a915959cb5'
    assert q['schema_version']==13 and q['business_tables']==43 and q['new_tables']==q['new_dependencies']==0
    assert q['new_provider_calls']==1 and q['human_review']=='NOT_RUN'
    assert q['first_life_core_integration']=='PARTIAL' and not q['human_question_sent']
    assert not q['first_life_experience_ready'] and not q['first_life_integration_qualified'] and not q['beta_ready']
    assert not q['production'] and not q['private_data_accessed']
    journey=json.loads((E/'process_journey.json').read_text())
    assert journey['source_hashes_unchanged_and_match_commit'] and journey['duration_seconds']>=1800
    assert journey['same_identity_through_all_stages'] and journey['actions']==journey['verified_actions']==42
    assert journey['owned_dev_effects']==14 and journey['no_duplicate_effect']
    assert journey['fixture_semantic']['execution']=='SYNTHETIC_LOOPBACK_NOT_LIVE'
    assert journey['fixture_semantic']['withdrawn']=='UNKNOWN' and journey['fixture_semantic']['after_choice']=='NO_ACTION'
    assert journey['manager']['original_normative']=='ENDORSED' and journey['manager']['result']=='BLOCK'
    assert journey['private_intent']['withheld'] and journey['private_intent']['inspector_read_only']
    assert journey['actual_sigkill_restart']['no_action_replay'] and journey['restored_subject']['grants_all_revoked']
    assert journey['experience_outcomes']['FAILURE']>0 and journey['experience_outcomes']['SUCCESS']>0
    assert journey['strategy_assessments']['COUNTEREXAMPLE']>0 and journey['strategy_assessments']['SUCCESS']>0 and journey['code_skill_records']>0
    prepare=json.loads((E/'review_entry.json').read_text())
    assert prepare['identity_id']==journey['identity_id'] and prepare['primary_user_salience']=='HIGH'
    assert not prepare['role_grants_authority'] and prepare['framing']['state']=='REFRAME'
    assert prepare['framing']['judgment']=='ALTERNATIVE' and prepare['provider_calls']==0
    live=json.loads((E/'live_cognition.json').read_text())
    assert live['actual_new_calls']==1 and live['retry']==live['fallback']==0
    call=live['calls'][0]
    assert call['http']['response_http_status']==200 and call['http']['latency_ms']<=15000
    assert call['requested_model']==call['allowlisted_metadata']['model_returned']=='deepseek-flash'
    assert live['semantic']['state']=='FAILED' and live['semantic']['error_code']=='PROVIDER_MALFORMED'
    assert live['post_process']['new_goal_action_grant_counts_unchanged']
    assert live['post_process']['foreign_key_violations']==0 and live['post_process']['requests']==2
    assert not live['human_question_sent'] and live['secret_audit']['exact_matches']==0
    audit=json.loads((E/'security_audit.json').read_text())
    assert audit['secret_audit']['exact_matches']==0 and not audit['secret_audit']['persisted'] and audit['provider_calls']==0
    assert q['final_regression']['failed']==0 and q['focused']['failed']==0
    # Foundation and governance are not rewritten by the integration gate.
    assert not subprocess.check_output(['git','diff',q['base'],'--','PROJECT_BRAIN/00_MASTER_FRAMEWORK.md','PROJECT_BRAIN/01_CAPABILITY_MATRIX.md','src/nana_core/storage','pyproject.toml'],cwd=R)
    m=json.loads((E/'manifest.json').read_text())
    assert 'PROJECT_BRAIN/09_STATE.md' not in m['files'] and str((E/'manifest.json').relative_to(R)) not in m['files']
    for name,sha in m['files'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==sha,name
    return {'result':'PASS','scope':'HISTORICAL_0C6_CHECKPOINT_NOT_CURRENT_READINESS','master_and_63_definitions_unchanged':framework['definitions_unchanged'],'offline_process_scope':'PASS','human_review':'NOT_RUN','live_current_subject_semantic':'FAILED_STRICT_SCHEMA_NO_PROMOTION','first_life_integration_qualified':False,'first_life_experience_ready':False,'beta_ready':False,'new_provider_calls':1}

if __name__=='__main__':print(json.dumps(check(),indent=2))
