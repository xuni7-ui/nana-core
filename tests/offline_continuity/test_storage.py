import sqlite3
import pytest
from nana_core.clock import ManualClock, parse_utc
from nana_core.contracts import CoreError, Observation
from nana_core.storage import Store

pytestmark = pytest.mark.s1


def observation(**fields):
    return Observation(source_namespace="synthetic.reading", object_id="synthetic-event-1",
        raw_text="A fictional reader paused at a garden passage.", occurred_at="2026-10-01T08:30:00+08:00", **fields)


def test_identity_time_raw_and_channel_dedup(tmp_path):
    path = tmp_path / "nana.db"
    with Store(path, ManualClock()) as store:
        identity = store.identity
        eid = store.ingest(observation())
        for _ in range(100):
            assert store.ingest(observation(channel="second")) == eid
        assert len(store.all("memory_items")) == 1
        occurred = store.event(eid)["occurred_at_us"]
        raw = store.artifact(store.event(eid)["artifact_id"])
    with Store(path, ManualClock(1_999_000_000_000_000)) as store:
        assert store.identity == identity
        assert store.event(eid)["occurred_at_us"] == occurred == parse_utc("2026-10-01T00:30:00Z")
        assert store.artifact(store.event(eid)["artifact_id"]) == raw


def test_source_collision_not_silently_ignored(tmp_path):
    with Store(tmp_path / "nana.db") as store:
        original = observation()
        store.ingest(original)
        with pytest.raises(CoreError, match="SOURCE_KEY_COLLISION"):
            store.ingest(original.model_copy(update={"raw_text": "different"}))


def test_transaction_rolls_back_evidence_and_projection(tmp_path):
    with Store(tmp_path / "nana.db") as store:
        before = store.snapshot()
        with pytest.raises(RuntimeError):
            with store.transaction("test.rollback") as tx:
                tx.artifact(b"synthetic")
                tx.update("identities", store.identity["identity_id"], revision=2)
                raise RuntimeError("injected")
        assert store.snapshot() == before
        assert not store.all("artifacts")


def test_single_writer_and_corrupt_database_fail_closed(tmp_path):
    path = tmp_path / "nana.db"
    with Store(path):
        with pytest.raises(CoreError, match="RUNTIME_ALREADY_ACTIVE"):
            Store(path)
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"not a database")
    with pytest.raises(sqlite3.DatabaseError):
        Store(bad)
    assert bad.read_bytes() == b"not a database"


def test_append_only_and_pure_replay(tmp_path):
    with Store(tmp_path / "nana.db") as store:
        store.ingest(observation())
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            store.db.execute("UPDATE events SET kind='forged'")
        store.replay(tmp_path / "replay.db")
        with Store(tmp_path / "replay.db") as replay:
            original, reconstructed = store.snapshot(), replay.snapshot()
            for row in original["core_meta"]:
                if row["key"] == "recovery_quarantine":
                    row["value_json"] = "true"
            assert reconstructed == original
            assert replay.one("core_meta", "recovery_quarantine")["value_json"] == "true"
            assert replay.all("events") == store.all("events")
