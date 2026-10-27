"""Host-stdlib adapter for the existing Operator's checking command only.

Runs private Python/_ssl and original checker in the same qualified Docker image
as Core. Mounts explicit inputs read-only. No host Python SSL, global library
replacement, new identity, credential lookup, authority or production activation.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

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


def command(image, source, mode, roots, script=None, script_sha=None, original=()):
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image) or not re.fullmatch(r"[a-f0-9]{40}", source):
        raise ValueError("PINNED_IMAGE_AND_SOURCE_REQUIRED")
    if mode not in {"abi", "dry-run", "verify-only"} or len(roots) > 4:
        raise ValueError("READ_ONLY_CHECK_MODE_REQUIRED")
    approved = []
    for item in roots:
        path = Path(item)
        if (
            not path.is_absolute()
            or path.resolve() != path
            or not path.is_dir()
            or str(path) in {"/", "/srv", "/etc", "/root", "/home", "/proc", "/sys", "/run", "/var"}
            or "," in str(path)
            or any(ord(x) < 32 for x in str(path))
        ):
            raise ValueError("EXPLICIT_NARROW_READ_ROOT_REQUIRED")
        approved.append(path)
    if mode != "abi":
        path = Path(script or "")
        if not any(root in path.parents for root in approved) or not re.fullmatch(r"[a-f0-9]{64}", script_sha or ""):
            raise ValueError("ORIGINAL_CHECKER_SCOPE_REQUIRED")
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != script_sha:
            raise ValueError("ORIGINAL_CHECKER_DIGEST_MISMATCH")
    helper = Path(__file__).resolve().with_name("container_check.py")
    python = f"/opt/nana-core/runtime/core-releases/{source}/.venv/bin/python"
    args = [
        *DOCKER,
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--user",
        "999:999",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        "64",
        "--memory",
        "512m",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,nosuid,noexec,size=32m,uid=999,gid=999,mode=1770",
        "--mount",
        f"type=bind,src={helper},dst=/nana-container-check.py,readonly",
    ]
    for path in approved:
        args += ["--mount", f"type=bind,src={path},dst={path},readonly"]
    args += ["--entrypoint", python, image, "-I", "-B", "/nana-container-check.py", "--source", source, "--mode", mode]
    if script:
        args += ["--script", script, "--script-sha256", script_sha, "--", *original]
    return args


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--mode", required=True, choices=["abi", "dry-run", "verify-only"])
    p.add_argument("--read-root", action="append", default=[])
    p.add_argument("--script")
    p.add_argument("--script-sha256")
    p.add_argument("args", nargs=argparse.REMAINDER)
    a = p.parse_args()
    original = a.args[1:] if a.args[:1] == ["--"] else a.args
    result = subprocess.run(
        command(a.image, a.source, a.mode, a.read_root, a.script, a.script_sha256, original), timeout=60
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.TimeoutExpired):
        print(
            json.dumps({"status": "BLOCKED", "code": "QUALIFIED_OPERATOR_CHECK_UNAVAILABLE", "genesis_executed": False})
        )
        raise SystemExit(2) from None
