"""Reproducible offline experiment using separate processes and separate world databases.

Run: python -m nana_core.experiment --output /tmp/nana-v1-run
Only synthetic data and engineering ModelPort fixtures are used.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
from .actions import ActionKernel, OperatorAuthority
from .clock import ManualClock
from .contracts import Feedback, GrantSpec, Observation
from .experience import ExperienceEngine
from .fake_world import CAPABILITIES, VERIFY_CAPABILITY, FakeWorld
from .planning import FixtureModel
from .runtime import Runtime
from .storage import Store, canonical, digest

SOURCE = "source://synthetic/garden"
CARD1 = "notebook://synthetic/card-1"
CARD2 = "notebook://synthetic/card-2"


def _write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _summary(store, world):
    return {"pid": os.getpid(), "identity": store.identity, "world_counts": world.counts(),
        "goals": store.all("goals"), "plans": [json.loads(p["body_json"]) for p in store.all("plans")],
        "actions": store.all("actions"), "attempts": store.all("attempts"),
        "strategies": store.all("strategies"), "grants": store.all("grants"),
        "budgets": store.all("budgets"), "memories": store.all("memory_items"),
        "events": store.all("events"), "decisions": [json.loads(d["body_json"]) for d in store.all("decisions")],
        "cards": [dict(row) for row in world.db.execute("SELECT * FROM cards ORDER BY resource")],
        "artifacts": [{"artifact_id": r["artifact_id"], "sha256": r["sha256"],
            "bytes": len(r["payload"]) if r["payload"] else 0} for r in store.all("artifacts")]}


def _session(directory, phase, seed):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    clock = ManualClock()
    authority = OperatorAuthority()
    with Store(directory / "nana.db", clock) as store:
        world = FakeWorld(directory / "fake_world.db")
        try:
            kernel = ActionKernel(store, world, authority)
            runtime = Runtime(store, kernel, FixtureModel())
            engine = ExperienceEngine(store, kernel)
            if phase in {"initial", "crash_setup"}:
                world.seed_source(SOURCE, [{"text": f"A synthetic reader finds garden number {seed} beside a quiet stream.",
                    "locator": f"page {seed * 7 + 3}, paragraph {seed % 4 + 1}"}])
                kernel.set_budgets({"write_attempts": 8, "external_requests": 100, "cost_micro_units": 100}, authority)
                kernel.grant(GrantSpec(capabilities=tuple(sorted(CAPABILITIES | {VERIFY_CAPABILITY})),
                    resources=(SOURCE, CARD1, CARD2), not_before_us=clock.utc_now_us(),
                    expires_at_us=clock.utc_now_us() + 3_600_000_000), authority)
            if phase == "initial":
                goal = runtime.process(Observation(source_namespace="synthetic.reading", object_id=f"reading-{seed}-1",
                    raw_text=f"Synthetic reader {seed} was interrupted and may enjoy a private reading card.",
                    occurred_at="2026-10-01T09:00:00+08:00", source_id=SOURCE, card_resource=CARD1))
                engine.learn(Feedback(goal_id=goal, text="Synthetic feedback: next time include the original passage location.",
                    requested_fields=("locator",)), authority)
            elif phase in {"next", "without"}:
                if phase == "without":
                    for strategy in store.all("strategies"):
                        if strategy["status"] == "ACTIVE":
                            engine.retire(strategy["strategy_id"], authority)
                runtime.resume()
                runtime.process(Observation(source_namespace="synthetic.reading", object_id=f"reading-{seed}-2",
                    raw_text=f"Synthetic reader {seed} resumes another interrupted reading session.",
                    occurred_at="2026-10-02T09:00:00+08:00", source_id=SOURCE, card_resource=CARD2))
            elif phase == "crash_setup":
                source = world.db.execute("SELECT text FROM sources WHERE source_id=?", (SOURCE,)).fetchone()[0]
                action = kernel.propose("reading.card.create", CARD1, {"source_id": SOURCE,
                    "source_digest": digest(source.encode()), "content": source, "locator": None})
                kernel.prepare(action)
            elif phase == "crash":
                action = next(a for a in store.all("actions") if a["state"] == "READY")
                def fault(point):
                    if point == "after_effect":
                        print(canonical({"fault": point, "pid": os.getpid(), "action_id": action["action_id"]}), flush=True)
                        os.kill(os.getpid(), signal.SIGKILL)
                kernel.dispatch(action["action_id"], fault=fault)
            elif phase == "recover":
                before = [a["state"] for a in store.all("actions")]
                recovered = kernel.recover()
                result = _summary(store, world)
                result.update({"states_before_recovery": before, "recovery": recovered})
                return result
            return _summary(store, world)
        finally:
            world.close()


def _child(directory, phase, seed, allow_crash=False):
    # Do not forward account credentials or private configuration to experiment processes.
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
           "PYTHONDONTWRITEBYTECODE": "1"}
    child = subprocess.run([sys.executable, "-m", "nana_core.experiment", "--session", phase,
        "--output", str(directory), "--seed", str(seed)], env=env, capture_output=True, text=True, timeout=30)
    if allow_crash:
        if child.returncode != -signal.SIGKILL:
            raise RuntimeError(f"expected actual SIGKILL, got {child.returncode}: {child.stderr}")
        return {"returncode": child.returncode, "marker": json.loads(child.stdout), "stderr": child.stderr}
    if child.returncode != 0:
        raise RuntimeError(f"session {phase} failed: {child.stderr}")
    return json.loads(child.stdout)


def run_experiment(output, seed=1):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    reference, control = root / "reference", root / "control"
    before = _child(reference, "initial", seed)
    if not all(a["state"] == "SUCCEEDED" for a in before["actions"]):
        raise RuntimeError("controlled experiment fork requires fully resolved prior actions")
    control.mkdir()
    # This is a synthetic experimental branch, not a production restore path.
    # The source process exited; SQLite closed/checkpointed both independent DBs.
    hashes = {}
    for name in ("nana.db", "fake_world.db"):
        if Path(str(reference / name) + "-wal").exists():
            raise RuntimeError("cannot copy an uncheckpointed experimental database")
        shutil.copy2(reference / name, control / name)
        hashes[name] = digest((reference / name).read_bytes())
        if hashes[name] != digest((control / name).read_bytes()):
            raise RuntimeError("experimental branch snapshot mismatch")
    after = _child(reference, "next", seed)
    ablated = _child(control, "without", seed)
    treatment_plan, control_plan = after["plans"][-1], ablated["plans"][-1]
    treatment_card = json.loads(next(c for c in after["cards"] if c["resource"] == CARD2)["content_json"])
    control_card = json.loads(next(c for c in ablated["cards"] if c["resource"] == CARD2)["content_json"])
    assertions = {
        "same_identity_across_processes": before["identity"] == after["identity"] == ablated["identity"],
        "actual_process_restart": before["pid"] != after["pid"],
        "historical_events_preserved": after["events"][:len(before["events"])] == before["events"],
        "matched_raw_proposal": after["decisions"][-1]["proposal"] == ablated["decisions"][-1]["proposal"],
        "matched_initial_plan": treatment_plan["before"] == control_plan["before"],
        "learning_did_not_change_grants": before["grants"] == after["grants"] == ablated["grants"],
        "experience_cited": bool(treatment_plan["applied_strategies"]) and not control_plan["applied_strategies"],
        "plan_changed": len(treatment_plan["steps"]) == len(control_plan["steps"]) + 1,
        "actual_new_read": after["world_counts"]["locate_calls"] == 1 and ablated["world_counts"]["locate_calls"] == 0,
        "requested_field_present": bool(treatment_card["locator"]) and control_card["locator"] is None,
        "same_number_of_cards": after["world_counts"]["effects"] == ablated["world_counts"]["effects"] == 2,
        "all_actions_verified": all(a["state"] == "SUCCEEDED" for a in after["actions"] + ablated["actions"]),
    }
    if not all(assertions.values()):
        raise AssertionError(assertions)
    crash_dir = root / "crash"
    prepared = _child(crash_dir, "crash_setup", seed)
    killed = _child(crash_dir, "crash", seed, allow_crash=True)
    recovered = _child(crash_dir, "recover", seed)
    crash_ok = (recovered["states_before_recovery"] == ["DISPATCHING"]
        and list(recovered["recovery"].values()) == ["SUCCEEDED"]
        and recovered["world_counts"]["effects"] == recovered["world_counts"]["execute_calls"] == 1)
    if not crash_ok:
        raise AssertionError("lost-receipt recovery failed")
    _write(root / "identity_snapshot_before.json", before["identity"])
    _write(root / "identity_snapshot_after.json", after["identity"])
    _write(root / "event_trace.json", after["events"])
    _write(root / "action_recovery_trace.json", {"prepared": prepared["actions"], "killed": killed,
        "before_recovery": recovered["states_before_recovery"], "after_recovery": recovered["actions"],
        "attempts": recovered["attempts"], "world_counts": recovered["world_counts"], "passed": crash_ok})
    _write(root / "learning_ablation.json", {"assertions": assertions, "fork_hashes": hashes,
        "with_experience": {"plan": treatment_plan, "counts": after["world_counts"], "card": treatment_card},
        "without_experience": {"plan": control_plan, "counts": ablated["world_counts"], "card": control_card},
        "interpretation": "causal compiler/behavior evidence with engineering fixtures, not real-model semantics"})
    _write(root / "dependency_manifest.json", {"python": sys.version, "sqlite": sqlite3.sqlite_version,
        "pydantic": importlib.metadata.version("pydantic"), "schema_version": 1,
        "model": "engineering-fixture-v1", "real_model_calls": 0, "external_service_calls": 0,
        "real_service_cost": 0, "budget_units": "simulation only"})
    manifest = {"seed": seed, "passed": True, "assertions": assertions,
        "processes": {"initial": before["pid"], "restarted": after["pid"], "control": ablated["pid"],
                      "killed": killed["marker"]["pid"], "recovering": recovered["pid"]},
        "crash_recovery_passed": crash_ok, "S5": "NOT_RUN",
        "evidence": [p.name for p in sorted(root.glob("*.json"))]}
    _write(root / "experiment_manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--session", choices=["initial", "next", "without", "crash_setup", "crash", "recover"], help=argparse.SUPPRESS)
    args = parser.parse_args()
    result = _session(args.output, args.session, args.seed) if args.session else run_experiment(args.output, args.seed)
    print(canonical(result))


if __name__ == "__main__":
    main()
