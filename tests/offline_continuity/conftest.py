import socket
import json
from pathlib import Path
import pytest
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import GrantSpec
from nana_core.fake_world import CAPABILITIES, VERIFY_CAPABILITY, FakeWorld
from nana_core.storage import Store, digest

SOURCE = "source://synthetic/garden"
CARD = "notebook://synthetic/card-1"
PARAGRAPHS = [{"text": "A quiet fictional garden grows beside a stream.", "locator": "page 7, paragraph 2"}]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline test attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def environment(tmp_path):
    clock = ManualClock()
    store = Store(tmp_path / "nana.db", clock)
    world = FakeWorld(tmp_path / "fake_world.db")
    world.seed_source(SOURCE, PARAGRAPHS)
    authority = OperatorAuthority()
    kernel = ActionKernel(store, world, authority)
    kernel.set_budgets({"write_attempts": 10, "external_requests": 100, "cost_micro_units": 100}, authority)
    yield store, world, kernel, authority, clock
    world.close()
    store.close()


def authorize(kernel, authority, clock, resources=(SOURCE, CARD), capabilities=None, ttl=10_000_000):
    return kernel.grant(GrantSpec(capabilities=tuple(sorted(capabilities or CAPABILITIES | {VERIFY_CAPABILITY})),
        resources=tuple(resources), not_before_us=clock.utc_now_us(), expires_at_us=clock.utc_now_us() + ttl), authority)


def card_args(content="Synthetic reading card", locator=None):
    return {"source_id": SOURCE, "source_digest": digest(PARAGRAPHS[0]["text"].encode()),
            "content": content, "locator": locator}


ACCEPTANCE = {
    "E01": ["test_E01_E02_event_to_verified_card_once"],
    "E02": ["test_E01_E02_event_to_verified_card_once", "test_identity_time_raw_and_channel_dedup"],
    "E03": ["test_E03_E04_real_SIGKILL_recovery[after_effect]", "test_entire_goal_recovers_after_real_card_commit_SIGKILL"],
    "E04": ["test_E03_E04_real_SIGKILL_recovery[before_call]"],
    "E05": ["test_E05_no_grant_means_no_execution", "test_goal_can_be_proposed_without_execution_authority"],
    "E06": ["test_E06_recheck_after_reservation"],
    "E07": ["test_E07_attempt_budget_atomic_reservation", "test_E07_competing_processes_cannot_overreserve"],
    "E08": ["test_E08_unknown_does_not_refund_or_blind_retry"],
    "E09": ["test_identity_time_raw_and_channel_dedup", "test_invalid_or_naive_time_is_unknown", "test_utc_offset_preserved"],
    "E10": ["test_E10_untrusted_model_success_and_target_are_rejected", "test_model_cannot_change_authorized_plan_target"],
    "E11": ["test_E11_E13_E14_process_restart_and_behavioral_ablation", "test_identity_time_raw_and_channel_dedup"],
    "E12": ["test_E12_real_model_migration"],
    "E13": ["test_E13_E14_experience_changes_plan_and_actual_reads", "test_E11_E13_E14_process_restart_and_behavioral_ablation"],
    "E14": ["test_E11_E13_E14_process_restart_and_behavioral_ablation"],
    "E15": ["test_E15_learning_does_not_grant_added_read_permission", "test_E15_invalid_strategy_operations_are_rejected"],
    "E16": ["test_E16_scope_negative_and_E17_feedback_retraction", "test_E16_unrelated_event_has_no_goal"],
    "E17": ["test_E16_scope_negative_and_E17_feedback_retraction", "test_E17_invalidated_support_suspends_strategy"],
    "E18": ["test_E18_backup_quarantine_prevents_old_state_redispatch"],
    "E19": ["test_E19_full_projection_replay_after_learning", "test_append_only_and_pure_replay"],
    "E20": ["test_E20_wakes_are_deduplicated_and_not_autonomous_goals"],
}
RESULTS = {}


def pytest_addoption(parser):
    parser.addoption("--acceptance-report", default=None, help="Write actual test outcomes and E01-E20 matrix to this directory")


def pytest_collection_modifyitems(items):
    for item in items:
        if any(pattern in item.nodeid for patterns in ACCEPTANCE.values() for pattern in patterns):
            item.add_marker(pytest.mark.acceptance)


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and (report.skipped or report.failed)):
        RESULTS[report.nodeid] = report.outcome
    elif report.when == "teardown" and report.failed:
        RESULTS[report.nodeid] = "failed"


def pytest_sessionfinish(session, exitstatus):
    output = session.config.getoption("--acceptance-report")
    if not output:
        return
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    matrix = {}
    for eid, patterns in ACCEPTANCE.items():
        found = {node: result for node, result in RESULTS.items() if any(p in node for p in patterns)}
        complete = all(any(p in node for node in found) for p in patterns)
        outcomes = set(found.values())
        status = "PASS" if complete and outcomes == {"passed"} else "FAIL" if "failed" in outcomes else "NOT_RUN"
        matrix[eid] = {"status": status, "tests": found,
            "scope": "S5 real-model semantics excluded" if eid == "E12" else "synthetic offline engineering acceptance"}
    result = {"exitstatus": int(exitstatus), "totals": {outcome: sum(v == outcome for v in RESULTS.values())
        for outcome in ("passed", "failed", "skipped")}, "acceptance": matrix, "tests": RESULTS,
        "real_model_calls": 0}
    (root / "acceptance_results.json").write_text(json.dumps(result, indent=2) + "\n")
