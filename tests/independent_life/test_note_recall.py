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
        ("归途", "合成资料：归途见面约在周四。", "合成资料：归途见面约在周五。"),
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


@pytest.fixture
def literal_store(tmp_path):
    from nana_core.actions import OperatorAuthority
    from nana_core.clock import ManualClock
    from nana_core.continuity import ContinuityStore,IdentityService
    from nana_core.continuity.memory import MemoryService
    authority=OperatorAuthority()
    with ContinuityStore(tmp_path/'literal'/'self.db',ManualClock(),schema_target=13) as store:
        IdentityService(store,authority);memory=MemoryService(store,authority)
        for entity in ('bench','other'):memory.entity(entity,'PERSON')
        yield store,memory,authority


def test_common_short_literal_reads_only_four_newest_authorized_bodies(literal_store):
    import inspect,textwrap
    from nana_core.continuity import memory as module
    from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
    from tools.nana_next_experience.memory_diverse_compare import add
    store,memory,_=literal_store;good=[];allowed=set();reads=[]
    for i in range(70):
        mid=add(memory,'common.good.'+str(i),'SYNTHETIC current co report '+str(i));good.append(mid)
        allowed.add(store.one('memories',mid)['payload_artifact_id'])
    for i in range(80):
        for name,kw in [('private',{'privacy':'PERSONAL'}),('scope',{'scope':'elsewhere'}),('entity',{'entity':'other'})]:
            add(memory,'common.'+name+'.'+str(i),'SYNTHETIC forbidden co text',**kw)
        # A semantic/DIRECT/user-note header alone does not grant source consent.
        eid=memory.capture(EvidenceInput(provenance=Provenance(domain='SYNTHETIC_ONLY',source_namespace='synthetic.other-source',
            source_reference='note:common.lookalike.'+str(i),source_kind='USER_STATEMENT'),text='SYNTHETIC unqualified co body',privacy_class='PROJECT',observed_time_us=101))
        memory.add(MemoryCandidate(entity_id='bench',scope='bench',memory_type=MemoryType.SEMANTIC,epistemic_kind='STATEMENT',
            source_evidence_id=eid,text='SYNTHETIC unqualified co body',predicate_key='user-note.common.lookalike.'+str(i)))
    def observed(aid,payload):
        assert aid in allowed,'unqualified/private artifact body was evaluated'
        reads.append(aid);return payload.decode()
    store.db.create_function('observed_body',2,observed)
    source=textwrap.dedent(inspect.getsource(module.MemoryService.literal_notes)).replace('CAST(a.payload AS TEXT)','observed_body(a.artifact_id,a.payload)')
    namespace=dict(vars(module));exec(compile(source,'<instrumented-original-literal-body-read>','exec'),namespace)
    class Traced(module.MemoryService):literal_notes=namespace['literal_notes']
    found=Traced(store).literal_notes(entity_ids=('bench',),scopes=('bench',),privacy_classes=('PROJECT',),terms=('co',),limit=4)
    assert [m['memory_id'] for m in found]==list(reversed(good[-4:]))
    assert len(reads)==4


@pytest.mark.parametrize('term',['归途','🦊🌙','a\ud7ff','\U0010ffff\U0010ffff','a%'])
def test_short_literal_tail_legacy_gap_correction_and_withdrawal_are_exact(literal_store,term):
    from tools.nana_next_experience.memory_diverse_compare import add
    from nana_core.continuity.memory import NOTE_END_PREFIX
    store,memory,authority=literal_store;text='SYNTHETIC an independent ending '+term
    mid=add(memory,'short.boundary',text,predicate='user-note.short.boundary')
    keys=[r[0] for r in store.db.execute('SELECT term FROM memory_terms WHERE memory_id=?',(mid,)) if r[0].startswith(NOTE_END_PREFIX)]
    assert keys==[NOTE_END_PREFIX+text.casefold()[-2:]]
    query=lambda:memory.literal_notes(entity_ids=('bench',),scopes=('bench',),privacy_classes=('PROJECT',),terms=(term,),limit=4)
    assert [m['memory_id'] for m in query()]==[mid]
    # Only a derived cache row is absent. No old fact is deleted or reclassified.
    store.db.execute('DELETE FROM memory_terms WHERE memory_id=? AND term=?',(mid,keys[0]))
    assert [m['memory_id'] for m in query()]==[mid]
    updated=add(memory,'short.corrected','SYNTHETIC changed detail',predicate='user-note.short.boundary',correction=mid)
    assert query()==[]
    memory.forget(updated,authority);assert query()==[]
    assert not store.db.execute('SELECT 1 FROM memory_terms WHERE memory_id=?',(updated,)).fetchone()


def test_short_literal_long_unindexed_and_old_cache_reader_remain_supported(literal_store):
    from tools.nana_next_experience.memory_diverse_compare import add
    from tools.nana_next_experience.literal_two_prefix_probe import original
    from nana_core.continuity.memory import NOTE_END_PREFIX
    store,memory,authority=literal_store
    a=add(memory,'short.legacy','SYNTHETIC a distant 星月')
    b=add(memory,'short.long','SYNTHETIC '+('x'*4100)+' 归途')
    assert not any(r[0].startswith(NOTE_END_PREFIX) for r in store.db.execute('SELECT term FROM memory_terms WHERE memory_id=?',(b,)))
    terms=('星月','归途');kwargs=dict(entity_ids=('bench',),scopes=('bench',),privacy_classes=('PROJECT',),terms=terms,limit=4)
    assert [m['memory_id'] for m in memory.literal_notes(**kwargs)]==[b,a]
    old=original.MemoryService(store,authority)
    assert [m['memory_id'] for m in old.literal_notes(**kwargs)]==[b,a]
    # The original reader's own rebuild may discard new derived keys; the new
    # reader must still find old and long notes exactly, without schema changes.
    old.rebuild_index()
    assert [m['memory_id'] for m in memory.literal_notes(**kwargs)]==[b,a]
    store.db.execute('DROP INDEX memory_terms_term_lookup')
    assert [m['memory_id'] for m in memory.literal_notes(**kwargs)]==[b,a]
