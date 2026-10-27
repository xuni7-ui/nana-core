"""Install only the sealed non-sensitive runtime exported from the exact image.

manifest: fingerprint a docker-cp tar from a CREATED, never started container.
install: root-only, stage+verify+atomic replace of an absent/empty runtime dir.
Never traverses Subject data, starts a service, or changes an existing tree.
"""

import argparse
import fcntl
import hashlib
import json
import os
import posixpath
import re
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

IMAGE = "sha256:0d8426762cef4bc19b12a7930361fbc9a9c4096628ffb0ee4024407ec5a1a5ee"
PREFIX = "/opt/nana-core/runtime"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while b := f.read(1024 * 1024):
            h.update(b)
    return h.hexdigest()


def describe(tar):
    rows = {}
    members = {}
    total = 0
    for m in tar:
        p = PurePosixPath(m.name)
        name = str(p)
        if p.is_absolute() or ".." in p.parts or "\\" in m.name or name in rows or len(rows) >= 30000:
            raise ValueError("RUNTIME_MEMBER_PATH_INVALID")
        if m.uid not in (0, 999) or m.gid not in (0, 999) or m.mode & 0o7000:
            raise ValueError("RUNTIME_OWNER_OR_SPECIAL_MODE_INVALID")
        row = {"uid": m.uid, "gid": m.gid, "mode": m.mode & 0o777}
        total += m.size
        if total > 1024**3 or m.size > 64 * 1024**2:
            raise ValueError("RUNTIME_TREE_BOUND")
        if m.isdir():
            row["type"] = "directory"
        elif m.isfile():
            row.update(type="file", bytes=m.size, sha256=hashlib.sha256(tar.extractfile(m).read()).hexdigest())
        elif m.issym():
            virtual = posixpath.normpath(posixpath.join(PREFIX, str(p.parent), m.linkname))
            if virtual != PREFIX and not virtual.startswith(PREFIX + "/"):
                raise ValueError("RUNTIME_LINK_ESCAPE")
            row.update(type="symlink", target=m.linkname)
        else:
            raise ValueError("RUNTIME_SPECIAL_MEMBER_DENIED")
        rows[name], members[name] = row, m
    links = {n for n, r in rows.items() if r["type"] == "symlink"}
    for n in rows:
        if any(str(parent) in links for parent in PurePosixPath(n).parents):
            raise ValueError("RUNTIME_SYMLINK_PARENT_DENIED")
    for n in links:
        seen = set()
        while n in links:
            if n in seen:
                raise ValueError("RUNTIME_LINK_CYCLE")
            seen.add(n)
            target = rows[n]["target"]
            n = posixpath.relpath(
                posixpath.normpath(posixpath.join(PREFIX, str(PurePosixPath(n).parent), target)), PREFIX
            )
        if n not in rows:
            raise ValueError("RUNTIME_LINK_TARGET_MISSING")
    if "bin/python3" not in rows or "core-releases" not in rows or "web-releases" not in rows:
        raise ValueError("COMPLETE_RUNTIME_CORE_WEB_REQUIRED")
    return rows, members


def manifest(archive, *, image_id=IMAGE):
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
        raise ValueError("PINNED_IMAGE_REQUIRED")
    if Path(archive).stat().st_size > 1024**3:
        raise ValueError("RUNTIME_ARCHIVE_BOUND")
    with tarfile.open(archive, "r:") as t:
        rows, _ = describe(t)
    return {
        "schema_version": 1,
        "image_id": image_id,
        "archive_sha256": sha(archive),
        "archive_bytes": Path(archive).stat().st_size,
        "virtual_prefix": PREFIX,
        "entries": rows,
        "subject_included": False,
        "root_mode_after_install": 0o555,
    }


