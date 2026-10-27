"""Read-only process-context persistence/supervision probe. No credentials or bodies.

Run explicitly through an approved host channel for host evidence. Merely running
this tool, even as UID 0, does not establish that channel or prove host identity.
No restart,
installation, account creation, Docker config/Env read, Store open or private
history. An optional Docker inspect selects ONLY Mounts, never the full config.
"""

import argparse
import json
import platform
import subprocess
from pathlib import Path

from nana_core.execution_context.contracts import ContextBinding
from nana_core.execution_context.probe import LocalContextProbe


def local_probe():
    """Unknown endpoint until a trusted application binds its actual channel."""
    return LocalContextProbe(
        ContextBinding(target_id="local-process", scope="UNKNOWN", binding_id="operator-local-probe")
    )


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


def directory(path, *, observer=None):
    """Metadata in this namespace; a missing path says nothing about the host."""
    evidence = (observer or local_probe()).observe(str(Path(path).absolute()))
    output = {
        "state": {
            "MISSING": "NOT_PRESENT_IN_EXECUTION_CONTEXT",
            "DENIED": "PERMISSION_DENIED_IN_EXECUTION_CONTEXT",
            "SYMLINK": "SYMLINK_REVIEW_REQUIRED",
            "UNKNOWN": "UNKNOWN",
        }.get(evidence.status, "PRESENT_NOT_DURABILITY_QUALIFIED"),
        "path_observation": evidence.model_dump(mode="json"),
        "host_verification": "UNKNOWN",
    }
    if evidence.status != "PRESENT":
        return output
    output.update({
        "state": "PRESENT_NOT_DURABILITY_QUALIFIED",
        "uid": evidence.uid,
        "gid": evidence.gid,
        "mode": oct(evidence.mode),
        "directory": evidence.file_kind == "DIRECTORY",
        "is_mount": evidence.mount.mount_point == evidence.actual_path if evidence.mount else None,
    })
    return output


def docker_mount_metadata(container, runtime_path, context):
    """The selected Docker daemon may itself be remote or nested."""
    try:
        process = subprocess.run(
            ["docker", "inspect", "--format", "{{json .Mounts}}", container],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if process.returncode:
            raise ValueError("MOUNT_METADATA_UNAVAILABLE")
        result = mount_for(json.loads(process.stdout), runtime_path)
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        result = {"state": "MOUNT_METADATA_UNAVAILABLE"}
    result.update({
        "observation_context_id": context.context_id,
        "execution_channel": "EXPLICIT_LOCAL_DOCKER_CLIENT",
        "docker_endpoint_scope": "UNKNOWN",
        "supplied_container_label": container,
        "source_path_scope": "DOCKER_DAEMON_METADATA_NOT_LOCAL_FILESYSTEM_PROOF",
        "host_verification": "UNKNOWN",
    })
    return result


def probe(a):
    observer = local_probe()
    context = observer.capture()
    try:
        pid1 = Path("/proc/1/comm").read_text()[:128].strip()
    except OSError:
        pid1 = "UNKNOWN"
    output = {
        "evidence": "ACTUAL_READ_ONLY_IN_CURRENT_EXECUTION_CONTEXT",
        "execution_context": context.model_dump(mode="json"),
        "host_verification": "UNKNOWN",
        "host_root_authority": "UNKNOWN",
        "machine": platform.machine(),
        "kernel": platform.release(),
        "pid1": pid1,
        "process_euid_is_zero": context.euid == 0,
        # Compatibility field; deliberately scoped, never host authority.
        "running_as_root": context.euid == 0,
        "running_as_root_deprecated": True,
        "root_identity_scope": "CURRENT_USER_NAMESPACE_ONLY",
        "systemd_runtime_present": Path("/run/systemd/system").is_dir(),
        "systemd_observation_scope": "CURRENT_EXECUTION_CONTEXT_ONLY",
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
        output["systemd_state"] = "NOT_OBSERVED_IN_EXECUTION_CONTEXT"
    output["recommended_supervision"] = "INDEPENDENT_NONROOT_DOCKER_USER_SELECTED"
    output["host_systemd_is_gate"] = False
    for name, path in [("subject_directory", a.subject), ("backup_directory", a.backups)]:
        if path:
            output[name] = directory(path, observer=observer)
    if a.container:
        output["runtime_persistence"] = docker_mount_metadata(a.container, a.container_runtime, context)
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
                else {"state": "EXPLICIT_PYTHON_EXECUTION_FAILED", "returncode": process.returncode}
            )
        except (OSError, ValueError, subprocess.TimeoutExpired):
            output["runtime_binding"] = {"state": "EXPLICIT_PYTHON_EXECUTION_UNAVAILABLE"}
        output["runtime_binding"]["launch_context_id"] = context.context_id
        output["runtime_binding"]["host_verification"] = "UNKNOWN"
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
