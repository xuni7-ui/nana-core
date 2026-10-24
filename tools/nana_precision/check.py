"""Read-only consistency check; no Store, Subject, provider, or effects."""
import argparse,hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'docs/nana_precision_v2_evidence'


def check(archive=None):
    manifest=json.loads((EVIDENCE/'manifest.json').read_text())
    for name,sha in manifest['files'].items():
        path=Path(name)
        assert not path.is_absolute() and '..' not in path.parts and name!='manifest.json'
        assert hashlib.sha256((EVIDENCE/path).read_bytes()).hexdigest()==sha, name
    q=json.loads((EVIDENCE/'qualification.json').read_text())
    assert q['model_ablation']=='MODEL_ABLATION_NOT_RUN' and q['new_paid_provider_calls']==0
    assert q['semantic_generalization']=='NOT_RUN' and q['human_naturalness']=='NOT_RUN'
    assert q['historical_residency']=='PARTIAL_EXTERNAL_LIMIT'
    assert q['long_real_residency']=='PENDING_EXTERNAL_STABLE_ENV'
    assert hashlib.sha256((ROOT/'PROJECT_BRAIN/00_MASTER_FRAMEWORK.md').read_bytes()).hexdigest()=='fe6efe121a05145b44178d5ec26b99430a28e873fca8d1b80f16671c65e5133c'
    assert not subprocess.check_output(['git','diff','d695ed7','--','docs/nana_real_world_controlled_expansion_v1_evidence'],cwd=ROOT)
    baseline=json.loads((EVIDENCE/'baseline-final.json').read_text())
    candidate=json.loads((EVIDENCE/'after.json').read_text())
    held_before=json.loads((EVIDENCE/'heldout-before.json').read_text())
    held_after=json.loads((EVIDENCE/'heldout-after.json').read_text())
    for before,after in ((baseline,candidate),(held_before,held_after)):
        assert before['evaluator_sha256']==after['evaluator_sha256']
        assert before['count']==after['count'] and before['feasible_count']==after['feasible_count']
        assert [c['request_sha256'] for c in before['cases']]==[c['request_sha256'] for c in after['cases']]
        assert after['verified_completions']>before['verified_completions']
        assert after['false_success']==0
    assert baseline['seed']!=held_after['seed']
    reg=json.loads((EVIDENCE/'regression.json').read_text())
    assert reg['final']['failed']==0 and reg['final']['errors']==0 and reg['final']['passed']>=1510
    assert reg['focused']['failed']==0
    fingerprints=json.loads((EVIDENCE/'source_fingerprints.json').read_text())
    for name,sha in fingerprints['files'].items():
        assert name.startswith('src/nana_core/') and '..' not in Path(name).parts
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha, name
    if archive:
        release=json.loads((EVIDENCE/'portable.json').read_text())
        assert hashlib.sha256(Path(archive).read_bytes()).hexdigest()==release['release']['sha256']
    return {'status':'PASS_SCOPED_PRECISION_EVIDENCE_CONSISTENCY','semantic_qualification':'NOT_RUN','residency_qualified':False,'files':len(manifest['files']),'runtime_source':fingerprints['source_commit'],'new_provider_calls':0,'store_opened':False,'archive_rehashed':bool(archive)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',type=Path);args=parser.parse_args();print(json.dumps(check(args.archive),indent=2))
