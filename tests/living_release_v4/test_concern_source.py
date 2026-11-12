"""Synthetic counterexamples for managed attention provenance and retention."""

import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, PENDING_LOCAL_RECEIPT, Provenance
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.world_loop.cognition import CognitionReply, InterestProposal, StructuredProposal
from nana_core.continuity.world_loop.concern_source import binding
from tests.world_loop.helpers import fresh


def source(runtime, key, domain, *, parents=()):
    namespace = {'SYNTHETIC_ONLY': 'synthetic.concern-source-test',
                 'DEVELOPMENT_PROJECT': 'recorded.project.concern-source-test',
                 'RECORDED_PUBLIC': 'recorded.concern-source-test',
                 'LOCAL_INTERACTION_METADATA': 'recorded.local.concern-source-test',
                 'CONSENTED_INTERACTION': 'recorded.conversation.input'}[domain]
    privacy = 'PROJECT' if domain in {'DEVELOPMENT_PROJECT', 'LOCAL_INTERACTION_METADATA'} else 'PUBLIC'
    text = PENDING_LOCAL_RECEIPT if domain == 'LOCAL_INTERACTION_METADATA' else 'Explicit synthetic provenance qualification material'
    kind = 'MODEL_DERIVATION' if parents else 'USER_STATEMENT' if domain == 'CONSENTED_INTERACTION' else 'DIRECT_OBSERVATION'
    memory = MemoryService(runtime.store)
    evidence = memory.capture(EvidenceInput(provenance=Provenance(domain=domain, source_namespace=namespace,
        source_reference=key, source_kind=kind), text=text, privacy_class=privacy,
        retention_consent_ref=key if domain == 'CONSENTED_INTERACTION' else None,
        observed_time_us=runtime.clock.utc_now_us()))
    return memory.add(MemoryCandidate(entity_id=runtime.config.entity_id, scope=runtime.config.scopes[0],
        memory_type=MemoryType.EPISODIC, epistemic_kind='INFERENCE' if parents else 'STATEMENT' if kind == 'USER_STATEMENT' else 'OBSERVATION',
        source_evidence_id=evidence, text=text, derived_from=parents))


def offer(runtime, concerns, key, memories):
    reply = CognitionReply(request_id=key, request_digest='synthetic-provenance-proof',
        provider_id='synthetic.concern-test', model_id='synthetic.concern-test', origin='SYNTHETIC',
        proposal=StructuredProposal(interpretation='Explicit synthetic proposal, never provider evidence',
            source_refs=memories, interests=(InterestProposal(topic='source-provenance', motivation_source='CURIOSITY',
                source_memory_ids=memories, interpretation='A sourced attention candidate', expected_value='HIGH',
                possible_behaviors=('EXPLORE',)),)))
    with runtime.store.transaction('synthetic.concern_source_proposal') as tx:
        record = RecordService(runtime.store).create(tx, kind='COGNITION_PROPOSAL', scope=runtime.config.scopes[0],
            payload={'reply': reply.model_dump(mode='json')}, memories=memories)
    return concerns.offer(record)[0]


@pytest.mark.parametrize('earlier,expected_domain,expected_event', [
    ('SYNTHETIC_ONLY', 'SYNTHETIC_ONLY', 'SYNTHETIC_ONLY'),
    ('DEVELOPMENT_PROJECT', 'DEVELOPMENT_PROJECT', 'DEVELOPMENT_MATERIAL'),
])
def test_new_public_encounter_preserves_accumulated_source_domains(tmp_path, earlier, expected_domain, expected_event):
    with fresh(tmp_path / 'self.db') as runtime:
        concerns = ConcernService(runtime, resources=('synthetic://source-proof',))
        previous = source(runtime, 'earlier', earlier)
        offer(runtime, concerns, 'old', (previous,))
        public = source(runtime, 'later', 'RECORDED_PUBLIC')
        cid = offer(runtime, concerns, 'new', (public,))
        assert binding(runtime.store, runtime.store.one('open_concerns', cid))[1] == expected_domain
        event = concerns.opportunity().input
        assert event.domain == expected_event
        cue = MemoryService(runtime.store).read(event.source_memory_ids[0])
        assert cue['source_provenance']['domain'] == expected_domain
        assert {previous, public} <= {row['parent_id'] for row in runtime.store.db.execute(
            'SELECT parent_id FROM memory_dependencies WHERE memory_id=?', (cue['memory_id'],))}


