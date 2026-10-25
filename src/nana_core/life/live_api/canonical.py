"""One-time canonical activation planning and verifiable legacy-source linkage.

No automatic genesis from an APK/BFF, no old shadow UUID promotion, and no private
reader. Production activation consumes an explicit operator receipt after the
old writers are fenced. Original identity/Memory/Record services remain authority.
"""

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Literal
from pydantic import Field
from ...contracts import DTO
from .contracts import ApiError


class CanonicalPlan(DTO):
    operation: Literal["CANONICAL_GENESIS_WITH_LEGACY_SOURCE_LINK"] = "CANONICAL_GENESIS_WITH_LEGACY_SOURCE_LINK"
    predecessor: Literal["NO_CANONICAL_CORE_ON_HOST"] = "NO_CANONICAL_CORE_ON_HOST"
    inventory_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    legacy_source_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    known_gaps: tuple[str, ...] = Field(max_length=16)
    state: Literal["PLANNED_REQUIRES_PRODUCTION_APPROVAL"] = "PLANNED_REQUIRES_PRODUCTION_APPROVAL"
    legacy_core_uuid_inherited: Literal[False] = False
    shadow_identity_promoted: Literal[False] = False
    history_imported: Literal[False] = False


def plan(inventory_digest):
    return CanonicalPlan(
        inventory_digest=inventory_digest,
        legacy_source_ids=("iris.0.3.0", "astrbot.platform-history", "livingmemory.legacy"),
        known_gaps=(
            "L1_EARLY_TEXT_TRIMMED",
            "L2_FRESHNESS_GAP",
            "LEDGER_ROTATION_NOT_RECONCILED",
            "PRIVATE_EXPORT_NOT_AUTHORIZED",
            "NO_OLD_CORE_LINEAGE",
        ),
    )


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_activation(home, activation):
    """Validate fixed private operator receipts; never follow a client path.

    Receipts attest an operator-approved cutover, not a cryptographic proof of
    hostile host-root fencing. The trusted host operator is part of the boundary.
    """
    home = Path(home).absolute()
    if (home / "nana-space-development.json").exists():
        raise ApiError("DEVELOPMENT_SUBJECT_CANNOT_BECOME_PRODUCTION", 403)
    root = home / "activation"
    if root.resolve() != root or not root.is_dir() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ApiError("PRODUCTION_ACTIVATION_UNVERIFIED", 403)
    names = {
        "old_writer_fence_digest": "old-writer-fence.json",
        "approval_digest": "operator-approval.json",
        "genesis_receipt_digest": "canonical-genesis.json",
    }
    records = {}
    for key, name in names.items():
        p = root / name
        if (
            p.is_symlink()
            or not p.is_file()
            or p.stat().st_uid != os.getuid()
            or p.stat().st_mode & 0o077
            or p.stat().st_size > 16384
            or _digest(p) != activation[key]
        ):
            raise ApiError("PRODUCTION_ACTIVATION_UNVERIFIED", 403)
        try:
            records[name] = json.loads(p.read_text())
        except (ValueError, OSError):
            raise ApiError("PRODUCTION_ACTIVATION_UNVERIFIED", 403) from None
    approval = records["operator-approval.json"]
    fence = records["old-writer-fence.json"]
    genesis = records["canonical-genesis.json"]
    if approval.get("operation") != "CANONICAL_GENESIS_AND_LIMITED_CUTOVER" or approval.get("approved") is not True:
        raise ApiError("PRODUCTION_ACTIVATION_UNAPPROVED", 403)
    if (
        approval.get("subject_id") != activation["subject_id"]
        or approval.get("lineage_binding") != activation["lineage_binding"]
    ):
        raise ApiError("INVALID_IDENTITY", 409)
    required = {
        "astrbot.agent",
        "iris.writer",
        "livingmemory.writer",
        "proactive.social",
        "bili.act-pump",
        "selfevolution.cron",
        "legacy.command-control",
    }
    if set(fence.get("writers", {})) != required or any(
        v != "FENCED_RESTART_PATH_VERIFIED" for v in fence["writers"].values()
    ):
        raise ApiError("OLD_WRITER_FENCE_INCOMPLETE", 403)
    if (
        fence.get("approval_digest") != activation["approval_digest"]
        or fence.get("subject_id") != activation["subject_id"]
    ):
        raise ApiError("OLD_WRITER_FENCE_UNBOUND", 403)
    if (
        genesis.get("subject_id") != activation["subject_id"]
        or genesis.get("legacy_core_uuid_inherited") is not False
        or genesis.get("mode") != "CANONICAL_GENESIS_WITH_LEGACY_SOURCE_LINK"
    ):
        raise ApiError("CANONICAL_GENESIS_UNVERIFIED", 403)
    # Canonical activation is a sourced original Core event, not only a host flag.
    path = home / "subject/self.db"
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        row = db.execute(
            "SELECT data_json FROM events WHERE kind='CANONICAL_ACTIVATED' AND identity_id=? ORDER BY seq DESC LIMIT 1",
            (activation["subject_id"],),
        ).fetchone()
    if not row:
        raise ApiError("CANONICAL_CORE_EVENT_REQUIRED", 403)
    body = json.loads(row[0])["data"]
    if (
        body.get("approval_digest") != activation["approval_digest"]
        or body.get("old_writer_fence_digest") != activation["old_writer_fence_digest"]
    ):
        raise ApiError("CANONICAL_CORE_EVENT_UNBOUND", 403)
    return {"verified": True, "level": "TRUSTED_HOST_OPERATOR_ATTESTATION", "new_identity_created": False}


