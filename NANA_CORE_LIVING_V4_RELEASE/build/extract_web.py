"""Extract a digest-bound LIVE Web build; never accept host/config/Subject data."""

import gzip
import hashlib
import json
import os
import re
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


def extract(archive, expected, root=Path("/opt/nana-core/runtime/web-releases")):
    archive = Path(archive)
    if not re.fullmatch(r"[a-f0-9]{64}", expected) or archive.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("WEB_DIGEST_REQUIRED")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError("WEB_DIGEST_MISMATCH")
    target = root / expected
    if root.is_symlink() or target.exists() or target.is_symlink():
        raise ValueError("FRESH_WEB_DESTINATION_REQUIRED")
    with gzip.open(archive, "rb") as source, tempfile.TemporaryFile() as raw:
        total = 0
        while block := source.read(1024 * 1024):
            total += len(block)
            if total > 32 * 1024 * 1024:
                raise ValueError("WEB_DECOMPRESSION_BOUND")
            raw.write(block)
        raw.seek(0)
        with tarfile.open(fileobj=raw, mode="r:") as tar:
            seen = set()
            members = []
            for member in tar:
                name = PurePosixPath(member.name)
                relative = PurePosixPath(*name.parts[1:])
                if (name.is_absolute() or not name.parts or name.parts[0] != "nana-space-web"
                        or ".." in name.parts or "\\" in member.name or str(name) in seen
                        or len(seen) >= 1000 or not (member.isdir() or member.isfile())
                        or (member.isfile() and (len(name.parts) < 2
                            or relative.suffix not in {".html", ".js", ".css", ".webp", ".png", ".svg", ".ico", ".json"}))):
                    raise ValueError("WEB_ARCHIVE_MEMBER_DENIED")
                seen.add(str(name))
                members.append((member, relative))
            if "nana-space-web/index.html" not in seen:
                raise ValueError("LIVE_WEB_INDEX_REQUIRED")
            root.mkdir(parents=True, mode=0o755, exist_ok=True)
            root.chmod(0o755)
            target.mkdir(mode=0o755)
            target.chmod(0o755)
            for member, relative in members:
                path = target / str(relative)
                if member.isdir():
                    path.mkdir(mode=0o755, parents=True, exist_ok=True)
                    path.chmod(0o755)
                    continue
                path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                path.parent.chmod(0o755)
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
                with os.fdopen(fd, "wb") as out, tar.extractfile(member) as stream:
                    os.fchmod(out.fileno(), 0o644)
                    out.write(stream.read())
    return {"web_sha256": expected, "path": str(target), "members": len(seen), "subject_created": False}


if __name__ == "__main__":
    print(json.dumps(extract(sys.argv[1], sys.argv[2])))