def install(archive, manifest_file, expected, destination, *, image_id=IMAGE):
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
        raise ValueError("PINNED_IMAGE_REQUIRED")
    if os.geteuid() != 0:
        raise ValueError("ROOT_OPERATOR_REQUIRED_FOR_NUMERIC_OWNERSHIP")
    manifest_file, destination = Path(manifest_file), Path(destination).absolute()
    if manifest_file.stat().st_size > 8 * 1024**2 or sha(manifest_file) != expected:
        raise ValueError("RUNTIME_MANIFEST_DIGEST_MISMATCH")
    value = json.loads(manifest_file.read_bytes())
    if value["image_id"] != image_id or value["virtual_prefix"] != PREFIX:
        raise ValueError("ORIGINAL_IMAGE_REQUIRED")
    if Path(archive).stat().st_size > 1024**3:
        raise ValueError("RUNTIME_ARCHIVE_BOUND")
    observed_archive_sha = sha(archive)
    # docker-cp tar encoding can differ across Engine28/29. The trusted manifest
    # pins every normalized member/type/mode/owner/content/link below. Packaging
    # bytes may differ; the complete runtime tree may not differ at all.
    if destination.resolve() != destination or not destination.parent.is_dir():
        raise ValueError("REAL_DESTINATION_PARENT_REQUIRED")
    if destination.parent.stat().st_uid != 0 or destination.parent.stat().st_mode & 0o022:
        raise ValueError("ROOT_OWNED_NONWRITABLE_RUNTIME_PARENT_REQUIRED")
    lock = destination.parent / ".runtime-provision.lock"
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
            raise ValueError("EMPTY_RUNTIME_DESTINATION_REQUIRED_NO_OVERWRITE")
        original_inode = destination.stat().st_ino if destination.exists() else None
        stage = Path(tempfile.mkdtemp(prefix=".runtime-staged-", dir=destination.parent))
        # Failed stages remain for diagnosis; never remove unknown data.
        with tarfile.open(archive, "r:") as t:
            rows, members = describe(t)
            if rows != value["entries"]:
                raise ValueError("RUNTIME_TREE_MANIFEST_MISMATCH")
            for name, row in rows.items():
                path = stage / name
                if row["type"] == "directory":
                    path.mkdir(parents=True, exist_ok=True)
                elif row["type"] == "file":
                    path.parent.mkdir(parents=True, exist_ok=True)
                    out = os.open(path, os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_WRONLY, 0o600)
                    with os.fdopen(out, "wb") as f:
                        f.write(t.extractfile(members[name]).read())
                        os.fchown(f.fileno(), row["uid"], row["gid"])
                        os.fchmod(f.fileno(), row["mode"])
                        f.flush()
                        os.fsync(f.fileno())
                    os.utime(path, (members[name].mtime, members[name].mtime))
                    if sha(path) != row["sha256"]:
                        raise ValueError("STAGED_RUNTIME_FILE_MISMATCH")
            for name, row in rows.items():
                if row["type"] == "symlink":
                    path = stage / name
                    path.symlink_to(row["target"])
                    os.lchown(path, row["uid"], row["gid"])
            for name in sorted(rows, key=lambda n: len(PurePosixPath(n).parts), reverse=True):
                row = rows[name]
                if row["type"] == "directory":
                    path = stage / name
                    os.chown(path, row["uid"], row["gid"])
                    os.chmod(path, 0o555 if name == "." else row["mode"])
                    directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
        if destination.exists():
            if destination.stat().st_ino != original_inode or any(destination.iterdir()):
                raise ValueError("RUNTIME_DESTINATION_CHANGED")
        elif original_inode is not None:
            raise ValueError("RUNTIME_DESTINATION_CHANGED")
        os.replace(stage, destination)
        directory = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return {
            "state": "RUNTIME_INSTALLED_NOT_STARTED",
            "image_id": image_id,
            "members": len(rows),
            "root_mode": "0555",
            "subject_created": False,
            "runtime_tree_matches_trusted_manifest": True,
            "observed_runtime_tar_sha256": observed_archive_sha,
            "runtime_tar_encoding_matches_reference": observed_archive_sha == value["archive_sha256"],
        }
    finally:
        os.close(fd)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="operation", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--archive", type=Path, required=True)
    i = sub.add_parser("install")
    for name in ("archive", "manifest", "destination"):
        i.add_argument("--" + name, type=Path, required=True)
    i.add_argument("--manifest-sha256", required=True)
    a = p.parse_args()
    result = (
        manifest(a.archive)
        if a.operation == "manifest"
        else install(a.archive, a.manifest, a.manifest_sha256, a.destination)
    )
    print(json.dumps(result, indent=2))
