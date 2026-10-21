"""Bounded evidence/optional artifact verification; no runtime/provider calls."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from tools.nana_foundation_audit.check import check as foundation
R=Path(__file__).resolve().parents[2];E=R/'docs/nana_portable_cloud_runtime_v1_evidence'
BASE='024e22649365560ef57e0f3fa82e41383d95d315'

def check(archive=None):
    f=foundation();q=json.loads((E/'qualification.json').read_text());b=json.loads((E/'bundle.json').read_text());m=json.loads((E/'migration_rehearsal.json').read_text());s=json.loads((E/'security.json').read_text());c=json.loads((E/'binding_and_package_contracts.json').read_text())
    assert q['base_head']==BASE and q['NEW_PROVIDER_CALLS']==0 and q['PORTABLE_CLOUD_BUNDLE_READY']=='YES'
    assert q['NEW_BUSINESS_TABLES']==q['NEW_DEPENDENCIES']==0 and q['SCHEMA_VERSION']==13
    assert q['runtime_source_commit']==b['source_commit']==b['rehearsed_runtime_source']
    assert q['focused']['failed']==q['full_regression']['failed']==0
    assert m['source_archive_sha256']==b['sha256'] and m['new_provider_calls']==0
    assert m['transfer']['same_identity'] and m['transfer']['source_retired'] and m['transfer']['old_start_rejected'] and m['transfer']['old_grants_revoked']
    assert m['transfer']['private_intent_continuity'] and not m['transfer']['private_content_displayed']
    assert all(m['closure'].values()) and m['process']['real_sigkill'] and m['process']['duplicate_start_blocked']
    assert m['process']['epochs']==sorted(set(m['process']['epochs']))
    assert s['secret_literal_matches']==0 and not s['private_files'] and not s['operational_codex_absolute_path_literals'] and not s['current_subject_migrated']
    assert all(v for k,v in c.items() if k not in {'new_provider_calls','real_keys_accessed'}) and c['new_provider_calls']==0 and not c['real_keys_accessed']
    assert not subprocess.check_output(['git','diff',BASE,'--','PROJECT_BRAIN/00_MASTER_FRAMEWORK.md','PROJECT_BRAIN/01_CAPABILITY_MATRIX.md','src/nana_core/storage','pyproject.toml'],cwd=R)
    manifest=json.loads((E/'manifest.json').read_text())
    assert manifest['runtime_source_commit']==b['source_commit']
    assert 'PROJECT_BRAIN/09_STATE.md' not in manifest['files']
    for name,sha in manifest['files'].items():assert name!='docs/nana_portable_cloud_runtime_v1_evidence/manifest.json' and hashlib.sha256((R/name).read_bytes()).hexdigest()==sha,name
    if archive is not None:assert hashlib.sha256(Path(archive).read_bytes()).hexdigest()==b['sha256']
    return {'result':'PASS_PORTABLE_DEVELOPMENT_CANDIDATE','frozen_framework_and_63criteria':f['definitions_unchanged'],'new_provider_calls':0,'actual_target_cloud':'NOT_RUN','human_review':'NOT_RUN','artifact_verified':archive is not None}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path);a=p.parse_args();print(json.dumps(check(a.archive),indent=2))
if __name__=='__main__':main()
