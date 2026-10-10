import json
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.semantic.contracts import Endpoint, EvaluationCase, ModelBudget
from nana_core.semantic.evaluation import aggregate
from nana_core.semantic.model_port import CallLedger, CompatibleModelPort
from nana_core.semantic.runner import evaluate, execute_case
from nana_core.semantic.snapshot import prepare_snapshot, verify_snapshot
from nana_core.storage import canonical, digest
from .helpers import ScriptedTransport

pytestmark = pytest.mark.s5


@pytest.fixture
def frozen(tmp_path):
    root = tmp_path / "snapshot"
    prepare_snapshot(root, seed=67)
    return root


def test_frozen_snapshot_identity_history_and_heldout_cases(frozen):
    manifest, summary = verify_snapshot(frozen)
    assert len(summary["cases"]) == 4 and len(summary["strategies"]) == 1
    assert summary["strategies"][0]["status"] == "ACTIVE"
    raw_history = canonical(summary["event_prefix"])
    for case in summary["cases"]:
        # Heldout observations never participated in the training history.
        assert case["raw_text"] not in raw_history
        assert case["source_id"] != summary["training_source"]
    assert manifest["files"]["nana.db"] == digest((frozen / "nana.db").read_bytes())


def test_tampered_snapshot_and_overwrite_are_rejected(frozen):
    with pytest.raises(FileExistsError):
        prepare_snapshot(frozen)
    with (frozen / "nana.db").open("ab") as file:
        file.write(b"synthetic tampering")
    with pytest.raises(CoreError, match="SNAPSHOT_HASH_MISMATCH"):
        verify_snapshot(frozen)


def test_default_runner_reports_no_real_models_and_does_not_fake_pass(frozen, tmp_path):
    before = verify_snapshot(frozen)
    report = evaluate(frozen, tmp_path / "report")
    assert report["semantic_gate"] == report["E12"] == "NOT_RUN"
    assert report["real_model_attempts"] == 0 and report["provider_models"] == []
    assert report["fees"]["actual_external_cost"] == 0
    assert report["blockers"] and report["snapshot_unchanged"]
    assert verify_snapshot(frozen) == before


def test_missing_development_binding_is_reported_without_network(frozen, tmp_path, monkeypatch):
    monkeypatch.delenv("NANA_S5_DEV_UNAVAILABLE", raising=False)
    config = {"endpoints": [{"alias": "a", "base_url": "https://example.invalid/v1", "model": "dev-model",
        "account_scope": "development", "funding": "existing_quota", "credential_env": "NANA_S5_DEV_UNAVAILABLE"}]}
    path = tmp_path / "config.json"
    path.write_text(canonical(config))
    report = evaluate(frozen, tmp_path / "missing-binding", path)
    assert report["E12"] == "NOT_RUN" and report["real_model_attempts"] == 0
    assert any("not injected" in b for b in report["blockers"])


@pytest.mark.parametrize("case_index", [0, 1, 2, 3])
def test_same_frozen_identity_and_scoped_behavior_in_both_arms(frozen, tmp_path, case_index):
    manifest, summary = verify_snapshot(frozen)
    case = EvaluationCase.model_validate_json(canonical(summary["cases"][case_index]))
    ledger = CallLedger(tmp_path / "calls.db", ModelBudget(), {"snapshot": digest(manifest)})
    endpoint = Endpoint(alias="a", base_url="http://127.0.0.1:9999/v1", model="fixture-only",
        account_scope="local_offline", funding="local_offline")
    try:
        results = []
        for arm in ("with", "without"):
            factory = lambda continuity, case, arm: CompatibleModelPort(endpoint, ledger, continuity, case, arm, ScriptedTransport())
            result = execute_case(frozen, tmp_path / arm, case, arm, factory)
            assert result["semantic"]["passed"], result
            assert result["behavior"]["passed"], result
            assert result["provenance"] == "transport_fixture"
            results.append(result)
        assert results[0]["request_identity"] == results[1]["request_identity"]
        assert verify_snapshot(frozen)[0] == manifest
        if case_index in (0, 2):
            assert results[0]["behavior"]["world_counts"]["locate_calls"] == 1
            assert results[1]["behavior"]["world_counts"]["locate_calls"] == 0
        if case_index == 1:
            assert results[0]["behavior"]["goal_state"] == "BLOCKED"
        report = aggregate(results, ledger.summary(), [], digest(manifest), 4, 2)
        assert report["E12"] == report["semantic_gate"] == "NOT_RUN"
        assert report["real_model_attempts"] == 0
    finally:
        ledger.close()


def test_compiler_compensation_cannot_pass_model_understanding(frozen, tmp_path):
    manifest, summary = verify_snapshot(frozen)
    case = EvaluationCase.model_validate_json(canonical(summary["cases"][0]))
    ledger = CallLedger(tmp_path / "calls.db", ModelBudget(), {})
    endpoint = Endpoint(alias="a", base_url="http://127.0.0.1:9999/v1", model="fixture-only",
        account_scope="local_offline", funding="local_offline")
    try:
        result = execute_case(frozen, tmp_path / "branch", case, "with", lambda context, case, arm:
            CompatibleModelPort(endpoint, ledger, context, case, arm, ScriptedTransport(omit_learned_step=True)))
        assert result["behavior"]["passed"]
        assert not result["semantic"]["passed"]
        assert not result["semantic"]["checks"]["learned_step_in_raw_plan"]
        assert result["behavior"]["world_counts"]["locate_calls"] == 1
    finally:
        ledger.close()


