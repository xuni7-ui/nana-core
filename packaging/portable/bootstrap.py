"""Stdlib-only integrity and offline installation bootstrap."""
import hashlib,json,os,platform,sqlite3,subprocess,sys,venv
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
# Runtime imports must not mutate the checksummed source tree with .pyc files.
sys.dont_write_bytecode=True

def verify(root):
    if root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o022:raise ValueError()
    seen=set()
    for line in (root/'SHA256SUMS').read_text().splitlines():
        sha,name=line.split('  ',1);p=PurePosixPath(name)
        if len(sha)!=64 or name in seen or p.is_absolute() or '..' in p.parts or '\\' in name:raise ValueError()
        seen.add(name);path=root/name
        if path.resolve()!=path or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError()
    for directory,dirs,files in os.walk(root,followlinks=False):
        if Path(directory)==root:dirs[:]=[d for d in dirs if d not in {'.venv','var'}]
        for name in dirs+files:
            p=Path(directory)/name;rel=p.relative_to(root)
            if p.is_symlink() or p.is_file() and rel.as_posix() not in seen|{'SHA256SUMS'}:raise ValueError()

def main():
    verify(ROOT)
    sys.path.insert(0,str(ROOT/'src'))
    from nana_core.host_requirements import sqlite_runtime_report
    sqlite_report=sqlite_runtime_report()
    if not sqlite_report['supported']:
        print(json.dumps({'state':'START_BLOCKED','code':sqlite_report['code'],'sqlite_runtime':sqlite_report}));raise SystemExit(2)
    if sys.argv[1:2]==['install']:
        if sys.version_info[:2]!=(3,12) or sys.platform!='linux' or platform.machine()!='x86_64':raise ValueError()
        path=ROOT/'.venv'
        if path.is_symlink():raise ValueError()
        if not path.exists():venv.EnvBuilder(with_pip=True).create(path)
        python=path/'bin/python'
        # An existing venv may point at another interpreter. Inspect that binding
        # before pip or any Subject operation; never trust installer Python alone.
        probe="import sys,json;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv[1]);from nana_core.host_requirements import sqlite_runtime_report;print(json.dumps({'python':list(sys.version_info[:2]),'sqlite':sqlite_runtime_report()}))"
        actual=json.loads(subprocess.check_output([str(python),'-I','-c',probe,str(ROOT/'src')],text=True))
        if actual['python']!=[3,12] or not actual['sqlite']['supported']:
            print(json.dumps({'state':'START_BLOCKED','code':'INSTALLED_INTERPRETER_UNSUPPORTED','actual':actual}));raise SystemExit(2)
        subprocess.run([str(python),'-m','pip','--isolated','install','--no-index','--find-links',str(ROOT/'wheelhouse'),'--require-hashes','-r',str(ROOT/'requirements.lock')],check=True)
        subprocess.run([str(python),'-m','pip','--isolated','check'],check=True)
        print(json.dumps({'state':'INSTALLED_OFFLINE','network_requests':0,'actual_interpreter':actual}));return
    if sys.prefix==sys.base_prefix:
        print(json.dumps({'state':'START_BLOCKED','code':'INSTALL_REQUIRED','python_supported':sys.version_info[:2]==(3,12)}));raise SystemExit(2)
    sys.path.insert(0,str(ROOT/'src'))
    from nana_core.life.portable_runtime import main as run
    run(ROOT)

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,ImportError,subprocess.SubprocessError):
        print(json.dumps({'state':'START_BLOCKED','code':'BUNDLE_INTEGRITY_OR_INSTALL_FAILED'}));raise SystemExit(2) from None
