import json
from pathlib import Path
import pytest
from tools.nana_astrbot_shadow.package import verify_package
from tools.nana_host_shadow.safety import digest
from tools.nana_astrbot_shadow.harness import run


def minimal(root):
    root.mkdir(mode=0o700)
    (root/'observer.py').write_text('# synthetic immutable file\n')
    hashes={'observer.py':digest((root/'observer.py').read_bytes())}
    manifest={'files':hashes}
    (root/'manifest.json').write_text(json.dumps(manifest))
    (root/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in sorted(hashes.items()))+digest((root/'manifest.json').read_bytes())+'  manifest.json\n')

def test_package_hash_exact_file_list_and_runtime_artifact_rejection(tmp_path):
    root=tmp_path/'package';minimal(root);verify_package(root)
    (root/'unexpected.db').write_bytes(b'synthetic SQLite marker')
    with pytest.raises(ValueError,match='INTEGRITY'):verify_package(root)
    (root/'unexpected.db').unlink();(root/'observer.py').write_text('# tamper\n')
    with pytest.raises(ValueError,match='INTEGRITY'):verify_package(root)

def test_package_symlink_never_follows_production_path(tmp_path):
    root=tmp_path/'package';minimal(root)
    body=(root/'observer.py').read_text();(root/'observer.py').unlink()
    unrelated=tmp_path/'synthetic-unrelated';unrelated.write_text(body)
    (root/'observer.py').symlink_to(unrelated)
    with pytest.raises(ValueError,match='SYMLINK'):verify_package(root)

def test_actual_neutral_harness_receipt_restart_and_unload(tmp_path):
    first=run(tmp_path/'shadow');second=run(tmp_path/'shadow')
    assert first['identity_id']==second['identity_id']
    assert first['proof']['stages'][4]['observation_id']==second['proof']['stages'][4]['observation_id']
    assert first['verification']['status']==second['verification']['status']=='SIMULATED_BINDING_PROOF_PASS'
    assert first['verification']['core_links_verified'] and second['verification']['core_links_verified']
    assert first['observer_removed'] and first['store_closed'] and first['host_binding']=='UNVERIFIED'
    assert first['production_calls']==first['private_records_read']==first['real_model_calls']==0
    assert first['proof']['probe_class']=='C'
