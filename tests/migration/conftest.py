import json
from pathlib import Path
import socket
import pytest

RESULTS = {}


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
