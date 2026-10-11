"""Isolated package launcher. No host installer, Dashboard, API, network, model."""
import json
from pathlib import Path
import subprocess
import sys

def main():
    try:
        if not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):raise ValueError()
        root=Path(sys.argv[1]).absolute();args=sys.argv[2:]
        # Reuse existing stdlib-first full-file integrity gate in isolated child.
        checked=subprocess.run([sys.executable,'-I','-B','-S',str(root/'observer_entry.py'),str(root),'verify'],capture_output=True,text=True,timeout=10)
        if checked.returncode!=0:raise ValueError()
        # Support imports only AFTER approved package hashes checked.
        sys.path.insert(0,str(root/'package'/'support'))
        from tools.nana_astrbot_shadow.package import verify_package
        verify_package(root)
        from nana_host_shadow.bootstrap_entry import runtime
        runtime(root)
        sys.path.insert(0,str(root/'package'/'src'))
        if args==['harness']:
            from tools.nana_astrbot_shadow.one_shot_harness import run
            report=run(root/'data'/'r04-harness');print(json.dumps(report,sort_keys=True));return 0
        from tools.nana_astrbot_shadow.one_shot_cli import main as cli
        return cli(args)
    except BaseException:
        print(json.dumps({'status':'BLOCKED','reason':'R04_PACKAGE_POLICY_OR_STATE','host_binding':'UNVERIFIED'}));return 2
if __name__=='__main__':raise SystemExit(main())
