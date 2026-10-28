"""Precise sealed-file diagnostics; no repairs, deletion or relaxed exclusions."""

import hashlib
import os
from pathlib import Path


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        while raw := source.read(1024 * 1024):
            result.update(raw)
    return result.hexdigest()


def inventory(root):
    root = Path(root)
    actual = {".": root} if root.is_dir() else {}
    if actual:
        for base, directories, files in os.walk(root, followlinks=False):
            for name in directories + files:
                path = Path(base) / name
                actual[path.relative_to(root).as_posix()] = path
                if len(actual) > 30000:
                    raise ValueError("TREE_ENTRY_BOUND")
    return actual


def content_errors(name, expected, path):
    mismatches = []
    kind = "symlink" if path.is_symlink() else "directory" if path.is_dir() else "file" if path.is_file() else "special"
    if kind != expected["type"]:
        return [{"path": name, "reason": "TYPE_MISMATCH", "expected": expected["type"], "actual": kind}]
    if kind == "file":
        observed_hash = sha(path)
        if observed_hash != expected["sha256"]:
            mismatches.append({"path": name, "reason": "CONTENT_MISMATCH", "expected_sha256": expected["sha256"], "actual_sha256": observed_hash})
    elif kind == "symlink" and os.readlink(path) != expected["target"]:
        mismatches.append({"path": name, "reason": "LINK_MISMATCH", "expected": expected["target"], "actual": os.readlink(path)})
    observed = path.lstat()
    mode = 0o555 if name == "." else expected["mode"]
    if kind != "symlink" and (observed.st_mode & 0o777 != mode or (observed.st_uid, observed.st_gid) != (expected["uid"], expected["gid"])):
        mismatches.append({"path": name, "reason": "MODE_OR_NUMERIC_OWNER_MISMATCH", "expected_mode": oct(mode),
                           "actual_mode": oct(observed.st_mode & 0o777), "expected_uid_gid": [expected["uid"], expected["gid"]],
                           "actual_uid_gid": [observed.st_uid, observed.st_gid]})
    return mismatches


def verify_tree(root, entries):
    actual = inventory(root)
    mismatches = []
    for name in sorted(set(entries) | set(actual)):
        expected, path = entries.get(name), actual.get(name)
        if expected is None:
            mismatches.append({"path": name, "reason": "EXTRA_FILE", "expected_sha256": None,
                               "actual_sha256": sha(path) if path.is_file() and not path.is_symlink() else None})
            continue
        if path is None:
            mismatches.append({"path": name, "reason": "MISSING", "expected_sha256": expected.get("sha256"), "actual_sha256": None})
            continue
        mismatches.extend(content_errors(name, expected, path))
    return mismatches

