import hashlib
import json
import pytest
from nana_core.life.live_api.canonical import plan, create_genesis, activate, verify_activation
from nana_core.life.live_api.contracts import ApiError, Binding, Realm
from nana_core.life.live_api.supervisor import Supervisor
from nana_core.life.live_api.adapters import reconcile_legacy
from nana_core.life.config import load_config
from nana_core.integration.exporter import bundle
from tests.first_life_android_v2.test_supervisor import owned


def test_one_explicit_genesis_then_fenced_activation_no_shadow_promotion(tmp_path):
    old, binding, release = owned(tmp_path)
    canonical_plan = plan("a" * 64)
    approval = {
        "operation": "CREATE_ONE_CANONICAL_GENESIS_ONLY",
        "approved": True,
        "inventory_digest": "a" * 64,
        "plan_digest": hashlib.sha256(canonical_plan.model_dump_json().encode()).hexdigest(),
    }
    home = tmp_path / "canonical"
    with pytest.raises(ApiError, match="EXPLICIT_GENESIS_APPROVAL_REQUIRED"):
        create_genesis(home, load_config(old), canonical_plan, {})
    genesis = create_genesis(home, load_config(old), canonical_plan, approval)
    assert genesis["subject_id"] != binding.subject_id and not genesis["history_imported"]
    with pytest.raises(ApiError, match="GENESIS_ALREADY_EXISTS_NO_RETRY"):
        create_genesis(home, load_config(old), canonical_plan, approval)
    consent = {
        "operation": "CANONICAL_GENESIS_AND_LIMITED_CUTOVER",
        "approved": True,
        "subject_id": genesis["subject_id"],
        "lineage_binding": genesis["lineage_binding"],
    }
    raw = json.dumps({"schema_version": 1, "revision": 0, **consent}, sort_keys=True, separators=(",", ":")).encode()
    fence = {
        "subject_id": genesis["subject_id"],
        "approval_digest": hashlib.sha256(raw).hexdigest(),
        "writers": {
            k: "FENCED_RESTART_PATH_VERIFIED"
            for k in [
                "astrbot.agent",
                "iris.writer",
                "livingmemory.writer",
                "proactive.social",
                "bili.act-pump",
                "selfevolution.cron",
                "legacy.command-control",
            ]
        },
    }
    receipt = activate(home, consent, fence)
    assert verify_activation(home, receipt)["verified"]
    from types import SimpleNamespace

    Supervisor._production_gate(
        SimpleNamespace(
            home=home,
            binding=Binding(
                subject_id=genesis["subject_id"], lineage_binding=genesis["lineage_binding"], realm=Realm.PRODUCTION
            ),
        ),
        receipt,
    )
    # All approval/fence records in this test are SYNTHETIC. No actual cloud fence.
    (home / "nana-space-development.json").write_text("{}")
    with pytest.raises(ApiError, match="DEVELOPMENT_SUBJECT_CANNOT_BECOME_PRODUCTION"):
        verify_activation(home, receipt)


def test_legacy_hash_only_dryrun_conflicts_and_no_authority():
    records = [
        ("l1", "one", {"role": "user", "content": "SYNTHETIC_NOT_REAL_HISTORY", "timestamp": "2026-10-25T00:00:00Z"})
    ]
    a = bundle(records, "TEST_ONLY_NOT_SECRET_iris", mode="hash-only")
    b = bundle(
        [("l1", "one", {**records[0][2], "content": "SYNTHETIC_CHANGED"})],
        "TEST_ONLY_NOT_SECRET_iris",
        mode="hash-only",
    )
    result = reconcile_legacy([a, a])
    assert result["unique_records"] == 1 and result["duplicate_rows"] == 1
    assert result["history_imported"] is False and result["external_effects_replayed"] == 0
    assert reconcile_legacy([a, b])["state"] == "CONFLICT_REVIEW_REQUIRED"
    with pytest.raises(ApiError, match="LEGACY_MANIFEST_MISMATCH"):
        reconcile_legacy([{**a, "total_records": 0}])
    with pytest.raises(ApiError, match="HASH_ONLY_BOUNDED_EXPORT_REQUIRED"):
        reconcile_legacy([bundle(records, "TEST_ONLY_NOT_SECRET_iris", mode="include")])
