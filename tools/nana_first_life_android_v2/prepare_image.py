"""Prepare a small explicit Docker context from hash-bound non-sensitive inputs.

Does not run Docker, create a Subject, contact the cloud or inspect credentials.
Run the emitted argument array with the managed local daemon and public CA mount.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNTIME_SHA256 = "1dbbcf46f6a16ab41deac96657a43a8fcecbba6ab7dea1d0113a84b2c8285b27"


def prepare(runtime, destination):
    runtime = Path(runtime)
    destination = Path(destination).absolute()
    artifacts = REPO / "artifacts/first-life-android-v2"
    manifest = json.loads((artifacts / "manifest.json").read_text())
    source = manifest["runtime_source_commit"]
    archives = {"runtime.tar.gz": (runtime, RUNTIME_SHA256),
                "core.tar.gz": (artifacts / f"nana-core-{source[:7]}.tar.gz", manifest["files"][f"nana-core-{source[:7]}.tar.gz"]["sha256"]),
                "web.tar.gz": (artifacts / "nana-space-live-web.tar.gz", manifest["files"]["nana-space-live-web.tar.gz"]["sha256"])}
    if destination.exists() or destination.resolve() != destination:
        raise ValueError("FRESH_DOCKER_CONTEXT_REQUIRED")
    for path, sha in archives.values():
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("DOCKER_INPUT_HASH_MISMATCH")
    destination.mkdir(mode=0o700, parents=True)
    directory = REPO / "deployment/first-life-v2/docker"
    for name in ("Dockerfile", ".dockerignore", "container_entry.py", "loopback_relay.py", "extract_runtime.py", "extract_web.py"):
        shutil.copyfile(directory / name, destination / name)
    shutil.copyfile(artifacts / "nana-unpack.py", destination / "unpack_core.py")
    for name, (path, _) in archives.items():
        shutil.copyfile(path, destination / name)
    result = {"context": str(destination), "runtime_source_commit": source,
              "runtime_sha256": RUNTIME_SHA256,
              "core_sha256": archives["core.tar.gz"][1], "web_sha256": archives["web.tar.gz"][1],
              "subject_created": False, "secrets_copied": False,
              "docker_build_arguments": ["build", "--target", "qualified-runtime",
                  "--build-arg", "RUNTIME_SHA256=" + RUNTIME_SHA256,
                  "--build-arg", "CORE_SHA256=" + archives["core.tar.gz"][1],
                  "--build-arg", "WEB_SHA256=" + archives["web.tar.gz"][1],
                  "--build-arg", "CORE_SOURCE_COMMIT=" + source,
                  "--secret", "id=system_ca,src=/etc/ssl/certs/ca-certificates.crt", str(destination)]}
    (destination / "build-inputs.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.runtime, args.destination), indent=2))
