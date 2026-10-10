"""A separate durable external world, with actual commits and read-back verification."""
import json
from pathlib import Path
import sqlite3
from .contracts import CAPABILITIES, VERIFY_CAPABILITY, CoreError, Invocation, Receipt, Verification
from .storage import canonical, digest, uid

class FakeWorld:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        if self.db.execute("SELECT name FROM sqlite_master WHERE name='identities'").fetchone():
            self.db.close()
            raise CoreError("EXTERNAL_WORLD_MUST_BE_SEPARATE")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS sources(source_id TEXT PRIMARY KEY, text TEXT NOT NULL, pages_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cards(resource TEXT PRIMARY KEY, content_json TEXT NOT NULL, operation_key TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS operations(operation_key TEXT PRIMARY KEY, capability TEXT NOT NULL, resource TEXT NOT NULL,
          args_hash TEXT NOT NULL, result_json TEXT NOT NULL, external_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS calls(seq INTEGER PRIMARY KEY AUTOINCREMENT, operation_key TEXT NOT NULL,
          capability TEXT NOT NULL, resource TEXT NOT NULL, kind TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS controls(key TEXT PRIMARY KEY, value INTEGER NOT NULL);
        """)

    def close(self):
        self.db.close()

    def seed_source(self, source_id, paragraphs):
        """Operator/test setup only; never exposed as a model capability."""
        text = "\n".join(p["text"] for p in paragraphs)
        self.db.execute("INSERT INTO sources VALUES(?,?,?)", (source_id, text, canonical(paragraphs)))

    def control(self, key, value):
        self.db.execute("INSERT INTO controls VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def _controlled(self, key):
        r = self.db.execute("SELECT value FROM controls WHERE key=?", (key,)).fetchone()
        return bool(r and r[0])

    def execute(self, invocation: Invocation) -> Receipt:
        if invocation.capability not in CAPABILITIES or invocation.args_hash != digest(invocation.args):
            raise CoreError("INVALID_INVOCATION")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("INSERT INTO calls(operation_key,capability,resource,kind) VALUES(?,?,?,'EXECUTE')",
                (invocation.idempotency_key, invocation.capability, invocation.resource))
            existing = self.db.execute("SELECT * FROM operations WHERE operation_key=?", (invocation.idempotency_key,)).fetchone()
            if existing:
                if (existing["capability"], existing["resource"], existing["args_hash"]) != (
                        invocation.capability, invocation.resource, invocation.args_hash):
                    raise CoreError("IDEMPOTENCY_COLLISION")
                result = Receipt(external_id=existing["external_id"], result=json.loads(existing["result_json"]))
            else:
                source = self.db.execute("SELECT * FROM sources WHERE source_id=?", (invocation.args["source_id"],)).fetchone()
                if not source:
                    raise CoreError("SOURCE_UNAVAILABLE")
                if invocation.capability == "reading.source.read":
                    body = {"source_id": source["source_id"], "text": source["text"],
                            "source_digest": digest(source["text"].encode())}
                elif invocation.capability == "reading.source.locate":
                    pages = json.loads(source["pages_json"])
                    body = {"source_id": source["source_id"], "locator": pages[0]["locator"],
                            "source_digest": digest(source["text"].encode())}
                else:
                    if invocation.args["source_digest"] != digest(source["text"].encode()):
                        raise CoreError("STALE_SOURCE")
                    body = {"resource": invocation.resource, **invocation.args}
                    self.db.execute("INSERT INTO cards VALUES(?,?,?)", (
                        invocation.resource, canonical(body), invocation.idempotency_key))
                external_id = uid()
                self.db.execute("INSERT INTO operations VALUES(?,?,?,?,?,?)", (
                    invocation.idempotency_key, invocation.capability, invocation.resource,
                    invocation.args_hash, canonical(body), external_id))
                result = Receipt(external_id=external_id, result=body)
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        if self._controlled("lose_receipt"):
            raise TimeoutError("synthetic transport lost response after external commit")
        return result

    def verify(self, invocation: Invocation) -> Verification:
        self.db.execute("INSERT INTO calls(operation_key,capability,resource,kind) VALUES(?,?,?,'VERIFY')",
                        (invocation.idempotency_key, VERIFY_CAPABILITY, invocation.resource))
        if self._controlled("verify_unavailable"):
            raise TimeoutError("synthetic verifier unavailable")
        operation = self.db.execute("SELECT * FROM operations WHERE operation_key=?", (invocation.idempotency_key,)).fetchone()
        if not operation:
            # The offline runtime owns an exclusive OS lock and executes in-process.
            # After recovery, no prior executor is alive; this query covers the entire world.
            return Verification(verdict="FINAL_NO_EFFECT", evidence={"operation_key": invocation.idempotency_key,
                "complete_operation_lookup": True, "external_world": "offline", "result": None})
        matches = (operation["capability"], operation["resource"], operation["args_hash"]) == (
            invocation.capability, invocation.resource, invocation.args_hash)
        result = json.loads(operation["result_json"])
        if invocation.capability == "reading.card.create":
            card = self.db.execute("SELECT * FROM cards WHERE resource=?", (invocation.resource,)).fetchone()
            expected = {"resource": invocation.resource, **invocation.args}
            matches = bool(matches and card and card["operation_key"] == invocation.idempotency_key
                           and json.loads(card["content_json"]) == expected)
        return Verification(verdict="MATCH" if matches else "EFFECT_MISMATCH", evidence={
            "external_world": "offline", "operation_key": invocation.idempotency_key,
            "external_id": operation["external_id"], "args_hash": operation["args_hash"],
            "resource": operation["resource"], "result": result,
            "independent_readback": True})

    def counts(self):
        return {"effects": self.db.execute("SELECT count(*) FROM cards").fetchone()[0],
            "execute_calls": self.db.execute("SELECT count(*) FROM calls WHERE kind='EXECUTE'").fetchone()[0],
            "locate_calls": self.db.execute("SELECT count(*) FROM calls WHERE kind='EXECUTE' AND capability='reading.source.locate'").fetchone()[0],
            "verify_calls": self.db.execute("SELECT count(*) FROM calls WHERE kind='VERIFY'").fetchone()[0]}
