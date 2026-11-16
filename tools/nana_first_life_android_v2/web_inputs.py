"""Snapshot committed Web inputs, including the public live-mode flag.

No workspace dotenv, credentials, Store, node_modules or build output is copied.
Compilation and npm installation remain explicit caller steps.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

REPO=Path(__file__).resolve().parents[2]
APP='apps/nana-space/'


def prepare(revision,output):
    if not re.fullmatch(r'[0-9a-f]{40}',revision):raise ValueError('EXACT_SOURCE_COMMIT_REQUIRED')
    output=Path(output).absolute()
    if output.exists() or output.resolve()!=output or not output.parent.is_dir():raise ValueError('FRESH_WEB_SNAPSHOT_REQUIRED')
    def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)
    names=git('ls-tree','-r','--name-only',revision,'--','apps/nana-space','contracts/nana-space-live-v2').decode().splitlines()
    selected=[]
    for name in names:
        p=Path(name)
        if name.startswith('contracts/nana-space-live-v2/'):
            selected.append(name)
        elif name.startswith((APP+'src/',APP+'public/')):
            selected.append(name)
        elif str(p.parent)=='apps/nana-space' and (
                p.name in {'index.html','package.json','package-lock.json','vite.config.ts','.env.live'}
                or (p.name.startswith('tsconfig') and p.suffix=='.json')):
            selected.append(name)
    public_flag=APP+'.env.live'
    if public_flag not in selected:raise ValueError('COMMITTED_LIVE_MODE_CONFIG_REQUIRED')
    flag=git('show',revision+':'+public_flag)
    if flag.strip()!=b'VITE_NANA_DELIVERY=live':raise ValueError('PUBLIC_BUILD_CONFIG_REQUIRES_REVIEW')
    output.mkdir(mode=0o700)
    manifest={}
    for name in selected:
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('WEB_INPUT_PATH_DENIED')
        raw=git('show',revision+':'+name)
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        manifest[name]=hashlib.sha256(raw).hexdigest()
    result={'source_commit':revision,'input_sha256':manifest,'input_files':len(manifest),
        'public_live_mode_verified':True,'local_dotenv_or_store_copied':False,
        'app_directory':str(output/'apps/nana-space')}
    (output/'WEB-INPUT-SHA256.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--revision',required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();result=prepare(args.revision,args.output)
    print(json.dumps({k:v for k,v in result.items() if k!='input_sha256'}))


if __name__=='__main__':main()
