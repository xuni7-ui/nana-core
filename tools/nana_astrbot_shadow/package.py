"""Build a separately reviewed development observer kit, not an installed plugin."""
import gzip
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from tools.nana_host_shadow.safety import digest,private_file,checked_path
from tools.nana_host_shadow.build import build
from tools.nana_host_shadow.isolated_runtime import reuse_runtime

DOC_NAMES=('PRE_INSTALL_CHECKLIST.md','POST_LOAD_PROOF_CHECKLIST.md','UNLOAD_PROOF_CHECKLIST.md','ROLLBACK.md','OPERATOR_RUNBOOK.md')

def verify_package(root):
    root=checked_path(root,directory=True)
    manifest=checked_path(root/'manifest.json')
    m=json.loads(manifest.read_text())
    expected=m['files']
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.relative_to(root).parts[0]!='data'}
    if actual!=set(expected)|{'manifest.json','SHA256SUMS'}:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    for name,value in expected.items():
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
        if digest(checked_path(root/name).read_bytes())!=value:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    sums=''.join(h+'  '+name+'\n' for name,h in sorted(expected.items()))+digest(manifest.read_bytes())+'  manifest.json\n'
    if checked_path(root/'SHA256SUMS').read_text()!=sums:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    return m

def create(repo,destination,*,runtime_from):
    repo=checked_path(repo,directory=True);root=checked_path(destination,directory=True,missing=True)
    if root.exists():raise ValueError('NEW_PACKAGE_DIRECTORY_REQUIRED')
    if subprocess.check_output(['git','status','--porcelain','--','tools/nana_astrbot_shadow','tools/nana_host_shadow'],cwd=repo,text=True):
        raise ValueError('COMMITTED_SUPPORT_REQUIRED')
    support_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    root.mkdir(mode=0o700)
    build(repo,root/'package');rt=reuse_runtime(runtime_from,root/'runtime')
    lib=root/'package'/'support'/'tools'/'nana_astrbot_shadow';lib.mkdir(parents=True)
    for p in Path(__file__).parent.glob('*.py'):shutil.copyfile(p,lib/p.name)
    host=root/'package'/'support'/'tools'/'nana_host_shadow';host.mkdir()
    for p in ('__init__.py','safety.py','build.py','isolated_runtime.py','bootstrap_entry.py'):
        shutil.copyfile(repo/'tools'/'nana_host_shadow'/p,host/p)
    for name in DOC_NAMES:shutil.copyfile(repo/'docs'/'nana_astrbot_shadow_package'/name,root/name)
    shutil.copyfile(repo/'LICENSES_AND_PROVENANCE.md',root/'LICENSES_AND_PROVENANCE.md')
    shutil.copyfile(Path(__file__).parent/'entry.py',root/'observer_entry.py')
    driver='''#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
python=$(command -v python3.12 || command -v python3) || exit 2
exec "$python" -I -B -S "$base/observer_entry.py" "$base" "$@"
'''
    (root/'observer.sh').write_text(driver);(root/'observer.sh').chmod(0o700)
    for name,command in [('install_dry_run.sh','install-dry-run'),('uninstall_dry_run.sh','uninstall-dry-run'),('rollback.sh','rollback')]:
        p=root/name;p.write_text('#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)\nexec "$base/observer.sh" '+command+' "$@"\n');p.chmod(0o700)
    files={str(p.relative_to(root)):digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
    m={'schema_version':1,'Core_source_SHA':'ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513','support_source_SHA':support_sha,
        'files':files,'runtime_sha256':rt['runtime_sha256'],'runtime_kind':rt['kind'],'licenses':rt['licenses'],
        'binding_ready':False,'binding_status':'BLOCKED_API_EVIDENCE','probe_support':'C','host_binding':'UNVERIFIED',
        'production_execute':False,'no_runtime_database_in_package':True,'no_credentials':True,'mutable_paths':['data/'],
        'install_requires':'reviewed Nana exact hook audit and separate real-host execution; no API guessed',
        'zero_drift':{'existing_source_changes':0,'existing_configuration_changes':0,'real_host_inspected':False}}
    private_file(root/'manifest.json',m)
    (root/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in sorted(files.items()))+digest((root/'manifest.json').read_bytes())+'  manifest.json\n')
    verify_package(root)
    archive=root.with_suffix('.tar.gz')
    with archive.open('xb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as z:
            with tarfile.open(fileobj=z,mode='w') as t:
                for p in sorted(root.rglob('*')):
                    if not p.is_file():continue
                    b=p.read_bytes();i=tarfile.TarInfo(root.name+'/'+str(p.relative_to(root)));i.size=len(b);i.mode=0o700 if p.suffix=='.sh' else 0o600;i.mtime=0;t.addfile(i,io.BytesIO(b))
    return {'filename':archive.name,'bytes':archive.stat().st_size,'SHA256':digest(archive.read_bytes()),'support_source_SHA':support_sha,
            'Core_source_SHA':m['Core_source_SHA'],'runtime_sha256':rt['runtime_sha256'],'binding_status':'BLOCKED_API_EVIDENCE'}
