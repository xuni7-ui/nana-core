"""Original real Store/G/runtime, synthetic retained notes; no live model claim."""

import json
import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.records import RecordService
from nana_core.continuity.retrieval_growth import (
    qualified_method,
    DOMAIN,
    case_for,
)
from nana_core.continuity.subject.experience_need import project_need
from nana_core.life.application import LifeApplication
from nana_core.life.memory_notes import save
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from .conftest import initialize
from .test_dialogue import relay
from .test_note_recall import supplied_notes, render_from_supplied_sources


def notes(app, words=("ＯＲＩＯＮ", "ＡＴＬＡＳ", "ＬＹＲＡ"), prefix="first"):
    return [
        save(
            app, text="SYNTHETIC " + word + " window is Thursday.", privacy="PROJECT", request_id=prefix + "." + str(i)
        )["memory_id"]
        for i, word in enumerate(words)
    ]


def advance(app, steps=32):
    for _ in range(steps):
        app.runtime.clock.source.advance(SECOND)
        app.runtime.step()


def selected(app):
    r = app.runtime
    return qualified_method(r.store, r.authority, r.config.entity_id, "project-work", r.config.privacy_classes)


def test_autonomous_maintenance_gap_practice_restart_real_later_lookup_and_withdrawal(tmp_path, record_property):
    home = tmp_path / "home"
    initialize(home, active=0)
    clock = VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        mids = notes(app)
        identity = app.runtime.identity_id
        evaluator = app.runtime.work.note_retrieval_growth.evaluator
        snapshot = evaluator.snapshot("project-work")
        assert evaluator.lookup("IDENTITY", ("ORION",), snapshot) == []
        # Only the existing due maintenance safe point offers the opportunity.
        app.runtime.work.maintenance.interval = SECOND
        app.runtime.work.maintenance.discover()
        assert app.runtime.work.maintenance_slice() is None
        clock.advance(SECOND)
        activity = app.runtime.work.maintenance_slice()
        assert activity["retrieval_growth"]["note_retrieval"] == "OFFERED_TO_C"
        assert not app.runtime.store.all("lessons")
        # Original C, not the adapter, starts G. It has no user learn command.
        app.runtime.step()
        jobs = app.runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchall()
        assert len(jobs) == 1
        assert not app.runtime.store.all("cognitive_requests")
    with LifeApplication(home, clock=clock) as app:
        assert app.runtime.identity_id == identity
        advance(app)
        assert selected(app)[1] == "UNICODE_WORDS"
        job = app.runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone()
        body = RecordService(app.runtime.store).read(job["record_id"])["payload"]
        assert job["state"] == "DONE"
        assert body["results"]["BASELINE"]["passed"] == 0
        assert body["results"]["EVALUATE"]["all_passed"] and body["results"]["TRANSFER"]["all_passed"]
        assert body["practice_competition"]["selection_scope"] == "PRACTICE_ONLY_NOT_QUALIFICATION"
        # Actual new saved source; NOT any training/evaluation/transfer note.
        later = notes(app, ("ＡＬＴＡＩＲ",), prefix="later")[0]
    with (
        relay(
            home,
            "CHAT",
            renderer=render_from_supplied_sources,
            remote_model_id="fixture-resource-b",
            recall_query_terms=("ALTAIR",),
        ) as (router, requests),
        LifeApplication(home, clock=clock, router=router) as app,
    ):
        app.pause()
        reply = app.chat("SYNTHETIC what was the later agreement?", privacy="PROJECT", message_id="unseen.later")
        assert app.runtime.identity_id == identity
        assert [n["memory_id"] for n in supplied_notes(requests[-1])] == [later]
        assert "ＡＬＴＡＩＲ" in reply["text"] and len(requests) == 2
        lesson_ref = selected(app)[0]
        # Source-bound G lesson is part of the context support, not a new truth.
        blocks = json.loads(requests[-1]["context_json"])["blocks"]
        assert any(lesson_ref in b["source_record_ids"] for b in blocks if b["kind"] == "MEMORY")
        app.forget(mids[0])
        assert selected(app) is None
        app.chat("SYNTHETIC same question after withdrawal?", privacy="PROJECT", message_id="after.withdrawal")
        assert supplied_notes(requests[-1]) == []
    record_property("scope", "Actual DEV Store/G/HTTP fixture; real provider/human/long life NOT_RUN")


