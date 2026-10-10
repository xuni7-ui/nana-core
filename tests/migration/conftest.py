import json
from pathlib import Path
import socket
import pytest
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CAPABILITIES, GrantSpec, VERIFY_CAPABILITY
from nana_core.fake_world import FakeWorld
from nana_core.migration.routing import CapabilityRouter
from nana_core.storage import Store

RESULTS = {}

SOURCE = "source://synthetic/migration-book"
CARD = "notebook://synthetic/migration-card"
NEXT = "notebook://synthetic/migration-next"


@pytest.fixture
def routed(tmp_path):
    clock, authority = ManualClock(), OperatorAuthority("synthetic-migration-operator")
    with Store(tmp_path / "core.db", clock) as store:
        world = FakeWorld(tmp_path / "world.db")
        world.seed_source(SOURCE, [{"text": "A synthetic reader sketches a paper telescope.", "locator": "page 17, paragraph 4"}])
        router = CapabilityRouter(store, {c: world for c in CAPABILITIES}, authority)
        router.select_owner("legacy_simulator", authority)
        kernel = ActionKernel(store, router.bind("legacy_simulator", authority), authority)
        kernel.set_budgets({"write_attempts": 12, "external_requests": 150, "cost_micro_units": 150}, authority)
        kernel.grant(GrantSpec(capabilities=tuple(sorted(CAPABILITIES | {VERIFY_CAPABILITY})),
            resources=(SOURCE, CARD, NEXT), not_before_us=clock.utc_now_us(), expires_at_us=clock.utc_now_us() + 100_000_000), authority)
        try:
            yield store, world, router, kernel, authority, clock
        finally:
            world.close()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("S6 synthetic migration attempted network access")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def pytest_addoption(parser):
    parser.addoption("--s6-report", default=None)


def pytest_runtest_logreport(report):
    if "tests/migration/" not in report.nodeid:
        return
    if report.when == "call" or (report.when == "setup" and (report.failed or report.skipped)):
        RESULTS[report.nodeid] = report.outcome
    elif report.when == "teardown" and report.failed:
        RESULTS[report.nodeid] = "failed"


def pytest_sessionfinish(session, exitstatus):
    output = session.config.getoption("--s6-report")
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"exitstatus": int(exitstatus), "tests": RESULTS,
            "totals": {k: sum(v == k for v in RESULTS.values()) for k in ("passed", "failed", "skipped")},
            "engineering_gate": "PASS" if RESULTS and all(v == "passed" for v in RESULTS.values()) and exitstatus == 0 else "FAIL",
            "E12": "NOT_RUN", "real_model_calls": 0, "production_migration": "NOT_RUN"}, indent=2) + "\n")
