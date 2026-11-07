import pytest

from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.commitments import CommitmentCandidate, CommitmentService, FulfillmentCheck
from nana_core.continuity.contracts import MemoryType, MemoryCandidate
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.projects import Milestone, ProjectContent, ProjectService
from nana_core.continuity.relationships import relationship_view
from nana_core.contracts import CoreError
from .conftest import evidence
from .test_memory import add
from .test_privacy import CANARY


def test_relationship_promises_project_revision_and_restart(cognitive):
    store, memory, authority = cognitive
    identity = IdentityService(store, authority).current()
    shared = add(memory, evidence(memory, "shared", "We reviewed fictional project P"),
                 "We reviewed fictional project P", kind=MemoryType.EPISODIC)
    preference = add(memory, evidence(memory, "norm", "Use concise notes"), "Use concise notes",
        kind=MemoryType.RELATIONAL, predicate_key="preference.notes")
    commitments = CommitmentService(store, authority)
    candidate = commitments.propose(CommitmentCandidate(entity_id="synthetic-sister",
        scope="synthetic-home", description="Finish the fictional offline review",
        support_memory_ids=(shared,), due_at_us=store.clock.utc_now_us() + 100))
    view = relationship_view(store, "synthetic-sister", scopes=("synthetic-home",), privacy_classes=("PERSONAL",))
    assert not view.adopted_commitment_ids and view.known_preferences == ("Use concise notes",)
    with pytest.raises(CoreError, match="UNAUTHENTICATED_OPERATOR"):
        commitments.transition(candidate, "ADOPTED", expected_revision=1, authority=OperatorAuthority())
    commitments.transition(candidate, "ADOPTED", expected_revision=1, authority=authority)
    commitments.transition(candidate, "ACTIVE", expected_revision=2, authority=authority)
    with pytest.raises(CoreError, match="INDEPENDENT_FULFILLMENT"):
        commitments.transition(candidate, "FULFILLED", expected_revision=3, authority=authority)
    project = ProjectService(store, authority)
    first = project.save(project_id="synthetic-nana-core", entity_id="synthetic-sister", scope="synthetic-home",
        content=ProjectContent(goal="Offline continuity", current_state="Implementation in progress",
            milestones=(Milestone(milestone_id="C", title="Memory", state="ACTIVE"),),
            decisions=("Use one Store",), blockers=("Real-data scope not authorized",),
            next_actions=("Rebuild context",)), source_memory_ids=(shared,), expected_revision=0, authority=authority)
    second = project.save(project_id=first.project_id, entity_id="synthetic-sister", scope="synthetic-home",
        content=first.content.model_copy(update={"current_state": "Memory completed", "recent_progress": ("C implemented",)}),
        source_memory_ids=(shared,), expected_revision=1, authority=authority)
    with pytest.raises(CoreError, match="STALE_PROJECT_REVISION"):
        project.save(project_id=first.project_id, entity_id="synthetic-sister", scope="synthetic-home",
            content=first.content, source_memory_ids=(shared,), expected_revision=1, authority=authority)
    store.clock.advance(200)
    assert commitments.get(candidate).overdue
    backup = store.path.with_name("restarted.db")
    store.backup(backup)
    with ContinuityStore(backup, store.clock) as reopened:
        assert IdentityService(reopened, authority).current() == identity
        assert CommitmentService(reopened, authority).get(candidate).state == "ACTIVE"
        assert ProjectService(reopened, authority).get(first.project_id) == second
        current = relationship_view(reopened, "synthetic-sister", scopes=("synthetic-home",), privacy_classes=("PERSONAL",))
        assert current.adopted_commitment_ids == (candidate,) and current.shared_project_ids == (first.project_id,)
    check = FulfillmentCheck(commitment_id=candidate, commitment_revision=3, satisfied=True,
                             result_reference=first.project_id).model_dump_json()
    proof = memory.add(MemoryCandidate(entity_id="synthetic-sister", scope="synthetic-home",
        memory_type=MemoryType.EPISODIC, epistemic_kind="OBSERVATION",
        source_evidence_id=evidence(memory, "verified", check, kind="SYSTEM_VERIFICATION"), text=check))
    assert commitments.transition(candidate, "FULFILLED", expected_revision=3, authority=authority,
                                  fulfillment_memory_id=proof).state == "FULFILLED"
    with pytest.raises(CoreError, match="ILLEGAL_COMMITMENT_TRANSITION"):
        commitments.transition(candidate, "ACTIVE", expected_revision=4, authority=authority)


