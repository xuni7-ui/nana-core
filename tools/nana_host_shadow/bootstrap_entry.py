"""Verified, no-network host entry. Bootstrap defaults never attach a message hook."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import sysconfig


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(root):
    manifest=root/'manifest.json'
    if manifest.is_symlink():raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    m=json.loads(manifest.read_text())
    if m.get('Core_source_SHA')!='ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513':
        raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    if m.get('support_worktree_dirty',False):raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    expected=m['files']
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and 'data' not in p.relative_to(root).parts[:1]}
    if actual != set(expected)|{'manifest.json','SHA256SUMS'}:
        raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    for name,h in expected.items():
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
        p=root/name
        if p.is_symlink() or any(parent.is_symlink() for parent in p.parents if parent!=root.parent) or digest(p.read_bytes())!=h:
            raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    sums=''.join(h+'  '+n+'\n' for n,h in sorted(expected.items()))+digest(manifest.read_bytes())+'  manifest.json\n'
    if (root/'SHA256SUMS').read_text()!=sums:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
    return m


def runtime(root):
    import sqlite3
    host={'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'executable':sys.executable}
    # -S avoids executing global .pth/sitecustomize while obtaining metadata.
    # Read distribution metadata at the interpreter's standard install paths,
    # without adding those paths to imports or invoking site.main(). A venv's
    # private site location may not be visible under -S: preserve UNKNOWN.
    paths=list({sysconfig.get_path('purelib'),sysconfig.get_path('platlib')})
    versions=[d.version for d in importlib.metadata.distributions(name='pydantic',path=paths)]
    host['pydantic']=versions[0] if len(set(versions))==1 else 'UNKNOWN'
    host['pydantic_scope']='installation metadata only; global site initialization disabled'
    libc,version=platform.libc_ver()
    if sys.implementation.name!='cpython' or platform.python_version()!='3.12.14' or getattr(sys,'abiflags','') or platform.machine()!='x86_64' or platform.system()!='Linux':
        raise ValueError('BLOCKED_RUNTIME_ABI')
    if libc!='glibc' or tuple(map(int,version.split('.')[:2]))<(2,34):raise ValueError('BLOCKED_RUNTIME_ABI')
    # Explicitly load the real standard-library binding built from CPython source.
    # This changes only this short-lived process's module namespace.
    for name in list(sys.modules):
        if name=='_sqlite3' or name=='sqlite3' or name.startswith('sqlite3.'):
            del sys.modules[name]
    spec=importlib.util.spec_from_file_location('_sqlite3',root/'runtime/_sqlite3.cpython-312-x86_64-linux-gnu.so')
    binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding);sys.modules['_sqlite3']=binding
    sys.path.insert(0,str(root/'runtime/deps'))
    import sqlite3 as shadow_sql
    shadow={'python':platform.python_version(),'sqlite':shadow_sql.sqlite_version,'pydantic':importlib.metadata.version('pydantic'),
            'executable':sys.executable,'interpreter_scope':'existing host binary; private process-only SQLite/dependencies'}
    if shadow['sqlite']!='3.51.3' or shadow['pydantic']!='2.13.5':raise ValueError('BLOCKED_RUNTIME_VERSION')
    return host,shadow


def main():
    sys.dont_write_bytecode=True
    p=argparse.ArgumentParser()
    p.add_argument('root');p.add_argument('command',choices=['preflight','probe','restart-check','stop','rollback','collect','hook-probe','iris-wrapper'])
    p.add_argument('--dry-run',action='store_true');p.add_argument('--window-seconds',type=int,default=30)
    p.add_argument('--mode',choices=['schema-only','count-only','hash-only','redacted-sample'],default='schema-only')
    p.add_argument('--synthetic-fixture')
    a=p.parse_args();root=Path(a.root).absolute()
    try:
        if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
            raise ValueError('BLOCKED_STARTUP_ISOLATION')
        m=verify(root)
        host,shadow=runtime(root)
        if not 0<=a.window_seconds<=600:raise ValueError('BOUNDED_WINDOW_REQUIRED')
        if a.dry_run:
            r={'status':'DRY_RUN','command':a.command,'HOST_GLOBAL_ENV':host,'SHADOW_RUNTIME_ENV':shadow,'files_written':0,
               'workdir':str(root/'data'),'external_execute':False,'model_calls':0}
        else:
            package=root/'package';sys.path.insert(0,str(package/'support'));sys.path.insert(0,str(package/'src'))
            from nana_host_shadow.launcher import start,stop,rollback,collect
            from nana_host_shadow.metadata import preflight
            if a.command=='preflight':r=preflight(package)
            elif a.command in {'probe','restart-check'}:
                if a.command=='restart-check' and not (root/'data/identity_metadata.json').exists():
                    raise ValueError('INITIAL_PROBE_REQUIRED')
                r=start(package,root/'data',host_instance='operator-host',window_seconds=a.window_seconds if a.command=='probe' else 0)
            elif a.command=='stop':r=stop(root/'data')
            elif a.command=='rollback':r=rollback(root/'data')
            elif a.command=='collect':r=collect(root/'data')
            elif a.command=='hook-probe':
                from nana_host_shadow.hook_probe import probe
                r=probe()
            else:
                from nana_host_shadow.iris_wrappers import export
                r=export(a.synthetic_fixture,mode=a.mode)
            r.update(HOST_GLOBAL_ENV=host,SHADOW_RUNTIME_ENV=shadow,bootstrap_source=m['support_source_SHA'])
        print(json.dumps(r,sort_keys=True))
    except Exception as exc:
        allowed={'BLOCKED_PACKAGE_INTEGRITY','BLOCKED_RUNTIME_ABI','BLOCKED_RUNTIME_VERSION','BLOCKED_STARTUP_ISOLATION','INITIAL_PROBE_REQUIRED','BOUNDED_WINDOW_REQUIRED'}
        category=str(exc) if type(exc) is ValueError and str(exc) in allowed else getattr(exc,'code',type(exc).__name__)
        print(json.dumps({'status':'BLOCKED','reason':category,'production_calls':0,'private_records_read':0}))
        raise SystemExit(2)


if __name__=='__main__':main()
