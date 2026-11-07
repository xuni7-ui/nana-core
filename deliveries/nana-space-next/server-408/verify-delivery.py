"""Read-only APK/Web/Core handoff consistency; no extraction or Core startup.

Run against an explicitly downloaded delivery directory. Integrity does not
authorize activation or attest real cloud, phone, provider or human experience.
Frontend source remains a build-pipeline assertion; Core source is checked in
the actual archive, and every Web file is compared with the actual APK assets.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import zipfile


def safe_name(name):
    if (
        not isinstance(name, str)
        or not name
        or "\\" in name
        or PurePosixPath(name).is_absolute()
        or any(part in {"", ".", ".."} for part in name.split("/"))
    ):
        raise ValueError("UNSAFE_DELIVERY_PATH")
    return name


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def verify(root, manifest_name):
    root = Path(root).absolute()
    if root.resolve() != root:
        raise ValueError("EXPLICIT_REAL_DELIVERY_ROOT_REQUIRED")
    path = root / safe_name(manifest_name)
    if path.resolve() != path or path.stat().st_size > 65536:
        raise ValueError("MANIFEST_INVALID")
    manifest = json.loads(path.read_text())
    files = manifest["files"]
    if not isinstance(files, dict) or not 3 <= len(files) <= 64:
        raise ValueError("DELIVERY_FILE_BOUND")
    for name, expected in files.items():
        item = root / safe_name(name)
        if item.resolve() != item or not item.is_file():
            raise ValueError("DELIVERY_FILE_UNAVAILABLE")
        if item.stat().st_size > 128 * 1024 * 1024:
            raise ValueError("DELIVERY_FILE_SIZE_BOUND")
        if item.stat().st_size != expected["bytes"] or sha256(item) != expected["sha256"]:
            raise ValueError("DELIVERY_FILE_INTEGRITY_MISMATCH")
    apk = [root / n for n in files if n.endswith(".apk")]
    web = [root / n for n in files if n.endswith("-web.tar.gz")]
    core = [root / n for n in files if n.endswith("-portable.tar.gz")]
    if len(apk) != 1 or len(web) != 1 or len(core) != 1:
        raise ValueError("ONE_MATCHED_ARTIFACT_SET_REQUIRED")
    with tarfile.open(core[0], "r:gz") as archive:
        runtime = archive.getmember("nana-first-life-portable-v1/runtime.json")
        if not runtime.isfile() or runtime.size > 65536:
            raise ValueError("CORE_RUNTIME_METADATA_INVALID")
        actual = json.load(archive.extractfile(runtime))
    if actual["source_commit"] != manifest["core_source"]:
        raise ValueError("CORE_SOURCE_MISMATCH")
    if manifest["frontend_source"] != manifest["core_source"]:
        raise ValueError("MATCHED_SOURCE_REQUIRED")
    count = 0
    with tarfile.open(web[0], "r:gz") as archive, zipfile.ZipFile(apk[0]) as android:
        names = set()
        for member in archive:
            name = safe_name(member.name)
            if (
                not name.startswith("nana-space-web/")
                or not member.isfile()
                or member.size > 8 * 1024 * 1024
                or name in names
                or count >= 256
            ):
                raise ValueError("WEB_ARCHIVE_INVALID")
            names.add(name)
            asset = "assets/public/" + name.removeprefix("nana-space-web/")
            info = android.getinfo(asset)
            if info.file_size != member.size or android.read(info) != archive.extractfile(member).read():
                raise ValueError("APK_WEB_MISMATCH")
            count += 1
    if count == 0:
        raise ValueError("WEB_ARCHIVE_EMPTY")
    return {
        "state": "ARTIFACT_CONSISTENCY_VERIFIED",
        "core_source": actual["source_commit"],
        "checked_files": len(files),
        "apk_web_files_equal": count,
        "frontend_source_attestation": "BUILD_PIPELINE_MANIFEST_NOT_INDEPENDENT_SOURCE_PROOF",
        "production_activation": False,
        "host_phone_provider_qualification": "NOT_IMPLIED",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.manifest), indent=2))
