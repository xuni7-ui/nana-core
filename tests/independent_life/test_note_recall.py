"""Actual original-Store/HTTP plumbing; fixture hints are NOT model semantics."""

import json

import pytest

from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config, update_config
from nana_core.life.memory_notes import save
from nana_core.life.surfaces import SurfaceBinding
from nana_core.presence.authority import VirtualClock
from .conftest import initialize
from .test_dialogue import relay


def supplied_notes(request):
    return [
        json.loads(b["data_json"])
        for b in json.loads(request["context_json"])["blocks"]
        if b["kind"] == "MEMORY"
        and json.loads(b["data_json"])["epistemic_kind"] == "STATEMENT"
        and json.loads(b["data_json"])["memory_type"] == "SEMANTIC"
    ]


def render_from_supplied_sources(request):
    notes = supplied_notes(request)
    return "SYNTHETIC supplied user statement: " + notes[0]["text"] if notes else "SYNTHETIC no supplied note"


@pytest.mark.parametrize(
    "term,statement,correction",
    [
        ("ORION", "SYNTHETIC ORION delivery-window is Thursday.", "SYNTHETIC ORION delivery-window is Friday."),
        ("项目约定", "合成资料：项目约定在周四。", "合成资料：项目约定在周五。"),
    ],
)
def test_note_selected_after_restart_model_change_correction_and_withdrawal(tmp_path, term, statement, correction):
    home = tmp_path / "home"
    initialize(home, active=0)
    clock = VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        first = save(app, text=statement, privacy="PROJECT", request_id="note.first")["memory_id"]
        identity = app.runtime.identity_id
    for number, model in enumerate(("fixture-text-a", "fixture-text-b")):
        with (
            relay(
                home,
                "CHAT",
                renderer=render_from_supplied_sources,
                remote_model_id=model,
                recall_query_terms=(term, "UNRETAINED_QUERY_CANARY"),
            ) as (router, requests),
            LifeApplication(home, clock=clock, router=router) as app,
        ):
            app.pause()
            if number:
                current = save(app, text=correction, privacy="PROJECT", request_id="note.correction", target_id=first)[
                    "memory_id"
                ]
            else:
                current = first
            result = app.chat(
                "UNRETAINED_QUERY_CANARY what was our agreement?",
                privacy="PROJECT",
                message_id="question." + str(number),
            )
            assert app.runtime.identity_id == identity and len(requests) == 2
            # Actual received loopback body includes volatile wording/history;
            # measure that complete wire form, not just persisted descriptors.
            from nana_core.continuity.world_loop.cognition import CognitionRequest
            from nana_core.storage import canonical
            for received in requests:
                wire_request = CognitionRequest.model_validate_json(canonical(received))
                row = app.runtime.store.one("cognitive_requests", wire_request.request_id)
                transport = app.session.transport
                assert row["input_bytes"] == len(transport.request_body(wire_request))
                assert row["reserved_bytes"] == row["input_bytes"] + transport.response_bound(wire_request) + 1
                assert row["input_bytes"] + row["output_bytes"] <= row["reserved_bytes"]
            assert result["render_state"] == "UNVERIFIED_MODEL_WORDING"
            notes = supplied_notes(requests[-1])
            assert [n["memory_id"] for n in notes] == [current]
            assert notes[0]["text"] == (correction if number else statement)
            assert result["text"] == render_from_supplied_sources(requests[-1])
            assert not app.runtime.store.db.execute(
                "SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'UNRETAINED_QUERY_CANARY')>0"
            ).fetchone()
            assert app.session._volatile_recall == {}
            if number:
                app.forget(current)
                app.chat("What about that note now?", privacy="PROJECT", message_id="after-withdrawal")
                assert len(requests) == 4 and supplied_notes(requests[-1]) == []
                assert (
                    current not in requests[-1]["source_context_refs"]
                    and first not in requests[-1]["source_context_refs"]
                )
            assert not app.runtime.store.all("actions") and not app.runtime.store.all("lessons")


