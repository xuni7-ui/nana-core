"""Original-C counterfactuals; model transport here is explicitly synthetic."""

from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.world_loop.cognition import CognitionSession, InterestProposal, StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.memory import MemoryService
from nana_core.presence.authority import VirtualClock
from tests.world_loop.helpers import capture, fresh, policy, SECOND


def test_fresh_supported_encounter_reaches_original_c_after_restart_and_can_change_interest(tmp_path):
    path = tmp_path / 'subject/self.db'
    clock = VirtualClock()
    value = ['HIGH']

    def propose(request):
        return StructuredProposal(
            interpretation='Synthetic evidence for reconsideration, never authority',
            source_refs=request.source_context_refs,
            interests=(InterestProposal(topic='independent-question', motivation_source='CURIOSITY',
                source_memory_ids=request.primary_source_refs, expected_value=value[0],
                interpretation='A changed sourced appraisal', possible_behaviors=('EXPLORE',)),))

    with provider_harness(proposer=propose) as (transport, calls):
        with fresh(path, clock) as r:
            identity = r.identity_id
            session = CognitionSession(r, transport, policy())
            concerns = ConcernService(r, resources=('synthetic://public-question',))
            source = capture(r, 'first-question', {'data': 'A promising independent question'})
            proposal = session.execute(session.prepare('first-question', 'INTERPRET', (source,)))['record_id']
            cid = concerns.offer(proposal)[0]
            event = concerns.opportunity().input
            before = r.subject.run(event)
            assert before.intention.behavior == 'EXPLORE'
            concerns.after_cycle(before, event, None)
            assert r.store.one('open_concerns', cid)['state'] == 'PROPOSED'
            assert concerns.opportunity() is None
            assert concerns.offer(proposal) == ()
            if before.intention_id:
                row = r.store.one('subject_intentions', before.intention_id)
                r.subject.transition_intention(before.intention_id, expected_revision=row['revision'], state='COMPLETED')
        with fresh(path, clock) as r:
            concerns = ConcernService(r, resources=('synthetic://public-question',))
            assert r.identity_id == identity and concerns.opportunity() is None
            value[0] = 'LOW'
            clock.advance(SECOND)
            changed = capture(r, 'counter-observation', {'data': 'New independent evidence reduces its value'})
            session = CognitionSession(r, transport, policy())
            proposal = session.execute(session.prepare('changed-question', 'INTERPRET', (changed,)))['record_id']
            assert concerns.offer(proposal) == (cid,)
            event = concerns.opportunity().input
            after = r.subject.run(event)
            assert after.intention.behavior == 'IGNORE'
            assert after.cycle_id != before.cycle_id
            concerns.after_cycle(after, event, None)
            assert r.store.one('open_concerns', cid)['state'] == 'ABANDONED'
            assert concerns.opportunity() is None
            assert calls['calls'] == 2
            assert not r.store.all('goals') and not r.store.all('grants') and not r.store.all('actions')
            MemoryService(r.store, r.authority).forget(changed, r.authority)
            assert concerns.view() == () and concerns.opportunity() is None


def test_need_uses_relevant_visible_failures_before_bounded_history_limit(tmp_path):
    """Synthetic history distractors never stand in for actual life evidence."""
    from nana_core.continuity.learning import ExperienceService, ExperienceInput, StructuredQualityCheck
    from nana_core.continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
    from nana_core.continuity.subject.experience_need import project_need
    from nana_core.storage import digest

    with fresh(tmp_path / 'subject/self.db') as r:
        memory = MemoryService(r.store)
        service = ExperienceService(r.store, r.authority)

        def episode(key, *, scope='world', privacy='PUBLIC', passed=True):
            text = '{"data": 1}'
            evidence = memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.causal-history',
                source_reference=key, source_kind='DIRECT_OBSERVATION'), text=text, privacy_class=privacy,
                observed_time_us=r.clock.utc_now_us()))
            mid = memory.add(MemoryCandidate(entity_id='observer', scope=scope, memory_type=MemoryType.EPISODIC,
                epistemic_kind='OBSERVATION', source_evidence_id=evidence, text=text))
            check = StructuredQualityCheck(result_memory_id=mid,
                result_artifact_digest=digest(r.store.artifact(memory.read(mid)['payload_artifact_id'])),
                expected_digest=digest(1 if passed else 2), passed=passed)
            proof = memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.structured-check',
                source_reference=key, source_kind='SYSTEM_VERIFICATION'), text=check.model_dump_json(),
                privacy_class=privacy, observed_time_us=r.clock.utc_now_us()))
            proof_mid = memory.add(MemoryCandidate(entity_id='observer', scope=scope, memory_type=MemoryType.EPISODIC,
                epistemic_kind='OBSERVATION', source_evidence_id=proof, text=check.model_dump_json()))
            service.record(ExperienceInput(context_memory_ids=(mid,), scope=scope, task_class='known-gap',
                decision='Explicit synthetic counterfactual history '+key, result_memory_id=mid,
                verification_memory_id=proof_mid))
            return mid

        gap = episode('actual-test-gap', passed=False)
        for index in range(33):
            episode('other-scope-'+str(index), scope='another-platform', passed=False)
            episode('private-'+str(index), privacy='PERSONAL', passed=False)
            episode('success-'+str(index), passed=True)
        view = project_need(r.store, 'known-gap', scope='world', privacy_classes=('PUBLIC',), source_memory_ids=(gap,))
        assert view.state == 'OPEN' and len(view.source_record_ids) == 1
        MemoryService(r.store, r.authority).forget(gap, r.authority)
        assert project_need(r.store, 'known-gap', scope='world', privacy_classes=('PUBLIC',)).state == 'UNKNOWN'


