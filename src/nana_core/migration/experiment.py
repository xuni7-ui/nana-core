"""S6 synthetic import -> shadow -> single-owner execution -> restart/recovery.

No host adapters, credentials, real models or production services are loaded.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from ..actions import ActionKernel, OperatorAuthority
from ..clock import ManualClock
from ..contracts import CAPABILITIES, Feedback, GrantSpec, Observation, PlanProposal, StepProposal, VERIFY_CAPABILITY
from ..experience import ExperienceEngine
from ..experiment import _summary
from ..fake_world import FakeWorld
from ..planning import FixtureModel
from ..runtime import Runtime
from ..storage import Store, canonical
from .legacy import LegacyImporter, synthetic_records
from .routing import CapabilityRouter
from .shadow import ShadowObserver

SOURCE = "source://synthetic/s6/paper-observatory"
CARDS = tuple(f"notebook://synthetic/s6/card-{n}" for n in (1, 2, 3))


def _observation(n):
    return Observation(source_namespace="synthetic.s6.reading", object_id=f"synthetic-reading-{n}",
        raw_text=f"Fictional reader resumes chapter {n} about a paper observatory.",
        occurred_at=f"2026-09-1{n}T09:00:00+08:00", source_id=SOURCE, card_resource=CARDS[n - 1])


def _plan(n):
    return PlanProposal(purpose="A synthetic reading card.", steps=(
        StepProposal(capability="reading.source.read", resource=SOURCE),
        StepProposal(capability="reading.card.create", resource=CARDS[n - 1])))


def _session(root, phase):
    root = Path(root)
    clock, authority, model = ManualClock(), OperatorAuthority("synthetic-s6-operator"), FixtureModel()
    with Store(root / "core.db", clock) as store:
        world = FakeWorld(root / "world.db")
        try:
            router = CapabilityRouter(store, {c: world for c in CAPABILITIES}, authority)
            if phase == "initial":
                world.seed_source(SOURCE, [{"text": "A fictional observer folds a telescope from blue paper.",
                    "locator": "synthetic volume 2, page 41, paragraph 3"}])
                router.select_owner("legacy_simulator", authority)
            if not router.owner:
                raise RuntimeError("missing persisted synthetic execution owner")
            port = router.bind(router.owner["actor"], authority)
            kernel = ActionKernel(store, port, authority)
            runtime = Runtime(store, kernel, model)
            importer = LegacyImporter(store)
            imported = importer.import_batch(synthetic_records())
            extra = {}
            if phase == "initial":
                kernel.set_budgets({"write_attempts": 8, "external_requests": 100, "cost_micro_units": 100}, authority)
                kernel.grant(GrantSpec(capabilities=tuple(sorted(CAPABILITIES | {VERIFY_CAPABILITY})),
                    resources=(SOURCE, *CARDS), not_before_us=clock.utc_now_us(), expires_at_us=clock.utc_now_us() + 100_000_000), authority)
                shadow = ShadowObserver(store)
                compared = shadow.observe(_observation(1), _plan(1), _plan(1))
                extra["shadow_initial_world_counts"] = world.counts()
                goal = runtime.process(_observation(1))
                ExperienceEngine(store, kernel).learn(Feedback(goal_id=goal,
                    text="Synthetic feedback: future reading cards should preserve the original passage locator.",
                    requested_fields=("locator",)), authority)
                next_comparison = shadow.observe(_observation(2), _plan(2), _plan(2))
                extra.update({"shadow_first": compared, "shadow_after_learning": next_comparison})
            elif phase == "next":
                router.select_owner("core_simulator", authority)
                # Replace the only active driver after a resolved synthetic handoff.
                runtime = Runtime(store, ActionKernel(store, router.bind("core_simulator", authority), authority), model)
                goal = runtime.process(_observation(2))
                for _ in range(10):
                    if runtime.process(_observation(2)) != goal:
                        raise RuntimeError("duplicate event changed goal")
            elif phase == "crash":
                def fault(point, capability):
                    if point == "after_effect" and capability == "reading.card.create":
                        print(canonical({"fault": "after_external_effect", "pid": os.getpid(), "capability": capability}), flush=True)
                        os.kill(os.getpid(), signal.SIGKILL)
                runtime.process(_observation(3), fault=fault)
                raise RuntimeError("fault injection did not SIGKILL")
            elif phase == "recover":
                extra["states_before_recovery"] = [a["state"] for a in store.all("actions")]
                runtime.resume()
                snapshot = store.snapshot()
                store.replay(root / "replayed.db")
                with Store(root / "replayed.db", clock) as replay:
                    expected = json.loads(canonical(snapshot))
                    for row in expected["core_meta"]:
                        if row["key"] == "recovery_quarantine": row["value_json"] = "true"
                    extra["full_replay_equal_except_quarantine"] = expected == replay.snapshot()
            result = _summary(store, world)
            result.update({"owner": router.owner, "import_results": imported, "model_calls_this_process": model.calls, **extra})
            return result
        finally:
            world.close()


def _child(root, phase, crash=False):
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
           "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-m", "nana_core.migration.experiment", "--session", phase,
        "--output", str(root)], env=env, capture_output=True, text=True, timeout=30)
    if crash:
        if result.returncode != -signal.SIGKILL:
            raise RuntimeError("expected actual SIGKILL; got worker exit " + str(result.returncode))
        return {"returncode": result.returncode, "marker": json.loads(result.stdout)}
    if result.returncode:
        raise RuntimeError("synthetic worker failed with exit " + str(result.returncode))
    return json.loads(result.stdout)


def run_experiment(output):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    initial = _child(root, "initial")
    next_run = _child(root, "next")
    killed = _child(root, "crash", crash=True)
    recovered = _child(root, "recover")
    imports = [e for e in recovered["events"] if e["kind"] == "migration.legacy_imported"]
    cards = [json.loads(c["content_json"]) for c in recovered["cards"]]
    checks = {
        "same_identity_across_processes": initial["identity"] == next_run["identity"] == recovered["identity"],
        "actual_restart": initial["pid"] != next_run["pid"] != recovered["pid"],
        "history_prefix_equal": recovered["events"][:len(initial["events"])] == initial["events"],
        "legacy_sources_once": len(imports) == 4 and not any(r["added"] for r in recovered["import_results"]),
        "original_and_unknown_times_preserved": [e["occurred_at_us"] for e in imports] == [
            e["occurred_at_us"] for e in initial["events"] if e["kind"] == "migration.legacy_imported"] and imports[1]["occurred_at_us"] is None,
        "shadow_has_no_calls": all(v == 0 for v in initial["shadow_initial_world_counts"].values()),
        "shadow_detected_learned_plan_difference": initial["shadow_after_learning"]["differences"] == ["PLAN_STEPS_DIFFER"],
        "owner_changes_once": initial["owner"]["actor"] == "legacy_simulator" and next_run["owner"] == recovered["owner"]
            and recovered["owner"] == {"actor": "core_simulator", "epoch": 2, "scope": "synthetic_only"},
        "grants_unchanged": initial["grants"] == next_run["grants"] == recovered["grants"],
        "no_duplicate_side_effects": recovered["world_counts"]["effects"] == 3 and recovered["world_counts"]["execute_calls"] == 8,
        "experience_executes_new_read": recovered["world_counts"]["locate_calls"] == 2 and sum(bool(c["locator"]) for c in cards) == 2,
        "crash_recovered_by_verify_without_replan": "DISPATCHING" in recovered["states_before_recovery"]
            and recovered["model_calls_this_process"] == 0 and all(a["state"] == "SUCCEEDED" for a in recovered["actions"]),
        "full_replay_consistency": recovered["full_replay_equal_except_quarantine"],
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    report = {"provenance": "synthetic_only", "engineering_gate": "PASS", "E12": "NOT_RUN",
        "production_migration": "NOT_RUN", "real_model_calls": 0, "external_fees": 0, "checks": checks,
        "processes": {"initial": initial["pid"], "next": next_run["pid"], "killed": killed["marker"]["pid"], "recover": recovered["pid"]},
        "identity": recovered["identity"], "owner_before": initial["owner"], "owner_after": recovered["owner"],
        "legacy_imports": imports, "shadow_after_learning": initial["shadow_after_learning"],
        "crash": killed, "states_before_recovery": recovered["states_before_recovery"],
        "action_states_after_recovery": [a["state"] for a in recovered["actions"]],
        "world_counts": recovered["world_counts"], "cards": cards,
        "interpretation": "simulated legacy actor uses existing ActionKernel; not production host parity or takeover"}
    (root / "migration_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--session", choices=["initial", "next", "crash", "recover"], help=argparse.SUPPRESS)
    args = parser.parse_args()
    result = _session(args.output, args.session) if args.session else run_experiment(args.output)
    print(canonical(result))


if __name__ == "__main__":
    main()