def test_project_question_cannot_retrieve_personal_note_even_on_private_capable_provider(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    cfg = load_config(home)
    binding = SurfaceBinding(
        binding_id="private.notes",
        platform="cloud.local",
        surface="chat.direct",
        adapter="shadow.local",
        permitted_privacy=("PUBLIC", "PROJECT", "PERSONAL"),
        allow_personal_retention=True,
        personal_retention_consent_ref="synthetic.private.note.consent",
    )
    update_config(
        home,
        cfg.model_copy(update={"revision": cfg.revision + 1, "surface_bindings": (binding,)}),
        expected_revision=cfg.revision,
    )
    with (
        relay(home, "CHAT", recall_query_terms=("SYNTHETIC_PRIVATE_NEEDLE",)) as (router, requests),
        LifeApplication(home, clock=VirtualClock(), router=router) as app,
    ):
        private = save(
            app,
            text="SYNTHETIC_PRIVATE_NEEDLE explicitly retained private statement",
            privacy="PERSONAL",
            request_id="private.note",
            surface_binding_id=binding.binding_id,
        )["memory_id"]
        app.pause()
        app.chat("Look up that note", privacy="PROJECT", message_id="public.question")
        assert len(requests) == 2
        assert all(
            private not in r["source_context_refs"] and "explicitly retained private statement" not in r["context_json"]
            for r in requests
        )
        app.chat("Look up that note privately", privacy="PERSONAL", message_id="private.question")
        assert len(requests) == 4 and private in requests[-1]["source_context_refs"]


def test_long_optional_notes_preserve_person_self_and_context_bound(tmp_path):
    home = tmp_path / "home"
    initialize(home, active=0)
    with (
        relay(home, "CHAT", recall_query_terms=("SYNTHETIC_LONG_NOTE",)) as (router, requests),
        LifeApplication(home, clock=VirtualClock(), router=router) as app,
    ):
        for n in range(4):
            save(
                app,
                text="SYNTHETIC_LONG_NOTE " + str(n) + " 资料" * 600,
                privacy="PROJECT",
                request_id="long." + str(n),
            )
        app.pause()
        answer = app.chat("What do you know?", privacy="PROJECT", message_id="long-question")
        assert len(requests) == 2 and answer["render_state"] == "UNVERIFIED_MODEL_WORDING"
        context = json.loads(requests[-1]["context_json"])
        assert any(b["kind"] == "PERSON_SELF" for b in context["blocks"])
        assert context["manifest"]["input_tokens"] <= context["manifest"]["input_limit"]
        assert len(supplied_notes(requests[-1])) < 4


def test_public_chat_can_continue_after_project_work_without_leaking_project_fact(tmp_path):
    from .conftest import advance

    home = tmp_path / "home"
    initialize(home)
    with (
        relay(home, "CHAT") as (router, requests),
        LifeApplication(home, clock=VirtualClock(), router=router, bootstrap_grant=True) as app,
    ):
        advance(app, 100)
        app.pause()
        facts = app._fact_sources()
        assert facts and app._fact_sources("PUBLIC") == ()
        answer = app.chat("A public hello", privacy="PUBLIC", message_id="public-after-work")
        assert len(requests) == 2 and answer["render_state"] == "UNVERIFIED_MODEL_WORDING"
        assert requests[-1]["role_input"]["dialogue"]["effect_status"] == "NONE"
        assert not set(facts) & set(requests[-1]["source_context_refs"])


@pytest.mark.parametrize("source_domain",["SYNTHETIC_ONLY","RECORDED_PUBLIC"])
def test_non_note_rows_do_not_consume_literal_recall_limit(tmp_path,source_domain):
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
    home=tmp_path/'home';initialize(home,active=0)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause()
        valid=save(app,text='SYNTHETIC ORCHID actual saved note',privacy='PROJECT',request_id='valid-recall')['memory_id']
        memory=MemoryService(app.runtime.store)
        for n in range(4):
            eid=memory.capture(EvidenceInput(provenance=Provenance(domain=source_domain,source_namespace='synthetic.other-source' if source_domain=='SYNTHETIC_ONLY' else 'recorded.conversation.input',source_reference='note:other-'+str(n),source_kind='USER_STATEMENT'),
                text='SYNTHETIC ORCHID other-source statement',privacy_class='PUBLIC',observed_time_us=app.clock.utc_now_us()))
            memory.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.SEMANTIC,
                epistemic_kind='STATEMENT',source_evidence_id=eid,text='SYNTHETIC ORCHID other-source statement',predicate_key=f'user-note.other-{n}'))
        found=memory.literal_notes(entity_ids=('project-user',),scopes=('project-work',),privacy_classes=('PUBLIC','PROJECT'),terms=('ORCHID',))
        assert [row['memory_id'] for row in found]==[valid]
