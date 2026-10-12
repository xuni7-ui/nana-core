"""Small immutable package/source-review integrity repros, no real trust minting."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import pytest
from tools.nana_astrbot_shadow.package import verify_package
from tools.nana_astrbot_shadow.onboarding import source_review
from tools.nana_host_shadow.safety import canonical,digest


def kit(root):
    root.mkdir(mode=0o700)
    p=root/'support.py';p.write_text('# synthetic inert support\n');p.chmod(0o600)
    m={'files':{'support.py':digest(p.read_bytes())}}
    manifest=root/'manifest.json';manifest.write_text(canonical(m));manifest.chmod(0o600)
    sums=root/'SHA256SUMS';sums.write_text(digest(p.read_bytes())+'  support.py\n'+digest(manifest.read_bytes())+'  manifest.json\n');sums.chmod(0o600)
    return root

@pytest.mark.parametrize('attack',['dangling_symlink','fifo','writable_support','writable_manifest','writable_directory'])
def test_integrity_rejects_unmanifested_or_writable_entries(tmp_path,attack):
    root=kit(tmp_path/'kit')
    if attack=='dangling_symlink':(root/'extra').symlink_to('absent')
    elif attack=='fifo':os.mkfifo(root/'extra',0o600)
    elif attack=='writable_support':(root/'support.py').chmod(0o666)
    elif attack=='writable_manifest':(root/'manifest.json').chmod(0o666)
    else:root.chmod(0o777)
    with pytest.raises(ValueError):verify_package(root)


def test_source_review_rejects_git_symlink_even_if_blob_is_valid_json(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,stderr=subprocess.DEVNULL).decode().strip()
    git('init');p=repo/'reviews/r042/synthetic.json';p.parent.mkdir(parents=True)
    p.symlink_to(canonical({'synthetic_only':True})) # intentionally canonical JSON symlink blob
    git('add','.');git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-m','Synthetic symlink review')
    sha=git('rev-parse','HEAD')
    with pytest.raises(ValueError,match='REGULAR_REVIEW'):source_review(repo,sha,'reviews/r042/synthetic.json')

@pytest.mark.parametrize('attack',['extra_file','missing','hardlink','support_change','manifest_change','sums_change','symlink_dir'])
def test_content_tamper_blocks_before_import(tmp_path,attack):
    root=kit(tmp_path/'kit')
    if attack=='extra_file':(root/'extra.py').write_text('# unexpected')
    elif attack=='missing':(root/'support.py').unlink()
    elif attack=='hardlink':os.link(root/'support.py',tmp_path/'linked.py')
    elif attack=='support_change':(root/'support.py').write_text('# changed')
    elif attack=='manifest_change':(root/'manifest.json').write_text('{}')
    elif attack=='sums_change':(root/'SHA256SUMS').write_text('invalid')
    else:(root/'extra-dir').symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises((ValueError,KeyError,OSError)):verify_package(root)


def test_mtime_drift_is_content_equivalent_not_an_authorization(tmp_path):
    root=kit(tmp_path/'kit');before=verify_package(root)
    os.utime(root/'support.py',(1,1))
    assert verify_package(root)==before


def test_git_commit_pins_old_bytes_despite_dirty_worktree_and_new_commit(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,stderr=subprocess.DEVNULL).decode().strip()
    git('init');p=repo/'reviews/r042/synthetic.json';p.parent.mkdir(parents=True)
    p.write_text(canonical({'origin':'FIXTURE','revision':1}));git('add','.')
    git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-m','Fixture source1');one=git('rev-parse','HEAD')
    p.write_text(canonical({'origin':'FIXTURE','revision':2}));git('add','.')
    git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-m','Fixture source2');two=git('rev-parse','HEAD')
    p.write_text('PRIVATE-SYNTHETIC-DIRTY-CANARY')
    assert source_review(repo,one,'reviews/r042/synthetic.json')=={'origin':'FIXTURE','revision':1}
    assert source_review(repo,two,'reviews/r042/synthetic.json')=={'origin':'FIXTURE','revision':2}
    # SHA substitution changes actual pinned bytes. Human approved SHA is external.
