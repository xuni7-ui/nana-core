"""Committed synthetic source and wheels; verify archive bytes across host masks.

The tiny wheels are deliberately not installable. Actual native installation is
qualified separately with pinned public wheels and the original full manifest.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile

from tools.nana_portable_cloud import build as builder
from tools.nana_portable_cloud.unpack import unpack


def test_archive_is_identical_under_private_and_shared_creation_masks(tmp_path,monkeypatch):
    repo=tmp_path/'source';repo.mkdir()
    sources=['src/nana_core/example.py','src/nana_core/continuity/hands/server.py',
             'src/nana_core/continuity/hands/browser.py','src/nana_core/continuity/open_agency/skill_runner.py']
    for name in sources:
        p=repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# SYNTHETIC build fixture\n')
    packaging=repo/'packaging/portable';packaging.mkdir(parents=True)
    (packaging/'runtime-files.txt').write_text('\n'.join(sources)+'\n')
    for name in ('nana','preflight.sh'):(packaging/name).write_text('#!/bin/sh\n# SYNTHETIC fixture\n')
    unpacker=repo/'tools/nana_portable_cloud/unpack.py';unpacker.parent.mkdir(parents=True)
    unpacker.write_bytes(Path(builder.__file__).with_name('unpack.py').read_bytes())
    subprocess.run(['git','init','-b','fixture',str(repo)],check=True,capture_output=True)
    subprocess.run(['git','add','.'],cwd=repo,check=True)
    subprocess.run(['git','-c','user.name=Synthetic Fixture','-c','user.email=fixture@local',
        '-c','commit.gpgSign=false','commit','-m','Synthetic reproducibility inputs'],cwd=repo,check=True,capture_output=True)
    wheels=tmp_path/'wheels';wheels.mkdir()
    for name,version in builder.DEPENDENCIES.items():
        (wheels/(name.replace('-','_')+'-'+version+'-py3-none-any.whl')).write_bytes(b'SYNTHETIC NOT INSTALLABLE WHEEL '+name.encode())
    monkeypatch.setattr(builder,'REPO',repo)
    outputs=[];old=os.umask(0o022)
    try:
        for mask,name in ((0o022,'shared'),(0o077,'private')):
            os.umask(mask);outputs.append(builder.build(tmp_path/name,wheels))
    finally:os.umask(old)
    contents=[]
    for output in outputs:
        with tarfile.open(output['archive'],'r:gz') as archive:
            contents.append({m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive if m.isfile()})
    assert contents[0]==contents[1]
    assert outputs[0]['sha256']==outputs[1]['sha256']
    target=unpack(outputs[0]['archive'],tmp_path/'installed-fixture',outputs[0]['sha256'])
    assert target.stat().st_mode&0o077==0
    assert (target/'nana').stat().st_mode&0o777==0o700
    assert (target/'runtime.json').stat().st_mode&0o777==0o600
