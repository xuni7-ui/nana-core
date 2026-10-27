"""Stream the explicitly pinned local image into bounded gzip parts; no secrets."""

import argparse
import gzip
import hashlib
import json
import re
import subprocess
from pathlib import Path

D = [
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
IMAGE = "sha256:de89985296bff22fb3a4882120a71a0af43b7758fef9a5b4c9cf99fb31d13270"


class Parts:
    def __init__(self, root):
        self.root = root
        self.index = 0
        self.file = None
        self.size = 0
        self.sha = hashlib.sha256()
        self.total = 0

    def write(self, data):
        original_length = len(data)
        self.sha.update(data)
        self.total += len(data)
        while data:
            if self.file is None or self.size == 28 * 1024 * 1024:
                if self.file:
                    self.file.close()
                self.index += 1
                self.size = 0
                self.file = (self.root / f"image.tar.gz.part{self.index:03d}").open("xb")
            chunk = data[: 28 * 1024 * 1024 - self.size]
            self.file.write(chunk)
            self.size += len(chunk)
            data = data[len(chunk) :]
        return original_length


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--source", default="9217e3f3550dc5a875c42ac6de53035dd73deae2")
    parser.add_argument("--destination", type=Path, default=Path("artifacts/first-life-unified-release"))
    args = parser.parse_args()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", args.image) or not re.fullmatch(r"[a-f0-9]{40}", args.source):
        raise ValueError("PINNED_IMAGE_AND_SOURCE_REQUIRED")
    observed = json.loads(subprocess.check_output(D + ["image", "inspect", args.image], text=True))[0]
    if (observed["Id"], observed["Os"], observed["Architecture"], observed["Config"]["User"]) != (
        args.image,
        "linux",
        "amd64",
        "999:999",
    ):
        raise ValueError("QUALIFIED_IMAGE_PLATFORM_OR_USER_MISMATCH")
    root = args.destination.absolute()
    root.mkdir(parents=True, exist_ok=True)
    if root.resolve() != root or (root / "image.json").exists() or any(root.glob("image.tar.gz.part*")):
        raise ValueError("FRESH_EXPORT_DESTINATION_REQUIRED")
    writer = Parts(root)
    process = subprocess.Popen(D + ["save", args.image], stdout=subprocess.PIPE)
    raw = hashlib.sha256()
    size = 0
    with gzip.GzipFile(filename="", mode="wb", fileobj=writer, mtime=0) as compressed:
        while chunk := process.stdout.read(1024 * 1024):
            raw.update(chunk)
            size += len(chunk)
            compressed.write(chunk)
    writer.file.close()
    exit_code = process.wait()
    if exit_code != 0:
        raise RuntimeError("IMAGE_SAVE_FAILED")
    rows = [
        {"file": p.name, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(root.glob("image.tar.gz.part*"))
    ]
    (root / "image.json").write_text(
        json.dumps(
            {
                "image_id": args.image,
                "architecture": "linux/amd64",
                "core_source": args.source,
                "image_bytes": observed["Size"],
                "user": observed["Config"]["User"],
                "gzip_bytes": writer.total,
                "gzip_sha256": writer.sha.hexdigest(),
                "tar_bytes": size,
                "tar_sha256": raw.hexdigest(),
                "parts": rows,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
