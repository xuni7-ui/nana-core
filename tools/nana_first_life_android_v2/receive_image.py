"""Verify bounded image parts, restore original docker-save tar, optionally load.

No build, service start, image retag, daemon restart or Subject operation exists.
The manifest digest must come from the trusted delivery record.
"""

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

IMAGE = "sha256:0d8426762cef4bc19b12a7930361fbc9a9c4096628ffb0ee4024407ec5a1a5ee"
DOCKER = [
    "env",
    "-u",
    "DOCKER_HOST",
    "-u",
    "DOCKER_CONTEXT",
    "-u",
    "DOCKER_TLS",
    "-u",
    "DOCKER_TLS_VERIFY",
    "-u",
    "DOCKER_CERT_PATH",
    "docker",
    "--host=unix:///var/run/docker.sock",
]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while block := f.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def restore(manifest, expected, output):
    manifest, output = Path(manifest), Path(output)
    if digest(manifest) != expected:
        raise ValueError("IMAGE_MANIFEST_DIGEST_MISMATCH")
    value = json.loads(manifest.read_bytes())
    if value["image_id"] != IMAGE or value["platform"] != "linux/amd64" or value["user"] != "999:999":
        raise ValueError("QUALIFIED_IMAGE_IDENTITY_MISMATCH")
    if output.exists() or output.is_symlink() or output.resolve() != output.absolute():
        raise ValueError("FRESH_IMAGE_OUTPUT_REQUIRED")
    if not 0 < value["tar_bytes"] < 1024**3 or not 0 < len(value["parts"]) <= 32:
        raise ValueError("IMAGE_TRANSFER_BOUND")
    for i, part in enumerate(value["parts"], 1):
        if part["file"] != f"nana-firstlife-0d842676.tar.gz.part{i:03}":
            raise ValueError("IMAGE_PART_SEQUENCE_INVALID")
        p = manifest.parent / part["file"]
        if (
            p.is_symlink()
            or p.stat().st_size != part["bytes"]
            or part["bytes"] > 30 * 1024**2
            or digest(p) != part["sha256"]
        ):
            raise ValueError("IMAGE_PART_INVALID")
    compressed = output.with_name(output.name + ".verified.gz")
    with compressed.open("xb") as f:
        os.fchmod(f.fileno(), 0o600)
        for part in value["parts"]:
            with (manifest.parent / part["file"]).open("rb") as source:
                while block := source.read(1024 * 1024):
                    f.write(block)
        f.flush()
        os.fsync(f.fileno())
    if compressed.stat().st_size != value["gzip_bytes"] or digest(compressed) != value["gzip_sha256"]:
        raise ValueError("IMAGE_GZIP_INVALID")
    partial = output.with_name(output.name + ".partial")
    total = 0
    with gzip.open(compressed, "rb") as source, partial.open("xb") as f:
        os.fchmod(f.fileno(), 0o600)
        while block := source.read(1024 * 1024):
            total += len(block)
            if total > value["tar_bytes"]:
                raise ValueError("IMAGE_TAR_BOUND")
            f.write(block)
        f.flush()
        os.fsync(f.fileno())
    if total != value["tar_bytes"] or digest(partial) != value["tar_sha256"]:
        raise ValueError("ORIGINAL_IMAGE_TAR_MISMATCH")
    # Hard-link creation refuses a concurrent destination; no overwrite.
    os.link(partial, output)
    partial.unlink()
    return value


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--load", action="store_true")
    a = p.parse_args()
    v = restore(a.manifest, a.manifest_sha256, a.output)
    if a.load:
        subprocess.run([*DOCKER, "load", "-i", str(a.output)], check=True)
        result = json.loads(subprocess.check_output([*DOCKER, "image", "inspect", IMAGE]))[0]
        if (result["Id"], result["Os"], result["Architecture"], result["Config"]["User"]) != (
            IMAGE,
            "linux",
            "amd64",
            "999:999",
        ):
            raise ValueError("LOADED_IMAGE_IDENTITY_MISMATCH")
    print(
        json.dumps(
            {
                "original_tar_sha256": v["tar_sha256"],
                "image_id": IMAGE,
                "loaded": a.load,
                "built": False,
                "service_started": False,
                "subject_created": False,
            }
        )
    )
