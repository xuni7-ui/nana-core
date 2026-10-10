"""Controlled wire research -> cited evidence -> restart -> scoped multi-tool learning.

This uses the existing reading_card template and deterministic FixtureModel.
It does not prove natural-language research ability or public/real model access.
Only the parent starts a dedicated synthetic loopback service; child processes
inherit no credential variables. FakeWorld is the notebook and durable journal.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from ..actions import ActionKernel, OperatorAuthority
from ..clock import ManualClock
from ..contracts import CAPABILITIES, CoreError, Feedback, GrantSpec, Observation, VERIFY_CAPABILITY
from ..experience import ExperienceEngine
from ..fake_world import FakeWorld
from ..migration.routing import CapabilityRouter
from ..planning import FixtureModel
from ..runtime import Runtime
from ..storage import Store, canonical, digest, uid
from .controlled_web import ControlledWebTransport, FIXTURE_URL, controlled_service
from .public_http import WebSpec
from .web_source import WebSourcePort

SOURCE = "source://public/development/paper-research"
CARDS = ("notebook://synthetic/web-research/first", "notebook://synthetic/web-research/heldout")


def observation(index):
    return Observation(source_namespace="synthetic.web.research", object_id=f"reading-{index}",
        raw_text="Read the approved fictional paper-garden document; preserve a private card with evidence.",
        occurred_at=f"2026-09-0{index+1}T09:00:00Z", source_id=SOURCE, card_resource=CARDS[index])


def grant(kernel, authority, capabilities):
    now = kernel.store.clock.utc_now_us()
    return kernel.grant(GrantSpec(capabilities=tuple(sorted(capabilities)), resources=(SOURCE,*CARDS),
        not_before_us=now, expires_at_us=now+3_600_000_000), authority)


def cite_completed_goal(store, goal_id):
    """A sourced result derived only from verified actions; not model success text."""
    goal = store.one("goals", goal_id)
    if goal["state"] != "COMPLETED":
        return None
    for memory in store.all("memory_items"):
        body = json.loads(memory["body_json"])
        if body.get("result_kind") == "WEB_CITED_RESULT" and body["goal_id"] == goal_id:
            return body
    actions = [a for a in store.all("actions") if a["goal_id"] == goal_id]
    if not actions or any(a["state"] != "SUCCEEDED" for a in actions):
        raise CoreError("VERIFIED_WEB_RESULT_REQUIRED")
    read = next(a for a in actions if a["capability"] == "reading.source.read")
    result = json.loads(read["result_json"])
    verification_id = json.loads(read["body_json"])["verification_event_id"]
    verification = store.event(verification_id)
    # Read and hash-check the actual complete verification artifact before citing.
    store.artifact(verification["artifact_id"])
    body = {"result_kind": "WEB_CITED_RESULT", "goal_id": goal_id,
        "summary": result["text"][:240], "summary_coverage": "SUMMARY",
        "trust": "UNTRUSTED_SOURCE_DATA", "source_url": result["source_url"],
        "source_blob_sha256": result["source_blob_sha256"], "fetched_at_us": result["fetched_at_us"],
        "original_event_id": goal["event_id"], "original_occurred_at_us": store.event(goal["event_id"])["occurred_at_us"],
        "read_action_id": read["action_id"], "evidence_event_id": verification_id,
        "evidence_artifact_id": verification["artifact_id"], "evidence_coverage": "FULL",
        "action_ids": [a["action_id"] for a in actions], "provenance": result["provenance"]}
    with store.transaction("research.result_recorded", {"goal_id": goal_id}) as tx:
        tx.payload_id = tx.artifact(canonical(body).encode())
        tx.put("memory_items", {"memory_id": uid(), "kind": "EPISODE", "status": "ACTIVE",
            "body_json": canonical(body), "created_event_id": tx.event_id})
    return body


def session(root, phase, port_number):
    root = Path(root)
    authority = OperatorAuthority("synthetic-web-research-operator")
    # An injectable engineering clock; original event time and HTTP UTC stay distinct.
    clock, model = ManualClock(), FixtureModel()
    with Store(root/"nana.db", clock) as store:
        world = FakeWorld(root/"fake_world.db")
        try:
            transport = ControlledWebTransport(port_number)
            web = WebSourcePort(store,{SOURCE:WebSpec(url=FIXTURE_URL,provenance="controlled_protocol")},world,authority,transport)
            router = CapabilityRouter(store,{c:world if c=="reading.card.create" else web for c in CAPABILITIES},
                authority,resource_scope="development_public")
            if phase == "initial":
                router.select_owner("core_simulator",authority)
            kernel = ActionKernel(store,router.bind("core_simulator",authority),authority)
            runtime = Runtime(store,kernel,model)
            extra = {}
            if phase == "initial":
                kernel.set_budgets({"external_requests":40,"cost_micro_units":40,"write_attempts":4},authority)
                grant(kernel,authority,CAPABILITIES|{VERIFY_CAPABILITY})
            if phase == "without_experience":
                for rule in store.all("strategies"):
                    if rule["status"] == "ACTIVE":
                        ExperienceEngine(store,kernel).retire(rule["strategy_id"],authority)
            if phase == "deny_locator":
                # An operator-issued narrower grant, not a strategy mutation.
                for old in store.all("grants"):
                    kernel.revoke(old["grant_id"],authority)
                grant(kernel,authority,(CAPABILITIES-{ "reading.source.locate" })|{VERIFY_CAPABILITY})
            grants_before = store.all("grants")
            extra["states_before"] = [a["state"] for a in store.all("actions")]
            if phase in {"recover","restart","blocked_restart"}:
                extra["recovery"] = runtime.resume()
                goals = store.all("goals")
                goal_id = goals[-1]["goal_id"]
            else:
                def fault(point, capability):
                    if phase=="crash" and point=="after_effect" and capability=="reading.source.read":
                        print(canonical({"pid":os.getpid(),"point":point,"capability":capability,
                            "identity_id":store.identity["identity_id"],"http_requests":transport.http_requests}),flush=True)
                        os.kill(os.getpid(),signal.SIGKILL)
                goal_id = runtime.process(observation(0 if phase=="initial" else 1),fault=fault)
                if phase=="crash":
                    raise CoreError("EXPECTED_SIGKILL_NOT_OBSERVED")
                # Re-delivery must not create a new goal, side effect or request.
                for _ in range(3):
                    if runtime.process(observation(0 if phase=="initial" else 1)) != goal_id:
                        raise CoreError("DUPLICATE_EVENT_CHANGED_GOAL")
            cited = cite_completed_goal(store,goal_id)
            if phase=="initial":
                _,rules=ExperienceEngine(store,kernel).learn(Feedback(goal_id=goal_id,
                    text="Synthetic feedback: next reading card needs original passage location.",requested_fields=("locator",)),authority)
                extra["learned_strategy_ids"] = rules
            actions = store.all("actions")
            current_actions = [a for a in actions if a["goal_id"]==goal_id]
            plan = next(p for p in store.all("plans") if p["goal_id"]==goal_id)
            events = store.all("events")
            return {"pid":os.getpid(),"phase":phase,"identity":store.identity,"owner":router.owner,
                "goal_id":goal_id,"goal_state":store.one("goals",goal_id)["state"],"plan":json.loads(plan["body_json"]),
                "actions":current_actions,"all_action_states":[a["state"] for a in actions],
                "event_fingerprints":[digest(e) for e in events],"original_events":[{
                    "event_id":e["event_id"],"occurred_at_us":e["occurred_at_us"],"artifact_id":e["artifact_id"]}
                    for e in events if e["kind"]=="observation.received"],
                "cited_result":cited,"world_counts":world.counts(),"http_requests_this_process":transport.http_requests,
                "model":model.descriptor,"fixture_proposals_this_process":model.calls,
                "grants":store.all("grants"),"grants_unchanged_during_decision":store.all("grants")==grants_before,**extra}
        finally:
            world.close()


def child(root, phase, port_number):
    # No inherited credential bindings and no second concurrent Runtime.
    env={"PATH":os.environ.get("PATH",""),"PYTHONPATH":str(Path(__file__).resolve().parents[2]),"PYTHONDONTWRITEBYTECODE":"1"}
    proc=subprocess.run([sys.executable,"-m","nana_core.development.web_lab","--output",str(root),
        "--session",phase,"--controlled-port",str(port_number)],env=env,capture_output=True,text=True,timeout=30)
    if phase=="crash":
        if proc.returncode != -signal.SIGKILL:
            raise CoreError("REAL_PROCESS_CRASH_NOT_OBSERVED")
        return {"returncode":proc.returncode,"marker":json.loads(proc.stdout)}
    if proc.returncode:
        # Store only safe return codes; never raw provider/transport errors in reports.
        raise CoreError("WEB_WORKER_FAILED_"+str(proc.returncode))
    return json.loads(proc.stdout)


def fork_quiescent(source, target):
    """Closed synthetic lab only. This is not production backup/handoff logic."""
    source,target=Path(source),Path(target)
    target.mkdir(exist_ok=False)
    hashes={}
    for name in ("nana.db","fake_world.db"):
        wal=source/(name+"-wal")
        if wal.exists() and wal.stat().st_size:
            raise CoreError("SNAPSHOT_NOT_QUIESCENT")
        before=digest((source/name).read_bytes())
        shutil.copyfile(source/name,target/name)
        hashes[name]=digest((target/name).read_bytes())
        if hashes[name] != before:
            raise CoreError("SNAPSHOT_COPY_MISMATCH")
    return hashes


def run(output):
    root=Path(output).absolute();root.mkdir(parents=True,exist_ok=False)
    baseline=root/"frozen";baseline.mkdir()
    with controlled_service() as server:
        first=child(baseline,"initial",server.server_port)
        arms={};fork_hashes={}
        for name,phase in (("with_experience","next"),("without_experience","without_experience"),
                           ("crash","crash"),("restricted","deny_locator")):
            branch=root/name;fork_hashes[name]=fork_quiescent(baseline,branch)
            arms[name]=child(branch,phase,server.server_port)
        next_run=arms["with_experience"];ablated=arms["without_experience"]
        restarted=child(root/"with_experience","restart",server.server_port)
        recovered=child(root/"crash","recover",server.server_port)
        denied=arms["restricted"]
        denied_restart=child(root/"restricted","blocked_restart",server.server_port)
        requests=server.requests
    initial_prefix=first["event_fingerprints"]
    phases=[first,next_run,ablated,restarted,recovered,denied,denied_restart]
    locates=[a for a in next_run["actions"] if a["capability"]=="reading.source.locate"]
    locate=json.loads(locates[0]["result_json"]) if len(locates)==1 else {}
    read=next(a for a in next_run["actions"] if a["capability"]=="reading.source.read")
    read_result=json.loads(read["result_json"])
    learned=first["learned_strategy_ids"]
    checks={
        "same_identity_across_actual_processes":all(p["identity"]==first["identity"] for p in phases),
        "actual_restart":len({p["pid"] for p in phases})==len(phases),
        "frozen_arms_identical":all(h==fork_hashes["with_experience"] for h in fork_hashes.values()),
        "history_prefix_retained":all(p["event_fingerprints"][:len(initial_prefix)]==initial_prefix for p in phases),
        "original_event_time_retained":all(p["original_events"][0]==first["original_events"][0] for p in phases),
        "cited_evidence_survives_restart":next_run["cited_result"]==restarted["cited_result"],
        "learning_did_not_change_grants":all(p["grants_unchanged_during_decision"] for p in phases)
            and all(p["grants"]==first["grants"] for p in (next_run,ablated,restarted,recovered)),
        "experience_referenced_and_executed":bool(learned) and set(learned)=={
            r["strategy_id"] for r in next_run["plan"]["applied_strategies"]} and len(locates)==1,
        "experience_ablation_changes_actual_behavior":next_run["world_counts"]["locate_calls"]==1
            and ablated["world_counts"]["locate_calls"]==0 and not ablated["plan"]["applied_strategies"],
        "same_fixture_proposal_for_ablation":next_run["plan"]["before"]==ablated["plan"]["before"],
        "downstream_consumes_verified_evidence":locate.get("upstream_action_id")==read["action_id"]
            and locate.get("upstream_verification_event_id")==json.loads(read["body_json"])["verification_event_id"]
            and locate.get("source_blob_sha256")==read_result["source_blob_sha256"],
        "actual_crash_after_get":arms["crash"]["returncode"]==-signal.SIGKILL
            and arms["crash"]["marker"]["http_requests"]==1 and "DISPATCHING" in recovered["states_before"],
        "recover_only_verifies_previous_get":recovered["http_requests_this_process"]==0
            and recovered["fixture_proposals_this_process"]==0 and all(s=="SUCCEEDED" for s in recovered["all_action_states"]),
        "restarts_and_redelivery_no_duplicate_effects":restarted["http_requests_this_process"]==0
            and all(p["world_counts"]["effects"]==2 for p in (next_run,ablated,restarted,recovered)),
        "learned_step_without_grant_blocks":denied["goal_state"]==denied_restart["goal_state"]=="BLOCKED"
            and denied["world_counts"]["effects"]==denied_restart["world_counts"]["effects"]==1,
        "blocked_restart_preserves_read_no_retry":denied["http_requests_this_process"]==1
            and denied_restart["http_requests_this_process"]==0
            and next(a for a in denied_restart["actions"] if a["capability"]=="reading.source.read")["state"]=="SUCCEEDED",
        "wire_calls_accounted":requests==sum(p["http_requests_this_process"] for p in phases)+arms["crash"]["marker"]["http_requests"],
        "same_single_executor":all(p["owner"]==first["owner"] for p in phases),
    }
    report={"schema_version":1,"scope":"synthetic controlled loopback HTTP; deterministic planner; fake notebook",
        "engineering_gate":"PASS" if all(checks.values()) else "FAIL","checks":checks,"E12":"NOT_RUN",
        "semantic_gate":"NOT_RUN","public_fetch_gate":"NOT_RUN","real_model_calls":0,"external_fees":0,
        "production_calls":0,"actual_loopback_http_requests":requests,"actual_public_http_requests":0,
        "identity":first["identity"],"fork_hashes":fork_hashes,"phases":phases,"crash":arms["crash"],
        "note":"Journal verification proves historical fetched bytes, not current web content. Not real research semantics."}
    (root/"web_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    parser.add_argument("--session",choices=["initial","next","without_experience","crash","recover","restart","deny_locator","blocked_restart"],help=argparse.SUPPRESS)
    parser.add_argument("--controlled-port",type=int,help=argparse.SUPPRESS)
    args=parser.parse_args()
    result=session(args.output,args.session,args.controlled_port) if args.session else run(args.output)
    print(canonical(result if args.session else {k:result[k] for k in (
        "engineering_gate","checks","actual_loopback_http_requests","E12")}))
    if not args.session and result["engineering_gate"]!="PASS":
        raise SystemExit(1)


if __name__=="__main__":main()
