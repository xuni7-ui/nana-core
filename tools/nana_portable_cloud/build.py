"""Build from an exact committed allowlist, never a workspace/database copy."""
import argparse,hashlib,json,subprocess,tarfile,gzip,io,re
from pathlib import Path
from datetime import datetime,timezone
REPO=Path(__file__).resolve().parents[2]
DEPENDENCIES={'pydantic':'2.13.4','pydantic-core':'2.46.4','annotated-types':'0.8.0','typing-extensions':'4.16.0','typing-inspection':'0.4.3'}

def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)
def build(destination,wheels,revision='HEAD'):
    destination=Path(destination).absolute()
    if destination.exists() or destination.resolve()!=destination:raise ValueError('CLEAN_BUILD_DESTINATION_REQUIRED')
    commit=git('rev-parse',revision+'^{commit}').decode().strip();epoch=int(git('show','-s','--format=%ct',commit))
    root=destination/'nana-first-life-portable-v1';root.mkdir(parents=True,mode=0o700)
    files=git('ls-tree','-r','--name-only',commit).decode().splitlines()
    for name in files:
        if name.startswith('src/nana_core/') and name.endswith(('.py','.sql')):
            rel=Path(name).relative_to('src/nana_core')
            # Ship the runtime dependency families, not Codex bridge/lab/legacy
            # integration entrypoints or their environment-specific tooling.
            if (len(rel.parts)>1 and rel.parts[0] not in {'life','presence','continuity','storage'}) or rel.as_posix()=='experiment.py':continue
            target=name
        elif name.startswith('packaging/portable/'):target=name.removeprefix('packaging/portable/')
        else:continue
        mode=git('ls-tree',commit,'--',name).split()[0]
        if mode not in {b'100644',b'100755'}:raise ValueError('SOURCE_SYMLINK_DENIED')
        path=root/target;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(git('show',commit+':'+name))
        path.chmod(0o755 if target=='nana' or target.endswith('.sh') else 0o644)
    lock=[];wheelroot=root/'wheelhouse';wheelroot.mkdir()
    for package,version in DEPENDENCIES.items():
        candidates=list(Path(wheels).glob(package.replace('-','_')+'-'+version+'-*.whl'))
        if len(candidates)!=1:raise ValueError('EXACT_WHEEL_REQUIRED')
        p=candidates[0];raw=p.read_bytes();(wheelroot/p.name).write_bytes(raw)
        lock.append(package+'=='+version+' --hash=sha256:'+hashlib.sha256(raw).hexdigest())
    (root/'requirements.lock').write_text('\n'.join(lock)+'\n')
    (root/'runtime.json').write_text(json.dumps({'bundle_version':1,'source_commit':commit,'schema_version':13,'supported_platform':'Linux x86_64 / CPython3.12 / glibc>=2.17','build_timestamp':datetime.fromtimestamp(epoch,timezone.utc).isoformat(),'timestamp_policy':'SOURCE_COMMIT_TIMESTAMP_REPRODUCIBLE','dependencies':DEPENDENCIES,'real_provider_calls':0},indent=2)+'\n')
    pattern=re.compile(rb'(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}')
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('BUNDLE_SYMLINK_DENIED')
        if p.is_file() and p.suffix!='.whl' and pattern.search(p.read_bytes()):raise ValueError('BUNDLE_SECRET_LITERAL')
    paths=sorted(p for p in root.rglob('*') if p.is_file())
    (root/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(root).as_posix()+'\n' for p in paths))
    archive=destination/'nana-first-life-portable-v1.tar.gz'
    with archive.open('wb') as stream,gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0) as compressed,tarfile.open(fileobj=compressed,mode='w') as tar:
        for p in sorted(root.rglob('*')):
            if not p.is_file():continue
            raw=p.read_bytes();info=tarfile.TarInfo('nana-first-life-portable-v1/'+p.relative_to(root).as_posix());info.size=len(raw);info.mode=p.stat().st_mode&0o777;info.mtime=epoch
            tar.addfile(info,io.BytesIO(raw))
    checksum=hashlib.sha256(archive.read_bytes()).hexdigest();archive.with_name(archive.name+'.sha256').write_text(checksum+'  '+archive.name+'\n')
    unpack=destination/'nana-unpack.py';unpack.write_bytes(git('show',commit+':tools/nana_portable_cloud/unpack.py'))
    return {'archive':str(archive),'sha256':checksum,'source_commit':commit,'bundle_files':len(paths)+1,'new_provider_calls':0}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--wheels',type=Path,required=True);p.add_argument('--revision',default='HEAD');a=p.parse_args();print(json.dumps(build(a.output,a.wheels,a.revision),indent=2))
if __name__=='__main__':main()