def test_deletion_covers_relationship_commitment_and_every_project_revision(cognitive):
    store, memory, authority = cognitive
    shared = add(memory, evidence(memory, "private-shared", CANARY), CANARY, kind=MemoryType.RELATIONAL)
    commitments = CommitmentService(store, authority)
    cid = commitments.propose(CommitmentCandidate(entity_id="synthetic-sister", scope="synthetic-home",
        description=CANARY, support_memory_ids=(shared,)))
    project = ProjectService(store, authority)
    for revision in range(2):
        project.save(project_id="synthetic-project", entity_id="synthetic-sister", scope="synthetic-home",
            content=ProjectContent(goal=CANARY, current_state=f"revision {revision}"), source_memory_ids=(shared,),
            expected_revision=revision, authority=authority)
    assert memory.forget(shared, authority)["state"] == "COMPLETE"
    with pytest.raises(CoreError, match="RECORD_UNAVAILABLE"):
        commitments.get(cid)
    with pytest.raises(CoreError, match="RECORD_UNAVAILABLE"):
        project.get("synthetic-project")
    assert all(r["lifecycle"] == "DELETED" for r in store.all("continuity_records"))
    assert CANARY.encode() not in store.path.read_bytes()
    assert not relationship_view(store, "synthetic-sister", scopes=("synthetic-home",),
                                 privacy_classes=("PERSONAL",)).memory_ids


def test_relationship_families_survive_unrelated_growth_restart_and_withdrawal(cognitive, monkeypatch):
    """Old important relationship facts cannot compete with unrelated trivia."""
    store, memory, authority = cognitive
    preference = add(memory, evidence(memory, "old-pref", "Prefer quiet evenings"),
        "Prefer quiet evenings", kind=MemoryType.SEMANTIC,
        predicate_key="preference.evenings", importance=0.1)
    boundary = add(memory, evidence(memory, "old-boundary", "Do not push declined topics"),
        "Do not push declined topics", kind=MemoryType.RELATIONAL,
        predicate_key="relationship.boundary.topic", importance=0.1)
    shared = add(memory, evidence(memory, "old-shared", "Reviewed the real synthetic project together"),
        "Reviewed the real synthetic project together", kind=MemoryType.EPISODIC, importance=0.1)
    for i in range(150):
        add(memory, evidence(memory, f"unrelated-{i}", f"Unrelated synthetic fact {i}"),
            f"Unrelated synthetic fact {i}", predicate_key=f"unrelated.{i}", importance=0.99)
    unrelated_payloads = {row["payload_artifact_id"] for row in store.all("memories")
                          if (row["predicate_key"] or "").startswith("unrelated.")}
    real_artifact = store.artifact
    def safe_read(artifact_id):
        assert artifact_id not in unrelated_payloads, "irrelevant payload loaded before family selection"
        return real_artifact(artifact_id)
    monkeypatch.setattr(store, "artifact", safe_read)
    kwargs = {"scopes": ("synthetic-home",), "privacy_classes": ("PERSONAL",)}
    view = relationship_view(store, "synthetic-sister", **kwargs)
    assert view.known_preferences == ("Prefer quiet evenings",)
    assert view.boundaries == ("Do not push declined topics",)
    assert shared in view.memory_ids and preference in view.memory_ids and boundary in view.memory_ids
    assert len(view.memory_ids) <= 128
    assert not relationship_view(store, "synthetic-sister", scopes=("synthetic-home",),
                                 privacy_classes=("PUBLIC",)).memory_ids
    backup = store.path.with_name("relationship-restart.db")
    store.backup(backup)
    with ContinuityStore(backup, store.clock) as restored:
        assert relationship_view(restored, "synthetic-sister", **kwargs) == view
    memory.forget(boundary, authority)
    assert not relationship_view(store, "synthetic-sister", **kwargs).boundaries
    assert relationship_view(store, "synthetic-sister", **kwargs).known_preferences == view.known_preferences


def test_relationship_correction_dispute_and_literal_family_boundaries(cognitive):
    store, memory, _ = cognitive
    original = add(memory, evidence(memory, "pref-old", "Prefer A", privacy="PUBLIC"),
                   "Prefer A", predicate_key="preference.choice")
    revised = add(memory, evidence(memory, "pref-new", "Prefer B", privacy="PUBLIC", when=200),
                  "Prefer B", predicate_key="preference.choice", correction_of=original)
    kwargs = {"scopes": ("synthetic-home",), "privacy_classes": ("PUBLIC",)}
    assert relationship_view(store, "synthetic-sister", **kwargs).known_preferences == ("Prefer B",)
    add(memory, evidence(memory, "pref-dispute", "Prefer C", privacy="PUBLIC", when=200),
        "Prefer C", predicate_key="preference.choice")
    assert not relationship_view(store, "synthetic-sister", **kwargs).known_preferences
    assert memory.read(revised, include_inactive=True)["assessment"] == "DISPUTED"
    assert not memory.query(**kwargs, predicate_prefixes=("preference.%",))
    with pytest.raises(CoreError, match="INVALID_PREDICATE_PREFIX_FILTER"):
        memory.query(**kwargs, predicate_prefixes=("",))
    with pytest.raises(CoreError, match="INVALID_PREDICATE_PREFIX_FILTER"):
        memory.query(**kwargs, predicate_prefixes=tuple("x" for _ in range(9)))
