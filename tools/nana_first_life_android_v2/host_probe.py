"""Read-only final-host persistence/supervision probe. No credentials or bodies.

Run explicitly on the Ubuntu HOST, not merely inside AstrBot. No restart,
installation, account creation, Docker config/Env read, Store open or private
history. An optional Docker inspect selects ONLY Mounts, never the full config.
"""

import argparse
import json
import os
import platform
import subprocess
from pathlib import Path


def mount_for(mounts, path):
    path = Path(path)
    matches = [m for m in mounts if path == Path(m["Destination"]) or Path(m["Destination"]) in path.parents]
    if not matches:
        return {"persistent": False, "reason": "CONTAINER_WRITABLE_LAYER_NOT_ACCEPTABLE"}
    row = max(matches, key=lambda m: len(m["Destination"]))
    return {
        "persistent": row.get("Type") in {"bind", "volume"},
        "type": row.get("Type"),
        "source": row.get("Source"),
        "destination": row["Destination"],
        "writable": row.get("RW"),
        "requires_host_path_owner_backup_and_restore_qualification": True,
    }


def directory(path):
    p = Path(path).absolute()
    if p.is_symlink():
        return {"state": "SYMLINK_REVIEW_REQUIRED"}
    if not p.exists():
        return {"state": "NOT_PRESENT"}
    info = p.stat()
    return {
        "state": "PRESENT_NOT_DURABILITY_QUALIFIED",
        "uid": info.st_uid,
        "gid": info.st_gid,
        "mode": oct(info.st_mode & 0o777),
        "directory": p.is_dir(),
        "is_mount": p.is_mount(),
    }


def probe(a):
    pid1 = Path("/proc/1/comm").read_text().strip()
    output = {
        "evidence": "ACTUAL_READ_ONLY_ON_EXECUTING_MACHINE",
        "machine": platform.machine(),
        "kernel": platform.release(),
        "pid1": pid1,
        "running_as_root": os.geteuid() == 0,
        "systemd_runtime_present": Path("/run/systemd/system").is_dir(),
        "production_modified": False,
        "store_opened": False,
        "private_content_read": False,
    }
    if pid1 == "systemd" and output["systemd_runtime_present"]:
        try:
            process = subprocess.run(
                ["systemctl", "is-system-running", "--no-pager"], capture_output=True, text=True, timeout=5
            )
            output["systemd_state"] = (
                process.stdout.strip()
                if process.stdout.strip()
                in {"running", "degraded", "starting", "maintenance", "stopping", "offline", "unknown"}
                else "UNKNOWN"
            )
        except (OSError, subprocess.TimeoutExpired):
            output["systemd_state"] = "UNAVAILABLE"
    else:
        output["systemd_state"] = "NOT_HOST_SYSTEMD"
    output["recommended_supervision"] = "INDEPENDENT_NONROOT_DOCKER_USER_SELECTED"
    output["host_systemd_is_gate"] = False
    for name, path in [("subject_directory", a.subject), ("backup_directory", a.backups)]:
        if path:
            output[name] = directory(path)
    if a.container:
        process = subprocess.run(
            ["docker", "inspect", "--format", "{{json .Mounts}}", a.container],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if process.returncode:
            output["runtime_persistence"] = {"state": "MOUNT_METADATA_UNAVAILABLE"}
        else:
            output["runtime_persistence"] = mount_for(json.loads(process.stdout), a.container_runtime)
    if a.python:
        # Explicit known runtime path, isolated import probe, no ambient secret
        # discovery and no file write/import of Nana or user data.
        code = "import sys,sqlite3,json;print(json.dumps({'python':list(sys.version_info[:3]),'sqlite':sqlite3.sqlite_version,'sqlite_supported':sqlite3.sqlite_version_info>=(3,51,3),'executable':sys.executable,'native':{n:__import__(n).__name__ for n in ('ctypes','ssl','zlib','sqlite3','resource','termios','venv')}}))"
        try:
            process = subprocess.run(
                [str(a.python), "-I", "-B", "-c", code],
                capture_output=True,
                text=True,
                timeout=10,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            )
            output["runtime_binding"] = (
                json.loads(process.stdout)
                if process.returncode == 0
                else {"state": "FINAL_HOST_EXECUTION_FAILED", "returncode": process.returncode}
            )
        except (OSError, ValueError, subprocess.TimeoutExpired):
            output["runtime_binding"] = {"state": "FINAL_HOST_EXECUTION_UNAVAILABLE"}
    output["bz2_lzma"] = "NOT_REQUIRED_BY_CURRENT_CORE_HOST_CONTRACT_NO_INSTALL_REQUESTED"
    output["code_skills_sandbox"] = "BLOCKED_NO_ASTRBOT_PRIVILEGE_CHANGE_AUTHORIZED"
    output["account_service_network_genesis_cutover"] = "SEPARATE_APPROVAL_REQUIRED"
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--python", type=Path)
    p.add_argument("--container")
    p.add_argument("--container-runtime", default="/opt/nana-core")
    p.add_argument("--subject", type=Path)
    p.add_argument("--backups", type=Path)
    a = p.parse_args()
    print(json.dumps(probe(a), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
