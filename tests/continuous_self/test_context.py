import json

import pytest
from pydantic import ValidationError

from nana_core.continuity.context import (ContextAssembler, ContextPolicy, ContextRequest,
    ObservationCoverage, record_coverage, self_frame)
from nana_core.continuity.contracts import MemoryType
from nana_core.contracts import CoreError
from .conftest import evidence
from .test_memory import add
from .test_privacy import CANARY


def request(**kwargs):
    return ContextRequest(entity_id="synthetic-sister", scopes=("synthetic-home",),
        task_class="reading_card", task="Prepare a synthetic reading card", **kwargs)


def policy(**kwargs):
    return ContextPolicy(policy_id="synthetic-local", allowed_scopes=("synthetic-home",),
        readable_privacy=("PUBLIC", "PROJECT", "PERSONAL"), **kwargs)


def test_self_frame_reconstruction_context_budget_sources_and_stale_delete(cognitive):
    store, memory, authority = cognitive
    mid = add(memory, evidence(memory, "relevant", CANARY), CANARY, kind=MemoryType.SELF)
    record_coverage(store, ObservationCoverage(scope="synthetic-home", start_us=100, end_us=200,
                                              status="PARTIAL", dropped_count=1))
    assembler = ContextAssembler(store, authority)
    frame = self_frame(store, authority, entity_id="synthetic-sister", scopes=("synthetic-home",),
        privacy_classes=("PERSONAL",), capabilities=("local.read",), limitations=("No execution authority",))
    assert frame.self_memory_ids == (mid,) and frame.derived
    context = assembler.assemble(request(query_terms=(CANARY,)), policy())
    assembler.validate(context, request(query_terms=(CANARY,)), policy())
    assert context.manifest.input_tokens <= context.manifest.input_limit
    assert context.manifest.coverage[0].status == "PARTIAL"
    assert CANARY in context.model_dump_json()
    assert any(mid in b.source_memory_ids for b in context.blocks)
    assert frame.identity.identity_id == context.manifest.identity_id
    memory.forget(mid, authority)
    with pytest.raises(CoreError, match="STALE_CONTEXT"):
        assembler.validate(context, request(query_terms=(CANARY,)), policy())
    replacement = assembler.assemble(request(), policy())
    assert CANARY not in replacement.model_dump_json()
    with pytest.raises(CoreError, match="INSUFFICIENT_CONTEXT_BUDGET"):
        assembler.assemble(request(max_input_tokens=256, output_reserve_tokens=0), policy())
    assert not store.all("actions") and not store.all("grants")


def test_remote_privacy_filter_and_complete_conflict_bundle(cognitive):
    store, memory, authority = cognitive
    add(memory, evidence(memory, "personal", CANARY), CANARY)
    a = add(memory, evidence(memory, "pref-a", "A", privacy="PUBLIC"), "A", predicate_key="preference.x")
    b = add(memory, evidence(memory, "pref-b", "B", privacy="PUBLIC"), "B", predicate_key="preference.x")
    assembler = ContextAssembler(store, authority)
    req, pol = request(destination="DEVELOPMENT_REMOTE"), policy(remote_privacy=("PUBLIC",))
    context = assembler.assemble(req, pol)
    assert CANARY not in context.model_dump_json()
    conflicts = [b for b in context.blocks if b.kind == "UNRESOLVED_CONFLICT"]
    assert len(conflicts) == 1 and set(conflicts[0].source_memory_ids) == {a, b}
    assert {c["text"] for c in json.loads(conflicts[0].data_json)["claims"]} == {"A", "B"}
    assert context.manifest.coverage[0].status == "UNKNOWN"
    with pytest.raises(CoreError, match="CONTEXT_SCOPE_DENIED"):
        assembler.assemble(request(), pol.model_copy(update={"allowed_scopes": ("another-scope",)}))
    altered = context.model_copy(update={"blocks": context.blocks[:-1]})
    with pytest.raises(CoreError, match="CONTEXT_TAMPERED"):
        assembler.validate(altered, req, pol)
    with pytest.raises(ValidationError):
        ObservationCoverage(scope="synthetic-home", start_us=100, end_us=200, status="FULL", dropped_count=1)
