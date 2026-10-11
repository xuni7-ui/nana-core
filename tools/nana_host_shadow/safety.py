"""No credentials, host SDKs, network or production path discovery."""
import hashlib
import json
import os
import secrets
from pathlib import Path
import stat

APPROVED_SHA = 'ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513'
CORE_FINGERPRINT = '1e925df523f01f3db6367ba43b1e28383104d4cdbb1464f82779fefe43d5f67c'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value).encode()).hexdigest()


def checked_path(path, *, directory=False, missing=False):
    """Reject symlinks in every component; never resolve through a production link."""
    p = Path(os.path.abspath(path))
    for part in (*reversed(p.parents), p):
        if part.is_symlink():
            raise ValueError('SYMLINK_PATH_BLOCKED')
    if missing and not p.exists():
        return p
    st = p.stat()
    if directory != stat.S_ISDIR(st.st_mode) or (not directory and not stat.S_ISREG(st.st_mode)):
        raise ValueError('REGULAR_PATH_REQUIRED')
    if not directory and st.st_nlink != 1:
        raise ValueError('HARDLINK_FILE_BLOCKED')
    return p


def private_file(path, body, *, replace=False):
    p = checked_path(path, missing=True)
    temporary = p.with_name('.write-' + secrets.token_hex(12)) if replace else p
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(canonical(body) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            checked_path(p, missing=True)
            os.replace(temporary, p)
    finally:
        if replace and temporary.exists():
            temporary.unlink()


def read_json(path):
    p = checked_path(path)
    if p.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('METADATA_SIZE_LIMIT')
    return json.loads(p.read_text())


def verify_bundle(root):
    root = checked_path(root, directory=True)
    m = read_json(root / 'bundle_manifest.json')
    if m.get('source_commit') != APPROVED_SHA or m.get('core_fingerprint') != CORE_FINGERPRINT:
        raise ValueError('APPROVED_SOURCE_MISMATCH')
    entries = m.get('core_files', {})
    if len(entries) != 55 or digest(entries) != CORE_FINGERPRINT:
        raise ValueError('CORE_MANIFEST_MISMATCH')
    for group in ('core_files', 'support_files'):
        for name, expected in m[group].items():
            if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('MANIFEST_PATH_BLOCKED')
            p = checked_path(root / name)
            if digest(p.read_bytes()) != expected:
                raise ValueError('PACKAGE_HASH_MISMATCH')
    actual = {str(p.relative_to(root)) for p in (root / 'src' / 'nana_core').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    if actual != set(entries):
        raise ValueError('UNREVIEWED_CORE_FILE')
    return m
