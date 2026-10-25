"""Release/static-file boundary tests; no network or Subject creation."""

import hashlib
import importlib.util
import io
import os
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def extractor():
    spec = importlib.util.spec_from_file_location("web_extractor", ROOT / "deployment/first-life-v2/docker/extract_web.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive(path, name, link=False):
    with tarfile.open(path, "w:gz") as tar:
        index = tarfile.TarInfo("nana-space-web/index.html")
        index.size = 8
        tar.addfile(index, io.BytesIO(b"WEB_TEST"))
        member = tarfile.TarInfo(name)
        if link:
            member.type = tarfile.SYMTYPE
            member.linkname = "/outside"
        tar.addfile(member, None if link else io.BytesIO(b""))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_live_web_is_hash_bound_and_readable_under_private_umask(tmp_path):
    path = tmp_path / "web.tgz"
    sha = archive(path, "nana-space-web/assets/live.js")
    old = os.umask(0o077)
    try:
        result = extractor().extract(path, sha, tmp_path / "web")
    finally:
        os.umask(old)
    assert result["subject_created"] is False
    index = tmp_path / "web" / sha / "index.html"
    assert index.read_bytes() == b"WEB_TEST"
    assert index.stat().st_mode & 0o777 == 0o644
    assert index.parent.stat().st_mode & 0o777 == 0o755
    with pytest.raises(ValueError, match="WEB_DIGEST_MISMATCH"):
        extractor().extract(path, "0" * 64, tmp_path / "wrong")


@pytest.mark.parametrize("name,link", [("nana-space-web/../outside.js", False),
    ("nana-space-web/private.key", False), ("nana-space-web/assets/link.js", True)])
def test_no_private_paths_escape_or_links_in_static_web(tmp_path, name, link):
    path = tmp_path / "web.tgz"
    sha = archive(path, name, link)
    with pytest.raises(ValueError, match="WEB_ARCHIVE_MEMBER_DENIED"):
        extractor().extract(path, sha, tmp_path / "target")
    assert not (tmp_path / "target").exists()
