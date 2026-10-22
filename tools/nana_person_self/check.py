"""Validate this bounded technical handoff; never promote a human readiness gate."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from tools.nana_foundation_audit.check import check as foundation
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'docs/nana_persistent_person_self_v1_evidence'

def check(archive=None):
    assert foundation()['criteria']==63
    q=json.loads((E/'qualification.json').read_text());m=json.loads((E/'manifest.json').read_text())
    assert q['BASE_HEAD']=='ae3cb34d478caa62861d2a6b85ddf4ed2cc8f11e'
    assert q['REAL_PROVIDER_CALLS']==0 and q['HUMAN_REVIEW']=='NOT_RUN'
    assert q['SCHEMA_VERSION']==13 and q['BUSINESS_TABLES']==43 and q['NEW_BUSINESS_TABLES']==q['NEW_DEPENDENCIES']==0
    assert not q['PRODUCTION_CHANGED'] and not q['CURRENT_REFERENCE_SUBJECT_CHANGED']
    assert q['full_regression']['failed']==0 and q['focused']['failed']==0 and q['related']['failed']==0
    for name,sha in m['files'].items():
        assert name!='docs/nana_persistent_person_self_v1_evidence/manifest.json'
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    for name,sha in m['runtime_source_files'].items():
        assert hashlib.sha256(subprocess.check_output(['git','show',m['runtime_source_commit']+':'+name],cwd=ROOT)).hexdigest()==sha
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    assert len(json.loads((E/'heldout_conversations.json').read_text())['cases'])==20
    corpus=json.loads((E/'initial_corpus.json').read_text())
    assert corpus['accepted_real_samples']==0 and corpus['same_episode_not_independent_support']
    if archive:assert hashlib.sha256(Path(archive).read_bytes()).hexdigest()==q['bundle']['sha256']
    return {'result':'PASS_BOUNDED_TECHNICAL_HANDOFF','human_review':'NOT_RUN','new_provider_calls':0,'actual_mobile_web_binding':'NOT_IDENTIFIED','first_life_beta_upgraded':False,'archive_verified':archive is not None}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path);a=p.parse_args();print(json.dumps(check(a.archive),indent=2))
if __name__=='__main__':main()
