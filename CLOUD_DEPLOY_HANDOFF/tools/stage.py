"""Stage a NEW version slot from a verified image; never start/stop a service.

Reuse the original numeric-owner/atomic runtime installer. Canonical home,
/srv/nana-core/runtime and old slots are never replaced. Host Operator invokes
this explicit preparation tool after checking the handoff manifest.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True

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


def original_installer():
    path = Path(__file__).with_name("install_runtime_tree.py")
    if not path.is_file():
        path = Path(__file__).resolve().parents[1] / "nana_first_life_android_v2/install_runtime_tree.py"
    spec = importlib.util.spec_from_file_location("original_runtime_install", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata(handoff):
    p = handoff / "release.json"
    if p.is_symlink() or p.stat().st_size > 65536:
        raise ValueError("RELEASE_METADATA_INVALID")
    value = json.loads(p.read_text())
    if not re.fullmatch("sha256:[a-f0-9]{64}", value["image_id"]) or not re.fullmatch(
        "[a-f0-9]{40}", value["core_source"]
    ):
        raise ValueError("PINNED_RELEASE_REQUIRED")
    return value


def stage(handoff, root):
    if os.geteuid() != 0:
        raise ValueError("ROOT_OPERATOR_REQUIRED_FOR_NUMERIC_OWNERSHIP")
    handoff = Path(handoff).resolve()
    root = Path(root).absolute()
    value = metadata(handoff)
    if root.resolve() != root or not root.is_dir() or root.stat().st_uid != 0 or root.stat().st_mode & 0o022:
        raise ValueError("EXPLICIT_ROOT_OWNED_HOME_REQUIRED")
    slots = root / "slots"
    if slots.is_symlink():
        raise ValueError("SLOT_SYMLINK_DENIED")
    slots.mkdir(mode=0o755, exist_ok=True)
    if slots.stat().st_uid != 0 or slots.stat().st_mode & 0o022:
        raise ValueError("SLOT_PARENT_OWNERSHIP_INVALID")
    slot = slots / value["core_source"]
    slot.mkdir(mode=0o755, exist_ok=False)  # No overwriting or resuming an unknown failed slot.
    reference = handoff / "runtime-tree.json"
    if hashlib.sha256(reference.read_bytes()).hexdigest() != value["runtime_manifest_sha256"]:
        raise ValueError("NEW_RUNTIME_SEAL_MISMATCH")
    actual = subprocess.check_output(
        DOCKER + ["image", "inspect", "--format", "{{.Id}}", value["image_id"]], text=True
    ).strip()
    if actual != value["image_id"]:
        raise ValueError("IMAGE_ID_MISMATCH")
    archive = slot / ".runtime-input.tar"
    container = subprocess.check_output(DOCKER + ["create", value["image_id"]], text=True).strip()
    try:
        with archive.open("xb") as stream:
            subprocess.run(
                DOCKER + ["cp", container + ":/opt/nana-core/runtime/.", "-"], stdout=stream, check=True, timeout=120
            )
        if archive.stat().st_size > 1024**3:
            raise ValueError("RUNTIME_ARCHIVE_BOUND")
        report = original_installer().install(
            archive, reference, value["runtime_manifest_sha256"], slot / "runtime", image_id=value["image_id"]
        )
        archive.unlink()  # Only this tool's non-sensitive temporary archive.
        report.update(slot=str(slot), production_started=False, canonical_home_changed=False, old_runtime_changed=False)
        (slot / "stage-receipt.json").write_text(json.dumps(report, indent=2) + "\n")
        return report
    finally:
        subprocess.run(DOCKER + ["rm", container], stdout=subprocess.DEVNULL, check=False, timeout=20)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--handoff", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path("/srv/nana-core"))
    a = p.parse_args()
    print(json.dumps(stage(a.handoff, a.root), indent=2))


if __name__ == "__main__":
    main()
