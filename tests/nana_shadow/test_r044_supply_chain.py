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
