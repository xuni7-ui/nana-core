import json
import subprocess
import sys

import pytest

from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.cognition import AnalyticalFixturePort, CautiousFixturePort, DeliberationSession
from nana_core.continuity.context import ContextAssembler
from nana_core.continuity.contracts import MemoryType
from nana_core.continuity.learning import ExperienceInput, ExperienceService
from nana_core.contracts import CoreError
from .conftest import evidence
from .test_context import policy, request
from .test_memory import add


def learn_missing_locator(store, memory, authority):
    original = add(memory, evidence(memory, "lesson-context", "Create a synthetic reading card"),
                   "Create a synthetic reading card", kind=MemoryType.EPISODIC)
    result = add(memory, evidence(memory, "lesson-result", '{"text":"Fictional card","success":true}'),
                 '{"text":"Fictional card","success":true}', kind=MemoryType.EPISODIC)
    learning = ExperienceService(store, authority)
    proof = learning.verify_reading_result(result, authority)
    experience = learning.record(ExperienceInput(context_memory_ids=(original,), scope="synthetic-home",
        task_class="reading_card", decision="Drafted without acquiring a source locator", result_memory_id=result,
        verification_memory_id=proof, proposed_update="Acquire the missing source locator before drafting"))
    assert learning.get(experience).outcome == "FAILURE"  # model's success:true ignored
    lesson = learning.derive_lesson(experience)
    assert learning.derive_lesson(experience) == lesson
    with pytest.raises(CoreError, match="UNTESTED_LESSON"):
        learning.activate(lesson, authority)
    assert all(learning.test_lesson(lesson).values())
    with pytest.raises(CoreError, match="UNAUTHENTICATED_OPERATOR"):
        learning.activate(lesson, OperatorAuthority())
    learning.activate(lesson, authority)
    return original, result, experience, lesson


def test_experience_restart_new_model_and_matched_ablation(cognitive):
    store, memory, authority = cognitive
    identity = IdentityService(store, authority).current()
    _, _, experience, lesson = learn_missing_locator(store, memory, authority)
    assembler = ContextAssembler(store, authority)
    context = assembler.assemble(request(), policy())
    learned = DeliberationSession(assembler).run(AnalyticalFixturePort(), context, request(), policy())
    assert learned.proposal.lesson_refs == (lesson,)
    assert learned.proposal.proposed_operations == ("READ_SOURCE", "LOCATE_SOURCE", "DRAFT")
    unrelated = assembler.assemble(request().model_copy(update={"task_class": "unrelated"}), policy())
    assert not any(b.kind == "LESSON" for b in unrelated.blocks)
    # An actual fresh interpreter opens a managed snapshot, swaps the fixture
    # port, and reconstructs context from Store; no Python object is shared.
    backup = store.path.with_name("restart-learning.db")
    store.backup(backup)
    code = '''
import sys
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore
from nana_core.continuity.context import ContextAssembler,ContextRequest,ContextPolicy
from nana_core.continuity.cognition import CautiousFixturePort,DeliberationSession
with ContinuityStore(sys.argv[1]) as s:
 a=ContextAssembler(s,OperatorAuthority())
 r=ContextRequest(entity_id='synthetic-sister',scopes=('synthetic-home',),task_class='reading_card',task='Prepare a synthetic reading card')
 p=ContextPolicy(policy_id='synthetic-local',allowed_scopes=('synthetic-home',),readable_privacy=('PUBLIC','PROJECT','PERSONAL'))
 print(DeliberationSession(a).run(CautiousFixturePort(),a.assemble(r,p),r,p).proposal.model_dump_json())
'''
    child = subprocess.run([sys.executable, "-c", code, str(backup)], capture_output=True, text=True, timeout=10, check=True)
    restored = json.loads(child.stdout)
    assert restored["identity_id"] == identity.identity_id and restored["identity_revision"] == identity.revision
    assert restored["lesson_refs"] == [lesson] and restored["proposed_operations"] == list(learned.proposal.proposed_operations)
    learning = ExperienceService(store, authority)
    # All input history retained; only this tested lesson is disabled.
    before = {t: store.all(t) for t in ("identities", "memories", "continuity_evidence", "commitments", "projects", "experiences")}
    learning.suspend(lesson, authority)
    without_context = assembler.assemble(request(), policy())
    without = DeliberationSession(assembler).run(AnalyticalFixturePort(), without_context, request(), policy())
    assert without.proposal.proposed_operations == ("READ_SOURCE", "DRAFT") and not without.proposal.lesson_refs
    assert before == {t: store.all(t) for t in before}
    assert any(b.kind == "EXPERIENCE" for b in without_context.blocks)
    assert not any(store.all(t) for t in ("actions", "attempts", "grants", "budgets", "strategies"))
    assert IdentityService(store, authority).current() == identity


def test_deleted_experience_source_retires_lessons_and_context(cognitive):
    store, memory, authority = cognitive
    original, _, experience, lesson = learn_missing_locator(store, memory, authority)
    memory.forget(original, authority)
    with pytest.raises(CoreError, match="RECORD_UNAVAILABLE"):
        ExperienceService(store, authority).get(experience)
    context = ContextAssembler(store, authority).assemble(request(), policy())
    assert not any(b.kind in {"LESSON", "EXPERIENCE"} for b in context.blocks)
    assert store.one("continuity_records", store.one("lessons", lesson)["record_id"])["lifecycle"] == "DELETED"
