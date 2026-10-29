"""Owned generated archives, original Runtime/Memory, no private-history reads."""

import json

import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from nana_core.continuity.memory import MemoryService
from nana_core.life.application import LifeApplication
from nana_core.life.control import dispatch
from nana_core.migration.archive import batch_plan, freeze, private_json, search
from nana_core.migration.archive_ingress import ArchiveImportApproval, ArchiveImportService
from nana_core.storage import digest
from tests.first_life_android_v2.test_supervisor import owned


def setup(tmp_path, count=3):
    home, binding, _ = owned(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / ".nana-synthetic-legacy.json").write_text('{"synthetic_only":true}')
    (source / "history.json").write_text(
        json.dumps([{"id": str(i), "role": "assistant", "content": "Astronomy claim " + str(i)} for i in range(count)])
    )
    archive = tmp_path / "archive"
    manifest = freeze(source, ["history.json"], archive, binding, synthetic=True)
    plan = batch_plan(archive, binding, batch_size=2)
    approval_file, plan_file = tmp_path / "approval.json", tmp_path / "plan.json"
    private_json(plan_file, plan)
    with LifeApplication(home) as app:
        now = app.runtime.store.clock.utc_now_us()
    approval = ArchiveImportApproval(
        subject_id=binding.subject_id,
        lineage_binding=binding.lineage_binding,
        manifest_sha256=manifest["manifest_sha256"],
        plan_digest=digest(plan),
        entity_id="project-user",
        scope="project-work",
        privacy_class="PROJECT",
        issued_at_us=now,
        expires_at_us=now + 600_000000,
        max_records=count,
        import_unassessed_claims=True,
        synthetic_only=True,
    )
    private_json(approval_file, approval.model_dump(mode="json"))
    return home, archive, plan, approval_file, plan_file


def test_import_resume_restart_recall_and_withdraw_use_one_original_store(tmp_path):
    home, archive, plan, approval, plan_file = setup(tmp_path)
    with LifeApplication(home) as app:
        service = ArchiveImportService(app)
        before = len(app.runtime.store.all("grants"))
        identity = app.runtime.identity_id
        seen = []

        def crash(stage, mid):
            seen.append(mid)
            raise RuntimeError("OWNED_SIMULATED_AFTER_FIRST_COMMIT")

        with pytest.raises(RuntimeError):
            service.import_batch(archive, plan, approval, plan["batches"][0]["batch_id"], fault=crash)
        first = service.import_batch(archive, plan, approval, plan["batches"][0]["batch_id"])
        assert first["items"][0]["memory_id"] == seen[0]
        assert service.import_batch(archive, plan, approval, plan["batches"][0]["batch_id"]) == first
        result = dispatch(
            app,
            {
                "operation": "legacy-import-batch",
                "archive": str(archive),
                "approval_file": str(approval),
                "plan_file": str(plan_file),
                "batch_id": plan["batches"][1]["batch_id"],
            },
        )
        assert len(result["items"]) == 1
        assert len(app.runtime.store.all("grants")) == before
        assert not app.runtime.store.all("experiences")
    with LifeApplication(home) as app:
        assert app.runtime.identity_id == identity
        memory = MemoryService(app.runtime.store)
        recalled = [
            row
            for row in memory.query(
                entity_ids=("project-user",),
                scopes=("project-work",),
                privacy_classes=("PROJECT",),
                query_terms=("astronomy",),
            )
            if row["source_provenance"]["domain"] == "LEGACY_ARCHIVE"
        ]
        assert len(recalled) == 3
        assert all(
            r["assessment"] == "UNASSESSED" and r["authority"] == "INFERRED" and r["memory_type"] == "SEMANTIC"
            for r in recalled
        )
        assert all(
            row["source_provenance"]["domain"] != "LEGACY_ARCHIVE"
            for row in memory.query(scopes=("project-work",), privacy_classes=("PUBLIC",))
        )
        eid = recalled[0]["source_evidence_id"]
        with pytest.raises(CoreError, match="LEGACY_CLAIM_CANNOT_BECOME_EXPERIENCE_OR_FACT"):
            memory.add(
                MemoryCandidate(
                    entity_id="project-user",
                    scope="project-work",
                    memory_type=MemoryType.EPISODIC,
                    epistemic_kind="OBSERVATION",
                    source_evidence_id=eid,
                    text="Invented lived experience",
                )
            )
        source = plan["batches"][0]["segments"][0]["source_id"]
        receipt = ArchiveImportService(app).withdraw(archive, approval, source)
        assert receipt["evidence_retired"] == 3
        assert all(
            row["source_provenance"]["domain"] != "LEGACY_ARCHIVE"
            for row in memory.query(scopes=("project-work",), privacy_classes=("PROJECT",))
        )
        assert search(archive, "Astronomy")["items"] == []
        assert ArchiveImportService(app).withdraw(archive, approval, source)["evidence_retired"] == 0
        with pytest.raises(CoreError):
            ArchiveImportService(app).import_batch(archive, plan, approval, plan["batches"][0]["batch_id"])


