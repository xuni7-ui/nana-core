"""Prepare a minimal reviewed patch for one literal original dryrun argv list.

Explicit source/digest only. No source execution, environment/credential search
or in-place replacement. Output is a new review file; unknown code shape refuses.
"""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path


def patch(source, expected):
    if hashlib.sha256(source).hexdigest() != expected:
        raise ValueError("ORIGINAL_OPERATOR_DIGEST_MISMATCH")
    text = source.decode()
    tree = ast.parse(text)
    matches = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            flags = [x.value for x in node.elts if isinstance(x, ast.Constant) and isinstance(x.value, str)]
            if "--dry-run" in flags and "--verify-only" in flags:
                matches.append(node)
    if len(matches) != 1:
        raise ValueError("UNAMBIGUOUS_ORIGINAL_ARGV_REQUIRED")
    node = matches[0]
    node.elts = [x for x in node.elts if not (isinstance(x, ast.Constant) and x.value == "--verify-only")]
    lines = text.splitlines(keepends=True)
    begin = sum(len(x.encode()) for x in lines[: node.lineno - 1]) + node.col_offset
    end = sum(len(x.encode()) for x in lines[: node.end_lineno - 1]) + node.end_col_offset
    data = source[:begin] + ast.unparse(node).encode() + source[end:]
    ast.parse(data)
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.source.is_symlink() or not a.source.is_file() or a.source.stat().st_size > 1024 * 1024:
        raise ValueError("EXPLICIT_BOUNDED_ORIGINAL_SOURCE_REQUIRED")
    data = patch(a.source.read_bytes(), a.expected_sha256)
    fd = os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    print(
        json.dumps(
            {
                "state": "REVIEW_PATCH_PREPARED_NOT_APPLIED",
                "original_sha256": a.expected_sha256,
                "patched_sha256": hashlib.sha256(data).hexdigest(),
                "production_modified": False,
            }
        )
    )


if __name__ == "__main__":
    main()
