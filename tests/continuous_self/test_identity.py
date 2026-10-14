import pytest

from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError, Observation
from nana_core.continuity import ContinuityStore, IdentityProvenance, IdentityService
from nana_core.storage import Store


def test_identity_revision_restart_replay_and_host_copy(tmp_path):
    path = tmp_path / "self.db"
    authority = OperatorAuthority()
    with ContinuityStore(path, ManualClock()) as store:
        service = IdentityService(store, authority)
        initial = service.current()
        revised = service.revise_expression(expected_revision=1, style="warm and playful",
            reason="Reviewed synthetic expression trial; charter unchanged",
            provenance=IdentityProvenance(source="OPERATOR_REVIEW", reference_id="synthetic-review-1"),
            authority=authority)
        assert revised.identity_id == initial.identity_id
        assert revised.charter == initial.charter
        assert revised.revision == 2
        with pytest.raises(CoreError, match="STALE_IDENTITY_REVISION"):
            service.revise_expression(expected_revision=1, style="precise", reason="stale",
                provenance=revised.provenance, authority=authority)
        with pytest.raises(CoreError, match="UNAUTHENTICATED_OPERATOR"):
            service.revise_expression(expected_revision=2, style="other", reason="model says so",
                provenance=revised.provenance, authority=OperatorAuthority())
        store.replay(tmp_path / "replay.db")
        store.backup(tmp_path / "another-host.db")
    for copy in (path, tmp_path / "replay.db", tmp_path / "another-host.db"):
        with ContinuityStore(copy, ManualClock()) as store:
            assert IdentityService(store, authority).current() == revised
            assert not store.all("grants") and not store.all("actions")


def test_explicit_development_upgrade_rejects_legacy_plaintext(tmp_path):
    with Store(tmp_path / "legacy.db") as store:
        original = store.identity["identity_id"]
    with ContinuityStore(tmp_path / "legacy.db") as store:
        assert IdentityService(store, OperatorAuthority()).current().identity_id == original
    with pytest.raises(CoreError, match="SCHEMA_VERSION_UNSUPPORTED"):
        Store(tmp_path / "legacy.db")
    with Store(tmp_path / "populated.db") as store:
        store.ingest(Observation(source_namespace="synthetic", object_id="x", raw_text="fictional"))
    with pytest.raises(CoreError, match="LEGACY_PAYLOAD_MIGRATION_REQUIRED"):
        ContinuityStore(tmp_path / "populated.db")
    with Store(tmp_path / "populated.db") as store:
        assert len(store.all("memory_items")) == 1  # failed migration made no changes
