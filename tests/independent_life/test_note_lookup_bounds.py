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


def test_literal_gram_accelerator_keeps_partial_legacy_long_and_erasure_paths(tmp_path):
    from nana_core.continuity.memory import NOTE_GRAM_COMPLETE, NOTE_GRAM_PREFIX
    home = tmp_path / 'home'; initialize(home, active=0)
    with LifeApplication(home, clock=VirtualClock()) as app:
        memory = MemoryService(app.runtime.store, app.runtime.authority)
        first = save(app, text='SYNTHETIC xxORCHIDsuffix and 星河约定', privacy='PROJECT', request_id='grams-first')['memory_id']
        other = save(app, text='SYNTHETIC unindexed prefixORCHIDlegacy', privacy='PROJECT', request_id='grams-legacy')['memory_id']
        db = app.runtime.store.db
        assert db.execute('SELECT 1 FROM memory_terms WHERE memory_id=? AND term=?', (first, NOTE_GRAM_COMPLETE)).fetchone()
        # Simulate an old writer's derived index only; source payload is intact.
        db.execute('DELETE FROM memory_terms WHERE memory_id=? AND substr(term,1,?)=?', (other, len(NOTE_GRAM_PREFIX), NOTE_GRAM_PREFIX))
        filters = dict(entity_ids=('project-user',), scopes=('project-work',), privacy_classes=('PROJECT',))
        assert [r['memory_id'] for r in memory.literal_notes(**filters, terms=('ORCHID',))] == [other, first]
        assert [r['memory_id'] for r in memory.literal_notes(**filters, terms=('河约',))] == [first]
        assert [r['memory_id'] for r in memory.literal_notes(**filters, terms=('星河约', 'ORCHID'))] == [other, first]
        assert memory.literal_notes(**{**filters, 'privacy_classes': ('PUBLIC',)}, terms=('ORCHID',)) == []
        # A payload over the indexing cap is still scanned, including its tail.
        from nana_core.continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
        ref='note:grams-long';text='SYNTHETIC ' + 'ordinary ' * 500 + 'TAILBEACON'
        eid=memory.capture(EvidenceInput(provenance=Provenance(domain='CONSENTED_INTERACTION',
            source_namespace='recorded.conversation.input', source_reference=ref, source_kind='USER_STATEMENT'),
            retention_consent_ref=ref, text=text, privacy_class='PROJECT', observed_time_us=app.runtime.clock.utc_now_us()))
        long_mid=memory.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.SEMANTIC,
            epistemic_kind='STATEMENT',source_evidence_id=eid,text=text,predicate_key='user-note.grams-long'))
        assert not db.execute('SELECT 1 FROM memory_terms WHERE memory_id=? AND term=?',(long_mid,NOTE_GRAM_COMPLETE)).fetchone()
        assert [r['memory_id'] for r in memory.literal_notes(**filters,terms=('TAILBEACON',))] == [long_mid]
        app.forget(first)
        assert not db.execute('SELECT 1 FROM memory_terms WHERE memory_id=?',(first,)).fetchone()
        assert [r['memory_id'] for r in memory.literal_notes(**filters,terms=('ORCHID',))] == [other]
        db.execute('DROP INDEX memory_terms_term_lookup')
        assert [r['memory_id'] for r in memory.literal_notes(**filters,terms=('ORCHID',))] == [other]
        db.execute('DROP INDEX memory_note_gram_coverage')
        assert [r['memory_id'] for r in memory.literal_notes(**filters,terms=('ORCHID',))] == [other]
        db.execute('CREATE INDEX memory_note_gram_coverage ON memories(scope)')
        with pytest.raises(CoreError,match='NOTE_RECALL_INDEX_DEFINITION_MISMATCH'):
            memory.literal_notes(**filters,terms=('ORCHID',))


def test_original_maintenance_slice_backfills_legacy_lookup_without_new_fact_or_model(tmp_path):
    from nana_core.continuity.memory import NOTE_GRAM_PREFIX, NOTE_GRAM_COMPLETE
    home=tmp_path/'home';initialize(home,active=0);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();db=app.runtime.store.db
        mid=save(app,text='SYNTHETIC legacy retained ORCHID detail',privacy='PROJECT',request_id='maintenance-grams')['memory_id']
        before=dict(app.runtime.store.one('memories',mid))
        db.execute('DELETE FROM memory_terms WHERE memory_id=? AND substr(term,1,?)=?',(mid,len(NOTE_GRAM_PREFIX),NOTE_GRAM_PREFIX))
        service=app.runtime.work.maintenance;service.interval=1_000_000;service.discover()
        for _ in range(16):
            due=db.execute("SELECT min(due_at_us) FROM jobs WHERE work_kind='SCAN' AND state='WAITING'").fetchone()[0]
            clock.advance(max(1,due-clock.utc_now_us()));app.runtime.lease.heartbeat();service.slice()
            if db.execute('SELECT 1 FROM memory_terms WHERE memory_id=? AND term=?',(mid,NOTE_GRAM_COMPLETE)).fetchone():break
        assert db.execute('SELECT 1 FROM memory_terms WHERE memory_id=? AND term=?',(mid,NOTE_GRAM_COMPLETE)).fetchone()
        assert dict(app.runtime.store.one('memories',mid))==before
        assert not app.runtime.store.all('cognitive_requests') and not app.runtime.store.all('actions')
        app.forget(mid)
        assert not db.execute('SELECT 1 FROM memory_terms WHERE memory_id=?',(mid,)).fetchone()
