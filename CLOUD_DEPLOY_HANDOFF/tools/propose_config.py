"""Create a NEW typed host configuration proposal; never install or activate it.

Preserve the original identity, lineage, production receipts, roles, home and
origin. Use the final image's original HostConfiguration DTO for validation.
No credentials, Subject initialization, config overwrite or service restart.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

from stage import DOCKER, metadata


def proposal(current, release, *, provider_settings=False):
    source = release["core_source"]
    result = json.loads(json.dumps(current))
    active = current["active_release"]
    previous = [item for item in current["releases"] if item["release_id"] == active]
    if len(previous) != 1:
        raise ValueError("EXISTING_ACTIVE_RELEASE_REQUIRED")
    root = "/opt/nana-core/runtime/core-releases/" + source
    # Retain the host's active slot alias: persisted Supervisor state must not
    # silently select an absent old source. The full source pin is explicit.
    result["releases"] = [
        {
            **previous[0],
            "root": root,
            "python": root + "/.venv/bin/python",
            "source_commit": source,
            "integrity_digest": release["core_integrity_sha256"],
        }
    ]
    result["web_root"] = "/opt/nana-core/runtime/web-releases/" + release["web_sha256"]
    if provider_settings:
        result["allow_provider_configuration"] = True
    return result


VALIDATE = r"""
import json,sys
from pathlib import Path
root=Path('/opt/nana-core/runtime/core-releases')/sys.argv[1]
sys.path.insert(0,str(root/'src'))
from nana_core.life.live_api.__main__ import HostConfiguration
from nana_core.life.live_api.supervisor import Release
value=json.load(sys.stdin)
original=HostConfiguration.model_validate_json(json.dumps(value['original']))
candidate=HostConfiguration.model_validate_json(json.dumps(value['candidate']))
for name in ('home','host_state','binding','roles','activation','public_origin','port','active_release'):
 if getattr(original,name)!=getattr(candidate,name):raise ValueError('HOST_IDENTITY_OR_AUTHORITY_CHANGED')
candidate.releases[0].validate_local(qualified=True)
print(json.dumps(candidate.model_dump(mode='json')))
"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--handoff", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--config-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--enable-provider-settings", action="store_true")
    a = p.parse_args()
    if a.config.is_symlink() or a.config.stat().st_size > 65536 or a.config.stat().st_mode & 0o077:
        raise ValueError("PRIVATE_EXPLICIT_CONFIGURATION_REQUIRED")
    original = a.config.read_bytes()
    if hashlib.sha256(original).hexdigest() != a.config_sha256:
        raise ValueError("ORIGINAL_CONFIGURATION_DIGEST_MISMATCH")
    release = metadata(a.handoff)
    current = json.loads(original)
    candidate = proposal(current, release, provider_settings=a.enable_provider_settings)
    python = "/opt/nana-core/runtime/core-releases/" + release["core_source"] + "/.venv/bin/python"
    command = DOCKER + [
        "run",
        "--rm",
        "-i",
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
        "32",
        "--memory",
        "256m",
        "--entrypoint",
        python,
        release["image_id"],
        "-I",
        "-B",
        "-c",
        VALIDATE,
        release["core_source"],
    ]
    checked = subprocess.run(
        command,
        input=json.dumps({"original": current, "candidate": candidate}),
        text=True,
        capture_output=True,
        timeout=30,
    )
    if checked.returncode:
        raise ValueError("ORIGINAL_DTO_OR_QUALIFIED_RELEASE_VALIDATION_FAILED")
    output = (json.dumps(json.loads(checked.stdout), indent=2) + "\n").encode()
    fd = os.open(a.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(output)
        stream.flush()
        os.fsync(stream.fileno())
    print(
        json.dumps(
            {
                "state": "PROPOSAL_ONLY_NOT_INSTALLED",
                "config_sha256": hashlib.sha256(original).hexdigest(),
                "proposal_sha256": hashlib.sha256(output).hexdigest(),
                "identity_or_authority_changed": False,
                "provider_calls": 0,
                "production_activated": False,
            }
        )
    )


if __name__ == "__main__":
    main()
