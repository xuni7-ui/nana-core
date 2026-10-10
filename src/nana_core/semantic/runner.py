"""Prepare and sequentially evaluate S5. Default execution performs zero model calls.

python -m nana_core.semantic.runner prepare --output /tmp/nana-s5-snapshot
python -m nana_core.semantic.runner evaluate --snapshot /tmp/nana-s5-snapshot --output /tmp/nana-s5-run
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from ..actions import ActionKernel, OperatorAuthority
from ..clock import ManualClock
from ..contracts import CoreError, ModelRequest, Observation
from ..experience import ExperienceEngine
from ..fake_world import FakeWorld
from ..planning import ContextBuilder
from ..runtime import Runtime
from ..storage import Store, canonical, digest
from .contracts import EvaluationCase, RunConfig
from .evaluation import aggregate, assess_behavior, assess_reply
from .model_port import CallLedger, CompatibleModelPort
from .snapshot import fork_snapshot, model_continuity, prepare_snapshot, verify_snapshot, write_json


def execute_case(snapshot, output, case, arm, model_factory):
    """One fresh branch/session per arm. Factory injection is for engineering tests."""
    _, frozen = fork_snapshot(snapshot, output)
    clock, authority = ManualClock(), OperatorAuthority("synthetic-s5-operator")
    with Store(Path(output) / "nana.db", clock) as store:
        world = FakeWorld(Path(output) / "fake_world.db")
        try:
            if (store.identity != frozen["identity"] or store.all("events") != frozen["event_prefix"]
                or any(a["state"] != "SUCCEEDED" for a in store.all("actions"))):
                raise CoreError("FROZEN_STATE_MISMATCH")
            kernel = ActionKernel(store, world, authority)
            if arm == "without":
                for strategy in store.all("strategies"):
                    if strategy["status"] == "ACTIVE":
                        ExperienceEngine(store, kernel).retire(strategy["strategy_id"], authority)
            elif arm != "with":
                raise CoreError("INVALID_EXPERIMENT_ARM")
            observation = Observation(source_namespace="synthetic.s5.heldout", object_id=case.case_id,
                kind=case.kind, raw_text=case.raw_text, occurred_at=case.occurred_at,
                source_id=case.source_id, card_resource=case.card_resource)
            event_id = store.ingest(observation)
            if case.kind == "reading":
                request, _ = ContextBuilder(store).build(event_id)
            else:
                request = ModelRequest(identity_id=store.identity["identity_id"], identity_revision=store.identity["revision"],
                    identity_snapshot=json.loads(store.identity["body_json"]), event_id=event_id,
                    event_text=case.raw_text, source_id=case.source_id, card_resource=case.card_resource)
            continuity = model_continuity(store, frozen)
            model = model_factory(continuity, case, arm)
            goal_id, failure = None, None
            try:
                if case.kind == "unrelated":
                    model.assess(request)
                else:
                    goal_id = Runtime(store, kernel, model).process(observation)
            except CoreError as exc:
                failure = exc.code
            reply = model.last_reply
            semantic = assess_reply(reply, request, continuity, case) if reply else {
                "passed": False, "checks": {}, "error": failure or "NO_VALID_MODEL_REPLY"}
            behavior = assess_behavior(store, world, frozen, case, goal_id, arm)
            return {"pid": os.getpid(), "case_id": case.case_id, "arm": arm,
                "alias": model.endpoint.alias, "provenance": "real_http" if model.transport.is_real_transport else "transport_fixture",
                "model_descriptor": model.descriptor, "call_id": model.last_call_id,
                "raw_proposal": reply.proposal.model_dump() if reply and reply.proposal else None,
                "semantic": semantic, "behavior": behavior, "error": failure,
                "request_identity": {"id": request.identity_id, "revision": request.identity_revision,
                                     "body": request.identity_snapshot}}
        finally:
            world.close()


def _worker(job_path):
    job = json.loads(Path(job_path).read_text())
    config = RunConfig.model_validate_json(Path(job["config"]).read_text())
    endpoint = next(e for e in config.endpoints if e.alias == job["alias"])
    ledger = CallLedger(job["ledger"], config.budget, job["scope"])
    try:
        result = execute_case(job["snapshot"], job["branch"], EvaluationCase.model_validate_json(canonical(job["case"])),
            job["arm"], lambda continuity, case, arm: CompatibleModelPort(endpoint, ledger, continuity, case, arm))
        calls = ledger.summary()["calls"]
        call = next((c for c in calls if c["call_id"] == result["call_id"]), None)
        result["provider_model"] = (call["evidence"] or {}).get("provider_model") if call else None
        write_json(job["result"], result)
    finally:
        ledger.close()


def evaluate(snapshot, output, config_path=None):
    snapshot, output = Path(snapshot).resolve(), Path(output).resolve()
    manifest, frozen = verify_snapshot(snapshot)
    config = RunConfig.model_validate_json(Path(config_path).read_text()) if config_path else RunConfig()
    output.mkdir(parents=True, exist_ok=False)
    actual_config = output / "run_config.json"
    write_json(actual_config, config.model_dump())  # no credential values, no secret files
    scope = {"snapshot_hash": digest(manifest), "config_hash": digest(config.model_dump()), "mode": "S5_synthetic_only"}
    ledger_path = output / "model_calls.db"
    ledger = CallLedger(ledger_path, config.budget, scope)
    ledger.close()
    ready, blockers, results = [], [], []
    for endpoint in config.endpoints:
        if endpoint.credential_env and not os.environ.get(endpoint.credential_env):
            blockers.append(f"{endpoint.alias}: dedicated development binding not injected")
        else:
            ready.append(endpoint)
    declared_real = sum(e.service_kind == "real_model" for e in ready)
    if declared_real < 2:
        blockers.append(f"only {declared_real} ready declared real ModelPort(s); two distinct real models required for E12")
    if not ready:
        blockers.append("historical production endpoint documentation and this assistant are not usable development ModelPorts")
    halted = False
    # Each subprocess opens exactly one runtime, executes once, then exits. No
    # two complete runtimes/Models resident together. Same snapshot for all cells.
    for endpoint in ready:
        for case_data in frozen["cases"]:
            for arm in ("with", "without"):
                if halted:
                    break
                index = len(results)
                job = {"snapshot": str(snapshot), "branch": str(output / f"branch-{index}"),
                    "ledger": str(ledger_path), "config": str(actual_config), "alias": endpoint.alias,
                    "scope": scope, "case": case_data, "arm": arm, "result": str(output / f"result-{index}.json")}
                job_path = output / f"job-{index}.json"
                write_json(job_path, job)
                # Forward only the selected development binding and inherited
                # proxy/CA setup; never production credentials/private config.
                env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
                       "PYTHONDONTWRITEBYTECODE": "1"}
                for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy",
                             "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE"):
                    if name in os.environ:
                        env[name] = os.environ[name]
                if endpoint.credential_env:
                    env[endpoint.credential_env] = os.environ[endpoint.credential_env]
                try:
                    child = subprocess.run([sys.executable, "-m", "nana_core.semantic.runner", "_worker", str(job_path)],
                        env=env, capture_output=True, timeout=endpoint.timeout_seconds + 20)
                except subprocess.TimeoutExpired:
                    blockers.append("worker deadline exceeded; uncertain attempt is retained, suite halted without retry")
                    halted = True
                    break
                if child.returncode != 0:
                    # Do not expose child stderr: a malformed operator config may
                    # contain values. The ledger and exit code suffice for triage.
                    blockers.append(f"worker exit {child.returncode}; no automatic retry")
                    halted = True
                    break
                result = json.loads(Path(job["result"]).read_text())
                results.append(result)
                if result["error"] in {"MODEL_TRANSPORT_UNCERTAIN", "MODEL_CALL_UNRESOLVED", "MODEL_BUDGET_EXHAUSTED",
                                       "MODEL_PROVIDER_BUDGET_VIOLATION"}:
                    blockers.append(result["error"] + "; suite halted without retry")
                    halted = True
    ledger = CallLedger(ledger_path, config.budget, scope)
    try:
        report = aggregate(results, ledger.summary(), blockers, scope["snapshot_hash"], len(frozen["cases"]), len(ready))
    finally:
        ledger.close()
    if verify_snapshot(snapshot)[0] != manifest:
        raise CoreError("FROZEN_SNAPSHOT_CHANGED")
    report["snapshot_unchanged"] = True
    report["sequential_processes"] = [r["pid"] for r in results]
    write_json(output / "semantic_report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output", required=True)
    prepare.add_argument("--seed", type=int, default=57)
    run = sub.add_parser("evaluate")
    run.add_argument("--snapshot", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--config")
    worker = sub.add_parser("_worker", help=argparse.SUPPRESS)
    worker.add_argument("job")
    args = parser.parse_args()
    if args.command == "_worker":
        _worker(args.job)
        return
    if args.command == "prepare":
        result = prepare_snapshot(args.output, args.seed)
    else:
        report = evaluate(args.snapshot, args.output, args.config)
        result = {k: report[k] for k in ("semantic_gate", "E12", "real_model_attempts", "provider_models", "blockers")}
    print(canonical(result))
    if args.command == "evaluate" and result["semantic_gate"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
