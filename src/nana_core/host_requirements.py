"""Stdlib-only host contract shared by Store, offline installer and preflight.

No Subject, files, credentials or authority are created by these probes. Version
3.51.3 includes the WAL-reset corruption fix; JSON/FTS5 alone cannot replace it.
Backported older SQLite builds require separate qualification, not a silent pass.
"""

import os
import importlib
from pathlib import Path
import sqlite3
from typing import TypedDict

MIN_SQLITE = (3, 51, 3)
SQLITE_REASON = "WAL_RESET_CORRUPTION_FIX_REQUIRED"
UNIX_SOCKET_MAX_BYTES = 107  # Linux sockaddr_un.sun_path, excluding trailing NUL.

REQUIRED_PYTHON_MODULES = ("ctypes", "ssl", "zlib", "sqlite3", "resource", "termios", "venv")


class PythonReport(TypedDict):
    """Native/stdlib prerequisites needed by shipped process and transport code."""

    supported: bool
    missing: list[str]
    code: str


def python_runtime_report() -> PythonReport:
    missing = []
    for name in REQUIRED_PYTHON_MODULES:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    return {
        "supported": not missing,
        "missing": missing,
        "code": "PYTHON_NATIVE_MODULES_MISSING" if missing else "SUPPORTED",
    }


class SQLiteChecks(TypedDict):
    """Actual in-memory capability checks, not permissions or version claims."""

    version: bool
    json: bool
    fts5: bool


class SQLiteReport(TypedDict):
    """Sanitized host-only readiness metadata; never authoritative Subject data."""

    supported: bool
    version: str
    minimum: str
    checks: SQLiteChecks
    code: str
    reason: str | None


def sqlite_runtime_report() -> SQLiteReport:
    """Inspect the binding loaded by this exact interpreter, in memory only."""
    checks: SQLiteChecks = {"version": sqlite3.sqlite_version_info >= MIN_SQLITE, "json": False, "fts5": False}
    try:
        with sqlite3.connect(":memory:") as db:
            checks["json"] = db.execute("SELECT json_valid('{}')").fetchone()[0] == 1
            try:
                db.execute("CREATE VIRTUAL TABLE host_fts_probe USING fts5(text)")
                checks["fts5"] = True
            except sqlite3.Error:
                pass
    except sqlite3.Error:
        pass
    return {
        "supported": all(checks.values()),
        "version": sqlite3.sqlite_version,
        "minimum": ".".join(map(str, MIN_SQLITE)),
        "checks": checks,
        "code": "SQLITE_VERSION_UNSUPPORTED"
        if not checks["version"]
        else "SQLITE_FEATURES_UNSUPPORTED"
        if not all(checks.values())
        else "SUPPORTED",
        "reason": SQLITE_REASON if not checks["version"] else None,
    }


def require_sqlite_runtime() -> None:
    report = sqlite_runtime_report()
    if not report["supported"]:
        raise ValueError(report["code"])


def unix_socket_path(path: str | Path) -> Path:
    """Validate final absolute filesystem bytes; never relocate a user home."""
    value = Path(path).absolute()
    raw = os.fsencode(value)
    if b"\0" in raw or len(raw) > UNIX_SOCKET_MAX_BYTES:
        raise ValueError("UNIX_SOCKET_PATH_TOO_LONG")
    return value
