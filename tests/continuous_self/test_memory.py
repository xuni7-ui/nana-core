import json

import pytest
from pydantic import ValidationError

from nana_core.continuity import ContinuityStore
from nana_core.continuity.contracts import (EvidenceInput, IngressQualification,
    MemoryCandidate, MemoryType, Provenance, RealMemoryIngress)
from nana_core.continuity.memory import MemoryService
from nana_core.contracts import CoreError
from .conftest import evidence


def add(memory, source, text, *, kind=MemoryType.SEMANTIC, **fields):
    entity_id = memory.store.identity["identity_id"] if kind == MemoryType.SELF else "synthetic-sister"
    return memory.add(MemoryCandidate(entity_id=entity_id, scope="synthetic-home",
        memory_type=kind, epistemic_kind="BELIEF", source_evidence_id=source, text=text, **fields))


def test_seven_memory_types_provenance_dedup_and_restart(cognitive):
    store, memory, _ = cognitive
    ids = []
    for index, kind in enumerate(MemoryType):
        source = evidence(memory, f"source-{index}", f"synthetic {kind.value} observation")
        assert source == evidence(memory, f"source-{index}", f"synthetic {kind.value} observation")
        ids.append(add(memory, source, f"synthetic {kind.value} interpretation", kind=kind))
    before = memory.query(scopes=("synthetic-home",), privacy_classes=("PERSONAL",))
    assert {r["memory_type"] for r in before} == {x.value for x in MemoryType}
    assert all(r["event_time_us"] == 100 and r["observed_time_us"] == 101 for r in before)
    assert all(r["source_provenance"]["domain"] == "SYNTHETIC_ONLY" for r in before)
    assert not memory.query(scopes=("synthetic-home",), privacy_classes=("PUBLIC",))
    store.replay(store.path.with_name("replay.db"))
    with ContinuityStore(store.path.with_name("replay.db"), store.clock) as replay:
        assert MemoryService(replay).query(scopes=("synthetic-home",), privacy_classes=("PERSONAL",)) == before
    assert all("interpretation" not in e["data_json"] for e in store.all("events"))
    assert not any(store.all(t) for t in ("actions", "grants", "attempts", "strategies"))


def test_claim_correction_conflict_and_inference_cannot_upgrade(cognitive):
    store, memory, _ = cognitive
    a = add(memory, evidence(memory, "old", "I prefer A", when=100), "A", predicate_key="preference")
    b = add(memory, evidence(memory, "new", "Actually I prefer B", when=200), "B",
            predicate_key="preference", correction_of=a)
    assert memory.read(a, include_inactive=True)["superseded_by"] == b
    assert memory.read(b)["correction_of"] == a
    assert add(memory, evidence(memory, "new", "Actually I prefer B", when=200), "B",
               predicate_key="preference", correction_of=a) == b
    assert [r["text"] for r in memory.query(scopes=("synthetic-home",), privacy_classes=("PERSONAL",))] == ["B"]
    c = add(memory, evidence(memory, "ambiguous", "C", when=200), "C", predicate_key="preference")
    assert not memory.query(scopes=("synthetic-home",), privacy_classes=("PERSONAL",))
    assert {r["memory_id"] for r in memory.family("synthetic-sister", "synthetic-home", "preference")} == {b, c}
    source = evidence(memory, "inferred", "model guess", kind="MODEL_DERIVATION")
    with pytest.raises(CoreError, match="INVALID_CORRECTION"):
        add(memory, source, "D", predicate_key="preference", correction_of=c)
    with pytest.raises(CoreError, match="DERIVATION_CANNOT_BECOME_OBSERVATION"):
        memory.add(MemoryCandidate(entity_id="synthetic-sister", scope="synthetic-home",
            memory_type=MemoryType.EPISODIC, epistemic_kind="OBSERVATION",
            source_evidence_id=source, text="model guess"))
    with pytest.raises(CoreError, match="CORRECTION_TIME_UNPROVEN"):
        add(memory, evidence(memory, "older", "older", when=1), "older",
            predicate_key="preference", correction_of=c)


def test_contracts_and_real_ingress_fail_closed(cognitive):
    _, memory, _ = cognitive
    with pytest.raises(ValidationError):
        Provenance(source_namespace="real.iris", source_reference="x", source_kind="USER_STATEMENT")
    with pytest.raises(CoreError, match="REAL_MEMORY_IMPORT_DISABLED"):
        RealMemoryIngress().import_real(IngressQualification(**{
            field: True for field in IngressQualification.model_fields}), payload=object())
    source = evidence(memory, "same", "one")
    with pytest.raises(CoreError, match="SOURCE_KEY_COLLISION"):
        evidence(memory, "same", "different")
    with pytest.raises(ValidationError):
        MemoryCandidate(entity_id="x", scope="s", memory_type=MemoryType.SELF,
            epistemic_kind="SUMMARY", source_evidence_id=source, text="unsupported summary")
