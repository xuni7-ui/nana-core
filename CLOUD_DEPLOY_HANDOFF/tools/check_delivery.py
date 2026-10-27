"""Check the complete handoff against an independently supplied checksum anchor."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024**2):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--handoff", required=True, type=Path)
    p.add_argument("--manifest-sha256", required=True)
    a = p.parse_args()
    root = a.handoff.resolve()
    manifest = root / "SHA256SUMS"
    if manifest.is_symlink() or digest(manifest) != a.manifest_sha256:
        raise ValueError("TRUSTED_HANDOFF_ANCHOR_MISMATCH")
    seen = set()
    for line in manifest.read_text().splitlines():
        expected, name = line.split("  ", 1)
        relative = PurePosixPath(name)
        path = root / name
        if (
            not re.fullmatch(r"[a-f0-9]{64}", expected)
            or relative.is_absolute()
            or ".." in relative.parts
            or "\\" in name
            or name in seen
            or name == "SHA256SUMS"
            or path.resolve() != path
        ):
            raise ValueError("HANDOFF_PATH_OR_DUPLICATE_DENIED")
        if not path.is_file() or digest(path) != expected:
            raise ValueError("HANDOFF_FILE_DIGEST_MISMATCH")
        seen.add(name)
    if {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()} != seen | {"SHA256SUMS"}:
        raise ValueError("HANDOFF_UNLISTED_FILE")
    print(f"HANDOFF_VERIFIED files={len(seen)}; no service started or identity opened")


if __name__ == "__main__":
    main()
