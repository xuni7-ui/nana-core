"""Literal retrieval does not substitute recent records or interrupt writes."""

from types import SimpleNamespace

import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.life.application import LifeApplication
from nana_core.life.memory_notes import save
from nana_core.presence.authority import VirtualClock
from .conftest import initialize


def test_old_matching_note_survives_candidate_bound_and_timeout_leaves_store_usable(tmp_path, monkeypatch):
    home = tmp_path / "home"
    initialize(home, active=0)
    with LifeApplication(home, clock=VirtualClock()) as app:
        wanted = save(app, text="SYNTHETIC ancient-needle 合成重要约定", privacy="PROJECT", request_id="old.needle")[
            "memory_id"
        ]
        for n in range(260):
            save(
                app, text="SYNTHETIC unrelated retained note " + str(n), privacy="PROJECT", request_id="noise." + str(n)
            )
        memory = MemoryService(app.runtime.store)
        query = {
            "entity_ids": ("project-user",),
            "scopes": ("project-work",),
            "privacy_classes": ("PUBLIC", "PROJECT"),
            "terms": ("ancient-needle",),
        }
        assert [m["memory_id"] for m in memory.literal_notes(**query)] == [wanted]
        assert memory.literal_notes(**{**query, "entity_ids": ("other-person",)}) == []
        assert memory.literal_notes(**{**query, "privacy_classes": ("PUBLIC",)}) == []
        import nana_core.continuity.memory as module

        ticks = iter((0.0, 1000.0))
        with monkeypatch.context() as patch:
            patch.setattr(module, "time", SimpleNamespace(monotonic=lambda: next(ticks, 1000.0)))
            with pytest.raises(CoreError, match="NOTE_RECALL_TIME_BOUND"):
                memory.literal_notes(**query, timeout_ms=1)
        assert app.runtime.store.db.execute("SELECT 1").fetchone()[0] == 1
        assert [m["memory_id"] for m in memory.literal_notes(**query)] == [wanted]
        with app.runtime.store.transaction("synthetic.note-query-safe-point"):
            with pytest.raises(CoreError, match="NOTE_RECALL_SAFE_POINT_REQUIRED"):
                memory.literal_notes(**query)
        assert memory.read(wanted)["assessment"] == "CURRENT"
        db = app.runtime.store.db
        from nana_core.continuity.store import REBUILDABLE_LOOKUP_INDEXES

        ddl = REBUILDABLE_LOOKUP_INDEXES["memory_user_note_lookup"]
        assert db.execute("SELECT sql FROM sqlite_master WHERE name='memory_user_note_lookup'").fetchone()[0] == ddl
        db.execute("DROP INDEX memory_user_note_lookup")
        assert [m["memory_id"] for m in memory.literal_notes(**query)] == [wanted]
        db.execute("CREATE INDEX memory_user_note_lookup ON memories(scope)")
        with pytest.raises(CoreError, match="NOTE_RECALL_INDEX_DEFINITION_MISMATCH"):
            memory.literal_notes(**query)
        db.execute("DROP INDEX memory_user_note_lookup")
        db.execute(ddl)
        assert [m["memory_id"] for m in memory.literal_notes(**query)] == [wanted]


def test_invalid_query_is_rejected_before_reading_memory(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    with LifeApplication(home, clock=VirtualClock()) as app:
        memory = MemoryService(app.runtime.store)
        for terms in ((), ("x",), ("a" * 65,), ("term",) * 9):
            with pytest.raises(CoreError, match="INVALID_NOTE_RECALL_QUERY"):
                memory.literal_notes(
                    entity_ids=("project-user",), scopes=("project-work",), privacy_classes=("PROJECT",), terms=terms
                )
