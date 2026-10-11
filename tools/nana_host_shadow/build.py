"""Build a source package from exactly the approved Git object, never HEAD."""
import argparse
from pathlib import Path
import subprocess
import shutil
from .safety import APPROVED_SHA, CORE_FINGERPRINT, canonical, digest, private_file, checked_path


def build(repo, destination):
    repo = checked_path(repo, directory=True)
    dest = checked_path(destination, directory=True, missing=True)
    if dest.exists():
        raise ValueError('BUNDLE_DESTINATION_MUST_BE_NEW')
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', APPROVED_SHA, 'src/nana_core'], cwd=repo, text=True).splitlines()
    blobs = {n: subprocess.check_output(['git', 'show', APPROVED_SHA + ':' + n], cwd=repo) for n in names}
    hashes = {n: digest(b) for n, b in blobs.items()}
    if digest(hashes) != CORE_FINGERPRINT:
        raise ValueError('APPROVED_SOURCE_MISMATCH')
    dest.mkdir(mode=0o700)
    for name, data in blobs.items():
        p = dest / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    support = dest / 'support' / 'nana_host_shadow'
    support.mkdir(parents=True)
    for p in Path(__file__).parent.glob('*.py'):
        shutil.copyfile(p, support / p.name)
    launcher = dest / 'nana-shadow'
    launcher.write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\nsys.dont_write_bytecode = True\nsys.path.insert(0, str(Path(__file__).resolve().parent / "support"))\nfrom nana_host_shadow.launcher import main\nmain()\n')
    launcher.chmod(0o700)
    extra = {str(p.relative_to(dest)): digest(p.read_bytes()) for p in support.glob('*.py')}
    extra['nana-shadow'] = digest(launcher.read_bytes())
    m = {'bundle_schema': 1, 'source_commit': APPROVED_SHA, 'core_fingerprint': CORE_FINGERPRINT,
         'core_files': hashes, 'support_files': extra, 'core_modified': False,
         'support_scope': 'separately reviewed operator probe tooling; not part of approved Core SHA',
         'installation': 'isolated import path; no pip/global dependency changes',
         'authenticity': 'Core hashes pinned in support; transport manifest must also be reviewed by operator'}
    private_file(dest / 'bundle_manifest.json', m)
    return {'source_commit': APPROVED_SHA, 'core_fingerprint': CORE_FINGERPRINT,
            'manifest_hash': digest((dest / 'bundle_manifest.json').read_bytes()), 'path': str(dest)}


def main():
    p = argparse.ArgumentParser(); p.add_argument('destination'); p.add_argument('--repo', default='.')
    a = p.parse_args(); print(canonical(build(a.repo, a.destination)))


if __name__ == '__main__':
    main()