def test_model_identity_drift_is_reported_without_rewriting_state(frozen, tmp_path):
    _, summary = verify_snapshot(frozen)
    case = EvaluationCase.model_validate_json(canonical(summary["cases"][0]))
    ledger = CallLedger(tmp_path / "calls.db", ModelBudget(), {})
    endpoint = Endpoint(alias="a", base_url="http://127.0.0.1:9999/v1", model="fixture-only",
        account_scope="local_offline", funding="local_offline")
    try:
        def drift(reply): reply["identity"]["identity_id"] = "invented-new-identity"
        result = execute_case(frozen, tmp_path / "branch", case, "with", lambda context, case, arm:
            CompatibleModelPort(endpoint, ledger, context, case, arm, ScriptedTransport(mutate=drift)))
        assert result["behavior"]["checks"]["persistent_identity_equal"]
        assert not result["semantic"]["checks"]["identity_id_preserved"]
    finally:
        ledger.close()


def test_one_ready_model_is_only_partial_even_if_rubric_passes():
    result = {"provenance": "real_http", "provider_model": "model-a", "alias": "a", "case_id": "synthetic",
        "arm": "with", "call_id": "hypothetical", "semantic": {"passed": True}, "behavior": {"passed": True}}
    calls = [{"call_id": "hypothetical", "context_json": canonical({"provenance": "real_http", "service_kind": "real_model"}),
        "state": "COMPLETED", "evidence": {"provider_model": "model-a"}}]
    report = aggregate([result], {"calls": calls, "attempts": 1}, ["second missing"], "frozen", 4, 1)
    assert report["E12"] == "PARTIAL"


def test_claimed_real_results_without_call_evidence_cannot_pass():
    result = {"provenance": "real_http", "provider_model": "model-a", "alias": "a", "case_id": "synthetic",
        "arm": "with", "call_id": "invented", "semantic": {"passed": True}, "behavior": {"passed": True}}
    report = aggregate([result] * 16, {"calls": [], "attempts": 0}, [], "frozen", 4, 2)
    assert report["E12"] == "NOT_RUN" and report["real_model_attempts"] == 0


def test_failed_real_attempt_is_not_marked_not_run():
    calls = [{"call_id": "hypothetical", "context_json": canonical({"provenance": "real_http", "service_kind": "real_model"}),
        "state": "FAILED", "evidence": {"error": "rejected"}}]
    report = aggregate([], {"calls": calls, "attempts": 1}, [], "frozen", 4, 2)
    assert report["E12"] == "FAIL" and report["real_model_attempts"] == 1
    assert report["fees"]["actual_external_cost"] is None


def test_sequential_actual_process_runner_cannot_label_transport_fixtures_real(frozen, tmp_path, monkeypatch):
    """16 real child processes, scripted HTTP, zero real models/network calls."""
    import os
    import subprocess
    from nana_core.semantic import runner
    config = {"schema_version": 1, "endpoints": [{"alias": alias,
        "base_url": "http://127.0.0.1:9999/v1", "model": "fixture-" + alias,
        "account_scope": "local_offline", "funding": "local_offline"} for alias in ("a", "b")]}
    config_path = tmp_path / "synthetic_config.json"
    config_path.write_text(canonical(config))
    original_run = subprocess.run
    script = """
import sys
from helpers import ScriptedTransport
from nana_core.semantic import runner
from nana_core.semantic.model_port import CompatibleModelPort
def fixture_port(endpoint,ledger,context,case,arm):
    return CompatibleModelPort(endpoint,ledger,context,case,arm,ScriptedTransport())
runner.CompatibleModelPort=fixture_port
runner._worker(sys.argv[1])
"""
    started = []
    def fixture_worker(command, **kwargs):
        # Only transport replacement; all actual runner/storage/Kernel paths used.
        env = dict(kwargs["env"])
        env["PYTHONPATH"] += os.pathsep + str(Path(__file__).parent)
        kwargs["env"] = env
        result = original_run([command[0], "-c", script, command[-1]], **kwargs)
        assert result.returncode == 0, result.stderr
        started.append(command[-1])
        return result
    monkeypatch.setattr(runner.subprocess, "run", fixture_worker)
    report = evaluate(frozen, tmp_path / "sequential", config_path)
    assert len(started) == len(report["results"]) == 16
    assert len(set(report["sequential_processes"])) == 16
    assert report["ledger"]["attempts"] == 16
    assert report["real_model_attempts"] == 0 and report["E12"] == "NOT_RUN"
    assert all(r["semantic"]["passed"] and r["behavior"]["passed"] for r in report["results"])
    assert report["fees"]["actual_external_cost"] == 0
    # Emit only compact, explicitly engineering evidence for the official test run.
    proof = {"provenance": "transport_fixture", "real_model_attempts": 0, "E12": "NOT_RUN",
        "snapshot_hash": report["snapshot_hash"], "sequential_processes": report["sequential_processes"],
        "results": [{"case_id": r["case_id"], "alias": r["alias"], "arm": r["arm"],
            "identity": r["request_identity"], "semantic_rubric_checks": r["semantic"]["checks"],
            "behavior_checks": r["behavior"]["checks"], "goal_state": r["behavior"]["goal_state"],
            "world_counts": r["behavior"]["world_counts"]} for r in report["results"]],
        "contrasts": report["experience_contrasts"]}
    proof_path = os.environ.get("NANA_S5_ENGINEERING_PROOF")
    if proof_path:
        Path(proof_path).write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n")