def test_fresh_encounter_does_not_unpark_ambiguous_provider_completion(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionBudget

    def propose(request):
        return StructuredProposal(interpretation='Synthetic independent question', source_refs=request.source_context_refs,
            interests=(InterestProposal(topic='held-question', motivation_source='CURIOSITY',
                source_memory_ids=request.primary_source_refs, expected_value='HIGH',
                interpretation='An attention candidate, not permission', possible_behaviors=('EXPLORE',)),))

    with fresh(tmp_path / 'subject/self.db') as r, provider_harness(proposer=propose) as (transport, metrics):
        session = CognitionSession(r, transport, policy())
        concerns = ConcernService(r, resources=('synthetic://public-question',))
        first = capture(r, 'held-first', {'data': 'First source'})
        cid = concerns.offer(session.execute(session.prepare('held-first', 'INTERPRET', (first,)))['record_id'])[0]
        event = concerns.opportunity().input
        cycle = r.subject.run(event)
        concerns.after_cycle(cycle, event, None)
        changed = capture(r, 'held-new', {'data': 'A legitimate fresh encounter'})
        prepared_proposal = session.execute(session.prepare('held-new', 'INTERPRET', (changed,)))['record_id']
        metrics['delay'] = .2
        uncertain = session.prepare('independent-timeout', 'INTERPRET', (changed,), budget=CognitionBudget(timeout_ms=50))
        assert session.execute(uncertain)['state'] == 'UNKNOWN'
        assert concerns.offer(prepared_proposal) == (cid,)
        assert r.store.one('open_concerns', cid)['state'] == 'PROPOSED'
        assert concerns.opportunity() is None
        assert metrics['calls'] == 3
        assert not r.store.all('actions') and not r.store.all('grants')


def test_recorded_source_keeps_its_domain_in_managed_c_attention(tmp_path):
    from nana_core.continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
    from nana_core.continuity.records import RecordService

    def propose(request):
        return StructuredProposal(interpretation='Fixture interpretation of a project source', source_refs=request.source_context_refs,
            interests=(InterestProposal(topic='recorded-source-question', motivation_source='CURIOSITY',
                source_memory_ids=request.primary_source_refs, expected_value='HIGH',
                interpretation='The source keeps its origin even with a fixture model', possible_behaviors=('EXPLORE',)),))

    with fresh(tmp_path / 'subject/self.db') as r, provider_harness(proposer=propose) as (transport, _):
        memory = MemoryService(r.store)
        evidence = memory.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT',
            source_namespace='recorded.project.material', source_reference='qualification-source-domain',
            source_kind='DIRECT_OBSERVATION'), text='Project-owned source-domain qualification material',
            privacy_class='PROJECT', observed_time_us=r.clock.utc_now_us()))
        mid = memory.add(MemoryCandidate(entity_id=r.config.entity_id, scope=r.config.scopes[0],
            memory_type=MemoryType.EPISODIC, epistemic_kind='OBSERVATION', source_evidence_id=evidence,
            text='Project-owned source-domain qualification material'))
        session = CognitionSession(r, transport, policy())
        concerns = ConcernService(r, resources=('synthetic://public-question',))
        cid = concerns.offer(session.execute(session.prepare('recorded-source', 'INTERPRET', (mid,)))['record_id'])[0]
        event = concerns.opportunity().input
        assert event.domain == 'DEVELOPMENT_MATERIAL' and event.source_key.startswith('development.world.concern.')
        cue_source = memory.read(event.source_memory_ids[0])['source_provenance']
        assert cue_source['domain'] == 'DEVELOPMENT_PROJECT' and cue_source['source_kind'] == 'MODEL_DERIVATION'
        cycle = r.subject.run(event)
        assert cycle.intention.behavior == 'EXPLORE'
        concerns.after_cycle(cycle, event, None)
        MemoryService(r.store, r.authority).forget(mid, r.authority)
        assert not RecordService(r.store).current_support(r.store.one('open_concerns', cid)['record_id'])
        assert concerns.view() == ()
