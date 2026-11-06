"""Plan, then explicitly tighten an owned life.json without rewriting content.

Host-operator tool only, never a model/HTTP capability. Apply requires the exact
planned digest and the original Store's existing exclusive ownership fence.
No Subject, configuration values, ownership changes or new lock files are made.
"""
import argparse
import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path


def regular(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise ValueError('OWNED_REGULAR_SINGLE_LINK_REQUIRED')
    return info


def content(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    size = 0
    while True:
        part = os.read(fd, min(16384, 131073-size))
        if not part:
            return b"".join(chunks)
        size += len(part)
        if size>131072:
            raise ValueError('LIFE_CONFIGURATION_BOUND')
        chunks.append(part)


def prepare(home, *, apply=False, expected_sha256=None):
    root = Path(home).absolute()
    if root.resolve()!=root or root.stat().st_uid!=os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError('PRIVATE_OWNED_HOME_REQUIRED')
    path = root/'life.json'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = regular(fd)
        raw = content(fd)
        fingerprint = hashlib.sha256(raw).hexdigest()
        if apply and fingerprint!=expected_sha256:
            raise ValueError('LIFE_CONFIGURATION_DIGEST_CHANGED')
        mode = stat.S_IMODE(info.st_mode)
        result = {'state':'NO_CHANGE' if mode==0o600 else 'PERMISSION_PLAN', 'sha256':fingerprint,
                  'uid':info.st_uid, 'gid':info.st_gid, 'mode_before':oct(mode), 'mode_target':'0o600',
                  'content_changed':False, 'ownership_changed':False, 'subject_opened':False,
                  'persistent_changes':0}
        if mode==0o600:
            return result
        lock = root/'subject/self.db.lock'
        if lock.resolve()!=lock or lock.parent.resolve()!=lock.parent:
            raise ValueError('EXISTING_OWNER_FENCE_REQUIRED')
        fence = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            regular(fence)
            try:
                fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if apply:
                    raise ValueError('STOPPED_OWNER_REQUIRED') from None
                return {**result, 'state':'OWNER_ACTIVE_APPLY_BLOCKED'}
            if not apply:
                return {**result, 'state':'PERMISSION_PLAN_OWNER_STOPPED'}
            # Recheck the exact file, contents and parent under the existing
            # writer fence; pathname replacement never redirects the mutation.
            current = path.lstat()
            if (current.st_ino, current.st_dev)!=(info.st_ino, info.st_dev) or content(fd)!=raw:
                raise ValueError('LIFE_CONFIGURATION_CHANGED')
            os.fchmod(fd, 0o600)
            os.fsync(fd)
            if content(fd)!=raw or stat.S_IMODE(regular(fd).st_mode)!=0o600:
                raise ValueError('PERMISSION_RESULT_UNVERIFIED_STOP')
            return {**result, 'state':'PERMISSIONS_TIGHTENED', 'persistent_changes':1}
        finally:
            os.close(fence)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--expected-sha256')
    args = parser.parse_args()
    try:
        result = prepare(args.home, apply=args.apply, expected_sha256=args.expected_sha256)
    except (ValueError, OSError) as exc:
        code = str(exc) if isinstance(exc, ValueError) else 'CONFIGURATION_PATH_OR_PERMISSION_DENIED'
        print(json.dumps({'state':'BLOCKED', 'code':code}))
        raise SystemExit(2) from None
    print(json.dumps(result))


if __name__=='__main__':
    main()
