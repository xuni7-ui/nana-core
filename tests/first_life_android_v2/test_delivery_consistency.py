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
