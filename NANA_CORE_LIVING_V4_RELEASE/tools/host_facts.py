"""Read-only, allowlisted host/daemon facts. No private text, env or keys.

Run in the approved host/Operator context. Socket availability is never treated
as proof that this Python process itself is the Ubuntu host or host root.
"""

import json
import os
import platform
import time
from pathlib import Path
if __package__:
    from .docker_api import Docker
else:
    from docker_api import Docker


def collect(docker):
    rows = docker.containers()
    wanted = {"nana-bff-supervisor", "astrbot", "napcat"}
    selected = [row for row in rows if any(name.lstrip("/") in wanted for name in row["names"])]
    return {
        "schema_version": 1, "observed_at_us": time.time_ns() // 1000,
        "source_context": {"platform": platform.system(), "numeric_uid": os.geteuid(), "numeric_gid": os.getegid(),
                           "container_marker": Path("/.dockerenv").exists(), "host_identity": "UNKNOWN",
                           "user_namespace": os.readlink("/proc/self/ns/user"),
                           "mount_namespace": os.readlink("/proc/self/ns/mnt")},
        "target_context": "EXPLICIT_LOCAL_DOCKER_DAEMON", "daemon": docker.version(),
        "services": [docker.inspect(row["id"]) for row in selected],
        "missing_named_services": sorted(wanted - {name.lstrip("/") for row in selected for name in row["names"]}),
        "subject_or_private_body_read": False, "secrets_read": False, "services_changed": False,
        "source_hotfix_bodies": "NOT_COLLECTED_REQUIRE_EXPLICIT_REVIEW",
    }


if __name__ == "__main__":
    try:
        print(json.dumps(collect(Docker()), indent=2))
    except (OSError, ValueError, RuntimeError):
        print(json.dumps({"state": "DOCKER_CONTEXT_UNAVAILABLE", "services_changed": False}))
        raise SystemExit(2) from None
