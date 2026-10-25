"""Crash-safe payload erasure and restore tombstones, not mere query suppression.

The fsynced external journal contains opaque IDs only. It must survive a restore
and accompanies managed backups. It cannot defeat a privileged whole-disk clone
or erase copies outside this application's control. No claim of SSD forensics.
"""

import fcntl
import json
import os
import stat
from pathlib import Path
import sqlite3
import tempfile
from contextlib import contextmanager
from uuid import UUID

from ..contracts import CoreError
from ..storage import canonical, digest, uid


def _atomic(path, data):
    encoded = canonical(data)
    if len(encoded.encode()) > 16 * 1024 * 1024:
        raise CoreError("PRIVACY_JOURNAL_CAPACITY")
    fd, temporary = tempfile.mkstemp(prefix=".privacy-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as out:
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _json_object(pairs):
    body = {}
    for key, value in pairs:
        if key in body:
            raise ValueError("duplicate metadata key")
        body[key] = value
    return body


def _load(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd) as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 16 * 1024 * 1024:
                raise ValueError()
            raw = source.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise ValueError()
            return json.loads(raw, object_pairs_hook=_json_object)
    except (OSError, ValueError, TypeError):
        raise CoreError("PRIVACY_ANCHOR_INVALID") from None


class PrivacyJournal:
    def __init__(self, store, *, new_database):
        self.store = store
        self.sidecar = Path(str(store.path) + ".privacy.json")
        if self.sidecar.is_symlink():
            raise CoreError("PRIVACY_ANCHOR_INVALID")
        if self.sidecar.exists():
            link = _load(self.sidecar)
            if type(link) is not dict:
                raise CoreError("PRIVACY_ANCHOR_INVALID")
            if "anchor_path" in link:
                if (
                    set(link) != {"anchor_path"}
                    or type(link["anchor_path"]) is not str
                    or not Path(link["anchor_path"]).is_absolute()
                ):
                    raise CoreError("PRIVACY_ANCHOR_INVALID")
                self.path = Path(link["anchor_path"])
            else:
                self.path = self.sidecar
        elif new_database:
            self.path = self.sidecar
            _atomic(
                self.path,
                {
                    "schema_version": 1,
                    "identity_id": store.identity["identity_id"],
                    "intents": [],
                    "backups": [str(store.path.resolve())],
                },
            )
        else:
            raise CoreError("PRIVACY_ANCHOR_MISSING")
        self.applied = None
        self._checked_signature = None
        self._applying = False
        self.read()
        self.ensure_current()
        self.pending_backups = self.sanitize_backups()

    def read(self):
        if self.path.is_symlink() or not self.path.is_file():
            raise CoreError("PRIVACY_ANCHOR_UNAVAILABLE")
        try:
            body = _load(self.path)
            if (
                type(body) is not dict
                or set(body) != {"schema_version", "identity_id", "intents", "backups"}
                or type(body["schema_version"]) is not int
                or body["schema_version"] != 1
                or body["identity_id"] != self.store.identity["identity_id"]
                or type(body["intents"]) is not list
                or type(body["backups"]) is not list
            ):
                raise ValueError()
            if any(type(x) is not str or not Path(x).is_absolute() for x in body["backups"]):
                raise ValueError()
            for item in body["intents"]:
                if (
                    type(item) is not dict
                    or set(item) != {"intent_id", "memory_ids", "evidence_ids", "created_at_us"}
                    or type(item["memory_ids"]) is not list
                    or type(item["evidence_ids"]) is not list
                    or type(item["created_at_us"]) is not int
                    or item["created_at_us"] < 0
                ):
                    raise ValueError()
                for value in [item["intent_id"], *item["memory_ids"], *item["evidence_ids"]]:
                    if type(value) is not str or str(UUID(value)) != value:
                        raise ValueError()
            return body
        except (OSError, ValueError, TypeError, KeyError):
            raise CoreError("PRIVACY_ANCHOR_INVALID") from None

    @contextmanager
    def _locked(self):
        # Restored copies share one external deletion anchor. Serialize its
        # updates as well as each DB's existing single-writer lock.
        path = Path(str(self.path) + ".lock")
        if path.is_symlink():
            raise CoreError("PRIVACY_ANCHOR_INVALID")
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def ensure_current(self):
        if self._applying:
            return

        # Trusted writers replace the anchor atomically. Recheck filesystem
        # identity/metadata on EVERY call, but do not reopen/reparse unchanged
        # opaque metadata tens of thousands of times within one C slice.
        # This is a rebuildable validity cache, never deletion authority.
        def signature():
            try:
                info = self.path.lstat()
            except OSError:
                raise CoreError("PRIVACY_ANCHOR_UNAVAILABLE") from None
            if not stat.S_ISREG(info.st_mode):
                raise CoreError("PRIVACY_ANCHOR_UNAVAILABLE")
            return (
                info.st_dev,
                info.st_ino,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
                info.st_mode,
                info.st_uid,
                info.st_gid,
            )

        current = signature()
        if self.applied is not None and current == self._checked_signature:
            return
        for _ in range(3):
            body = self.read()
            after = signature()
            if after == current:
                break
            current = after
        else:
            raise CoreError("PRIVACY_ANCHOR_CHANGED_DURING_READ")
        fingerprint = digest(body["intents"])
        if fingerprint == self.applied:
            self._checked_signature = current
            return
        self._applying = True
        try:
            for intent in body["intents"]:
                self._purge(self.store.db, intent)
            result = self.store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if result[0] != 0:
                raise CoreError("PURGE_CHECKPOINT_PENDING")
            self.applied = fingerprint
            self._checked_signature = current
        finally:
            self._applying = False

    def _erase(self, memory_id):
        # Called only after MemoryService's controller-owned authority check.
        row = self.store.one("memories", memory_id)
        if not row:
            raise CoreError("MEMORY_UNAVAILABLE")
        intent = {
            "intent_id": uid(),
            "memory_ids": [memory_id],
            "evidence_ids": [row["source_evidence_id"]],
            "created_at_us": self.store.clock.utc_now_us(),
        }
        with self._locked():
            body = self.read()
            body["intents"].append(intent)
            _atomic(self.path, body)  # privacy intent durable BEFORE destructive work
        self.ensure_current()
        pending = self.sanitize_backups()
        return {
            "intent_id": intent["intent_id"],
            "state": "COMPLETE" if not pending else "PENDING_BACKUP_PURGE",
            "pending_backup_count": len(pending),
        }

    def register_copy(self, destination):
        destination = Path(destination).resolve()
        with self._locked():
            body = self.read()
            if str(destination) not in body["backups"]:
                body["backups"].append(str(destination))
                _atomic(self.path, body)
        _atomic(Path(str(destination) + ".privacy.json"), {"anchor_path": str(self.path.resolve())})

    def sanitize_backups(self):
        body = self.read()
        pending = []
        if not body["intents"]:
            return pending
        for name in body["backups"]:
            path = Path(name)
            if not path.exists():
                continue
            if path.resolve() == self.store.path.resolve():
                continue  # this restored Store was already purged before reads
            if path.is_symlink():
                pending.append(name)
                continue
            lock = open(str(path) + ".lock", "a+b")
            db = None
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                db = sqlite3.connect(path, isolation_level=None)
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA foreign_keys=ON")
                db.execute("PRAGMA secure_delete=ON")
                identity = db.execute("SELECT identity_id FROM identities").fetchone()
                if not identity or identity[0] != body["identity_id"]:
                    raise CoreError("BACKUP_IDENTITY_MISMATCH")
                for intent in body["intents"]:
                    self._purge(db, intent)
                if db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] != 0:
                    raise CoreError("PURGE_CHECKPOINT_PENDING")
            except (BlockingIOError, sqlite3.Error, CoreError):
                pending.append(name)
            finally:
                if db:
                    db.close()
                lock.close()
        return pending

    def _purge(self, db, intent):
        """Conservative source-object closure; never retain a partial private blob."""
        evidence = set(intent["evidence_ids"])
        memories = set(intent["memory_ids"])
        rows = [dict(r) for r in db.execute("SELECT * FROM memories")]
        dependencies = list(db.execute("SELECT * FROM memory_dependencies"))
        changed = True
        while changed:
            before = len(evidence), len(memories)
            for row in rows:
                if row["source_evidence_id"] in evidence or row["memory_id"] in memories:
                    memories.add(row["memory_id"])
                    evidence.add(row["source_evidence_id"])
            for edge in dependencies:
                parents = evidence if edge["parent_kind"] == "EVIDENCE" else memories
                if edge["parent_id"] in parents:
                    memories.add(edge["memory_id"])
            changed = before != (len(evidence), len(memories))
        artifacts, changes = set(), []
        db.execute("BEGIN IMMEDIATE")
        try:
            for row in rows:
                if row["memory_id"] in memories:
                    artifacts.add(row["payload_artifact_id"])
                    if row["lifecycle"] != "DELETED":
                        row.update(lifecycle="DELETED", assessment="WITHDRAWN", updated_at_us=intent["created_at_us"])
                        db.execute(
                            "UPDATE memories SET lifecycle='DELETED',assessment='WITHDRAWN',updated_at_us=? "
                            "WHERE memory_id=?",
                            (row["updated_at_us"], row["memory_id"]),
                        )
                        changes.append({"table": "memories", "row": row})
                    db.execute("DELETE FROM memory_terms WHERE memory_id=?", (row["memory_id"],))
            for raw in db.execute("SELECT * FROM continuity_evidence").fetchall():
                row = dict(raw)
                if row["evidence_id"] in evidence:
                    artifacts.add(row["payload_artifact_id"])
                    if row["state"] != "DELETED":
                        row["state"] = "DELETED"
                        db.execute(
                            "UPDATE continuity_evidence SET state='DELETED' WHERE evidence_id=?", (row["evidence_id"],)
                        )
                        changes.append({"table": "continuity_evidence", "row": row})
            # Other permanent cognitive records use the same payload/dependency discipline.
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "continuity_records" in tables:
                records = set()
                edges = list(db.execute("SELECT * FROM record_dependencies"))
                while True:
                    before = len(records)
                    for edge in edges:
                        if edge["parent_id"] in (memories if edge["parent_kind"] == "MEMORY" else records):
                            records.add(edge["record_id"])
                    if len(records) == before:
                        break
                for raw in db.execute("SELECT * FROM continuity_records").fetchall():
                    row = dict(raw)
                    if row["record_id"] in records:
                        artifacts.add(row["payload_artifact_id"])
                        if row["lifecycle"] != "DELETED":
                            row["lifecycle"] = "DELETED"
                            db.execute(
                                "UPDATE continuity_records SET lifecycle='DELETED' WHERE record_id=?",
                                (row["record_id"],),
                            )
                            changes.append({"table": "continuity_records", "row": row})
            for artifact in artifacts:
                db.execute(
                    "UPDATE artifacts SET payload=NULL,sha256='',completeness='UNAVAILABLE' WHERE artifact_id=?",
                    (artifact,),
                )
            if changes:
                now = self.store.clock.utc_now_us()
                db.execute(
                    "INSERT INTO events(event_id,kind,schema_version,identity_id,observed_at_us,recorded_at_us,data_json) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (
                        uid(),
                        "privacy.erased",
                        1,
                        self.store.identity["identity_id"],
                        now,
                        now,
                        canonical({"data": {"intent_id": intent["intent_id"]}, "changes": changes}),
                    ),
                )
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
