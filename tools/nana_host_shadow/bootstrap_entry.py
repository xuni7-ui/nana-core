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

SOABI = 'cpython-312-x86_64-linux-gnu'
EXT_SUFFIX = '.cpython-312-x86_64-linux-gnu.so'
VERIFIED_PYTHON_RELEASES = ('3.12.3', '3.12.14')


class RuntimeBlocked(ValueError):
    """Preserve only non-sensitive runtime metadata in a classified failure."""
    def __init__(self, reason, host, shadow=None):
        super().__init__(reason)
        self.host = host
        self.shadow = shadow


def host_metadata():
    libc, version = platform.libc_ver()
    host = {'python': platform.python_version(), 'python_major_minor': list(sys.version_info[:2]),
            'implementation': sys.implementation.name, 'executable': sys.executable,
            'SOABI': sysconfig.get_config_var('SOABI'), 'EXT_SUFFIX': sysconfig.get_config_var('EXT_SUFFIX'),
            'architecture': platform.machine(), 'system': platform.system(),
            'glibc': {'kind': libc, 'version': version}, 'abiflags': getattr(sys, 'abiflags', ''),
            'python_patch_regression': 'VERIFIED' if platform.python_version() in VERIFIED_PYTHON_RELEASES else 'UNTESTED'}
    return host


def check_abi(host):
    # Extension ABI checks, not a language-level patch version requirement.
    checks = [(host['implementation'] == 'cpython', 'BLOCKED_PYTHON_IMPLEMENTATION'),
              (host['python_major_minor'] == [3, 12], 'BLOCKED_PYTHON_MINOR'),
              (not host['abiflags'], 'BLOCKED_PYTHON_BUILD'),
              (host['system'] == 'Linux', 'BLOCKED_OS'),
              (host['architecture'] == 'x86_64', 'BLOCKED_ARCH'),
              (host['SOABI'] == SOABI, 'BLOCKED_SOABI'),
              (host['EXT_SUFFIX'] == EXT_SUFFIX, 'BLOCKED_EXT_SUFFIX')]
    for passed, reason in checks:
        if not passed:
            raise RuntimeBlocked(reason, host)
    try:
        libc = host['glibc']
        compatible = libc['kind'] == 'glibc' and tuple(map(int, libc['version'].split('.')[:2])) >= (2, 34)
    except (ValueError, TypeError, KeyError):
        compatible = False
    if not compatible:
        raise RuntimeBlocked('BLOCKED_GLIBC', host)


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
    host = host_metadata()
    check_abi(host)
    try:
        import sqlite3
        host['sqlite'] = sqlite3.sqlite_version
    except ImportError:
        host['sqlite'] = 'UNKNOWN'
    # -S avoids executing global .pth/sitecustomize while obtaining metadata.
    # Read distribution metadata at the interpreter's standard install paths,
    # without adding those paths to imports or invoking site.main(). A venv's
    # private site location may not be visible under -S: preserve UNKNOWN.
    paths=list({sysconfig.get_path('purelib'),sysconfig.get_path('platlib')})
    versions=[d.version for d in importlib.metadata.distributions(name='pydantic',path=paths)]
    host['pydantic']=versions[0] if len(set(versions))==1 else 'UNKNOWN'
    host['pydantic_scope']='installation metadata only; global site initialization disabled'
    # Explicitly load the real standard-library binding built from CPython source.
    # This changes only this short-lived process's module namespace.
    for name in list(sys.modules):
        if name=='_sqlite3' or name=='sqlite3' or name.startswith('sqlite3.'):
            del sys.modules[name]
    shadow = {'python': platform.python_version(), 'extension_ABI_target': SOABI,
              'extension_build_python': '3.12.14', 'minimum_glibc': '2.34',
              'executable': sys.executable, 'python_patch_regression': host['python_patch_regression'],
              'sqlite': 'UNKNOWN', 'pydantic': 'UNKNOWN'}
    try:
        spec=importlib.util.spec_from_file_location('_sqlite3',root/('runtime/_sqlite3'+EXT_SUFFIX))
        binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding);sys.modules['_sqlite3']=binding
    except Exception as exc:
        shadow['load_failure_type'] = type(exc).__name__
        raise RuntimeBlocked('BLOCKED_EXTENSION_LOAD', host, shadow) from None
    sys.path.insert(0,str(root/'runtime/deps'))
    try:
        import sqlite3 as shadow_sql
        import pydantic
        shadow.update(sqlite=shadow_sql.sqlite_version, pydantic=pydantic.__version__,
                      interpreter_scope='existing host binary; private process-only SQLite/dependencies')
    except Exception as exc:
        shadow['load_failure_type'] = type(exc).__name__
        raise RuntimeBlocked('BLOCKED_DEPENDENCY_LOAD', host, shadow) from None
    if shadow['sqlite']!='3.51.3' or shadow['pydantic']!='2.13.5':
        raise RuntimeBlocked('BLOCKED_RUNTIME_VERSION', host, shadow)
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
        r['python_regression_coverage'] = {'verified': list(VERIFIED_PYTHON_RELEASES), 'other_3_12_patches': 'UNTESTED'}
        print(json.dumps(r,sort_keys=True))
    except Exception as exc:
        allowed={'BLOCKED_PACKAGE_INTEGRITY','BLOCKED_RUNTIME_ABI','BLOCKED_RUNTIME_VERSION','BLOCKED_STARTUP_ISOLATION','INITIAL_PROBE_REQUIRED','BOUNDED_WINDOW_REQUIRED'}
        category=str(exc) if type(exc) is ValueError and str(exc) in allowed else getattr(exc,'code',type(exc).__name__)
        if isinstance(exc, RuntimeBlocked):
            category=str(exc)
        report={'status':'BLOCKED','reason':category,'adapter_local_probe_ready':False,
                'production_calls':0,'private_records_read':0}
        if isinstance(exc, RuntimeBlocked):
            report.update(HOST_GLOBAL_ENV=exc.host, SHADOW_RUNTIME_ENV=exc.shadow)
        print(json.dumps(report))
        raise SystemExit(2)


if __name__=='__main__':main()
