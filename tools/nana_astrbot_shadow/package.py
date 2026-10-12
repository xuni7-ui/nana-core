"""Build a separately reviewed development observer kit, not an installed plugin."""
import gzip
import io
import json
from pathlib import Path
import shutil
import subprocess
import stat
import tarfile
from tools.nana_host_shadow.safety import digest,private_file,checked_path
from tools.nana_host_shadow.build import build
from tools.nana_host_shadow.isolated_runtime import reuse_runtime

DOC_NAMES=('PRE_INSTALL_CHECKLIST.md','POST_LOAD_PROOF_CHECKLIST.md','UNLOAD_PROOF_CHECKLIST.md','ROLLBACK.md','OPERATOR_RUNBOOK.md')

def package_members(root):
    """No symlink/special-file blind spots; never walk mutable Shadow data."""
    pending=[root];files=set()
    while pending:
        directory=pending.pop();ds=directory.lstat()
        if not stat.S_ISDIR(ds.st_mode) or ds.st_mode & 0o022:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
        for p in directory.iterdir():
            st=p.lstat();name=str(p.relative_to(root))
            if stat.S_ISLNK(st.st_mode) or st.st_mode & 0o022:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
            if stat.S_ISDIR(st.st_mode):
                if name!='data':pending.append(p)
            elif stat.S_ISREG(st.st_mode):
                if st.st_nlink!=1:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
                files.add(name)
            else:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    return files


def verify_package(root):
    root=checked_path(root,directory=True)
    manifest=checked_path(root/'manifest.json')
    m=json.loads(manifest.read_text())
    expected=m['files']
    actual=package_members(root)
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
        'binding_ready':False,'binding_status':'BLOCKED_AUTH_REQUIRED','probe_support':'C','host_binding':'UNVERIFIED',
        'production_execute':False,'no_runtime_database_in_package':True,'no_credentials':True,'mutable_paths':['data/'],
        'lifecycle_shim':'IMPLEMENTED_TESTED_SOURCE_AUDIT_652a72f', 'dispatcher_probe':'BLOCKED_NO_INTERNAL_PROBE',
        'install_requires':'Nana explicit integration into existing observer plugin and verified permitted load path; no automatic host install',
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
            'Core_source_SHA':m['Core_source_SHA'],'runtime_sha256':rt['runtime_sha256'],'binding_status':'BLOCKED_AUTH_REQUIRED'}