@pytest.mark.parametrize('other_domain', ['SYNTHETIC_ONLY', 'DEVELOPMENT_PROJECT'])
def test_mixed_transient_receipt_never_persists_managed_semantics(tmp_path, other_domain):
    with fresh(tmp_path / 'self.db') as runtime:
        concerns = ConcernService(runtime, resources=('synthetic://source-proof',))
        local = source(runtime, 'transient', 'LOCAL_INTERACTION_METADATA')
        other = source(runtime, 'other', other_domain)
        cid = offer(runtime, concerns, 'mixed', (local, other))
        with pytest.raises(CoreError, match='CONCERN_EXPLICIT_RETENTION_REQUIRED'):
            binding(runtime.store, runtime.store.one('open_concerns', cid))
        assert concerns.opportunity() is None
        assert not runtime.store.db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace LIKE '%world-concern'").fetchone()


def test_transient_receipt_cannot_hide_in_an_earlier_encounter_or_derived_memory(tmp_path):
    with fresh(tmp_path / 'self.db') as runtime:
        concerns = ConcernService(runtime, resources=('synthetic://source-proof',))
        local = source(runtime, 'transient', 'LOCAL_INTERACTION_METADATA')
        derived = source(runtime, 'derived', 'DEVELOPMENT_PROJECT', parents=(local,))
        offer(runtime, concerns, 'derived-proposal', (derived,))
        public = source(runtime, 'later', 'RECORDED_PUBLIC')
        cid = offer(runtime, concerns, 'later-proposal', (public,))
        with pytest.raises(CoreError, match='CONCERN_EXPLICIT_RETENTION_REQUIRED'):
            binding(runtime.store, runtime.store.one('open_concerns', cid))
        assert concerns.opportunity() is None


def test_consented_attention_keeps_exact_authorized_namespace_and_existing_cycle_identity(tmp_path):
    from nana_core.continuity.subject.watch import collect_opportunities

    with fresh(tmp_path / 'self.db') as runtime:
        concerns = ConcernService(runtime, resources=('synthetic://source-proof',))
        retained = source(runtime, 'retained', 'CONSENTED_INTERACTION')
        cid = offer(runtime, concerns, 'consented-proposal', (retained,))
        event = concerns.opportunity()
        provenance = MemoryService(runtime.store).read(event.input.source_memory_ids[0])['source_provenance']
        assert provenance['domain'] == 'CONSENTED_INTERACTION'
        assert provenance['source_namespace'] == 'recorded.conversation.concern'
        assert provenance['source_reference'] == event.input.source_key.removeprefix('local.world.concern.')
        watched = collect_opportunities(runtime.subject, entity_id=runtime.config.entity_id,
            now_us=runtime.clock.utc_now_us(), quiet_since_us=0, quiet_window_us=0)
        assert not any(item.source_id == event.input.source_memory_ids[0] for item in watched)
        queue = runtime.submit(event)
        assert runtime.submit(event) == queue
        assert binding(runtime.store, runtime.store.one('open_concerns', cid))[0] == event.input.source_key


@pytest.mark.parametrize('original_domain', ['DEVELOPMENT_PROJECT', 'LOCAL_INTERACTION_METADATA'])
def test_existing_legacy_event_keeps_its_original_key_before_fresh_retention_checks(tmp_path, original_domain):
    from unittest.mock import patch
    from nana_core.storage import digest

    with fresh(tmp_path / 'self.db') as runtime:
        concerns = ConcernService(runtime, resources=('synthetic://source-proof',))
        retained = source(runtime, 'original-source', original_domain)
        cid = offer(runtime, concerns, 'project-proposal', (retained,))
        row = runtime.store.one('open_concerns', cid)
        key = 'synthetic.world.concern.' + digest([cid, row['revision']])
        original = (key, 'SYNTHETIC_ONLY', 'synthetic.world-concern', 'SYNTHETIC_ONLY')
        with patch('nana_core.continuity.world_loop.attention.concern_binding', return_value=original):
            legacy = concerns.opportunity()
        queue = runtime.submit(legacy)
        assert binding(runtime.store, row)[0] == key
        restored = concerns.opportunity()
        assert restored.input.source_key == key
        assert runtime.submit(restored) == queue


