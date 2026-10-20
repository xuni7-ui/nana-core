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
    assert statuses['S4-C06']==statuses['S5-C06']=='UNKNOWN_AUDIT_REQUIRED'
    assert not subprocess.check_output(['git','diff','edda7d08','--','src/nana_core/storage','pyproject.toml'],cwd=ROOT)
    manifest=json.loads((E/'manifest.json').read_text())
    assert 'PROJECT_BRAIN/09_STATE.md' not in manifest['files']
    for name,value in manifest['files'].items():
        assert name!='docs/nana_foundation_closure_v1_evidence/manifest.json'
        raw=(ROOT/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==value,name
        assert not re.search(rb'sk-[A-Za-z0-9_-]{16,}',raw),name
    q=json.loads((E/'qualification.json').read_text())
    assert q['new_paid_provider_calls']==0 and q['status']=='PARTIAL_TWO_QUALIFICATION_GATES_OPEN'
    assert q['schema_version']==13 and q['business_tables']==43
    assert q['new_business_tables']==q['new_dependencies']==0
    assert q['full_regression']['failures']==q['full_regression']['errors']==0
    return {'result':'PASS','criteria':dict(Counter(statuses.values())),'framework_bytes_unchanged':frozen['framework_bytes_unchanged'],'fixed_criteria_unchanged':True,'fingerprinted_files':len(manifest['files']),'new_paid_provider_calls':0,'foundation_closure':'PARTIAL'}

if __name__=='__main__':print(json.dumps(check(),indent=2))
