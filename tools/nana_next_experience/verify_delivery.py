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


def metadata(root, name, expected_sha=None):
    path = root / safe_name(name)
    if path.resolve() != path or path.stat().st_size > 65536:
        raise ValueError("MANIFEST_INVALID")
    if expected_sha is not None and sha256(path) != expected_sha:
        raise ValueError("SELECTOR_MANIFEST_INTEGRITY_MISMATCH")
    return json.loads(path.read_text())


def runtime_metadata(path):
    with tarfile.open(path, "r:gz") as archive:
        member = archive.getmember("nana-first-life-portable-v1/runtime.json")
        if not member.isfile() or member.size > 65536:
            raise ValueError("CORE_RUNTIME_METADATA_INVALID")
        return json.load(archive.extractfile(member))


def verify_current(root, selector_name):
    """Explicit client + server patch; old same-source verification stays strict.

    Proves file/declared contract consistency, not semantic compatibility, latest
    Git freshness, trusted execution receipts or real production qualification.
    """
    root = Path(root).absolute()
    if root.resolve() != root:
        raise ValueError("EXPLICIT_REAL_DELIVERY_ROOT_REQUIRED")
    selector = metadata(root, selector_name)
    client = metadata(root, selector["client_manifest"], selector["client_manifest_sha256"])
    original = verify(root, selector["client_manifest"])
    patch_name = safe_name(selector["server_manifest"])
    patch = metadata(root, patch_name, selector["server_manifest_sha256"])
    if (
        patch["frontend_source"] != client["frontend_source"]
        or selector["frontend_source"] != client["frontend_source"]
        or selector["runtime_source"] != patch["runtime_source"]
        or patch["compatible_apk_version_code"] != client["app_version_code"]
        or selector["apk_version_code"] != client["app_version_code"]
        or patch.get("api_contract") != client.get("api_contract")
        or not client.get("api_contract")
        or patch.get("api_contract_changed") is not False
    ):
        raise ValueError("SERVER_PATCH_CLIENT_CONTRACT_MISMATCH")
    patch_root = (root / patch_name).parent
    files = patch["files"]
    if type(files) is not dict or not 3 <= len(files) <= 64:
        raise ValueError("DELIVERY_FILE_BOUND")
    for name, expected in files.items():
        path = patch_root / safe_name(name)
        if path.resolve() != path or not path.is_file() or path.stat().st_size > 128 * 1024 * 1024:
            raise ValueError("DELIVERY_FILE_UNAVAILABLE")
        if path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
            raise ValueError("DELIVERY_FILE_INTEGRITY_MISMATCH")
    archives = [patch_root / n for n in files if n.endswith("-portable.tar.gz")]
    old_archives = [root / n for n in client["files"] if n.endswith("-portable.tar.gz")]
    if len(archives) != 1 or len(old_archives) != 1:
        raise ValueError("ONE_SERVER_PATCH_REQUIRED")
    actual, previous = runtime_metadata(archives[0]), runtime_metadata(old_archives[0])
    if actual["source_commit"] != patch["runtime_source"]:
        raise ValueError("CORE_SOURCE_MISMATCH")
    contracts = (
        "schema_version",
        "bundle_version",
        "supported_platform",
        "secret_binding_contract",
        "archive_ingress_contract",
        "bilibili_life_contract",
        "platform_runtime_contract",
        "private_context_contract",
    )
    if any(key not in actual or key not in previous or actual[key] != previous[key] for key in contracts):
        raise ValueError("SERVER_PATCH_RUNTIME_CONTRACT_MISMATCH")
    if not set(previous["features"]) <= set(actual["features"]):
        raise ValueError("SERVER_PATCH_FEATURE_REGRESSION")
    return {
        "state": "CURRENT_DELIVERY_CONSISTENCY_VERIFIED",
        "client_source": client["frontend_source"],
        "runtime_source": actual["source_commit"],
        "apk_web_files_equal": original["apk_web_files_equal"],
        "runtime_contracts_preserved": True,
        "production_activation": False,
        "semantic_compatibility_or_execution_qualification": "NOT_PROVEN_BY_METADATA",
    }


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
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--manifest")
    selection.add_argument("--current")
    args = parser.parse_args()
    print(
        json.dumps(
            verify_current(args.root, args.current) if args.current else verify(args.root, args.manifest), indent=2
        )
    )
