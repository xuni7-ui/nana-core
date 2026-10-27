"""Verify all bounded image parts and gzip/tar digests without extracting files."""

import hashlib, json, sys, zlib
from pathlib import Path

root = Path(sys.argv[1])
m = json.loads((root / "image.json").read_text())
compressed = hashlib.sha256()
raw = hashlib.sha256()
decoder = zlib.decompressobj(31)
total = 0
for item in m["parts"]:
    p = root / item["file"]
    if p.parent != root or p.is_symlink():
        raise ValueError("PART_PATH_DENIED")
    data = p.read_bytes()
    if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise ValueError("PART_DIGEST_MISMATCH")
    compressed.update(data)
    out = decoder.decompress(data)
    raw.update(out)
    total += len(out)
if not decoder.eof or decoder.unused_data:
    raise ValueError("GZIP_INCOMPLETE_OR_TRAILING")
if compressed.hexdigest() != m["gzip_sha256"] or raw.hexdigest() != m["tar_sha256"] or total != m["tar_bytes"]:
    raise ValueError("ARCHIVE_DIGEST_MISMATCH")
print(json.dumps({"verified": True, "image_id": m["image_id"], "gzip_sha256": m["gzip_sha256"]}))
