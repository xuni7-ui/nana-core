"""Fresh image only: use standard same-venv aliases for identical Python files.

Never run against a host runtime/Subject. The new image gets an independent
seal; old images and sealed host slots are unchanged. No library is replaced.
"""

import hashlib
import os
from pathlib import Path


def compact(root=Path("/opt/nana-core/runtime/core-releases")):
    saved = 0
    for release in sorted(root.iterdir()):
        binary = release / ".venv/bin/python3.12"
        if not binary.is_file() or binary.is_symlink():
            raise ValueError("QUALIFIED_REGULAR_INTERPRETER_REQUIRED")
        expected = hashlib.sha256(binary.read_bytes()).digest()
        for name in ("python", "python3"):
            alias = binary.with_name(name)
            if alias.is_symlink() and alias.readlink() == Path("python3.12"):
                continue
            if alias.is_symlink() or not alias.is_file() or hashlib.sha256(alias.read_bytes()).digest() != expected:
                raise ValueError("INTERPRETER_ALIAS_CONTENT_MISMATCH")
            size = alias.stat().st_size
            alias.unlink()
            alias.symlink_to("python3.12")
            os.chown(alias, binary.stat().st_uid, binary.stat().st_gid, follow_symlinks=False)
            saved += size
    return saved


if __name__ == "__main__":
    print({"fresh_image_identical_alias_bytes_removed": compact(), "host_runtime_modified": False})