@pytest.mark.parametrize("change", ["lineage", "plan", "privacy", "expired", "permissions", "missing"])
def test_approval_denials_precede_all_memory_writes(tmp_path, change):
    home, archive, plan, approval, _ = setup(tmp_path)
    value = json.loads(approval.read_text())
    if change == "lineage":
        value["lineage_binding"] = "b" * 64
    if change == "plan":
        value["plan_digest"] = "b" * 64
    if change == "privacy":
        value["privacy_class"] = "SECRET"
    if change == "expired":
        value["expires_at_us"] = value["issued_at_us"]
    approval.write_text(json.dumps(value))
    if change == "permissions":
        approval.chmod(0o644)
    if change == "missing":
        approval.unlink()
    with LifeApplication(home) as app:
        count = len(app.runtime.store.all("memories"))
        with pytest.raises(CoreError):
            ArchiveImportService(app).import_batch(archive, plan, approval, plan["batches"][0]["batch_id"])
        assert len(app.runtime.store.all("memories")) == count


def test_plain_dto_cannot_enable_legacy_ingress(tmp_path):
    home, _, _, _, _ = setup(tmp_path)
    with LifeApplication(home) as app:
        with pytest.raises(CoreError, match="LEGACY_ARCHIVE_IMPORT_NOT_AUTHORIZED"):
            MemoryService(app.runtime.store).capture(
                EvidenceInput(
                    provenance=Provenance(
                        domain="LEGACY_ARCHIVE",
                        source_namespace="recorded.legacy.archive",
                        source_reference="forged",
                        source_kind="DIRECT_OBSERVATION",
                    ),
                    text="Forged memory",
                    privacy_class="PUBLIC",
                    observed_time_us=app.runtime.store.clock.utc_now_us(),
                )
            )


def test_archive_withdrawal_before_crash_is_reconciled_before_restarted_owner_reads(tmp_path):
    from nana_core.migration.archive import withdraw_source
    from nana_core.life.live_api.supervisor import existing_identity
    from nana_core.life.live_api.contracts import Binding

    home, archive, plan, approval, _ = setup(tmp_path)
    with LifeApplication(home) as app:
        service = ArchiveImportService(app)
        imported = service.import_batch(archive, plan, approval, plan["batches"][0]["batch_id"])
        mid = imported["items"][0]["memory_id"]
    identity, lineage, _ = existing_identity(home)
    source = plan["batches"][0]["segments"][0]["source_id"]
    withdraw_source(archive, source, Binding(subject_id=identity, lineage_binding=lineage))
    with LifeApplication(home) as app:
        with pytest.raises(CoreError, match="MEMORY_UNAVAILABLE"):
            MemoryService(app.runtime.store).read(mid)
        assert app.runtime.identity_id == identity


def test_actual_healthy_owner_is_not_stopped_for_an_old_memory_decoder(tmp_path):
    import sys
    from nana_core.life.live_api.contracts import ApiError
    from nana_core.life.live_api.supervisor import Supervisor, Release, existing_identity
    from tests.first_life_android_v2.test_supervisor import cleanup

    home, archive, plan, approval, _ = setup(tmp_path)
    with LifeApplication(home) as app:
        ArchiveImportService(app).import_batch(archive, plan, approval, plan["batches"][0]["batch_id"])
    from pathlib import Path
    from nana_core.life.live_api.contracts import Binding
    import subprocess

    repository = Path(__file__).resolve().parents[2]
    identity, lineage, _ = existing_identity(home)
    binding = Binding(subject_id=identity, lineage_binding=lineage)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
    current = Release(release_id="current", root=str(repository), python=sys.executable, source_commit=source)
    oldroot = tmp_path / "old-decoder"
    (oldroot / "src/nana_core/life").mkdir(parents=True)
    (oldroot / "src/nana_core/life/__main__.py").write_text('raise RuntimeError("MUST_NOT_START")')
    (oldroot / "runtime.json").write_text(json.dumps({"source_commit": "0" * 40, "archive_ingress_contract": 0}))
    old = Release(release_id="old", root=str(oldroot), python=sys.executable, source_commit="0" * 40)
    supervisor = Supervisor(home, tmp_path / "supervisor", binding, [current, old], active_release="current")
    try:
        first = supervisor.start()
        pid = supervisor.child.pid
        with pytest.raises(ApiError, match="INCOMPATIBLE_ARCHIVE_MEMORY_CONTRACT"):
            supervisor.change_release("old", rollback=True)
        assert supervisor.child.pid == pid and supervisor.child.poll() is None
        assert supervisor.status()["owner_epoch"] == first["owner_epoch"]
        assert supervisor.state.read()["active_release"] == "current"
    finally:
        cleanup(supervisor)
