"""Trusted stdlib unpacker. Supply the independently verified archive SHA256."""
import argparse,hashlib,os,tarfile,gzip,io
from pathlib import Path,PurePosixPath
MAX=64*1024*1024

def unpack(archive,destination,expected):
    archive=Path(archive);destination=Path(destination).absolute()
    if archive.is_symlink() or archive.stat().st_size>MAX or hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise ValueError('ARCHIVE_INTEGRITY')
    if destination.exists() or destination.resolve()!=destination or not destination.parent.is_dir():raise ValueError('CLEAN_DESTINATION_REQUIRED')
    # Bound the entire decompressed stream, including hidden PAX/GNU metadata
    # parsed by tarfile before it yields an ordinary member.
    with gzip.open(archive,'rb') as stream:raw=stream.read(MAX+4*1024*1024+1)
    if len(raw)>MAX+4*1024*1024:raise ValueError('ARCHIVE_DECOMPRESSION_BOUND')
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tar:
        items=[];seen=set();total=0
        # Validate incrementally: getmembers() could allocate an unbounded
        # decompressed header list before enforcing the member/size ceilings.
        for member in tar:
            p=PurePosixPath(member.name);total+=member.size
            if (not p.parts or p.parts[0]!='nana-first-life-portable-v1' or p.is_absolute() or '..' in p.parts or '\\' in member.name
                or member.name in seen or not (member.isfile() or member.isdir()) or member.size>MAX or total>MAX or len(items)>=4096):raise ValueError('ARCHIVE_MEMBERS_DENIED')
            seen.add(member.name);items.append(member)
        destination.mkdir(mode=0o700)
        for member in items:
            rel=PurePosixPath(member.name).parts[1:]
            if not rel:continue
            target=destination.joinpath(*rel)
            if member.isdir():target.mkdir(parents=True,mode=0o700,exist_ok=True);continue
            target.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
            fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o700 if member.mode&0o111 else 0o600)
            with os.fdopen(fd,'wb') as f:f.write(tar.extractfile(member).read())
    return destination

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('--destination',type=Path,required=True);p.add_argument('--sha256',required=True);a=p.parse_args()
    try:print(unpack(a.archive,a.destination,a.sha256))
    except (ValueError,OSError,tarfile.TarError):raise SystemExit('ARCHIVE_REJECTED') from None

if __name__=='__main__':main()
