"""Exact committed developer harness, separate from the ordinary Runtime."""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
from tools.nana_portable_cloud.build import git


def build(output, revision):
    output = Path(output)
    if output.exists():
        raise ValueError("FRESH_QUALIFICATION_OUTPUT_REQUIRED")
    commit = git("rev-parse", revision + "^{commit}").decode().strip()
    epoch = int(git("show", "-s", "--format=%ct", commit))
    root = output / "nana-quality-qualification-v2"
    root.mkdir(parents=True, mode=0o700)
    for source, name in [
        ("src/nana_core/continuity/controlled_world/lab.py", "lab.py"),
        ("tools/nana_precision/installed_probe.py", "installed_probe.py"),
        ("tools/nana_quality/QUALIFICATION.md", "README.md"),
    ]:
        (root / name).write_bytes(git("show", commit + ":" + source))
    (root / "source.json").write_text(
        json.dumps({"source_commit": commit, "ordinary_runtime": False, "new_provider_calls": 0}, indent=2) + "\n"
    )
    (root / "SHA256SUMS").write_text(
        "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in sorted(root.iterdir()))
    )
    archive = output / "nana-quality-qualification-v2.tar.gz"
    with (
        archive.open("wb") as target,
        gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as tar,
    ):
        for path in sorted(root.iterdir()):
            raw = path.read_bytes()
            entry = tarfile.TarInfo(root.name + "/" + path.name)
            entry.size = len(raw)
            entry.mode = 0o600
            entry.mtime = epoch
            tar.addfile(entry, io.BytesIO(raw))
    return {
        "source_commit": commit,
        "archive": str(archive),
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": 5,
        "ordinary_runtime": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--revision", required=True)
    a = p.parse_args()
    print(json.dumps(build(a.output, a.revision), indent=2))
