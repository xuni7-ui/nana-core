"""Isolated package launcher. No host installer, Dashboard, API, network, model."""
import hashlib
import json
from pathlib import Path
import sys
import stat

def main():
    try:
        if not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):raise ValueError()
        root=Path(sys.argv[1]).absolute();args=sys.argv[2:]
        # Stdlib-only gate BEFORE executing/importing any package code. Never
        # invoke observer_entry until its own bytes have been checked either.
        if root.is_symlink() or (root/'manifest.json').is_symlink():raise ValueError()
        manifest=json.loads((root/'manifest.json').read_text());expected=manifest['files']
        actual=set();pending=[root]
        while pending:
            directory=pending.pop();ds=directory.lstat()
            if not stat.S_ISDIR(ds.st_mode) or ds.st_mode & 0o022:raise ValueError()
            for p in directory.iterdir():
                st=p.lstat();name=str(p.relative_to(root))
                if stat.S_ISLNK(st.st_mode) or st.st_mode & 0o022:raise ValueError()
                if stat.S_ISDIR(st.st_mode):
                    if name!='data':pending.append(p)
                elif stat.S_ISREG(st.st_mode):
                    if st.st_nlink!=1:raise ValueError()
                    actual.add(name)
                else:raise ValueError()
        if actual!=set(expected)|{'manifest.json','SHA256SUMS'}:raise ValueError()
        def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
        for name,h in expected.items():
            p=root/name
            if (Path(name).is_absolute() or '..' in Path(name).parts or p.is_symlink()
                or any(x.is_symlink() for x in p.parents) or p.stat().st_nlink!=1 or sha(p)!=h):raise ValueError()
        sums=''.join(h+'  '+n+'\n' for n,h in sorted(expected.items()))+sha(root/'manifest.json')+'  manifest.json\n'
        if (root/'SHA256SUMS').read_text()!=sums:raise ValueError()
        # Support imports only AFTER approved package hashes checked.
        sys.path.insert(0,str(root/'package'/'support'))
        from tools.nana_astrbot_shadow.package import verify_package
        verify_package(root)
        from nana_host_shadow.bootstrap_entry import runtime
        runtime(root)
        sys.path.insert(0,str(root/'package'/'src'))
        if args[:1]==['onboarding']:
            from tools.nana_astrbot_shadow.onboarding import main as onboarding
            return onboarding(args[1:])
        if args[:1]==['bridge']:
            from tools.nana_astrbot_shadow.bridge_cli import main as bridge
            return bridge(args[1:])
        if args==['harness']:
            from tools.nana_astrbot_shadow.one_shot_harness import run
            report=run(root/'data'/'r04-harness');print(json.dumps(report,sort_keys=True));return 0
        from tools.nana_astrbot_shadow.one_shot_cli import main as cli
        return cli(args)
    except BaseException:
        print(json.dumps({'status':'BLOCKED','reason':'R04_PACKAGE_POLICY_OR_STATE','host_binding':'UNVERIFIED'}));return 2
if __name__=='__main__':raise SystemExit(main())