def test_own_occurrence_retains_private_attention_provenance_and_registered_erasure(tmp_path):
    from nana_core.continuity.autonomy.private_intent import anchor_own_occurrence
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity import ContinuityStore
    with fresh(tmp_path/'self.db') as runtime:
        event=SubjectInput(kind='WAKE',origin='SELF_WAKE',source_key='synthetic.own-occurrence',
            entity_id=runtime.config.entity_id,scope='world',privacy_class='PERSONAL',observed_at_us=runtime.clock.utc_now_us())
        rooted=anchor_own_occurrence(runtime.store,event,authority=runtime.authority)
        own=rooted.source_memory_ids[0];memory=MemoryService(runtime.store,runtime.authority)
        source_row=runtime.store.one('memories',own)
        # Metadata is real; it is not meaningful dream material to be repeatedly
        # summarized instead of the subject's actual experiences.
        assert runtime.work.maintenance._select((source_row,),'world')==()
        concerns=ConcernService(runtime,resources=('synthetic://source-proof',))
        cid=offer(runtime,concerns,'own-concern',(own,))
        assert binding(runtime.store,runtime.store.one('open_concerns',cid))[1:3]==('SELF_COGNITION','recorded.subject.concern')
        view=concerns.view()[0]
        assert view['private_content_withheld'] and view['topic']=='private-content-withheld' and view['motivation']=='PRIVATE_CONTENT_WITHHELD'
        opportunity=concerns.opportunity();derived=memory.read(opportunity.input.source_memory_ids[0])
        assert derived['source_provenance']['domain']=='SELF_COGNITION' and derived['epistemic_kind']=='INFERENCE'
        assert derived['authority']=='INFERRED' and derived['memory_type']=='PROSPECTIVE'
        from nana_core.continuity.subject.watch import collect_opportunities
        watched=collect_opportunities(runtime.subject,entity_id=runtime.config.entity_id,now_us=runtime.clock.utc_now_us(),quiet_since_us=0,quiet_window_us=0)
        assert not any(item.source_id==derived['memory_id'] for item in watched)
        # The same source may never be promoted to an external observation or
        # attributed to the recipient by changing MemoryCandidate alone.
        with pytest.raises(CoreError,match='SELF_COGNITION_IS_OCCURRENCE_NOT_WORLD_CLAIM'):
            memory.add(MemoryCandidate(entity_id=runtime.config.entity_id,scope='world',memory_type=MemoryType.EPISODIC,
                epistemic_kind='OBSERVATION',source_evidence_id=source_row['source_evidence_id'],text=memory.read(own)['text']))
        with pytest.raises(CoreError,match='SELF_COGNITION_DERIVATION_REQUIRES_INFERENCE'):
            memory.add(MemoryCandidate(entity_id=runtime.config.entity_id,scope='world',memory_type=MemoryType.EPISODIC,
                epistemic_kind='OBSERVATION',source_evidence_id=derived['source_evidence_id'],text=derived['text']))
        backup=tmp_path/'inactive'/'private.db';runtime.store.backup(backup)
        identity=runtime.identity_id
        memory.forget(own,runtime.authority)
        assert not concerns.view()
        with pytest.raises(CoreError,match='SOURCE_DELETED'):anchor_own_occurrence(runtime.store,event,authority=runtime.authority)
        with ContinuityStore(backup,runtime.clock,schema_target=13) as inactive:
            assert inactive.identity['identity_id']==identity and inactive.one('memories',own)['lifecycle']=='DELETED'
        assert not runtime.store.all('actions') and not runtime.store.all('grants')
