"""Deterministic non-sensitive delivery only; never contact or change a host."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def build(output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("NEW_DELIVERY_PATH_REQUIRED")
    names = [
        "docs/nana_first_life_android_v2/PRODUCTION_APPROVAL_V1.md",
        "docs/nana_first_life_android_v2/CLOUD_RUNTIME_VALIDATION.md",
        "deployment/first-life-v2/canonical-plan.json",
        "deployment/first-life-v2/activation-preparation.json",
        "tools/nana_first_life_android_v2/prepare_image.py",
        "tools/nana_first_life_android_v2/build_operator_pack.py",
    ]
    names += ["deployment/first-life-v2/docker/" + name for name in (
        "Dockerfile", ".dockerignore", "README.md", "compose.yaml",
        "container_entry.py", "extract_runtime.py", "extract_web.py", "loopback_relay.py")]
    names += ["artifacts/first-life-android-v2/" + name for name in (
        "README.md", "manifest.json", "SHA256SUMS", "nana-core-dbfb37e.tar.gz",
        "nana-space-live-web.tar.gz", "nana-space-2.0.0-debug.apk",
        "nana-space-2.0.0-release-unsigned.apk", "nana-unpack.py")]
    payload = {}
    for name in names:
        p = REPO / name
        if p.is_symlink() or not p.is_file():
            raise ValueError("REGULAR_WHITELIST_MEMBER_REQUIRED")
        payload[name] = p.read_bytes()
    payload["READ_FIRST.txt"] = (
        "PREPARED ONLY. No production approval or execution.\n"
        "Read docs/nana_first_life_android_v2/PRODUCTION_APPROVAL_V1.md first.\n"
        "The previously verified cloud SDK archive is NOT duplicated here.\n"
        "Run prepare_image.py with its explicit archive path and a new isolated context.\n"
        "Do not run compose up/serve or create a Subject before final approval.\n"
        "No cloud password, private DB or Subject identity is included.\n"
    ).encode()
    manifest = {
        "base_commit": "99b93d47632939b62909f50120402e60a7820ae7",
        "source_snapshot": "EXPLICIT_FILE_HASHES_NOT_A_CLAIM_OF_CLEAN_BASE",
        "production_approved": False, "production_executed": False,
        "runtime_sdk_included": False, "subject_included": False,
        "self_excluded": True,
        "sha256": {n: hashlib.sha256(b).hexdigest() for n, b in sorted(payload.items())},
    }
    payload["MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, body in sorted(payload.items()):
            info = zipfile.ZipInfo("nana-first-life-cloud-operator-v1/" + name, (2026, 10, 26, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, body, compresslevel=9)
    return {"bytes": output.stat().st_size, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "entries": len(payload), "production_changed": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    print(json.dumps(build(p.parse_args().output), indent=2))
