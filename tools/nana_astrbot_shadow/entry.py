"""Standalone stdlib integrity gate before support/Core/private-runtime imports."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    a=argparse.ArgumentParser();a.add_argument('root');a.add_argument('command',choices=('verify','preflight','harness','schema-only','install-dry-run','uninstall-dry-run','rollback','collect'))
    a.add_argument('--dry-run',action='store_true');a.add_argument('--frozen-path');a.add_argument('--kind',choices=('l2','kg'),default='l2')
    args=a.parse_args();root=Path(args.root).absolute()
    try:
        if not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):raise ValueError('BLOCKED_STARTUP_ISOLATION')
        if root.is_symlink() or (root/'manifest.json').is_symlink():raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
        m=json.loads((root/'manifest.json').read_text());expected=m['files']
        actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.relative_to(root).parts[0]!='data'}
        if actual!=set(expected)|{'manifest.json','SHA256SUMS'}:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
        def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
        for name,h in expected.items():
            p=root/name
            if Path(name).is_absolute() or '..' in Path(name).parts or p.is_symlink() or any(x.is_symlink() for x in p.parents) or sha(p)!=h:
                raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
        sums=''.join(h+'  '+n+'\n' for n,h in sorted(expected.items()))+sha(root/'manifest.json')+'  manifest.json\n'
        if (root/'SHA256SUMS').read_text()!=sums:raise ValueError('BLOCKED_PACKAGE_INTEGRITY')
        sys.path.insert(0,str(root/'package'/'support'))
        from tools.nana_astrbot_shadow.package import verify_package
        verify_package(root)
        if args.dry_run or args.command.endswith('dry-run'):
            report={'status':'DRY_RUN','binding_status':'BLOCKED_API_EVIDENCE','files_written':0,'host_operations':0,'external_execute':False}
        elif args.command=='verify':report={'status':'PACKAGE_INTEGRITY_PASS','binding_status':'BLOCKED_API_EVIDENCE'}
        elif args.command=='preflight':
            from nana_host_shadow.bootstrap_entry import runtime
            host,shadow=runtime(root)
            report={'status':'PASS','HOST_GLOBAL_ENV':host,'SHADOW_RUNTIME_ENV':shadow,'engineering_harness_ready':True,
                    'real_astrbot_binding_ready':False,'binding_status':'BLOCKED_API_EVIDENCE','host_binding':'UNVERIFIED'}
        elif args.command=='harness':
            from nana_host_shadow.bootstrap_entry import runtime
            runtime(root);sys.path.insert(0,str(root/'package'/'src'))
            from tools.nana_host_shadow.safety import verify_bundle
            verify_bundle(root/'package')
            from tools.nana_astrbot_shadow.harness import run
            report=run(root/'data')
        elif args.command=='schema-only':
            if not args.frozen_path:raise ValueError('EXPLICIT_FROZEN_METADATA_SOURCE_REQUIRED')
            from tools.nana_astrbot_shadow.iris_schema import SchemaInspector
            with SchemaInspector(args.frozen_path) as inspector:report=inspector.inspect(args.kind)
        elif args.command in {'rollback','collect'}:
            from tools.nana_host_shadow.safety import read_json,checked_path
            p=root/'data'/'binding_proof.json'
            # Harness is foreground and closes/unregisters in finally. No PID
            # killing, registry assumptions, private DB reads or file deletion.
            report=read_json(p) if p.exists() else {'observer_removed':'UNKNOWN','store_closed':'UNKNOWN'}
            if args.command=='rollback':
                report={k:report.get(k,'UNKNOWN') for k in ('observer_removed','store_closed','host_binding')}
                report['status']='LOCAL_HARNESS_CLOSED; real registry UNKNOWN'
        print(json.dumps(report,sort_keys=True))
    except Exception:
        # A foreign exception may contain a body/credential. Never print it.
        print(json.dumps({'status':'BLOCKED','reason':'SHADOW_OPERATOR_COMMAND_FAILED','host_binding':'UNVERIFIED','host_operations':0}))
        raise SystemExit(2)

if __name__=='__main__':main()
