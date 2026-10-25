"""Only fresh synthetic archives; no actual cloud runtime/private material."""

import hashlib
import importlib.util
import io
import tarfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location(
        "runtime_extractor", ROOT / "deployment/first-life-v2/docker/extract_runtime.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def archive(path, entries):
    with tarfile.open(path, "w:gz") as tar:
        for name, body, link in entries:
            item = tarfile.TarInfo(name)
            if link is not None:
                item.type = tarfile.SYMTYPE
                item.linkname = link
                tar.addfile(item)
            else:
                item.size = len(body)
                tar.addfile(item, io.BytesIO(body))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_supplied_runtime_is_hash_bound_and_links_stay_inside_prefix(tmp_path):
    path = tmp_path / "runtime.tgz"
    sha = archive(
        path,
        [("runtime/bin/python3.12", b"SYNTHETIC_NOT_EXECUTABLE", None), ("runtime/bin/python3", b"", "python3.12")],
    )
    target = tmp_path / "target"
    target.mkdir()
    result = module().extract(path, sha, target)
    assert result["subject_created"] is False
    assert (target / "runtime/bin/python3").read_bytes() == b"SYNTHETIC_NOT_EXECUTABLE"
    with pytest.raises(ValueError, match="SUPPLIED_RUNTIME_DIGEST_REQUIRED"):
        module().extract(path, "a" * 64, tmp_path / "other")


@pytest.mark.parametrize(
    "name,link",
    [
        ("runtime/../outside", None),
        ("/tmp/absolute", None),
        ("data/private.db", None),
        ("runtime/config/life.json", None),
        ("runtime/bin/python3", "../../outside"),
    ],
)
def test_runtime_archive_rejects_escape_private_config_and_wrong_roots(tmp_path, name, link):
    path = tmp_path / "runtime.tgz"
    sha = archive(path, [(name, b"SYNTHETIC", link)])
    target = tmp_path / "target"
    target.mkdir()
    with pytest.raises(ValueError):
        module().extract(path, sha, target)
    assert not (tmp_path / "outside").exists()
