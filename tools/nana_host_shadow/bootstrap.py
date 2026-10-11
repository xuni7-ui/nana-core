"""Make a single upload artifact; no host transfer, install, or network action."""
import argparse
from datetime import datetime,timezone
import gzip
import io
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
from .build import build
from .isolated_runtime import build_runtime, reuse_runtime
from .bootstrap_entry import SOABI, EXT_SUFFIX, VERIFIED_PYTHON_RELEASES
from .safety import digest,private_file


def create(repo,destination,inputs=None,*,runtime_from=None):
    repo,root=Path(repo).resolve(),Path(destination).absolute()
    if root.exists():raise ValueError('BOOTSTRAP_DESTINATION_MUST_BE_NEW')
    root.mkdir(mode=0o700)
    support_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain','--','tools/nana_host_shadow'],cwd=repo,text=True))
    if (inputs is None) == (runtime_from is None):raise ValueError('ONE_RUNTIME_SOURCE_REQUIRED')
    build(repo,root/'package')
    rt=reuse_runtime(runtime_from,root/'runtime') if runtime_from else build_runtime(inputs,root/'runtime')
    driver='''#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
if [ "${1:-}" = "--python" ]; then
    test "$#" -ge 3 || exit 2
    python=$2
    shift 2
else
    python=$(command -v python3.12 || command -v python3) || exit 2
fi
exec "$python" -I -B -S "$base/package/support/nana_host_shadow/bootstrap_entry.py" "$base" "$@"
'''
    (root/'run_shadow.sh').write_text(driver);(root/'run_shadow.sh').chmod(0o700)
    for filename,command in [('stop_shadow.sh','stop'),('collect_shadow.sh','collect'),('rollback_shadow.sh','rollback')]:
        (root/filename).write_text('#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)\nexec "$base/run_shadow.sh" '+command+' "$@"\n');(root/filename).chmod(0o700)
    (root/'README_HOST.txt').write_text('Nana adapter-local ENGINEERING SHADOW. No AstrBot hook or takeover.\nVerify the uploaded archive SHA256 against the separately provided receipt before extraction.\nExisting CPython3.12 normal ABI/SOABI cpython-312-x86_64-linux-gnu, Linux x86_64, glibc>=2.34 required.\nFull regression measured3.12.3 and3.12.14; other patches UNTESTED. No system install.\n./run_shadow.sh preflight --dry-run\n./run_shadow.sh preflight\n./run_shadow.sh probe\n./run_shadow.sh restart-check\n./run_shadow.sh rollback\n./run_shadow.sh collect\nOptional interpreter: ./run_shadow.sh --python /reviewed/python preflight\nEvery script supports --dry-run. Only data/ is mutable, all other files hash checked before import.\nStop from another terminal: ./stop_shadow.sh\nNo API key, secret, model call, production Action or Iris write is configured.\nDynamic AstrBot hook and real-host binding remain UNKNOWN/NOT_RUN.\n')
    files={str(p.relative_to(root)):digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
    m={'schema_version':1,'Core_source_SHA':'ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513','support_source_SHA':support_sha,
       'support_worktree_dirty':dirty,'created_at':datetime.now(timezone.utc).isoformat(),'files':files,
       'runtime_sha256':rt['runtime_sha256'],'package_sha256':digest({p:h for p,h in files.items() if p.startswith('package/')}),
       'python':'CPython3.12 normal ABI (existing host executable)','sqlite':'3.51.3 (private static-linked binding)','pydantic':'2.13.5 (private wheels)',
       'build_environment':{'system':platform.system(),'machine':platform.machine(),'python':platform.python_version()},
       'licenses':rt['licenses'],'mutable_paths':['data/'],'sensitive_configuration_count':0,'production_execute':False,
       'runtime_kind':rt['kind'],'host_requirements':{'implementation':'cpython','python_major_minor':[3,12],
           'SOABI':SOABI,'EXT_SUFFIX':EXT_SUFFIX,'normal_ABI':True,'machine':'x86_64','system':'Linux','glibc_minimum':'2.34'},
       'verified_python_releases':list(VERIFIED_PYTHON_RELEASES),'other_3_12_patches':'UNTESTED'}
    private_file(root/'manifest.json',m)
    (root/'SHA256SUMS').write_text(''.join(h+'  '+p+'\n' for p,h in sorted(files.items()))+digest((root/'manifest.json').read_bytes())+'  manifest.json\n')
    archive=root.with_suffix('.tar.gz')
    with archive.open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as zipped:
            with tarfile.open(fileobj=zipped,mode='w') as tar:
                for p in sorted(root.rglob('*')):
                    if not p.is_file():continue
                    data=p.read_bytes();info=tarfile.TarInfo(root.name+'/'+str(p.relative_to(root)));info.size=len(data);info.mode=0o700 if p.suffix=='.sh' or p.name=='nana-shadow' else 0o600;info.mtime=0
                    tar.addfile(info,io.BytesIO(data))
    return {'archive':str(archive),'SHA256':digest(archive.read_bytes()),'bytes':archive.stat().st_size,
            'support_source_SHA':support_sha,'support_worktree_dirty':dirty,'runtime_bytes':rt['bytes'],'runtime_sha256':rt['runtime_sha256']}


def main():
    p=argparse.ArgumentParser();p.add_argument('destination');p.add_argument('--repo',default='.')
    source=p.add_mutually_exclusive_group(required=True);source.add_argument('--inputs');source.add_argument('--runtime-from')
    a=p.parse_args();print(json.dumps(create(a.repo,a.destination,a.inputs,runtime_from=a.runtime_from),indent=2))


if __name__=='__main__':main()