def create_r04(repo,destination,*,runtime_from):
    """Reuse fixed Core/runtime builder; add a dormant message-only plugin ZIP.

    No install action and no fixture trust pin. Private runtime only belongs to
    isolated CLI/harness, never load into already-running AstrBot interpreter.
    """
    import zipfile
    repo=Path(repo);root=Path(destination)
    if subprocess.check_output(['git','status','--porcelain','--','src/plugins/astrbot_plugin_nana_shadow_observer','docs/nana_r04_package'],cwd=repo,text=True):
        raise ValueError('COMMITTED_PLUGIN_AND_RUNBOOK_REQUIRED')
    # Existing builder creates a verified kit in the new directory. Preserve its
    # intermediate archive; final R04 archive has a separate explicit suffix.
    create(repo,root,runtime_from=runtime_from)
    plugin=root/'plugin';plugin.mkdir()
    source=repo/'src/plugins/astrbot_plugin_nana_shadow_observer'
    files={'main.py':(source/'r04_main.py').read_bytes(),
           'message_hook_adapter.py':(source/'message_hook_adapter.py').read_bytes(),
           'metadata.yaml':b'name: astrbot_plugin_nana_shadow_observer\nauthor: nana-core\nversion: 0.0.4\ndesc: R04 dormant one-shot metadata shadow development package\n'}
    with zipfile.ZipFile(plugin/'nana-shadow-r04-observer.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo('astrbot_plugin_nana_shadow_observer/'+name,date_time=(2026,10,11,0,0,0))
            info.external_attr=0o600<<16;z.writestr(info,data)
    (root/'R04_RUNBOOK').mkdir()
    for p in sorted((repo/'docs/nana_r04_package').glob('*.md')):shutil.copyfile(p,root/'R04_RUNBOOK'/p.name)
    shutil.copyfile(repo/'tools/nana_astrbot_shadow/r04_entry.py',root/'r04_entry.py')
    script=root/'r04.sh'
    script.write_text('''#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
python=$(command -v python3.12 || command -v python3) || exit 2
exec "$python" -I -B -S "$base/r04_entry.py" "$base" "$@"
''');script.chmod(0o700)
    m=json.loads((root/'manifest.json').read_text())
    m.update(r04='IMPLEMENTED_TESTED_DEVELOPMENT_ONLY',production_trust_pins=0,real_runtime_proof_pins=0,
        real_astrbot_load='NOT_RUN',real_dispatcher_traversal='NOT_VERIFIED',host_binding='UNVERIFIED',E12='NOT_RUN',
        plugin='plugin/nana-shadow-r04-observer.zip',plugin_automatically_armed=False,
        plugin_support_wiring='operator-injected approved module path; no auto path/sys.modules/private runtime injection',
        native_host_sqlite_required='>=3.51.3; private runtime cannot replace running AstrBot imports')
    m['files']={str(p.relative_to(root)):digest(p.read_bytes()) for p in root.rglob('*')
                if p.is_file() and p.name not in ('manifest.json','SHA256SUMS')}
    private_file(root/'manifest.json',m,replace=True)
    (root/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in sorted(m['files'].items()))+digest((root/'manifest.json').read_bytes())+'  manifest.json\n')
    verify_package(root)
    archive=root.parent/(root.name+'-delivery.tar.gz')
    with archive.open('xb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as z:
            with tarfile.open(fileobj=z,mode='w') as t:
                for p in sorted(root.rglob('*')):
                    if not p.is_file():continue
                    b=p.read_bytes();i=tarfile.TarInfo(root.name+'/'+str(p.relative_to(root)));i.size=len(b);i.mode=0o700 if p.suffix=='.sh' else 0o600;i.mtime=0;t.addfile(i,io.BytesIO(b))
    return {'filename':archive.name,'bytes':archive.stat().st_size,'SHA256':digest(archive.read_bytes()),
        'support_source_SHA':m['support_source_SHA'],'Core_source_SHA':m['Core_source_SHA'],
        'runtime_sha256':m['runtime_sha256'],'host_binding':'UNVERIFIED','production_trust_pins':0}


def create_r041(repo,destination,*,runtime_from):
    """R04 fixed-source builder reused; plugin ZIP contains stdlib bridge only."""
    import zipfile
    repo=Path(repo);root=Path(destination)
    if subprocess.check_output(['git','status','--porcelain','--','docs/nana_r041_package','src/plugins/astrbot_plugin_nana_shadow_observer'],cwd=repo,text=True):
        raise ValueError('COMMITTED_BRIDGE_REQUIRED')
    create_r04(repo,root,runtime_from=runtime_from)
    source=repo/'src/plugins/astrbot_plugin_nana_shadow_observer'
    protocol=(repo/'tools/nana_astrbot_shadow/bridge_wire.py').read_bytes()
    if protocol!=(source/'bridge_wire.py').read_bytes():raise ValueError('SHARED_PROTOCOL_DRIFT')
    # Both earlier dormant ZIPs are historical kit components; only this ZIP
    # is the R041 host plugin. No Core/runtime/tools vendored into its process.
    files={'main.py':(source/'r041_main.py').read_bytes(),'bridge_client.py':(source/'bridge_client.py').read_bytes(),
           'bridge_wire.py':protocol,'message_hook_adapter.py':(source/'message_hook_adapter.py').read_bytes(),
           'metadata.yaml':b'name: astrbot_plugin_nana_shadow_bridge\nauthor: nana-core\nversion: 0.0.41\ndesc: R041 dormant metadata-only UDS bridge\n'}
    archive_zip=root/'plugin/nana-shadow-r041-bridge.zip'
    with zipfile.ZipFile(archive_zip,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo('astrbot_plugin_nana_shadow_bridge/'+name,date_time=(2026,10,11,0,0,0));info.external_attr=0o600<<16;z.writestr(info,data)
    book=root/'R041_RUNBOOK';book.mkdir()
    for p in sorted((repo/'docs/nana_r041_package').glob('*.md')):shutil.copyfile(p,book/p.name)
    launcher=root/'bridge.sh';launcher.write_text('''#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec "$base/r04.sh" bridge "$@"
''');launcher.chmod(0o700)
    m=json.loads((root/'manifest.json').read_text())
    m.update(r041='SHORT_LIVED_HOST_BRIDGE_IMPLEMENTED_TESTED',plugin='plugin/nana-shadow-r041-bridge.zip',
        plugin_dependencies='stdlib + existing AstrBot only; NO Core/privateSQLite/Pydantic',
        worker='explicit foreground isolated process <=600sec/receiptexpiry, one session/receipt/event; no daemon/autostart',
        IPC='AF_UNIX filesystem,0700dir/0600socket,4096byte canonical metadata frames,peerPID/UID+nonce/HMAC',
        real_host_bridge='NOT_RUN',production_review_pins=0,shared_protocol_sha256=digest(protocol))
    m['files']={str(p.relative_to(root)):digest(p.read_bytes()) for p in root.rglob('*') if p.is_file() and p.name not in ('manifest.json','SHA256SUMS')}
    private_file(root/'manifest.json',m,replace=True)
    (root/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in sorted(m['files'].items()))+digest((root/'manifest.json').read_bytes())+'  manifest.json\n')
    verify_package(root)
    archive=root.parent/(root.name+'-bridge-delivery.tar.gz')
    with archive.open('xb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as gz:
            with tarfile.open(fileobj=gz,mode='w') as t:
                for p in sorted(root.rglob('*')):
                    if not p.is_file():continue
                    b=p.read_bytes();i=tarfile.TarInfo(root.name+'/'+str(p.relative_to(root)));i.size=len(b);i.mode=0o700 if p.suffix=='.sh' else 0o600;i.mtime=0;t.addfile(i,io.BytesIO(b))
    return {'filename':archive.name,'bytes':archive.stat().st_size,'SHA256':digest(archive.read_bytes()),
        'Core_source_SHA':m['Core_source_SHA'],'support_source_SHA':m['support_source_SHA'],'runtime_sha256':m['runtime_sha256'],
        'shared_protocol_sha256':m['shared_protocol_sha256'],'production_review_pins':0,'real_host_bridge':'NOT_RUN'}


def create_r042(repo,destination,*,runtime_from):
    """Production default remains EMPTY. No receipt/review/proof generated here."""
    root=Path(destination)
    create_r041(repo,root,runtime_from=runtime_from)
    shutil.copyfile(Path(repo)/'docs/nana_r042_trust_onboarding.md',root/'R042_ONBOARDING.md')
    launcher=root/'onboarding.sh'
    launcher.write_text('#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)\nexec "$base/r04.sh" onboarding "$@"\n')
    launcher.chmod(0o700)
    m=json.loads((root/'manifest.json').read_text())
    m.update(r042='EMPTY_DEFAULT_ONBOARDING_READY',seal_mode='EMPTY',production_review_pins=0,
             production_trust_pins=0,real_runtime_proof_pins=0)
    from .onboarding import finalize
    return finalize(root,m)
