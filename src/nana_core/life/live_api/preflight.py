"""Read-only operational facts in the actual service namespace and UID.

No Supervisor/Auth construction, owner lock, Store constructor, init, activation,
model dispatch or credentials. Namespace-invisible owners remain unverified.
"""

import os
import sqlite3
from pathlib import Path

from .supervisor import identity_request_state
from .contracts import ApiError, Role
from ..config import load_config


def check(config):
    home = Path(config.home).absolute()
    identity, lineage, active, terminal = identity_request_state(home)
    if (identity, lineage) != (config.binding.subject_id, config.binding.lineage_binding):
        raise ApiError("INVALID_IDENTITY", 409)
    with sqlite3.connect((home / "subject/self.db").as_uri() + "?mode=ro", uri=True, timeout=1) as db:
        db.execute("PRAGMA query_only=ON")
        schema = db.execute("PRAGMA user_version").fetchone()[0]
        quick = db.execute("PRAGMA quick_check").fetchone()[0]
        fk = db.execute("PRAGMA foreign_key_check").fetchone()
    life = load_config(home)
    from ..provider import provider_status
    if not (home / "providers.json").exists():
        provider, revision = "PROVIDER_UNCONFIGURED", None
    else:
        try:
            settings = provider_status(home)["provider_settings"]
            provider = "CONFIGURED_SECRET_AND_RUNTIME_NOT_OBSERVED" if settings["routes"] else "PROVIDER_UNCONFIGURED"
            revision = settings["revision"]
        except Exception:
            provider, revision = "PROVIDER_CONFIGURATION_UNAVAILABLE", None
    from ..cloud import health
    health_view = health(home)
    return {
        "state": "READ_ONLY_BINDING_CHECKED" if schema == 13 and quick == "ok" and fk is None else "STORE_CHECK_FAILED",
        "subject_id": identity, "lineage_binding": lineage, "schema_version": schema,
        "database_integrity": quick, "foreign_key_violation": fk is not None,
        "numeric_uid": os.geteuid(), "numeric_gid": os.getegid(),
        "source_context": {"mount_namespace": os.readlink("/proc/self/ns/mnt"), "user_namespace": os.readlink("/proc/self/ns/user")},
        "runtime_owner_ready_in_this_namespace": health_view["process_ready"],
        "runtime_visibility": "VERIFIED_LOCAL_OWNER" if health_view["process_ready"] else "UNVERIFIED_IN_THIS_CONTEXT",
        "unknown_requests": active + terminal, "active_provider_requests": active,
        "storage_status": health_view["storage_status"],
        "disk_pressure": health_view["disk_pressure"], "configuration_revision": revision,
        "provider": provider, "provider_hosts_configured": bool(life.provider_hosts),
        "provider_budget_configured": life.provider_cost_ceiling_micro > 0 and life.provider_calls_per_day > 0,
        "management_entry": "CONFIGURED" if Role.HOST_ADMIN in config.roles else "NOT_CONFIGURED_NO_ROLE_ESCALATION",
        "live_provider_check": "LIVE_PROVIDER_CHECK_NOT_AUTHORIZED",
        "provider_calls": 0, "subject_created": False, "persistent_changes": 0,
    }