def create_genesis(home, config, canonical_plan, approval):
    """Trusted offline operator transition; never called by HTTP or an APK.

    Approval is for one NEW canonical identity, not for private import, model
    payment, social delivery or activation. Existing homes are never overwritten.
    A crash leaves the incomplete home quarantined for operator inspection.
    """
    from ..config import write_config
    from ..application import LifeApplication

    home = Path(home).absolute()
    canonical_plan = CanonicalPlan.model_validate(canonical_plan)
    if set(approval) != {"operation", "approved", "inventory_digest", "plan_digest"} or approval != {
        "operation": "CREATE_ONE_CANONICAL_GENESIS_ONLY",
        "approved": True,
        "inventory_digest": canonical_plan.inventory_digest,
        "plan_digest": hashlib.sha256(canonical_plan.model_dump_json().encode()).hexdigest(),
    }:
        raise ApiError("EXPLICIT_GENESIS_APPROVAL_REQUIRED", 403)
    if home.exists() or home.is_symlink():
        raise ApiError("GENESIS_ALREADY_EXISTS_NO_RETRY", 409)
    write_config(home, config)
    with LifeApplication(home, bootstrap_grant=False) as app:
        store = app.runtime.store
        with store.transaction(
            "CANONICAL_GENESIS",
            data={
                "mode": canonical_plan.operation,
                "legacy_core_uuid_inherited": False,
                "legacy_source_links": list(canonical_plan.legacy_source_ids),
                "known_gaps": list(canonical_plan.known_gaps),
                "history_imported": False,
                "inventory_digest": canonical_plan.inventory_digest,
            },
        ):
            pass
        identity = app.runtime.identity_id
    from .supervisor import existing_identity

    _, lineage, _ = existing_identity(home)
    return {
        "subject_id": identity,
        "lineage_binding": lineage,
        "mode": canonical_plan.operation,
        "legacy_core_uuid_inherited": False,
        "history_imported": False,
        "activation": "NOT_ACTIVATED_REQUIRES_FENCE_AND_APPROVAL",
    }


def activate(home, approval, fence):
    """Operator-only, original Store event; no private body import or social send.

    The operator first verifies old writers and their resurrection paths. This
    validates an explicit attestation, not the ability to stop hostile host root.
    """
    from .supervisor import existing_identity
    from ..application import LifeApplication
    from .state import AtomicDocument

    home = Path(home).absolute()
    identity, lineage, _ = existing_identity(home)
    if (home / "nana-space-development.json").exists():
        raise ApiError("DEVELOPMENT_SUBJECT_CANNOT_BECOME_PRODUCTION", 403)
    if (
        approval.get("operation") != "CANONICAL_GENESIS_AND_LIMITED_CUTOVER"
        or approval.get("approved") is not True
        or approval.get("subject_id") != identity
        or approval.get("lineage_binding") != lineage
    ):
        raise ApiError("PRODUCTION_ACTIVATION_UNAPPROVED", 403)
    required = {
        "astrbot.agent",
        "iris.writer",
        "livingmemory.writer",
        "proactive.social",
        "bili.act-pump",
        "selfevolution.cron",
        "legacy.command-control",
    }
    if set(fence.get("writers", {})) != required or any(
        v != "FENCED_RESTART_PATH_VERIFIED" for v in fence["writers"].values()
    ):
        raise ApiError("OLD_WRITER_FENCE_INCOMPLETE", 403)
    root = home / "activation"
    if root.exists():
        raise ApiError("ACTIVATION_ALREADY_ATTEMPTED_NO_RETRY", 409)
    root.mkdir(mode=0o700)

    def write(name, value):
        # Metadata only; no credentials or personal content.
        doc = AtomicDocument(root / name, {"schema_version": 1, "revision": 0, **value})
        return _digest(doc.path)

    approval_digest = write("operator-approval.json", approval)
    if fence.get("subject_id") != identity or fence.get("approval_digest") != approval_digest:
        raise ApiError("OLD_WRITER_FENCE_UNBOUND", 403)
    fence_digest = write("old-writer-fence.json", fence)
    with LifeApplication(home, bootstrap_grant=False) as app:
        exists = app.runtime.store.db.execute("SELECT 1 FROM events WHERE kind='CANONICAL_GENESIS'").fetchone()
        if not exists:
            raise ApiError("CANONICAL_GENESIS_REQUIRED", 403)
        with app.runtime.store.transaction(
            "CANONICAL_ACTIVATED", data={"approval_digest": approval_digest, "old_writer_fence_digest": fence_digest}
        ):
            pass
    genesis_digest = write(
        "canonical-genesis.json",
        {
            "subject_id": identity,
            "lineage_binding": lineage,
            "mode": "CANONICAL_GENESIS_WITH_LEGACY_SOURCE_LINK",
            "legacy_core_uuid_inherited": False,
            "history_imported": False,
        },
    )
    result = {
        "subject_id": identity,
        "lineage_binding": lineage,
        "realm": "PRODUCTION_SINGLE_SUBJECT",
        "approval_digest": approval_digest,
        "old_writer_fence_digest": fence_digest,
        "genesis_receipt_digest": genesis_digest,
    }
    verify_activation(home, result)
    return result
