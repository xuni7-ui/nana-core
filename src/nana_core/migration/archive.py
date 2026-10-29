"""Full frozen-source preservation and a rebuildable legacy search index.

This host-local archive is neither a Subject Store nor authoritative memory.
No old strategy, identity, Grant, action success or model belief is adopted.
Real private inputs require an explicit operator authorization; tests use an
owned synthetic marker. Original source paths are never modified.
"""

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path

from ..contracts import CoreError
from ..continuity.privacy import _json_object
from .source_safety import SECRET_NAMES, safe_payload as _safe_payload
from ..life.live_api.contracts import Binding
from ..storage import digest

SECRET = re.compile(rb"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")
MAX_TOTAL = 1024 ** 3
MAX_RECORDS = 500000


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while raw := stream.read(1024 * 1024):
            result.update(raw)
    return result.hexdigest()


def private_json(path, value):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        output.flush()
        os.fsync(output.fileno())


def safe_file(root, relative):
    if type(relative) is not str:
        raise CoreError("LEGACY_EXPLICIT_RELATIVE_FILE_REQUIRED")
    name = Path(relative)
    if name.is_absolute() or ".." in name.parts or not name.parts:
        raise CoreError("LEGACY_EXPLICIT_RELATIVE_FILE_REQUIRED")
    path = root / name
    if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
        raise CoreError("LEGACY_REGULAR_SOURCE_REQUIRED")
    if any(part.lower() in {"secrets", "credentials", ".git"} for part in name.parts):
        raise CoreError("LEGACY_SECRET_SOURCE_DENIED")
    if path.suffix.lower() in {".key", ".pem", ".env"} or any(word in path.name.lower() for word in ("cookie", "password", "token", "secret")):
        raise CoreError("LEGACY_SECRET_SOURCE_DENIED")
    if path.stat().st_size > MAX_TOTAL:
        raise CoreError("LEGACY_SOURCE_BYTE_BOUND")
    return path


def source_rows(path):
    """Preserve every byte; index known text fields without executing old code."""
    with path.open("rb") as stream:
        sqlite = stream.read(16) == b"SQLite format 3\x00"
    if sqlite:
        # Supplied sources must already be frozen; never ignore a live WAL.
        with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise CoreError("LEGACY_SQLITE_CORRUPT")
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            for (table,) in tables:
                quoted = '"' + table.replace('"', '""') + '"'
                columns = [r[1] for r in db.execute("PRAGMA table_info(" + quoted + ")")]
                if any(c.lower() in SECRET_NAMES for c in columns):
                    raise CoreError("SECRET_FIELD_IN_EXPORT")
                cursor = db.execute("SELECT * FROM " + quoted)
                for i, values in enumerate(cursor):
                    row = {name: value for name, value in zip(columns, values) if not isinstance(value, bytes)}
                    _safe_payload(row)
                    yield table, str(row.get("memory_id", row.get("id", row.get("message_id", i)))), row
        return
    if path.stat().st_size > 16 * 1024 * 1024:
        # Large line-oriented archives are streamed, not loaded as one array.
        with path.open("rb") as stream:
            i = 0
            while raw := stream.readline(262145):
                if len(raw) > 262144:
                    raise CoreError("LEGACY_LINE_BOUND")
                try:
                    line = raw.decode("utf-8")
                except UnicodeError:
                    return
                try:
                    row = json.loads(line, object_pairs_hook=_json_object)
                except ValueError:
                    row = {"text": line.rstrip("\n")}
                _safe_payload(row)
                yield "line", str(i), row if type(row) is dict else {"content": str(row)}
                i += 1
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError:
        return  # Unrecognized binary is fully preserved, never fabricated as text.
    try:
        value = json.loads(text, object_pairs_hook=_json_object)
    except ValueError:
        value = [{"text": line} for line in text.splitlines()]
    _safe_payload(value)
    rows = value if type(value) is list else [value]
    for i, row in enumerate(rows):
        if type(row) is not dict:
            row = {"content": str(row)}
        yield "json", str(row.get("memory_id", row.get("id", i))), row


