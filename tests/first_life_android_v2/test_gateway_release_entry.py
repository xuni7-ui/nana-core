"""Registered release selection before auth or any Subject access."""
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from nana_core.life.live_api.contracts import ApiError, Binding, Realm
from nana_core.life.live_api.release_entry import gateway_release, follow_gateway_release
from nana_core.life.live_api.state import AtomicDocument
from nana_core.life.live_api.supervisor import Release


def setup(tmp_path, *, production=False, sealed_entry=True):
    host = tmp_path/'host'; host.mkdir(mode=0o700, parents=True)
    slot = tmp_path/'slot'; slot.mkdir(mode=0o700)
    entry = slot/'src/nana_core/life/live_api/__main__.py'
    entry.parent.mkdir(parents=True); entry.write_text('# synthetic entry\n')
    (slot/'src/nana_core/life/__main__.py').write_text('# synthetic runtime entry\n')
    (slot/'host_gateway.py').write_text('# synthetic immutable bootstrap\n')
    (slot/'runtime.json').write_text(json.dumps({'source_commit':'a'*40}))
    paths = ['src/nana_core/life/live_api/__main__.py', 'src/nana_core/life/__main__.py', 'runtime.json']
    if sealed_entry: paths.append('host_gateway.py')
    sums = ''.join(hashlib.sha256((slot/p).read_bytes()).hexdigest()+'  '+p+'\n' for p in paths)
    (slot/'SHA256SUMS').write_text(sums)
    release = Release(release_id='next', source_commit='a'*40, root=str(slot), python=sys.executable,
        integrity_digest=hashlib.sha256(sums.encode()).hexdigest())
    cfg = SimpleNamespace(host_state=str(host), active_release='next', releases=(release,),
        binding=Binding(subject_id='synthetic-subject', lineage_binding='b'*64,
            realm=Realm.PRODUCTION if production else Realm.DEVELOPMENT))
    return cfg, release


def test_selection_without_state_does_not_create_host_files(tmp_path):
    cfg, target = setup(tmp_path)
    before = list(Path(cfg.host_state).iterdir())
    assert gateway_release(cfg, current_root=tmp_path/'old')==target
    assert list(Path(cfg.host_state).iterdir())==before
    assert gateway_release(cfg, current_root=Path(target.root)) is None


def test_existing_active_snapshot_overrides_old_baked_selection_and_does_not_write(tmp_path):
    cfg, target = setup(tmp_path)
    cfg.active_release = 'old-baked-slot'
    path = Path(cfg.host_state)/'supervisor.json'
    AtomicDocument(path, {'schema_version':1, 'revision':7, 'active_release':'next'})
    before = {p.name:p.read_bytes() for p in path.parent.iterdir()}
    assert gateway_release(cfg, current_root=tmp_path/'old')==target
    assert {p.name:p.read_bytes() for p in path.parent.iterdir()}==before
    AtomicDocument(path, {}).update(lambda state: state.update(active_release='unregistered'))
    with pytest.raises(ApiError, match='RELEASE_REGISTRY_INVALID'):
        gateway_release(cfg, current_root=tmp_path/'old')


def test_production_target_must_seal_the_entry_and_keep_its_bytes(tmp_path):
    cfg, target = setup(tmp_path, production=True, sealed_entry=False)
    with pytest.raises(ApiError, match='GATEWAY_RELEASE_SEAL_REQUIRED'):
        gateway_release(cfg, current_root=tmp_path/'old')
    cfg, target = setup(tmp_path/'qualified', production=True)
    assert gateway_release(cfg, current_root=tmp_path/'old')==target
    (Path(target.root)/'host_gateway.py').write_text('# modified\n')
    with pytest.raises(ApiError, match='RELEASE_INTEGRITY_MISMATCH'):
        gateway_release(cfg, current_root=tmp_path/'old')


def test_exec_replaces_one_bootstrap_and_preserves_explicit_fd_without_reading(tmp_path, monkeypatch):
    cfg, target = setup(tmp_path)
    monkeypatch.setattr('nana_core.life.live_api.release_entry.gateway_release', lambda cfg:target)
    monkeypatch.delenv('NANA_GATEWAY_REEXEC', raising=False)
    rfd, wfd = os.pipe()
    try:
        os.set_inheritable(rfd, True)
        monkeypatch.setattr(sys, 'argv', ['old-entry', '--config', 'host.json', '--password-fd', str(rfd)])
        called=[]
        monkeypatch.setattr(os, 'execv', lambda python, argv:called.append((python, argv)))
        follow_gateway_release(cfg)
        assert called==[(target.python, [target.python, '-I', '-B', str(Path(target.root)/'host_gateway.py'),
            '--config', 'host.json', '--password-fd', str(rfd)])]
        assert os.get_inheritable(rfd)
        with pytest.raises(ApiError, match='GATEWAY_RELEASE_SELECTION_LOOP'):
            follow_gateway_release(cfg)
        assert len(called)==1
    finally:
        os.close(rfd); os.close(wfd)
        os.environ.pop('NANA_GATEWAY_REEXEC', None)
