"""Append a version candidate using original DTO; no install, roles or genesis."""

import json
import os
import subprocess
from pathlib import Path

from integrity import sha

VALIDATE = r'''
import json,sys
root='/opt/nana-core/runtime/core-releases/'+sys.argv[1]
sys.path.insert(0,root+'/src')
from nana_core.life.live_api.__main__ import HostConfiguration
from nana_core.life.live_api.supervisor import Release
data=json.load(sys.stdin)
original=HostConfiguration.model_validate_json(json.dumps(data['original']))
candidate=HostConfiguration.model_validate_json(json.dumps(data['candidate']))
for field in ('home','host_state','binding','roles','activation','public_origin','port','active_release','allow_provider_configuration','provider_vault'):
 if getattr(original,field)!=getattr(candidate,field):raise ValueError('AUTHORITY_CHANGED')
for item in candidate.releases:
 if item.source_commit==sys.argv[1]:item.validate_local(qualified=True)
print(candidate.model_dump_json())
'''


def prepare(root, slot, source):
    current = root / "data/host/host.json"
    release_file = Path(__file__).with_name("release.json")
    if not current.is_file() or not release_file.is_file():
        return {"state": "NO_EXISTING_HOST_CONFIGURATION", "installed": False}
    if current.is_symlink() or current.stat().st_size > 65536 or current.stat().st_mode & 0o077:
        raise ValueError("PRIVATE_HOST_CONFIGURATION_REQUIRED")
    release = json.loads(release_file.read_text())
    original = json.loads(current.read_bytes())
    candidate = json.loads(json.dumps(original))
    target = "living-v4-" + source[:12]
    entries = candidate["releases"]
    if any(item["release_id"] == target for item in entries) or len(entries) >= 8:
        raise ValueError("RELEASE_REGISTRY_REVIEW_REQUIRED")
    prefix = "/opt/nana-core/runtime/core-releases/" + source
    entries.append({"release_id": target, "source_commit": source, "root": prefix,
                    "python": prefix + "/.venv/bin/python", "schema_version": 13,
                    "plan_contract": "PRECISION_V2", "integrity_digest": release["core_integrity_sha256"]})
    candidate["web_root"] = "/opt/nana-core/runtime/web-releases/" + release["web_sha256"]
    checked = subprocess.run([prefix + "/.venv/bin/python", "-I", "-B", "-c", VALIDATE, source],
                             input=json.dumps({"original": original, "candidate": candidate}),
                             text=True, capture_output=True, timeout=20)
    if checked.returncode:
        raise ValueError("ORIGINAL_DTO_PROPOSAL_REJECTED")
    value = json.dumps(json.loads(checked.stdout), indent=2).encode() + b"\n"
    destination = slot / "host-proposal.json"
    fd = os.open(destination, os.O_EXCL | os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(value)
        os.fchown(output.fileno(), 999, 999)
        output.flush()
        os.fsync(output.fileno())
    return {"state": "TYPED_PROPOSAL_ONLY", "source_config_sha256": sha(current),
            "proposal_sha256": sha(destination), "registered_candidate": target,
            "active_release_changed": False, "roles_changed": False, "installed": False}