def freeze(source_root, selected_files, destination, binding, *, private_authorized=False, synthetic=False):
    root = Path(source_root).absolute()
    if root.resolve() != root:
        raise CoreError("LEGACY_ROOT_SYMLINK_DENIED")
    binding = Binding.model_validate(binding)
    if type(synthetic) is not bool:
        raise CoreError("LEGACY_SYNTHETIC_LABEL_INVALID")
    if synthetic:
        marker = root / ".nana-synthetic-legacy.json"
        if not marker.is_file() or marker.is_symlink() or json.loads(marker.read_text()) != {"synthetic_only": True}:
            raise CoreError("LEGACY_SYNTHETIC_MARKER_REQUIRED")
    elif private_authorized is not True:
        raise CoreError("LEGACY_PRIVATE_READ_NOT_AUTHORIZED")
    if not isinstance(selected_files, (list, tuple)):
        raise CoreError("LEGACY_EXPLICIT_FILE_SELECTION_REQUIRED")
    names = tuple(selected_files)
    if any(type(name) is not str for name in names):
        raise CoreError("LEGACY_EXPLICIT_FILE_SELECTION_REQUIRED")
    if not 1 <= len(names) <= 512 or len(names) != len(set(names)):
        raise CoreError("LEGACY_EXPLICIT_FILE_SELECTION_REQUIRED")
    paths = [(name, safe_file(root, name)) for name in names]
    if sum(p.stat().st_size for _, p in paths) > MAX_TOTAL:
        raise CoreError("LEGACY_ARCHIVE_BYTE_BOUND")
    for _, path in paths:
        if Path(str(path) + "-wal").exists() or Path(str(path) + "-journal").exists():
            raise CoreError("LEGACY_CONSISTENT_FROZEN_SNAPSHOT_REQUIRED")
        # Reject structured credential fields before creating a durable copy.
        for _ in source_rows(path):
            pass
    target = Path(destination).absolute()
    if target.resolve() != target or target.exists() or target == root or root in target.parents:
        raise CoreError("LEGACY_FRESH_SEPARATE_ARCHIVE_REQUIRED")
    target.mkdir(mode=0o700, parents=True)
    incomplete = target / "CAPTURE_INCOMPLETE"
    private_json(incomplete, {"do_not_import": True})
    rawroot = target / "sources"
    rawroot.mkdir(mode=0o700)
    index = target / "source-index.sqlite"
    catalog, total_records, total_bytes = {}, 0, 0
    with sqlite3.connect(index) as db:
        index.chmod(0o600)
        db.execute("PRAGMA synchronous=FULL")
        db.execute("CREATE VIRTUAL TABLE source_text USING fts5(source_id UNINDEXED,legacy_kind UNINDEXED,legacy_key UNINDEXED,content,tokenize='unicode61')")
        for name, source in paths:
            source_id = hashlib.sha256(name.encode()).hexdigest()
            copy = rawroot / source_id
            before = source.stat()
            copied_hash = hashlib.sha256()
            tail = b""
            fd = os.open(copy, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "wb") as output, os.fdopen(source_fd, "rb") as incoming:
                opened = os.fstat(incoming.fileno())
                if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                    raise CoreError("LEGACY_SOURCE_CHANGED_DURING_CAPTURE")
                while data := incoming.read(1024 * 1024):
                    total_bytes += len(data)
                    if total_bytes > MAX_TOTAL:
                        raise CoreError("LEGACY_ARCHIVE_BYTE_BOUND")
                    if SECRET.search(tail + data):
                        raise CoreError("POSSIBLE_CREDENTIAL_IN_LEGACY_SOURCE")
                    output.write(data)
                    copied_hash.update(data)
                    tail = data[-256:]
                output.flush()
                os.fsync(output.fileno())
            after = source.stat()
            if ((before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns)
                    or sha(source) != copied_hash.hexdigest()):
                raise CoreError("LEGACY_SOURCE_CHANGED_DURING_CAPTURE")
            count = 0
            for kind, key, row in source_rows(copy):
                total_records += 1
                if total_records > MAX_RECORDS:
                    raise CoreError("LEGACY_INDEX_RECORD_BOUND")
                content = "\n".join(str(row[k]) for k in ("content", "text", "summary", "name", "title") if k in row)
                if len(content.encode()) > 65536:
                    content = content.encode()[:65536].decode(errors="ignore")
                db.execute("INSERT INTO source_text VALUES(?,?,?,?)", (source_id, kind, key, content))
                count += 1
            catalog[source_id] = {"source_name": name, "snapshot_path": "sources/" + source_id,
                                  "sha256": copied_hash.hexdigest(), "bytes": copy.stat().st_size,
                                  "indexed_records": count, "coverage": "FULL_FROZEN_FILE_BYTES",
                                  "semantics": "LEGACY_SOURCE_CLAIMS_UNASSESSED_NOT_CORE_EXPERIENCE"}
            copy.chmod(0o400)
        db.commit()
    result = {"contract": "nana-legacy-source-archive/v1", "subject_id": binding.subject_id,
              "lineage_binding": binding.lineage_binding, "files": catalog,
              "records_indexed": total_records, "index_sha256": sha(index),
              "storage_class": "REBUILDABLE_SOURCE_INDEX_NOT_AUTHORITATIVE_SUBJECT_STORE",
              "synthetic": synthetic, "private_read_authorized": private_authorized,
              "core_identity_created": False, "core_memory_imported": False,
              "grants_or_actions_imported": False, "source_files_modified": False}
    private_json(target / "manifest.json", result)
    (target / "manifest.json").chmod(0o400)
    index.chmod(0o400)
    (target / "withdrawn").mkdir(mode=0o700)
    incomplete.unlink()
    directory = os.open(target, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return {**result, "manifest_sha256": sha(target / "manifest.json")}


def _checked_archive(archive, *, private_authorized=False, expected_manifest_sha256=None):
    root = Path(archive).absolute()
    if root.resolve() != root or not root.is_dir() or (root / "CAPTURE_INCOMPLETE").exists():
        raise CoreError("LEGACY_ARCHIVE_INCOMPLETE_OR_UNSAFE")
    path = safe_file(root, "manifest.json")
    manifest_hash = sha(path)
    if expected_manifest_sha256 is not None and manifest_hash != expected_manifest_sha256:
        raise CoreError("LEGACY_MANIFEST_HASH_MISMATCH")
    try:
        manifest = json.loads(path.read_text(), object_pairs_hook=_json_object)
        if (manifest["contract"] != "nana-legacy-source-archive/v1"
                or type(manifest["synthetic"]) is not bool or type(manifest["files"]) is not dict
                or not 1 <= len(manifest["files"]) <= 512):
            raise ValueError()
        Binding(subject_id=manifest["subject_id"], lineage_binding=manifest["lineage_binding"])
    except (KeyError, TypeError, ValueError):
        raise CoreError("LEGACY_MANIFEST_INVALID") from None
    if not manifest["synthetic"] and private_authorized is not True:
        raise CoreError("LEGACY_PRIVATE_READ_NOT_AUTHORIZED")
    index = safe_file(root, "source-index.sqlite")
    if sha(index) != manifest["index_sha256"]:
        raise CoreError("LEGACY_REBUILDABLE_INDEX_CORRUPT")
    retired = []
    for source, item in manifest["files"].items():
        if (not re.fullmatch(r"[a-f0-9]{64}", source)
                or item.get("snapshot_path") != "sources/" + source
                or type(item.get("indexed_records")) is not int or item["indexed_records"] < 0):
            raise CoreError("LEGACY_MANIFEST_INVALID")
        snapshot = safe_file(root, item["snapshot_path"])
        if snapshot.stat().st_size != item["bytes"] or sha(snapshot) != item["sha256"]:
            raise CoreError("LEGACY_SOURCE_HASH_MISMATCH")
        marker = root / "withdrawn" / source
        if marker.exists() or marker.is_symlink():
            marker = safe_file(root, "withdrawn/" + source)
            try:
                value = json.loads(marker.read_text(), object_pairs_hook=_json_object)
            except (ValueError, UnicodeError):
                raise CoreError("LEGACY_WITHDRAWAL_INVALID") from None
            if value != {"manifest_sha256": manifest_hash, "source_id": source, "state": "WITHDRAWN"}:
                raise CoreError("LEGACY_WITHDRAWAL_INVALID")
            retired.append(source)
    if sum(item["indexed_records"] for item in manifest["files"].values()) != manifest["records_indexed"]:
        raise CoreError("LEGACY_MANIFEST_INVALID")
    return root, manifest, manifest_hash, tuple(sorted(retired))


def verify(archive, *, private_authorized=False, expected_manifest_sha256=None, binding=None):
    """Check every frozen file, even files with no searchable text.

    A caller retaining the capture's returned manifest hash can pin provenance
    across hosts. Local hashes detect corruption, not a malicious host owner.
    """
    _, manifest, manifest_hash, retired = _checked_archive(archive,
        private_authorized=private_authorized, expected_manifest_sha256=expected_manifest_sha256)
    if binding is not None:
        _check_binding(manifest, binding)
    return {"manifest_sha256": manifest_hash, "subject_id": manifest["subject_id"],
            "lineage_binding": manifest["lineage_binding"], "files_verified": len(manifest["files"]),
            "records_indexed": manifest["records_indexed"], "withdrawn_source_ids": list(retired),
            "core_memory_imported": False, "execution_authority": False}


def search(archive, query, *, private_authorized=False, limit=20, expected_manifest_sha256=None, binding=None):
    root, manifest, manifest_hash, retired = _checked_archive(archive,
        private_authorized=private_authorized, expected_manifest_sha256=expected_manifest_sha256)
    if binding is not None:
        _check_binding(manifest, binding)
    if type(query) is not str or not 1 <= len(query) <= 128 or type(limit) is not int or not 1 <= limit <= 64:
        raise CoreError("LEGACY_SEARCH_BOUND")
    index = root / "source-index.sqlite"
    # Quote FTS syntax: a user query cannot alter columns or request all rows.
    expression = '"' + query.replace('"', '""') + '"'
    with sqlite3.connect(index.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        placeholders = ",".join("?" for _ in retired)
        active = " AND source_id NOT IN (" + placeholders + ")" if retired else ""
        rows = db.execute("SELECT source_id,legacy_kind,legacy_key,content FROM source_text WHERE source_text MATCH ?" + active + " ORDER BY rowid LIMIT ?", (expression, *retired, limit)).fetchall()
    output = []
    for source, kind, key, content in rows:
        item = manifest["files"][source]
        output.append({"source_id": source, "source_sha256": item["sha256"], "legacy_kind": kind,
                       "legacy_key": key, "text": content, "assessment": "UNASSESSED_LEGACY_SOURCE_CLAIM",
                       "core_experience": False, "execution_authority": False})
    return {"items": output, "source_subject_id": manifest["subject_id"],
            "manifest_sha256": manifest_hash, "withdrawn_source_ids": list(retired), "core_memory_imported": False}


def withdraw_source(archive, source_id, binding, *, private_authorized=False, expected_manifest_sha256=None):
    """Retire search/import support; frozen bytes remain for authorized archival review.

    This is a source withdrawal, not a physical data-erasure API. It does not
    claim to erase previously exported files or already imported Core records.
    """
    root, manifest, manifest_hash, retired = _checked_archive(archive,
        private_authorized=private_authorized, expected_manifest_sha256=expected_manifest_sha256)
    _check_binding(manifest, binding)
    if source_id not in manifest["files"]:
        raise CoreError("LEGACY_SOURCE_NOT_BOUND")
    if source_id not in retired:
        directory = root / "withdrawn"
        if directory.resolve() != directory or not directory.is_dir():
            raise CoreError("LEGACY_WITHDRAWAL_INVALID")
        marker = directory / source_id
        private_json(marker, {"manifest_sha256": manifest_hash, "source_id": source_id, "state": "WITHDRAWN"})
        marker.chmod(0o400)
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    return {"source_id": source_id, "state": "WITHDRAWN", "frozen_source_bytes_retained": True,
            "core_memory_imported": False, "execution_authority": False}


def _check_binding(manifest, binding):
    binding = Binding.model_validate(binding)
    if (binding.subject_id, binding.lineage_binding) != (manifest["subject_id"], manifest["lineage_binding"]):
        raise CoreError("LEGACY_SUBJECT_LINEAGE_MISMATCH")


def batch_plan(archive, binding, *, batch_size=100, private_authorized=False, expected_manifest_sha256=None):
    """Deterministic, bounded source-row ranges for review, never import authority.

    The existing LegacyRecord/IrisRecord contracts remain synthetic_only=True.
    Real archives can be captured and searched after authorization, but their
    plan explicitly remains blocked by original RealMemoryIngress.
    """
    from ..continuity.contracts import RealMemoryIngress
    _, manifest, manifest_hash, retired = _checked_archive(archive,
        private_authorized=private_authorized, expected_manifest_sha256=expected_manifest_sha256)
    _check_binding(manifest, binding)
    if type(batch_size) is not int or not 1 <= batch_size <= 100:
        raise CoreError("LEGACY_IMPORT_BATCH_BOUND")
    batches, segments, pending, total = [], [], 0, 0
    for source, item in sorted(manifest["files"].items()):
        if source in retired:
            continue
        offset, count = 0, item["indexed_records"]
        while offset < count:
            take = min(count - offset, batch_size - pending)
            segments.append({"source_id": source, "source_sha256": item["sha256"],
                             "first_record": offset, "record_count": take})
            offset += take
            pending += take
            total += take
            if pending == batch_size:
                batches.append({"batch_id": digest([manifest_hash, segments]), "record_count": pending, "segments": segments})
                segments, pending = [], 0
    if segments:
        batches.append({"batch_id": digest([manifest_hash, segments]), "record_count": pending, "segments": segments})
    return {"contract": "nana-legacy-archive-batch-plan/v1", "manifest_sha256": manifest_hash,
            "subject_id": manifest["subject_id"], "lineage_binding": manifest["lineage_binding"],
            "batch_size": batch_size, "records_planned": total, "batches": batches,
            "withdrawn_source_ids": list(retired), "synthetic_only": manifest["synthetic"],
            "state": "SYNTHETIC_REVIEW_PLAN" if manifest["synthetic"] else "BLOCKED_REAL_MEMORY_IMPORT_DISABLED",
            "real_memory_ingress_enabled": RealMemoryIngress.enabled,
            "core_memory_imported": False, "execution_authority": False}


def validate_batch_plan(archive, plan, binding, *, private_authorized=False, expected_manifest_sha256=None):
    if type(plan) is not dict:
        raise CoreError("LEGACY_BATCH_PLAN_INVALID")
    if expected_manifest_sha256 is not None and plan.get("manifest_sha256") != expected_manifest_sha256:
        raise CoreError("LEGACY_MANIFEST_HASH_MISMATCH")
    current = batch_plan(archive, binding, batch_size=plan.get("batch_size"),
        private_authorized=private_authorized, expected_manifest_sha256=plan.get("manifest_sha256"))
    if current != plan:
        raise CoreError("LEGACY_BATCH_PLAN_STALE_OR_CHANGED")
    return current
