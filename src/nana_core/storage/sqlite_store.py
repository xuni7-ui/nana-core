"""Single writer, short transactions, append-only evidence and replayable projections."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid
from ..clock import Clock, parse_utc
from ..contracts import CoreError, Observation


def uid() -> str:
    return str(uuid.uuid4())


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    payload = value if isinstance(value, bytes) else canonical(value).encode()
    return hashlib.sha256(payload).hexdigest()


KEYS = {
    "core_meta": "key", "identities": "identity_id", "memory_items": "memory_id",
    "goals": "goal_id", "plans": "plan_id", "decisions": "decision_id", "grants": "grant_id",
    "budgets": "dimension", "actions": "action_id", "attempts": "attempt_id",
    "budget_holds": "hold_id", "strategies": "strategy_id", "jobs": "job_id",
}


class Transaction:
    def __init__(self, store):
        self.store = store
        self.event_id = uid()
        self.changes = []

    def put(self, table: str, row: dict) -> None:
        self.store._put(table, row)
        self.changes.append({"table": table, "row": dict(row)})

    def update(self, table: str, key, **fields) -> dict:
        row = self.store.one(table, key)
        if row is None:
            raise CoreError("NOT_FOUND")
        row.update(fields)
        self.put(table, row)
        return row

    def artifact(self, payload: bytes) -> str:
        if len(payload) > 8 * 1024 * 1024:
            raise CoreError("PAYLOAD_TOO_LARGE")
        artifact_id = uid()
        self.store.db.execute("INSERT INTO artifacts VALUES(?,?,?,?,?)", (
            artifact_id, digest(payload), payload, "COMPLETE", self.event_id))
        return artifact_id


class Store:
    def __init__(self, path, clock: Clock | None = None, *, schema_target=1):
        from .development_schema import keys_for
        self.schema_target = schema_target
        self.keys = {**KEYS, **keys_for(schema_target)}
        self.path = Path(path)
        self.clock = clock or Clock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = open(str(self.path) + ".lock", "a+b")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._lock.close()
            raise CoreError("RUNTIME_ALREADY_ACTIVE") from exc
        try:
            self.db = sqlite3.connect(self.path, isolation_level=None)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.execute("PRAGMA busy_timeout=5000")
            if sqlite3.sqlite_version_info < (3, 51, 3):
                raise CoreError("SQLITE_VERSION_UNSUPPORTED")
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version == 0 and tables:
                raise CoreError("UNRECOGNIZED_DATABASE")
            if version == 0:
                self.db.executescript(Path(__file__).with_name("schema_v1.sql").read_text())
            elif version > schema_target:
                raise CoreError("SCHEMA_VERSION_UNSUPPORTED")
            if schema_target > 1:
                from .development_schema import install
                install(self.db, version or 1, schema_target)
            if self.db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise CoreError("STORAGE_CORRUPT")
            if self.db.execute("PRAGMA foreign_key_check").fetchone():
                raise CoreError("BROKEN_FOREIGN_KEYS")
            if not self.all("identities"):
                if self.all("events"):
                    raise CoreError("IDENTITY_MISSING")
                with self.transaction("identity.created") as tx:
                    tx.put("identities", {"identity_id": uid(), "revision": 1,
                        "body_json": canonical({"name": "Nana", "charter": [
                            "retain independent judgement", "evidence before success", "learning cannot expand permissions"],
                            "self_preferences": [], "expression_defaults": {"style": "warm and precise"}}),
                        "created_event_id": tx.event_id})
                    tx.put("core_meta", {"key": "recovery_quarantine", "value_json": "false"})
        except BaseException:
            if hasattr(self, "db"):
                self.db.close()
            self._lock.close()
            raise

    def close(self):
        self.db.close()
        self._lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @property
    def identity(self):
        return self.all("identities")[0]

    def one(self, table, key):
        # Historical read-only host views deliberately borrow these read methods
        # without constructing a Store (no init/checkpoint/migration writes).
        keys = getattr(self, "keys", KEYS)
        if table not in keys:
            raise ValueError(table)
        row = self.db.execute(f"SELECT * FROM {table} WHERE {keys[table]}=?", (key,)).fetchone()
        return dict(row) if row else None

    def all(self, table):
        if table not in {*getattr(self, "keys", KEYS), "events", "artifacts"}:
            raise ValueError(table)
        return [dict(r) for r in self.db.execute(f"SELECT * FROM {table} ORDER BY rowid")]

    def event(self, event_id):
        r = self.db.execute("SELECT * FROM events WHERE event_id=?", (event_id,)).fetchone()
        if not r:
            raise CoreError("EVIDENCE_MISSING")
        return dict(r)

    def artifact(self, artifact_id):
        row = self.db.execute("SELECT * FROM artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
        if not row or row["payload"] is None:
            raise CoreError("EVIDENCE_UNAVAILABLE")
        if digest(row["payload"]) != row["sha256"]:
            raise CoreError("EVIDENCE_CORRUPT")
        return row["payload"]

    def _put(self, table, row):
        if table not in self.keys:
            raise ValueError(table)
        allowed = {r["name"] for r in self.db.execute(f"PRAGMA table_info({table})")}
        if set(row) != allowed:
            raise ValueError(f"invalid projection row for {table}")
        columns = list(row)
        key = self.keys[table]
        assignments = ",".join(f"{c}=excluded.{c}" for c in columns if c != key)
        self.db.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) "
                        f"ON CONFLICT({key}) DO UPDATE SET {assignments}", list(row.values()))

    @contextmanager
    def transaction(self, kind, data=None, source_namespace=None, source_key=None,
                    occurred_at_us=None, artifact_id=None):
        self.db.execute("BEGIN IMMEDIATE")
        tx = Transaction(self)
        try:
            yield tx
            now = self.clock.utc_now_us()
            identities = self.all("identities")
            body = {"data": data or {}, "changes": tx.changes}
            self.db.execute("INSERT INTO events(event_id,kind,schema_version,identity_id,source_namespace,source_key,"
                            "occurred_at_us,observed_at_us,recorded_at_us,data_json,artifact_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                            (tx.event_id, kind, 1, identities[0]["identity_id"] if identities else None,
                             source_namespace, source_key, occurred_at_us, now, now, canonical(body),
                             artifact_id or getattr(tx, "payload_id", None)))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def ingest(self, observation: Observation):
        if self.schema_target != 1:
            raise CoreError("USE_CONTINUITY_EVIDENCE_INGRESS")
        key = canonical([observation.kind, observation.object_id, observation.revision])
        previous = self.db.execute("SELECT * FROM events WHERE source_namespace=? AND source_key=?",
                                   (observation.source_namespace, key)).fetchone()
        raw = observation.raw_text.encode()
        stable = observation.model_dump(exclude={"channel"})
        if previous:
            if json.loads(previous["data_json"])["data"]["observation"] != stable:
                raise CoreError("SOURCE_KEY_COLLISION")
            return previous["event_id"]
        with self.transaction("observation.received", {"observation": stable,
                "channel": observation.channel, "time_quality": "SOURCE" if parse_utc(observation.occurred_at) is not None else "UNKNOWN"},
                observation.source_namespace, key, parse_utc(observation.occurred_at)) as tx:
            tx.payload_id = tx.artifact(raw)
            tx.put("memory_items", {"memory_id": uid(), "kind": "CLAIM", "status": "ACTIVE",
                "body_json": canonical({"epistemic_kind": "OBSERVATION", "assessment": "UNASSESSED",
                    "source_refs": [{"event_id": tx.event_id, "artifact_id": tx.payload_id, "coverage": "FULL"}],
                    "content": observation.raw_text}), "created_event_id": tx.event_id})
        return tx.event_id

    def replay(self, destination):
        """Rebuild in a separate offline database; no model/capability methods exist here."""
        if Path(destination).exists():
            raise CoreError("DESTINATION_EXISTS")
        target = sqlite3.connect(destination, isolation_level=None)
        try:
            target.executescript(Path(__file__).with_name("schema_v1.sql").read_text())
            if self.schema_target > 1:
                from .development_schema import install
                install(target, 1, self.schema_target)
            target.execute("PRAGMA foreign_keys=ON")
            target.execute("BEGIN IMMEDIATE")
            for row in self.all("events"):
                columns = list(row)
                target.execute(f"INSERT INTO events({','.join(columns)}) VALUES({','.join('?' for _ in columns)})", list(row.values()))
            for row in self.all("artifacts"):
                target.execute("INSERT INTO artifacts VALUES(?,?,?,?,?)", list(row.values()))
            for event in self.all("events"):
                for change in json.loads(event["data_json"])["changes"]:
                    table, row = change["table"], change["row"]
                    if table not in self.keys:
                        raise CoreError("INVALID_REPLAY_TABLE")
                    columns = list(row)
                    assignments = ",".join(f"{c}=excluded.{c}" for c in columns if c != self.keys[table])
                    target.execute(f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)}) "
                        f"ON CONFLICT({self.keys[table]}) DO UPDATE SET {assignments}", list(row.values()))
            # Rebuilt state is reviewable state, not permission to replay external effects.
            # This is local restoration metadata, intentionally separate from domain replay.
            target.execute("UPDATE core_meta SET value_json='true' WHERE key='recovery_quarantine'")
            target.execute("COMMIT")
        except BaseException:
            if target.in_transaction:
                target.execute("ROLLBACK")
            raise
        finally:
            target.close()

    def backup(self, destination):
        if Path(destination).exists():
            raise CoreError("DESTINATION_EXISTS")
        target = sqlite3.connect(destination)
        try:
            self.db.backup(target)
            target.execute("UPDATE core_meta SET value_json='true' WHERE key='recovery_quarantine'")
            target.commit()
        finally:
            target.close()

    def snapshot(self):
        return {table: self.all(table) for table in self.keys}
