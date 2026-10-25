"""Bounded supplied runtime extractor; never import, execute or carry private data."""

import hashlib
import gzip
import tempfile
from contextlib import contextmanager
import os
import re
import sys
import tarfile
from pathlib import Path, PurePosixPath


@contextmanager
def bounded_tar(archive):
    # Bound the decompressed stream INCLUDING PAX/GNU hidden metadata before
    # tarfile parses it. Spool to a private temporary file, not a large RAM blob.
    with gzip.open(archive, "rb") as source, tempfile.TemporaryFile() as raw:
        total = 0
        while True:
            block = source.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > 512 * 1024 * 1024:
                raise ValueError("RUNTIME_DECOMPRESSION_BOUND")
            raw.write(block)
        raw.seek(0)
        with tarfile.open(fileobj=raw, mode="r:") as tar:
            yield tar


def extract(archive, expected, root=Path("/opt/nana-core")):
    archive = Path(archive)
    if (
        not re.fullmatch("[a-f0-9]{64}", expected)
        or archive.stat().st_size > 512 * 1024 * 1024
        or hashlib.sha256(archive.read_bytes()).hexdigest() != expected
    ):
        raise ValueError("SUPPLIED_RUNTIME_DIGEST_REQUIRED")
    runtime = root / "runtime"
    if runtime.is_symlink() or (runtime.exists() and any(runtime.iterdir())):
        raise ValueError("EMPTY_RUNTIME_DESTINATION_REQUIRED")
    runtime.mkdir(mode=0o755, parents=True, exist_ok=True)
    runtime.chmod(0o755)
    total = 0
    seen = set()
    members = []
    links = []
    with bounded_tar(archive) as tar:
        for m in tar:
            name = PurePosixPath(m.name)
            total += m.size
            if (
                name.is_absolute()
                or not name.parts
                or name.parts[0] != "runtime"
                or ".." in name.parts
                or "\\" in m.name
                or m.name in seen
                or len(seen) > 30000
                or total > 1024 * 1024 * 1024
            ):
                raise ValueError("RUNTIME_ARCHIVE_MEMBER_DENIED")
            seen.add(m.name)
            if (
                (len(name.parts) > 1 and name.parts[1] in {"data", "logs", "backups"})
                or any(p in {".git", ".env", ".netrc", "providers.json", "life.json", "host.json"} for p in name.parts)
                or name.suffix in {".db", ".sqlite", ".sqlite3", ".key", ".p12", ".jks"}
            ):
                raise ValueError("RUNTIME_ARCHIVE_NOT_NON_SENSITIVE")
            if m.issym():
                target = PurePosixPath(m.linkname)
                if target.is_absolute():
                    raise ValueError("RUNTIME_ABSOLUTE_SYMLINK_DENIED")
                resolved = (root.joinpath(*name.parts).parent / m.linkname).resolve()
                if not resolved.is_relative_to(runtime):
                    raise ValueError("RUNTIME_LINK_ESCAPE")
                links.append((m.name, m.linkname))
                continue
            if not (m.isfile() or m.isdir()):
                raise ValueError("RUNTIME_SPECIAL_MEMBER_DENIED")
            members.append(m)
        if any(
            any(str(PurePosixPath(p)) == str(parent) for p, _ in links)
            for name in seen
            for parent in PurePosixPath(name).parents
        ):
            raise ValueError("RUNTIME_SYMLINK_PARENT_DENIED")
        for m in members:
            p = root / m.name
            # Only this new, validated runtime tree. Explicit modes must not
            # inherit a caller's private umask (e.g. 0077), which would make a
            # root-built read-only SDK inaccessible to runtime UID999.
            for directory in reversed((p if m.isdir() else p.parent).parents):
                if directory.is_relative_to(runtime) and not directory.exists():
                    directory.mkdir(mode=0o755)
                    directory.chmod(0o755)
            if m.isdir():
                p.mkdir(mode=0o755, parents=True, exist_ok=True)
                p.chmod(0o755)
                continue
            p.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            p.parent.chmod(0o755)
            with tar.extractfile(m) as stream:
                raw = stream.read()
            if re.search(rb"(?m)^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", raw) or re.search(
                rb"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}", raw
            ):
                raise ValueError("RUNTIME_CREDENTIAL_PATTERN_DENIED")
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o755 if m.mode & 0o111 else 0o644)
            with os.fdopen(fd, "wb") as out:
                os.fchmod(out.fileno(), 0o755 if m.mode & 0o111 else 0o644)
                out.write(raw)
        for name, target in links:
            p = root / name
            p.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            p.parent.chmod(0o755)
            p.symlink_to(target)
        # Resolve the COMPLETE link graph before any candidate interpreter runs.
        # File writes precede links and link-parents are rejected above.
        for name, _ in links:
            try:
                resolved = (root / name).resolve()
            except (RuntimeError, OSError):
                raise ValueError("RUNTIME_LINK_CYCLE") from None
            if not resolved.is_relative_to(runtime):
                raise ValueError("RUNTIME_LINK_ESCAPE")
    return {"source_sha256": expected, "members": len(seen), "subject_created": False}


if __name__ == "__main__":
    import json

    print(json.dumps(extract(sys.argv[1], sys.argv[2])))
