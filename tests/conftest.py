"""Explicit host fixture for the legacy client/old-SQLite isolation contract.

This is not a Runtime interpreter selection or credential lookup. The original
3.46.1 test remains strict; a missing/incompatible host fails, never skips.
"""

from pathlib import Path
import subprocess

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--old-sqlite-python",
        default="/usr/bin/python3",
        help="Explicit local interpreter linked to SQLite3.46.1 for the legacy client fixture",
    )


@pytest.fixture
def old_sqlite_python(request):
    path = Path(request.config.getoption("--old-sqlite-python"))
    if not path.is_absolute() or not path.is_file():
        pytest.fail("OLD_SQLITE_FIXTURE_INTERPRETER_MISSING: select --old-sqlite-python")
    probe = subprocess.run(
        [str(path), "-I", "-c", "import sqlite3;print(sqlite3.sqlite_version)"],
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TZ": "UTC"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    if probe.returncode or probe.stdout.strip() != "3.46.1":
        pytest.fail("OLD_SQLITE_FIXTURE_REQUIRES_3_46_1: select --old-sqlite-python")
    return str(path)
