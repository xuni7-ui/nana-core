"""Read-only post-genesis inspection. Never init/start/fix/activate a Subject.

Explicit home and expected identity/lineage, no ambient discovery or credentials.
Safe to use before handing the existing home to the already-qualified Supervisor.
"""

import argparse
import json
import sqlite3
import time
from pathlib import Path
from nana_core.life.live_api.supervisor import existing_identity
from nana_core.life.config import load_config
from nana_core.life.provider import provider_status
from nana_core.host_requirements import unix_socket_path
from nana_core.contracts import CoreError


def inspect_existing(home, *, subject_id, lineage_binding):
    home = Path(home).absolute()
    observed, lineage, unknown = existing_identity(home)
    if (observed, lineage) != (subject_id, lineage_binding):
        raise ValueError("EXISTING_IDENTITY_BINDING_MISMATCH")
    cfg = load_config(home)
    unix_socket_path(home / "control.sock")
    dbpath = home / "subject/self.db"
    with sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        started = time.monotonic()
        db.set_progress_handler(lambda: int(time.monotonic() - started > 2), 1000)
        if db.execute("PRAGMA user_version").fetchone()[0] != 13:
            raise ValueError("EXPLICIT_VERSION_MIGRATION_REQUIRED")
        quick = db.execute("PRAGMA quick_check").fetchall()
        foreign = db.execute("PRAGMA foreign_key_check").fetchone()
    if quick != [("ok",)] or foreign is not None:
        raise ValueError("SUBJECT_INTEGRITY_FAILED")
    try:
        providers = provider_status(home)["provider_settings"]
    except CoreError as exc:
        if exc.code != "PROVIDER_CONFIG_UNAVAILABLE":
            raise
        providers = {"revision": None, "routes": []}
    provider_state = (
        "MISSING_EXPLICIT_CONFIGURATION_REQUIRED" if providers["revision"] is None else "CONFIGURED_NOT_LIVE_QUALIFIED"
    )
    return {
        "state": "OFFLINE_PASS_EXISTING_HOME_ONLY",
        "subject_id": observed,
        "lineage_binding": lineage,
        "integrity": "PASS",
        "pending_provider_unknown": unknown,
        "provider_configuration_revision": providers["revision"],
        "provider_configuration_state": provider_state,
        "configured_operations": [r["operation"] for r in providers["routes"]],
        "privacy_scope": [str(p) for p in cfg.remote_privacy],
        "real_provider_pass": "NOT_RUN",
        "host_deployed": "NOT_VERIFIED",
        "android_connected": "NOT_VERIFIED",
        "first_life_ready": False,
        "new_subject_created": False,
        "execution_authority": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--subject-id", required=True)
    p.add_argument("--lineage-binding", required=True)
    a = p.parse_args()
    try:
        result = inspect_existing(a.home, subject_id=a.subject_id, lineage_binding=a.lineage_binding)
    except Exception:
        print(json.dumps({"state": "BLOCKED_EXISTING_HOME_PREFLIGHT", "new_subject_created": False}))
        raise SystemExit(2) from None
    print(json.dumps(result))


if __name__ == "__main__":
    main()
