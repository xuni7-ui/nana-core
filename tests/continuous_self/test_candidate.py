"""One vertical acceptance path across the permanent C–D services."""
import json
import subprocess
import sys

from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.cognition import AnalyticalFixturePort, DeliberationSession
from nana_core.continuity.commitments import CommitmentCandidate, CommitmentService
from nana_core.continuity.context import ContextAssembler
from nana_core.continuity.contracts import MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.projects import ProjectContent, ProjectService
from nana_core.storage import digest
from .conftest import evidence
from .test_context import policy, request
from .test_learning import learn_missing_locator
from .test_memory import add

TABLES = ("identities", "identity_revisions", "memories", "commitments", "projects", "experiences", "lessons")


def test_full_continuous_self_candidate_across_real_process_restart(tmp_path):
    path, authority = tmp_path / "candidate.db", OperatorAuthority()
    with ContinuityStore(path, ManualClock()) as store:
        identity = IdentityService(store, authority).current()
        memory = MemoryService(store, authority)
        memory.entity("synthetic-sister", "PERSON")
        shared = add(memory, evidence(memory, "shared-project", "We are building a fictional continuity project"),
                     "We are building a fictional continuity project", kind=MemoryType.RELATIONAL)
        self_memory = add(memory, evidence(memory, "self-focus", "Current focus: reliable continuity"),
                          "Current focus: reliable continuity", kind=MemoryType.SELF)
        old = add(memory, evidence(memory, "old-preference", "Long notes", when=100), "Long notes",
                  predicate_key="preference.notes")
        corrected = add(memory, evidence(memory, "corrected-preference", "Short notes with sources", when=200),
                        "Short notes with sources", predicate_key="preference.notes", correction_of=old)
        commitments = CommitmentService(store, authority)
        cid = commitments.propose(CommitmentCandidate(entity_id="synthetic-sister", scope="synthetic-home",
            description="Complete the fictional review", support_memory_ids=(shared,)))
        commitments.transition(cid, "ADOPTED", expected_revision=1, authority=authority)
        commitments.transition(cid, "ACTIVE", expected_revision=2, authority=authority)
        ProjectService(store, authority).save(project_id="synthetic-continuity", entity_id="synthetic-sister",
            scope="synthetic-home", content=ProjectContent(goal="Continuity without chat replay",
                current_state="Offline candidate", decisions=("Keep one identity",),
                next_actions=("Review offline results",)), source_memory_ids=(shared,), expected_revision=0, authority=authority)
        _, _, experience, lesson = learn_missing_locator(store, memory, authority)
        assembler = ContextAssembler(store, authority)
        context = assembler.assemble(request(), policy())
        a = DeliberationSession(assembler).run(AnalyticalFixturePort(), context, request(), policy())
        before = digest({t: store.all(t) for t in TABLES})
        assert old not in {mid for block in context.blocks for mid in block.source_memory_ids}
        assert corrected in {mid for block in context.blocks for mid in block.source_memory_ids}
        assert a.proposal.lesson_refs == (lesson,)
    code = '''
import json,sys
from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.context import ContextAssembler,ContextRequest,ContextPolicy,self_frame
from nana_core.continuity.cognition import CautiousFixturePort,DeliberationSession
from nana_core.continuity.memory import MemoryService
from nana_core.storage import digest
with ContinuityStore(sys.argv[1],ManualClock()) as s:
 a=OperatorAuthority()
 r=ContextRequest(entity_id='synthetic-sister',scopes=('synthetic-home',),task_class='reading_card',task='Prepare a synthetic reading card')
 p=ContextPolicy(policy_id='synthetic-local',allowed_scopes=('synthetic-home',),readable_privacy=('PUBLIC','PROJECT','PERSONAL'))
 assembler=ContextAssembler(s,a)
 context=assembler.assemble(r,p)
 result=DeliberationSession(assembler).run(CautiousFixturePort(),context,r,p)
 frame=self_frame(s,a,entity_id=r.entity_id,scopes=r.scopes,privacy_classes=p.readable_privacy)
 tables=('identities','identity_revisions','memories','commitments','projects','experiences','lessons')
 print(json.dumps({'identity_id':frame.identity.identity_id,'identity_revision':frame.identity.revision,
  'commitments':{x.commitment_id:x.state for x in frame.active_commitments},
  'projects':{x.project_id:x.content.current_state for x in frame.active_projects},
  'preferences':frame.relationship.known_preferences,'self_memory_ids':frame.self_memory_ids,
  'original_times':{x['memory_id']:x['event_time_us'] for x in MemoryService(s).query(scopes=r.scopes,privacy_classes=p.readable_privacy)},
  'lesson_refs':result.proposal.lesson_refs,'operations':result.proposal.proposed_operations,
  'state_digest':digest({t:s.all(t) for t in tables}),
  'action_counts':{t:len(s.all(t)) for t in ('actions','attempts','grants','budgets')}}))
'''
    child = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, text=True, check=True, timeout=10)
    b = json.loads(child.stdout)
    assert b["identity_id"] == identity.identity_id and b["identity_revision"] == identity.revision
    assert b["state_digest"] == before
    assert b["commitments"] == {cid: "ACTIVE"}
    assert b["projects"] == {"synthetic-continuity": "Offline candidate"}
    assert b["preferences"] == ["Short notes with sources"]
    assert b["self_memory_ids"] == [self_memory] and b["original_times"][corrected] == 200
    assert b["lesson_refs"] == [lesson] and b["operations"] == list(a.proposal.proposed_operations)
    assert all(v == 0 for v in b["action_counts"].values())
    report = {"test_origin": "SYNTHETIC_OFFLINE", "real_process_restart": True,
        "models": [a.model_descriptor, "offline-cautious-fixture-v2"], "real_model_calls": 0,
        "identity_id": identity.identity_id, "state_digest_unchanged": b["state_digest"] == before,
        "active_commitment_recovered": True, "project_recovered": True,
        "correction_original_time_us": b["original_times"][corrected], "experience_id": experience,
        "lesson_refs": b["lesson_refs"], "post_restart_operations": b["operations"],
        "action_counts": b["action_counts"], "real_ingress_enabled": False}
    (tmp_path / "candidate-evidence.json").write_text(json.dumps(report, indent=2) + "\n")
