"""Stream the explicitly pinned local image into bounded gzip parts; no secrets."""

import gzip, hashlib, json, subprocess
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
    root = Path("artifacts/first-life-unified-release")
    writer = Parts(root)
    process = subprocess.Popen(D + ["save", IMAGE], stdout=subprocess.PIPE)
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
                "image_id": IMAGE,
                "architecture": "linux/amd64",
                "core_source": "9217e3f3550dc5a875c42ac6de53035dd73deae2",
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
