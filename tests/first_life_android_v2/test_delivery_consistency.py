"""Resigned metadata cannot disguise a stale Core or APK/Web disagreement."""

import io
import json
import tarfile
import zipfile

import pytest

from tools.nana_next_experience.verify_delivery import verify, sha256


def archive(path, files):
    with tarfile.open(path, "w:gz") as tar:
        for name, value in files.items():
            raw = value.encode()
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))


def fixture(root, *, core_source="current", apk_body="same"):
    archive(
        root / "core-portable.tar.gz",
        {"nana-first-life-portable-v1/runtime.json": json.dumps({"source_commit": core_source})},
    )
    archive(root / "space-web.tar.gz", {"nana-space-web/index.html": "same"})
    with zipfile.ZipFile(root / "space.apk", "w") as apk:
        apk.writestr("assets/public/index.html", apk_body)
    files = {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in root.iterdir()}
    (root / "MANIFEST.json").write_text(
        json.dumps({"core_source": "current", "frontend_source": "current", "files": files})
    )


def test_actual_components_match_and_mutation_is_rejected(tmp_path):
    fixture(tmp_path)
    assert verify(tmp_path, "MANIFEST.json")["apk_web_files_equal"] == 1
    (tmp_path / "space.apk").write_bytes(b"changed")
    with pytest.raises(ValueError, match="INTEGRITY_MISMATCH"):
        verify(tmp_path, "MANIFEST.json")


@pytest.mark.parametrize(
    "options,reason",
    [
        ({"core_source": "old"}, "CORE_SOURCE_MISMATCH"),
        ({"apk_body": "old"}, "APK_WEB_MISMATCH"),
    ],
)
def test_fresh_hash_manifest_cannot_cover_mismatched_components(tmp_path, options, reason):
    fixture(tmp_path, **options)
    with pytest.raises(ValueError, match=reason):
        verify(tmp_path, "MANIFEST.json")


def test_manifest_cannot_read_outside_download_directory(tmp_path):
    with pytest.raises(ValueError, match="UNSAFE_DELIVERY_PATH"):
        verify(tmp_path, "../private.json")


def current_fixture(root):
    fixture(root)
    contract = {
        "schema_version": 13,
        "bundle_version": 1,
        "supported_platform": "synthetic-linux",
        "secret_binding_contract": 2,
        "archive_ingress_contract": 1,
        "bilibili_life_contract": 1,
        "platform_runtime_contract": 1,
        "private_context_contract": 1,
        "features": ["HOST_VAULT"],
    }
    archive(
        root / "core-portable.tar.gz",
        {"nana-first-life-portable-v1/runtime.json": json.dumps({**contract, "source_commit": "current"})},
    )
    client = json.loads((root / "MANIFEST.json").read_text())
    client.update(app_version_code=408, api_contract="nana-space-live/v2")
    client["files"]["core-portable.tar.gz"] = {
        "bytes": (root / "core-portable.tar.gz").stat().st_size,
        "sha256": sha256(root / "core-portable.tar.gz"),
    }
    (root / "MANIFEST.json").write_text(json.dumps(client))
    patch = root / "patch"
    patch.mkdir()
    archive(
        patch / "new-portable.tar.gz",
        {"nana-first-life-portable-v1/runtime.json": json.dumps({**contract, "source_commit": "new"})},
    )
    (patch / "HANDOFF.md").write_text("SYNTHETIC metadata, not a deployment receipt")
    (patch / "check.py").write_text("# never executed\n")
    manifest = {
        "runtime_source": "new",
        "frontend_source": "current",
        "compatible_apk_version_code": 408,
        "api_contract": "nana-space-live/v2",
        "api_contract_changed": False,
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in patch.iterdir()},
    }
    (patch / "MANIFEST.json").write_text(json.dumps(manifest))
    selector = {
        "client_manifest": "MANIFEST.json",
        "client_manifest_sha256": sha256(root / "MANIFEST.json"),
        "server_manifest": "patch/MANIFEST.json",
        "server_manifest_sha256": sha256(patch / "MANIFEST.json"),
        "frontend_source": "current",
        "runtime_source": "new",
        "apk_version_code": 408,
    }
    (root / "CURRENT.json").write_text(json.dumps(selector))
    return manifest, selector, contract


def test_current_selector_verifies_client_and_explicit_server_patch(tmp_path):
    from tools.nana_next_experience.verify_delivery import verify_current

    current_fixture(tmp_path)
    result = verify_current(tmp_path, "CURRENT.json")
    assert result["runtime_source"] == "new" and result["client_source"] == "current"
    assert result["production_activation"] is False
    assert result["semantic_compatibility_or_execution_qualification"] == "NOT_PROVEN_BY_METADATA"


@pytest.mark.parametrize(
    "defect",
    ["stale-core", "missing-vault", "schema-change", "wrong-client", "wrong-api", "changed-file", "pointer-hash"],
)
def test_current_selector_rejects_resigned_or_mismatched_server_patch(tmp_path, defect):
    from tools.nana_next_experience.verify_delivery import verify_current

    manifest, selector, contract = current_fixture(tmp_path)
    patch = tmp_path / "patch"
    if defect in {"stale-core", "missing-vault", "schema-change"}:
        runtime = {**contract, "source_commit": "old" if defect == "stale-core" else "new"}
        if defect == "missing-vault":
            runtime["features"] = []
        if defect == "schema-change":
            runtime["schema_version"] = 12
        archive(patch / "new-portable.tar.gz", {"nana-first-life-portable-v1/runtime.json": json.dumps(runtime)})
        manifest["files"]["new-portable.tar.gz"] = {
            "bytes": (patch / "new-portable.tar.gz").stat().st_size,
            "sha256": sha256(patch / "new-portable.tar.gz"),
        }
    elif defect == "wrong-client":
        manifest["compatible_apk_version_code"] = 407
    elif defect == "wrong-api":
        manifest["api_contract_changed"] = True
    elif defect == "changed-file":
        (patch / "check.py").write_text("changed")
    (patch / "MANIFEST.json").write_text(json.dumps(manifest))
    if defect != "pointer-hash":
        selector["server_manifest_sha256"] = sha256(patch / "MANIFEST.json")
    else:
        selector["server_manifest_sha256"] = "0" * 64
    (tmp_path / "CURRENT.json").write_text(json.dumps(selector))
    with pytest.raises(ValueError):
        verify_current(tmp_path, "CURRENT.json")
