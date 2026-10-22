"""Validate bounded owned growth delivery; never upgrade human/production gates."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from tools.nana_foundation_audit.check import check as foundation
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'docs/nana_open_life_expansion_v1_evidence'

def check(archive=None):
    assert foundation()['criteria']==63
    q=json.loads((E/'qualification.json').read_text());m=json.loads((E/'manifest.json').read_text())
    assert q['STATUS']=='OFFLINE_CANDIDATE_READY' and q['GLOBAL_STAGE']=='H'
    assert q['SCHEMA_VERSION']==13 and q['BUSINESS_TABLES']==43
    assert q['NEW_BUSINESS_TABLES']==q['NEW_DEPENDENCIES']==q['NEW_PAID_PROVIDER_CALLS']==q['REAL_SOCIAL_SEND']==0
    assert q['HUMAN_REVIEW']=='NOT_RUN' and q['FIRST_LIFE_EXPERIENCE_READY']=='NOT_READY' and q['CLOUD_DAILY_LIFE_BETA_READY']=='NO'
    assert q['full_regression']['failed']==0 and q['focused']['failed']==0
    assert q['HUMAN_REVIEW_BLOCKS_CONSTRUCTION']=='NO'
    assert q['ONE_SUBJECT'] and q['ONE_STORE_AUTHORITY'] and q['ONE_SUBJECT_LOOP'] and q['ONE_RUNTIME_OWNER'] and q['D_WHEN_C_WHAT_WHY']
    for name,sha in m['files'].items():
        assert name!='docs/nana_open_life_expansion_v1_evidence/manifest.json'
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    fingerprints=json.loads((E/'runtime_source_fingerprints.json').read_text())
    for name,sha in fingerprints['files'].items():
        assert hashlib.sha256(subprocess.check_output(['git','show',fingerprints['runtime_source_commit']+':'+name],cwd=ROOT)).hexdigest()==sha
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    life=json.loads((E/'integrated_lifecycle.json').read_text())
    assert life['source_was_clean'] and life['runtime_driven_research']['driver_did_not_call_notice_gather_compare']
    assert life['lifecycle']['later_kernel_skill_uses']==2 and life['migration']['old_grants_revoked'] and life['migration']['withdrawn_content_not_revived']
    assert life['shared_presence']['delivered'] is False and life['source_withdrawal']['world_state']=='UNKNOWN'
    assert life['wall_residency']['duration_seconds']>=120
    soak=json.loads((E/'autonomous_life.json').read_text())['automatic_runtime_sources_virtual_soak']
    assert soak['days']==60 and soak['research_jobs']==2 and soak['max_pending']<=8 and soak['source_expiry_to_unknown']
    assert json.loads((E/'bundle.json').read_text())['reproducible_rebuild']
    if archive:assert hashlib.sha256(Path(archive).read_bytes()).hexdigest()==q['archive']['sha256']
    return {'result':'PASS_OWNED_OFFLINE_GROWTH_ONLY','criteria':63,'new_paid_calls':0,'human_review':'NOT_RUN','first_life_beta_upgraded':False,'runtime_source_commit':q['runtime_source_commit'],'archive_checked':archive is not None}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path);a=p.parse_args();print(json.dumps(check(a.archive),indent=2))
if __name__=='__main__':main()
