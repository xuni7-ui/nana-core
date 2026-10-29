"""Finite root Operator in a disposable container, never the ordinary Core.

Only the explicit host slot root is writable. No socket, secret, Subject open,
service control, Genesis, migration or backup database overwrite.
"""

import argparse
import json
import os
import re
import shutil
import tarfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrity import sha, verify_tree
from install_runtime_tree import install


def checked_inputs(root, source, image, manifest, digest):
    root = Path(root).absolute()
    if root.resolve() != root or not root.is_dir() or root.stat().st_uid != 0 or root.stat().st_mode & 0o022:
        raise ValueError("EXPLICIT_ROOT_OWNED_HOST_BIND_REQUIRED")
    if not re.fullmatch(r"[a-f0-9]{40}", source) or not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise ValueError("PINNED_RELEASE_REQUIRED")
    if sha(manifest) != digest:
        raise ValueError("RUNTIME_MANIFEST_DIGEST_MISMATCH")
    seal = json.loads(Path(manifest).read_bytes())
    if seal["image_id"] != image:
        raise ValueError("RUNTIME_IMAGE_BINDING_MISMATCH")
    return root, seal


def existing_slot(mode, target, seal, common):
    mismatches = verify_tree(target, seal["entries"])
    if mismatches:
        return {**common, "state": "SEALED_SLOT_CONFLICT", "persistent_changes": 0,
                "idempotent": False, "mismatch_count": len(mismatches), "mismatches": mismatches[:64]}
    receipt = target.parent / "stage-receipt.json"
    try:
        prior = json.loads(receipt.read_bytes())
        if prior["image_id"] != common["image_id"] or prior["source_commit"] != common["source_commit"]:
            raise ValueError()
    except (OSError, ValueError, KeyError):
        return {**common, "state": "STAGE_REQUIRES_OPERATOR_REVIEW", "persistent_changes": 0}
    if prior.get("state") == "HOST_CONFIGURATION_REVIEW_REQUIRED" and mode == "install":
        from proposal import prepare
        proposal = prepare(target.parents[2], target.parent, common["source_commit"])
        if proposal["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED":
            return {**common, **proposal, "persistent_changes": 0}
        prior.update(common, state="RUNTIME_STAGED_VERIFY_REQUIRED", host_configuration_proposal=proposal)
        prior.pop("code", None)
        prior.pop("context", None)
        publish_receipt(receipt, prior)
        return {**common, "state": "RUNTIME_STAGED_VERIFY_REQUIRED", "persistent_changes": 1, "idempotent": False}
    if prior.get("state") == "RUNTIME_STAGED_VERIFY_REQUIRED":
        if mode != "commit":
            return {**common, "state": "RUNTIME_STAGED_VERIFY_REQUIRED", "persistent_changes": 0}
        prior.update(state="READY_FOR_SWITCH", runtime_abi_verified=True)
        publish_receipt(receipt, prior)
        return {**common, "state": "READY_FOR_SWITCH", "persistent_changes": 1, "idempotent": False}
    if prior.get("state") != "READY_FOR_SWITCH":
        return {**common, "state": "STAGE_REQUIRES_OPERATOR_REVIEW", "persistent_changes": 0}
    return {**common, "state": "READY_FOR_SWITCH", "persistent_changes": 0, "idempotent": True,
            "mismatch_count": 0, "mismatches": []}


def run(mode, root, source, image, manifest, digest):
    root, seal = checked_inputs(root, source, image, manifest, digest)
    target = root / "slots" / source / "runtime"
    if target.resolve() != target:
        raise ValueError("SLOT_SYMLINK_DENIED")
    required = sum(row.get("bytes", 0) for row in seal["entries"].values())
    free = shutil.disk_usage(root).free
    common = {"source_commit": source, "image_id": image, "target": str(target),
              "target_context": "DOCKER_DAEMON_HOST_BIND", "free_bytes": free,
              "subject_opened": False, "canonical_home_changed": False, "services_changed": False}
    # Check in the candidate image before staging, committing or trusting an old
    # READY receipt. Supervisor may use its persisted alias instead of host.json.
    from proposal import inspect_existing
    compatibility = inspect_existing(root, source)
    common["host_configuration_preflight"] = compatibility
    if compatibility["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED":
        return {**common, **compatibility, "persistent_changes": 0}
    if target.exists():
        return existing_slot(mode, target, seal, common)
    if mode != "install":
        return {**common, "state": "NOT_INSTALLED", "required_runtime_bytes": required,
                "proposed_changes": ["new immutable runtime slot only"],
                "preserved": ["canonical home", "identity", "Store", "host config", "old images", "old runtime", "devices"],
                "production_switch": "SEPARATE_ORIGINAL_APPROVAL_REQUIRED", "persistent_changes": 0}
    if free < required + 256 * 1024 * 1024:
        return {**common, "state": "DISK_INSUFFICIENT", "required_bytes": required + 256 * 1024 * 1024, "persistent_changes": 0}
    slots = root / "slots"
    slots.mkdir(mode=0o755, exist_ok=True)
    if slots.stat().st_uid != 0 or slots.stat().st_mode & 0o022:
        raise ValueError("SLOT_PARENT_OWNERSHIP_INVALID")
    slot = slots / source
    slot.mkdir(mode=0o755)  # Never resume an unknown failed attempt.
    # Public SDK snapshot stays in anonymous RAM when disk is constrained.
    # No credential or Subject is included; the original installer is reused.
    fd = os.memfd_create("nana-public-runtime", os.MFD_CLOEXEC)
    try:
        with os.fdopen(os.dup(fd), "w+b") as stream:
            with tarfile.open(fileobj=stream, mode="w", format=tarfile.PAX_FORMAT) as archive:
                archive.add("/opt/nana-core/runtime", arcname=".", recursive=True)
            stream.flush()
        os.lseek(fd, 0, os.SEEK_SET)
        result = install(Path("/proc/self/fd") / str(fd), manifest, digest, target, image_id=image)
    finally:
        os.close(fd)
    mismatches = verify_tree(target, seal["entries"])
    if mismatches:
        return {**common, "state": "SEALED_SLOT_CONFLICT", "mismatch_count": len(mismatches), "mismatches": mismatches[:64]}
    result.update(common)
    result.update(state="RUNTIME_STAGED_VERIFY_REQUIRED", idempotent=False, persistent_changes=1)
    from proposal import prepare
    result["host_configuration_proposal"] = prepare(root, slot, source)
    if result["host_configuration_proposal"]["state"] == "HOST_CONFIGURATION_REVIEW_REQUIRED":
        result.update(state="HOST_CONFIGURATION_REVIEW_REQUIRED",
                      code=result["host_configuration_proposal"]["code"],
                      context=result["host_configuration_proposal"].get("context", {}))
    receipt = slot / "stage-receipt.json"
    publish_receipt(receipt, result)
    return result


def publish_receipt(receipt, result):
    import tempfile
    fd, temp = tempfile.mkstemp(prefix=".stage-receipt-", dir=receipt.parent)
    with os.fdopen(fd, "w") as output:
        output.write(json.dumps(result, indent=2) + "\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temp, receipt)
    directory = os.open(receipt.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "dry-run", "install", "rollback", "commit"))
    for name in ("root", "source", "image", "manifest", "digest"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        result = run(args.mode, args.root, args.source, args.image, args.manifest, args.digest)
    except (ValueError, OSError, KeyError, tarfile.TarError) as exc:
        result = {"state": "BLOCKED", "code": str(exc) if isinstance(exc, ValueError) else "OPERATOR_PREPARATION_FAILED",
                  "subject_opened": False, "services_changed": False}
    print(json.dumps(result, separators=(",", ":")))
    raise SystemExit(0 if result["state"] in {"READY_FOR_SWITCH", "RUNTIME_STAGED_VERIFY_REQUIRED", "NOT_INSTALLED"} else 2)
