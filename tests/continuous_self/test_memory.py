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


def test_self_memories_are_filtered_before_candidate_limit(cognitive):
    store, memory, authority = cognitive
    self_id = store.identity['identity_id']
    source = evidence(memory, 'self-anchor', 'synthetic self anchor')
    anchor = add(memory, source, 'persistent self anchor', kind=MemoryType.SELF)
    for i in range(132):
        src = evidence(memory, f'self-note-{i}', f'note {i}')
        memory.add(MemoryCandidate(entity_id=self_id, scope='synthetic-home', memory_type=MemoryType.SEMANTIC,
            epistemic_kind='BELIEF', source_evidence_id=src, text=f'self note {i}', importance=1.0))
    args = dict(entity_ids=(self_id,), scopes=('synthetic-home',), privacy_classes=('PERSONAL',))
    assert anchor not in {m['memory_id'] for m in memory.query(**args)}
    filtered = memory.query(**args, memory_types=('SELF',), limit=1)
    assert [m['memory_id'] for m in filtered] == [anchor]
    assert memory.query_count(**args, memory_types=('SELF',)) == 1
    from nana_core.continuity.context import self_frame
    assert self_frame(store, authority, entity_id='synthetic-sister', scopes=('synthetic-home',), privacy_classes=('PERSONAL',)).self_memory_ids == (anchor,)
    with pytest.raises(CoreError, match='INVALID_MEMORY_TYPE_FILTER'):
        memory.query(**args, memory_types=('invented',))


def test_readonly_inventory_exposes_metadata_without_payload_or_writer(cognitive):
    from tools.nana_next_experience.live_memory_inventory import inventory
    store, memory, _ = cognitive
    source = evidence(memory, 'inventory-source', 'TEST_ONLY_NOT_SECRET_BODY_NOT_METADATA')
    add(memory, source, 'TEST_ONLY_NOT_SECRET_BODY_NOT_METADATA')
    changes = store.db.total_changes
    snapshot = inventory(store.path)
    assert snapshot['identity_id'] == store.identity['identity_id']
    assert snapshot['private_payloads_read'] is False
    assert 'TEST_ONLY_NOT_SECRET_BODY_NOT_METADATA' not in json.dumps(snapshot)
    assert snapshot['vector_binding'].startswith('NOT_VERIFIED')
    assert store.db.total_changes == changes
    alias = store.path.with_name('alias.db')
    alias.symlink_to(store.path)
    with pytest.raises(ValueError, match='OWNED_REGULAR_LIVE_STORE_REQUIRED'):
        inventory(alias)


def test_sparse_ranking_matches_independent_order_and_falls_back_without_index(cognitive):
    import re
    store, memory, _ = cognitive
    expected = []
    for i in range(700):
        text = f'entry {i} ' + ('needle anchor' if i%17 == 0 else 'ordinary unrelated')
        src = evidence(memory, f'rank-{i}', text)
        mid = add(memory, src, text, importance=(i%10)/10)
        expected.append((mid,text,(i%10)/10,i))
    args = dict(entity_ids=('synthetic-sister',), scopes=('synthetic-home',), privacy_classes=('PERSONAL',))
    for terms in (('needle','anchor'),('ordinary',),('no-match',),('needle','needle')):
        wanted = [x[0] for x in sorted(expected,key=lambda x:(-len(set(re.findall(r'\w{2,64}',x[1])) & set(terms)),-x[2],x[3]))][:128]
        assert [r['memory_id'] for r in memory.query(**args,query_terms=terms)] == wanted
    store.db.execute('DROP INDEX memory_terms_term_lookup')
    assert [r['memory_id'] for r in memory.query(**args,query_terms=('needle','anchor'))] == [x[0] for x in sorted(expected,key=lambda x:(-len(set(re.findall(r'\w{2,64}',x[1])) & {'needle','anchor'}),-x[2],x[3]))][:128]
    assert memory.query(**{**args,'privacy_classes':('PUBLIC',)},query_terms=('needle',)) == []


@pytest.mark.parametrize('namespace',['cognition-occurrence','provider-consideration'])
@pytest.mark.parametrize('fault',['no-authority','statement','private-body','foreign-namespace','consent','wrong-root-kind'])
def test_self_cognition_provenance_cannot_mint_external_claim_or_private_transcript(tmp_path,fault,namespace):
    from nana_core.actions import OperatorAuthority
    from nana_core.continuity.contracts import SELF_COGNITION_OCCURRENCE_TEXT,SELF_PROVIDER_CONSIDERATION_TEXT
    from nana_core.continuity import IdentityService
    from nana_core.presence.authority import VirtualClock
    with ContinuityStore(tmp_path/'own.db',VirtualClock(),schema_target=13) as store:
        IdentityService(store,OperatorAuthority())
        values=dict(domain='SELF_COGNITION',source_namespace='recorded.subject.'+namespace,
            source_reference=('self.request.' if namespace=='provider-consideration' else 'self.')+'a'*64,source_kind='SYSTEM_VERIFICATION')
        body=SELF_PROVIDER_CONSIDERATION_TEXT if namespace=='provider-consideration' else SELF_COGNITION_OCCURRENCE_TEXT
        if fault=='wrong-root-kind':body=SELF_COGNITION_OCCURRENCE_TEXT if namespace=='provider-consideration' else SELF_PROVIDER_CONSIDERATION_TEXT
        if fault=='statement':values['source_kind']='USER_STATEMENT'
        if fault=='private-body':body='Unverified private guess is not an observed world fact'
        if fault=='foreign-namespace':values['source_namespace']='recorded.external'
        with pytest.raises((CoreError,ValidationError)):
            MemoryService(store,None if fault=='no-authority' else OperatorAuthority()).capture(EvidenceInput(
                provenance=Provenance(**values),text=body,privacy_class='PERSONAL',observed_time_us=store.clock.utc_now_us(),
                retention_consent_ref='not-consent' if fault=='consent' else None))
        assert not store.db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace LIKE 'recorded.subject.%'").fetchone()
        with pytest.raises(ValidationError):
            Provenance(domain='RECORDED_PUBLIC',source_namespace='recorded.subject.cognition-occurrence',source_reference='x',source_kind='DIRECT_OBSERVATION')
