"""Offline checkpoint consistency; does not qualify a Provider or human review."""
import ast,hashlib,json,subprocess
from pathlib import Path
from tools.nana_foundation_audit.check import check as foundation
R=Path(__file__).resolve().parents[2];E=R/'docs/nana_first_life_live_response_v1_evidence'
BASE='0c6bb44580563976b066671a34e3689d386da023'


def check():
    f=foundation();q=json.loads((E/'qualification.json').read_text());old=json.loads((E/'old_response_forensics.json').read_text())
    assert q['base']==BASE and q['schema_version']==13 and q['business_tables']==43
    assert q['new_tables']==q['new_dependencies']==q['new_provider_calls_this_mission']==0
    assert q['remaining_authorized_call_slots']==7 and not q['historical_key_search']
    assert q['human_review']=='NOT_RUN' and not q['human_question_sent']
    assert not q['first_life_experience_ready'] and not q['first_life_integration_qualified'] and not q['beta_ready']
    assert old['strict_schema_failure_field']=='UNKNOWN_NOT_CAPTURED' and not old['raw_body_reconstructed']
    source='src/nana_core/continuity/world_loop/cognition.py'
    classes={'CognitionBudget','CognitionRequest','InterestProposal','StructuredProposal','HTTPObservation','CognitionReply'}
    def dtos(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name in classes}
    assert dtos(subprocess.check_output(['git','show',BASE+':'+source],cwd=R,text=True))==dtos((R/source).read_text())
    assert not subprocess.check_output(['git','diff',BASE,'--','PROJECT_BRAIN/00_MASTER_FRAMEWORK.md','PROJECT_BRAIN/01_CAPABILITY_MATRIX.md','src/nana_core/storage','pyproject.toml'],cwd=R)
    assert q['focused']['failed']==q['full_regression']['failed']==0
    snap=json.loads((E/'subject_checkpoint.json').read_text())
    assert snap['identity_id']=='37281abf-18c0-4460-b1de-566d3e0734b7' and snap['request_records']==2 and snap['installed_grants']==0
    assert snap['inspector_read_only'] and snap['db_wal_privacy_hashes_unchanged'] and snap['foreign_key_violations']==0
    m=json.loads((E/'manifest.json').read_text());assert 'PROJECT_BRAIN/09_STATE.md' not in m['files']
    for name,sha in m['files'].items():assert name!='docs/nana_first_life_live_response_v1_evidence/manifest.json' and hashlib.sha256((R/name).read_bytes()).hexdigest()==sha,name
    return {'result':'PASS_OFFLINE_CHECKPOINT','semantic_DTOs_unchanged':True,'frozen_criteria_unchanged':f['definitions_unchanged'],'new_provider_calls':0,'remaining_slots':7,'external_gate':'NO_CURRENT_SAFE_CREDENTIAL_BINDING','experience_ready':False,'human_review':'NOT_RUN'}

if __name__=='__main__':print(json.dumps(check(),indent=2))
