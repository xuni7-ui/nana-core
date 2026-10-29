"""Append a version candidate using original DTO; no install, roles or genesis."""

import json
import os
import subprocess
from pathlib import Path

from integrity import sha

VALIDATE = r'''
import json,os,re,stat,sys
from pathlib import Path
root=sys.argv[1]
sys.path.insert(0,root+'/src')
from nana_core.life.live_api.__main__ import HostConfiguration
from nana_core.continuity.privacy import _json_object
data=json.load(sys.stdin)
def review(code, **context):
 print(json.dumps({'state':'HOST_CONFIGURATION_REVIEW_REQUIRED','code':code,'context':context}))
 raise SystemExit(2)
original_data=data['original']
service_uid=int(sys.argv[4])
config_path=Path(sys.argv[3])/'data/host/host.json'
if config_path.stat().st_uid!=service_uid:review('PRIVATE_HOST_CONFIGURATION_REQUIRED',config_path=str(config_path),required_uid=service_uid)
registry={item['release_id']:item for item in original_data['releases']}
if len(registry)!=len(original_data['releases']):review('RELEASE_REGISTRY_INVALID')
state_root=Path(original_data['host_state'])
state_path=state_root/'supervisor.json'
if not state_root.is_absolute() or state_root.resolve()!=state_root or not state_root.is_relative_to(Path(sys.argv[3])):
 review('SUPERVISOR_STATE_NOT_VISIBLE_IN_HOST_BIND',state_path=str(state_path))
persisted=None
try:
 if state_root.exists() and (state_root.stat().st_uid!=service_uid or state_root.stat().st_mode & 0o077):review('HOST_PRIVATE_DIRECTORY_REQUIRED',state_path=str(state_path),required_uid=service_uid)
 fd=os.open(state_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
except FileNotFoundError:
 pass
except OSError:
 review('SUPERVISOR_STATE_UNREADABLE',state_path=str(state_path))
else:
 try:
  with os.fdopen(fd,'rb') as stream:
   info=os.fstat(stream.fileno())
   if not stat.S_ISREG(info.st_mode) or info.st_uid!=service_uid or info.st_mode & 0o077:raise ValueError()
   raw=stream.read(524289)
  if len(raw)>524288:raise ValueError()
  state=json.loads(raw,object_pairs_hook=_json_object)
  if state.get('schema_version')!=1 or type(state.get('revision')) is not int:raise ValueError()
  persisted=state['active_release']
  if not isinstance(persisted,str):raise ValueError()
 except (OSError,ValueError,TypeError,KeyError,AttributeError):
  review('HOST_METADATA_CORRUPT',state_path=str(state_path))
aliases=[('configured_active_release',original_data['active_release'])]
if persisted is not None:aliases.append(('persisted_active_release',persisted))
for origin,alias in aliases:
 if alias not in registry:review('ACTIVE_RELEASE_NOT_REGISTERED',origin=origin,release_id=alias,state_path=str(state_path))
 item=registry[alias]
 context={'origin':origin,'release_id':alias,'source_commit':item['source_commit'],'root':item['root'],'python':item['python'],'state_path':str(state_path)}
 if item.get('schema_version',13)!=13:review('INCOMPATIBLE_RELEASE_SCHEMA',**context)
 if item.get('plan_contract','PRECISION_V2')!='PRECISION_V2':review('INCOMPATIBLE_PLAN_CONTRACT',**context)
try:
 original=HostConfiguration.model_validate_json(json.dumps(original_data))
 candidate=HostConfiguration.model_validate_json(json.dumps(data['candidate']))
except ValueError:
 review('ORIGINAL_DTO_PROPOSAL_REJECTED')
for field in ('home','host_state','binding','roles','activation','public_origin','port','active_release','allow_provider_configuration','provider_vault'):
 if getattr(original,field)!=getattr(candidate,field):raise ValueError('AUTHORITY_CHANGED')
releases={item.release_id:item for item in original.releases}
for origin,alias in aliases:
 item=releases[alias]
 try:item.validate_local(qualified=True)
 except Exception as exc:
  code=getattr(exc,'code','ACTIVE_RELEASE_VALIDATION_FAILED')
  if not isinstance(code,str) or not re.fullmatch('[A-Z0-9_]{1,96}',code):code='ACTIVE_RELEASE_VALIDATION_FAILED'
  review(code,origin=origin,release_id=alias,source_commit=item.source_commit,root=item.root,python=item.python,state_path=str(state_path))
for item in candidate.releases:
 if item.source_commit==sys.argv[2]:item.validate_local(qualified=True)
print(json.dumps({'state':'ACTIVE_RELEASE_COMPATIBILITY_VERIFIED','configured_active_release':original.active_release,
 'persisted_active_release':persisted,'state_path':str(state_path),'candidate':json.loads(candidate.model_dump_json())}))
'''


def existing(root):
    current = root / "data/host/host.json"
    if not current.exists() and not current.is_symlink():
        return current, None
    if current.is_symlink() or current.stat().st_size > 65536 or current.stat().st_mode & 0o077:
        raise ValueError("PRIVATE_HOST_CONFIGURATION_REQUIRED")
    return current, json.loads(current.read_bytes())


def validate(root, source, original, candidate):
    prefix = "/opt/nana-core/runtime/core-releases/" + source
    try:
        checked = subprocess.run([prefix + "/.venv/bin/python", "-I", "-B", "-c", VALIDATE, prefix, source, str(root), "999"],
                                 input=json.dumps({"original": original, "candidate": candidate}),
                                 text=True, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"state": "HOST_CONFIGURATION_REVIEW_REQUIRED",
                "code": "HOST_PREFLIGHT_TIMED_OUT" if isinstance(exc, subprocess.TimeoutExpired) else "CANDIDATE_SDK_PREFLIGHT_UNAVAILABLE",
                "context": {"candidate_source_commit": source, "python": prefix + "/.venv/bin/python"}}
    try:
        result = json.loads(checked.stdout)
        if result["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED":
            return result
        if checked.returncode or result["state"] != "ACTIVE_RELEASE_COMPATIBILITY_VERIFIED":
            raise ValueError()
        return result
    except (ValueError, KeyError, TypeError):
        return {"state": "HOST_CONFIGURATION_REVIEW_REQUIRED", "code": "ORIGINAL_DTO_PROPOSAL_REJECTED"}


def inspect_existing(root, source):
    _, original = existing(root)
    if original is None:
        return {"state": "NO_EXISTING_HOST_CONFIGURATION", "installed": False}
    result = validate(root, source, original, original)
    result.pop("candidate", None)
    return result


def prepare(root, slot, source):
    current, original = existing(root)
    if original is None:
        return {"state": "NO_EXISTING_HOST_CONFIGURATION", "installed": False}
    release = json.loads(Path(__file__).with_name("release.json").read_text())
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
    result = validate(root, source, original, candidate)
    if result["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED":
        return result
    value = json.dumps(result.pop("candidate"), indent=2).encode() + b"\n"
    destination = slot / "host-proposal.json"
    fd = os.open(destination, os.O_EXCL | os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(value)
        os.fchown(output.fileno(), 999, 999)
        output.flush()
        os.fsync(output.fileno())
    return {"state": "TYPED_PROPOSAL_ONLY", "source_config_sha256": sha(current),
            "proposal_sha256": sha(destination), "registered_candidate": target,
            "active_release_compatibility": result,
            "active_release_changed": False, "roles_changed": False, "installed": False}
