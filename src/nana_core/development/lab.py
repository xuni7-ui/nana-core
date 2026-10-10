"""Sequential development lab: real file reads, synthetic notebook, optional ModelPort.

No endpoint config means engineering FixtureModel, not semantic verification.
For E12 use the existing frozen-snapshot nana-semantic evaluator separately.
"""
import argparse
import json
import os
from pathlib import Path
from ..actions import ActionKernel, OperatorAuthority
from ..clock import ManualClock
from ..contracts import CAPABILITIES, CoreError, Feedback, GrantSpec, Observation, VERIFY_CAPABILITY
from ..experience import ExperienceEngine
from ..fake_world import FakeWorld
from ..migration.routing import CapabilityRouter
from ..planning import FixtureModel
from ..runtime import Runtime
from ..semantic.contracts import EvaluationCase, load_run_config
from ..semantic.evaluation import assess_reply
from ..semantic.model_port import CallLedger, CompatibleModelPort
from ..semantic.snapshot import model_continuity, write_json
from ..storage import Store, digest
from .file_source import FileSourcePort, SourceBinding, SourceDocument

SOURCE = "source://synthetic/development/paper-garden"
CARDS = ("notebook://synthetic/development/first", "notebook://synthetic/development/next")


def run(output, config_path=None):
    root = Path(output).absolute()
    config = load_run_config(config_path)
    # No fallback to production docs, global credentials, or this assistant.
    if any(e.credential_env and not os.environ.get(e.credential_env) for e in config.endpoints):
        raise CoreError("MODEL_DEVELOPMENT_BINDING_MISSING")
    root.mkdir(parents=True, exist_ok=False)
    source_root = root / "synthetic_sources"
    source_root.mkdir()
    document = SourceDocument(synthetic_only=True,
        text="A fictional gardener grows a blue paper telescope.\nAll characters and events are invented.",
        locator="synthetic folio 3, page 9, paragraph 2")
    raw = document.model_dump_json(indent=2).encode()
    (source_root / "paper.json").write_bytes(raw)
    blob_hash = digest(raw)
    binding = SourceBinding(synthetic_only=True, relative_path="paper.json", blob_sha256=blob_hash)
    clock = ManualClock()
    ledger_scope = {"mode": "development_synthetic_only", "source_blob_sha256": blob_hash,
                    "config_hash": digest(config.model_dump())}
    phases, initial_identity, initial_grants = [], None, None
    learned_strategy_ids = []
    file_counts = {"execute_reads": 0, "verify_reads": 0}
    for index, card in enumerate(CARDS):
        authority = OperatorAuthority("synthetic-development-operator")
        with Store(root / "nana.db", clock) as store:
            world = FakeWorld(root / "world.db")
            files = FileSourcePort(source_root, {SOURCE: binding}, world)
            ledger = None
            try:
                if index == 0:
                    # Notebook remains fake; its source cache is setup data only.
                    world.seed_source(SOURCE, [{"text": document.text, "locator": document.locator}])
                router = CapabilityRouter(store, {"reading.source.read": files,
                    "reading.source.locate": files, "reading.card.create": world}, authority)
                router.select_owner("core_simulator", authority)
                kernel = ActionKernel(store, router.bind("core_simulator", authority), authority)
                if index == 0:
                    kernel.set_budgets({"write_attempts": 2, "external_requests": 20, "cost_micro_units": 20}, authority)
                    kernel.grant(GrantSpec(capabilities=tuple(sorted(CAPABILITIES | {VERIFY_CAPABILITY})),
                        resources=(SOURCE, *CARDS), not_before_us=clock.utc_now_us(),
                        expires_at_us=clock.utc_now_us() + 3_600_000_000), authority)
                    initial_identity, initial_grants = store.identity, store.all("grants")
                case = EvaluationCase(case_id=f"synthetic-development-{index}", kind="reading",
                    raw_text=f"A fictional reader pauses chapter {index+1}; prepare a private reading card.",
                    source_id=SOURCE, card_resource=card, occurred_at=f"2026-09-0{index+1}T09:00:00Z")
                prefix = store.all("events")
                observation = Observation(source_namespace="synthetic.development", object_id=case.case_id,
                    raw_text=case.raw_text, occurred_at=case.occurred_at, source_id=SOURCE, card_resource=card)
                store.ingest(observation)
                continuity = model_continuity(store, {"event_prefix": prefix})
                endpoint = config.endpoints[min(index, len(config.endpoints)-1)] if config.endpoints else None
                if endpoint:
                    ledger = CallLedger(root / "model_calls.db", config.budget, ledger_scope)
                    model = CompatibleModelPort(endpoint, ledger, continuity, case, "development")
                else:
                    model = FixtureModel()
                runtime = Runtime(store, kernel, model)
                goal = runtime.process(observation)
                for _ in range(5):
                    assert runtime.process(observation) == goal
                plan = next(p for p in store.all("plans") if p["goal_id"] == goal)
                compiled = json.loads(plan["body_json"])
                semantic = None
                if endpoint and model.last_reply:
                    decision = next(d for d in store.all("decisions") if d["goal_id"] == goal)
                    from ..contracts import ModelRequest
                    req = ModelRequest.model_validate_json(json.dumps(json.loads(decision["body_json"])["request"]))
                    semantic = assess_reply(model.last_reply, req, continuity, case)
                phases.append({"index": index, "identity": store.identity, "goal_state": store.one("goals", goal)["state"],
                    "plan": compiled, "world_counts": world.counts(), "model": model.descriptor,
                    "model_service_kind": endpoint.service_kind if endpoint else "fixture", "semantic_rubric": semantic,
                    "identity_equal": store.identity == initial_identity, "grants_unchanged": store.all("grants") == initial_grants})
                if index == 0 and store.one("goals", goal)["state"] == "COMPLETED":
                    _, learned_strategy_ids = ExperienceEngine(store, kernel).learn(Feedback(goal_id=goal,
                        text="Synthetic feedback: next time include original passage location.", requested_fields=("locator",)), authority)
                for key in file_counts:
                    file_counts[key] += files.counts[key]
            finally:
                if ledger:
                    ledger.close()
                files.close()
                world.close()
    ledger = CallLedger(root / "model_calls.db", config.budget, ledger_scope)
    try:
        summary = ledger.summary()
    finally:
        ledger.close()
    real_calls = [c for c in summary["calls"] if json.loads(c["context_json"]).get("service_kind") == "real_model"]
    applied_ids = {ref["strategy_id"] for ref in phases[-1]["plan"]["applied_strategies"]}
    locator_delta = phases[-1]["world_counts"]["locate_calls"] - phases[0]["world_counts"]["locate_calls"]
    experience_demonstrated = bool(learned_strategy_ids and set(learned_strategy_ids) <= applied_ids
                                  and locator_delta >= 1 and phases[0]["world_counts"]["locate_calls"] == 0)
    checks = {"same_identity": all(p["identity_equal"] for p in phases),
        "grants_unchanged": all(p["grants_unchanged"] for p in phases),
        "all_goals_completed": all(p["goal_state"] == "COMPLETED" for p in phases),
        "learned_locator_actually_read": experience_demonstrated,
        "no_duplicate_card": phases[-1]["world_counts"]["effects"] == 2,
        "source_file_unchanged": digest((source_root / "paper.json").read_bytes()) == blob_hash}
    report = {"schema_version": 1, "scope": "pinned synthetic filesystem reads; fake notebook; sequential Store reopen",
        "engineering_gate": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
        "phases": phases, "file_reads": file_counts, "model_ledger": summary,
        "experience_effect": {"gate": "DEMONSTRATED" if experience_demonstrated else "NOT_DEMONSTRATED",
            "learned_strategy_ids": learned_strategy_ids, "second_phase_locator_calls": locator_delta,
            "note": "A model that independently locates on the first event does not demonstrate an experience-caused change."},
        "real_model_attempts": len(real_calls), "E12": "NOT_RUN",
        "external_model_fees": 0 if not summary["calls"] or all(
            json.loads(c["context_json"]).get("service_kind") == "protocol_simulator" for c in summary["calls"]) else None,
        "actual_provider_billing_verified": False, "production_calls": 0,
        "note": "This lab is not the frozen two-model heldout semantic gate; use nana-semantic for E12."}
    write_json(root / "development_report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", help="existing S5 RunConfig; no credential values")
    args = parser.parse_args()
    report = run(args.output, args.config)
    print(json.dumps({key: report[key] for key in ("engineering_gate", "file_reads", "real_model_attempts", "E12")}))
    if report["engineering_gate"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
