import json

import pytest
from pydantic import ValidationError

from nana_core.actions import ActionKernel
from nana_core.continuity.cognition import AnalyticalFixturePort, CautiousFixturePort, DeliberationSession, FrozenModelInput
from nana_core.continuity.context import ContextAssembler
from nana_core.contracts import CoreError
from .conftest import evidence
from .test_context import policy, request
from .test_memory import add


def test_two_model_ports_share_same_identity_memory_and_no_write_authority(cognitive):
    store, memory, authority = cognitive
    mid = add(memory, evidence(memory, "subject", "Fictional shared reading history"), "Fictional shared reading history")
    assembler = ContextAssembler(store, authority)
    context = assembler.assemble(request(), policy())
    session = DeliberationSession(assembler)
    before = store.snapshot()
    a = session.run(AnalyticalFixturePort(), context, request(), policy())
    b = session.run(CautiousFixturePort(), context, request(), policy())
    assert a.proposal.identity_id == b.proposal.identity_id == store.identity["identity_id"]
    assert a.proposal.interpretation != b.proposal.interpretation
    assert a.proposal.memory_refs == b.proposal.memory_refs == (mid,)
    assert store.snapshot() == before
    class NoEffects:
        def execute(self, invocation):
            raise AssertionError("not reachable")
    kernel = ActionKernel(store, NoEffects(), authority)
    with pytest.raises(CoreError, match="SHADOW_BLOCKED"):
        kernel.set_budgets({"write_attempts": 1, "external_requests": 1, "cost_micro_units": 1}, authority)
    assert not any(store.all(t) for t in ("actions", "attempts", "grants", "budgets"))


def test_model_cannot_forge_authority_receipt_identity_or_memory_reference(cognitive):
    store, memory, authority = cognitive
    assembler = ContextAssembler(store, authority)
    context = assembler.assemble(request(), policy())
    base = json.loads(AnalyticalFixturePort().propose(FrozenModelInput(
            task_class="reading_card", context_json=context.model_dump_json(), context_digest=context.content_digest)))
    class HostilePort:
        descriptor = "offline-hostile-fixture"
        def __init__(self, body):
            self.body = body
        def propose(self, request):
            return json.dumps(self.body)
    for extra in ("grant", "receipt", "success", "authority"):
        with pytest.raises(ValidationError):
            DeliberationSession(assembler).run(HostilePort({**base, extra: "forged"}), context, request(), policy())
    with pytest.raises(CoreError, match="MODEL_IDENTITY_MISMATCH"):
        DeliberationSession(assembler).run(HostilePort({**base, "identity_id": "new-self"}), context, request(), policy())
    with pytest.raises(CoreError, match="UNSUPPORTED_COGNITIVE_REFERENCE"):
        DeliberationSession(assembler).run(HostilePort({**base, "memory_refs": ["invented-memory"]}), context, request(), policy())
    from nana_core.continuity import IdentityService
    from nana_core.continuity.commitments import CommitmentService
    from nana_core.continuity.projects import ProjectService
    from nana_core.continuity.learning import ExperienceService
    for constructor in (IdentityService, CommitmentService, ProjectService, ExperienceService, ContextAssembler):
        with pytest.raises(CoreError, match="OPERATOR_AUTHORITY_REQUIRED"):
            constructor(store, None)