def test_counterexample_suspends_original_lesson_then_later_study_can_choose_different_method(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    clock = VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        notes(app)
        growth = app.runtime.work.note_retrieval_growth
        growth.slice("project-work")
        advance(app)
        assert selected(app)[1] == "UNICODE_WORDS"
        old = app.runtime.store.db.execute("SELECT * FROM lessons WHERE task_class=?", (DOMAIN,)).fetchone()
        notes(app, ("ＡＬＰＨＡＢＥＴ", "ＢＥＴＡＭＡＸ", "ＧＡＭＭＡＲＡＹ"), prefix="changed")
        result = growth.slice("project-work")
        assert app.runtime.store.one("lessons", old["lesson_id"])["state"] == "SUSPENDED"
        assert result["note_retrieval"] == "OFFERED_TO_C"
        assert selected(app) is None
        advance(app)
        assert selected(app)[1] == "JOIN"
        assert app.runtime.store.one("lessons", old["lesson_id"])["state"] == "SUSPENDED"
        before = len(app.runtime.store.all("jobs"))
        assert growth.slice("project-work") is None
        assert len(app.runtime.store.all("jobs")) == before
        assert not app.runtime.store.all("actions") and not app.runtime.store.all("cognitive_requests")


def test_source_change_and_scope_bound_are_unknown_not_false_training_answers(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    with LifeApplication(home, clock=VirtualClock()) as app:
        notes(app)
        growth = app.runtime.work.note_retrieval_growth
        snapshot = growth.evaluator.snapshot("project-work")
        case = case_for(snapshot, ("ORION",), "heldout")
        notes(app, ("NEW-NOTE",), prefix="changed")
        with pytest.raises(CoreError, match="NOTE_STRATEGY_SOURCE_CHANGED"):
            growth.evaluator.evaluate("JOIN", (case,))
        for i in range(16):
            notes(app, (f"EXTRA{i}",), prefix="extra" + str(i))
        assert growth.slice("project-work")["reason"] == "NOTE_STRATEGY_SCOPE_BOUND"
        assert not app.runtime.store.all("lessons")
        assert not app.runtime.store.all("experiences")


def test_pause_and_personal_notes_do_not_create_a_study(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    with LifeApplication(home, clock=VirtualClock()) as app:
        notes(app)
        app.pause()
        assert app.runtime.work.note_retrieval_growth.slice("project-work") is None
        assert not app.runtime.store.all("experiences")


def test_restart_before_c_judgment_recovers_proposal_without_minting_lesson(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    clock = VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        notes(app)
        app.runtime.work.note_retrieval_growth.slice("project-work")
        assert not app.runtime.store.all("lessons")
        assert not app.runtime.store.db.execute("SELECT 1 FROM jobs WHERE work_kind='LEARNING'").fetchone()
        identity = app.runtime.identity_id
    with LifeApplication(home, clock=clock) as app:
        assert app.runtime.identity_id == identity
        assert not app.runtime.store.all("lessons")
        advance(app)
        assert selected(app)[1] == "UNICODE_WORDS"


def test_later_verified_reuse_settles_original_s3_need_and_counterexample_reopens_it(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    clock = VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        notes(app)
        growth = app.runtime.work.note_retrieval_growth
        growth.slice("project-work")
        advance(app)
        assert (
            project_need(app.runtime.store, DOMAIN, scope="project-work", privacy_classes=("PROJECT",)).state == "OPEN"
        )
        notes(app, ("ＡＬＰＨＡＢＥＴ", "ＢＥＴＡＭＡＸ", "ＧＡＭＭＡＲＡＹ"), prefix="counter")
        growth.slice("project-work")
        advance(app)
        assert selected(app)[1] == "JOIN"
        clock.advance(SECOND)
        notes(app, ("ＡＮＤＲＯＭＥＤＡ",), prefix="independent-later")
        growth.slice("project-work")
        assert (
            project_need(app.runtime.store, DOMAIN, scope="project-work", privacy_classes=("PROJECT",)).state
            == "SETTLED"
        )
        assessments = app.runtime.store.all("strategy_assessments")
        assert [a["verdict"] for a in assessments] == ["COUNTEREXAMPLE", "SUCCESS"]
        from nana_core.continuity.subject.contracts import SubjectInput

        cue = app.runtime.store.db.execute(
            "SELECT memory_id FROM memories WHERE predicate_key LIKE 'concern.note-retrieval.%' ORDER BY rowid DESC LIMIT 1"
        ).fetchone()[0]
        cycle = app.runtime.subject.run(
            SubjectInput(
                domain="SOURCED_LIFE",
                source_key="local.settled-retrieval",
                kind="WAKE",
                origin="SELF_WAKE",
                entity_id="project-user",
                scope="project-work",
                privacy_class="PROJECT",
                source_memory_ids=(cue,),
                task_class=DOMAIN,
                observed_at_us=clock.utc_now_us(),
            )
        )
        assert cycle.experience_need.state == "SETTLED" and cycle.intention.behavior == "WATCH"

        app.forget(RecordService(app.runtime.store).support(selected(app)[0])[0])
        assert selected(app) is None


def test_evaluator_oracle_and_entity_binding_are_not_provider_self_scores(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    with LifeApplication(home, clock=VirtualClock()) as app:
        notes(app)
        growth = app.runtime.work.note_retrieval_growth
        snapshot = growth.evaluator.snapshot("project-work")
        case = case_for(snapshot, ("ORION",), "correct")
        false_case = case.model_copy(update={"expected": []})
        with pytest.raises(CoreError, match="NOTE_STRATEGY_ORACLE_MISMATCH"):
            growth.evaluator.evaluate("JOIN", (false_case,))
        growth.slice("project-work")
        advance(app)
        assert selected(app)
        assert (
            qualified_method(app.runtime.store, app.runtime.authority, "another-person", "project-work", ("PROJECT",))
            is None
        )


def test_unknown_practice_is_parked_without_adoption_or_automatic_retry(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    with LifeApplication(home, clock=VirtualClock()) as app:
        notes(app)
        growth = app.runtime.work.note_retrieval_growth
        growth.slice("project-work")
        app.runtime.step()
        original = growth.evaluator.practice_evaluate

        def unavailable(*_):
            raise CoreError("NOTE_RECALL_TIME_BOUND")

        growth.evaluator.practice_evaluate = unavailable
        advance(app, 8)
        job = app.runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone()
        assert job["state"] == "UNKNOWN" and job["cursor"] == 2
        assert selected(app) is None
        growth.evaluator.practice_evaluate = original
        advance(app, 8)
        assert app.runtime.store.one("jobs", job["job_id"])["state"] == "UNKNOWN"
        assert not app.runtime.store.all("lessons")


def test_explicit_personal_notes_never_enter_project_self_study(tmp_path):
    from nana_core.life.config import load_config, update_config
    from nana_core.life.surfaces import SurfaceBinding

    home = tmp_path / "home"
    initialize(home, active=0)
    config = load_config(home)
    binding = SurfaceBinding(
        binding_id="private.notes",
        platform="cloud.local",
        surface="chat.direct",
        adapter="shadow.local",
        permitted_privacy=("PUBLIC", "PROJECT", "PERSONAL"),
        allow_personal_retention=True,
        personal_retention_consent_ref="synthetic-fixture-only",
    )
    update_config(
        home,
        config.model_copy(update={"surface_bindings": (binding,), "revision": config.revision + 1}),
        expected_revision=config.revision,
    )
    with LifeApplication(home, clock=VirtualClock()) as app:
        for i, word in enumerate(("ＯＲＩＯＮ", "ＡＴＬＡＳ", "ＬＹＲＡ")):
            save(
                app,
                text="SYNTHETIC PRIVATE " + word,
                privacy="PERSONAL",
                request_id="private." + str(i),
                surface_binding_id=binding.binding_id,
            )
        growth = app.runtime.work.note_retrieval_growth
        assert growth.evaluator.snapshot("project-work")["notes"] == []
        assert growth.slice("project-work") is None
        assert not app.runtime.store.all("experiences")


def test_partial_offer_recovery_does_not_duplicate_experience_or_self_wake(tmp_path, monkeypatch):
    home = tmp_path / "home"
    initialize(home, active=0)
    with LifeApplication(home, clock=VirtualClock()) as app:
        notes(app)
        growth = app.runtime.work.note_retrieval_growth
        submit = app.runtime.submit

        def lost_receipt(event):
            submit(event)
            raise RuntimeError("SYNTHETIC lost local offer receipt")

        monkeypatch.setattr(app.runtime, "submit", lost_receipt)
        with pytest.raises(RuntimeError, match="lost local offer"):
            growth.slice("project-work")
        count = len(app.runtime.store.all("experiences"))
        queued = len(app.runtime.store.all("runtime_queue"))
        app.runtime.clock.source.advance(SECOND)
        monkeypatch.setattr(app.runtime, "submit", submit)
        growth.slice("project-work")
        assert len(app.runtime.store.all("experiences")) == count
        assert len(app.runtime.store.all("runtime_queue")) == queued
        advance(app)
        assert selected(app)[1] == "UNICODE_WORDS"
