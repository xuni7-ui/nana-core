"""A bounded adapter-local probe, never a production executor or message hook."""
import json
import os
from pathlib import Path
import time
from .observer import LocalProbe, ProbeObserver, new_probe
from .safety import canonical, digest, private_file, read_json, checked_path


def probe_session(workdir, *, host_instance, window_seconds, stop_requested, observer_factory=ProbeObserver):
    # Imports occur only after the launcher has verified the approved package.
    from nana_core.storage import Store
    from nana_core.contracts import CoreError, CAPABILITIES, GrantSpec
    from nana_core.actions import ActionKernel, OperatorAuthority
    from nana_core.initiative import GoalCandidate
    from nana_core.migration.routing import CapabilityRouter
    from nana_core.integration.contracts import HostEvent, RuntimeIntegrationContext, ShadowCapabilityPort
    from nana_core.integration.shadow import ShadowBridge, ShadowDecision, ProposedHostAction
    from nana_core.integration.initiative import InitiativeHostGate

    w = Path(workdir)
    probe_file = w / 'probe_metadata.json'
    probe = LocalProbe(**read_json(probe_file)) if probe_file.exists() else new_probe()
    if not probe_file.exists():
        private_file(probe_file, vars(probe))
    event = HostEvent(host_instance=host_instance, platform='operator_probe', channel='host_local',
                      sender_id='synthetic_operator', event_id=probe.event_id, conversation_id='host_local_probe',
                      timestamp=probe.timestamp, content='Fictional Shadow integration probe 2026',
                      raw_content_reference='synthetic://operator_probe/first-shadow-v1', observation_source='operator_probe')
    # Reference metadata is synthetic. No host API, real conversation, model or
    # fetch port is available to the runtime, even if credentials exist on host.
    s = Store(w / 'shadow.db')
    observer = None
    try:
        identity = dict(s.identity)
        binding = RuntimeIntegrationContext(host_instance=host_instance, expected_identity_id=identity['identity_id'])
        bridge = ShadowBridge(s, binding)
        if any(s.all(t) for t in ('actions', 'attempts', 'grants', 'budgets', 'strategies')):
            raise CoreError('SHADOW_STORE_NOT_EMPTY_OF_EXECUTION_STATE')
        owner_before = s.one('core_meta', 'migration.execution_owner')
        memory_before = s.one('core_meta', 'cloud.memory_protocol')
        baseline_identity = w / 'identity_metadata.json'
        identity_was_present = baseline_identity.exists()
        identity_summary = {'identity_id': identity['identity_id'], 'identity_revision': identity['revision'],
                            'identity_snapshot_hash': digest(json.loads(identity['body_json']))}
        if baseline_identity.exists() and read_json(baseline_identity) != identity_summary:
            raise CoreError('SHADOW_IDENTITY_DRIFT')
        if not baseline_identity.exists():
            private_file(baseline_identity, identity_summary)
        def receive(internal_probe):
            if internal_probe != probe:
                raise CoreError('PROBE_PAYLOAD_MISMATCH')
            # Context is retrieved from persisted Evidence/Observation claims,
            # not fabricated from a model's recollection of this probe.
            observation_id = bridge.adapter.ingest(s, event)
            context_ids = tuple(m['memory_id'] for m in s.all('memory_items')
                                if json.loads(m['body_json']).get('epistemic_kind') == 'OBSERVATION'
                                and any(r.get('event_id') == observation_id for r in json.loads(m['body_json']).get('source_refs', [])))
            if len(context_ids) != 1:
                raise CoreError('PROBE_MEMORY_CONTEXT_AMBIGUOUS')
            decision = ShadowDecision(interpretation='Operator-created non-private local probe',
                                      memory_ids=context_ids, evidence_event_ids=(observation_id,),
                                      goal_purpose='Assess probe metadata without acting',
                                      planned_actions=(ProposedHostAction(capability='astrbot.message.send',
                                          resource='synthetic://no_delivery', reason='Exercise hard barrier only'),),
                                      rationale='Engineering fixture cites persisted observation; draft external action must be stopped')
            return bridge.observe(event, decision)
        observer = observer_factory(receive)
        token = observer.install()
        result = observer.emit(probe, token)
        n_events = len(s.all('events'))
        assert observer.emit(probe, token) == result and len(s.all('events')) == n_events
        eid = result['observation_event_id']
        candidate, candidate_body = InitiativeHostGate(s).propose_and_evaluate(GoalCandidate(
            purpose='Assess probe metadata without acting', intent='information', evidence_event_ids=(eid,),
            need=.8, importance=.6, urgency=.5, confidence=1., disturbance=0.))
        barrier_results = []
        authority = OperatorAuthority('shadow-probe-operator')
        port = ShadowCapabilityPort()
        router = CapabilityRouter(s, {c: port for c in CAPABILITIES}, authority)
        kernel = ActionKernel(s, router.bind('shadow', authority), authority)
        # Exercise BOTH the persistent Store fence and the port barrier, with no
        # actual backend. Even a mistakenly constructed kernel cannot dispatch.
        tests = [
            ('plan_execute', lambda: bridge.execute(result['plan_draft'])),
            ('kernel_propose', lambda: kernel.propose('reading.source.read', 'source://synthetic/probe', {'source_id': 'source://synthetic/probe'})),
            ('kernel_budget', lambda: kernel.set_budgets({'write_attempts': 1, 'external_requests': 1, 'cost_micro_units': 1}, authority)),
            ('kernel_grant', lambda: kernel.grant(GrantSpec(capabilities=('reading.source.read',), resources=('source://synthetic/probe',), not_before_us=0, expires_at_us=2**62), authority)),
            ('capability_execute', lambda: port.execute(None)),
        ]
        for name, invoke in tests:
            try:
                invoke()
            except CoreError as exc:
                if exc.code != 'SHADOW_BLOCKED':
                    raise
                barrier_results.append({'check': name, 'status': exc.code})
            else:
                raise CoreError('SHADOW_BARRIER_FAILED')
        audit_key = 'first_shadow.barrier:' + eid
        if not s.one('core_meta', audit_key):
            with s.transaction('cloud.probe_actions_blocked', {'checks': barrier_results, 'observation_event_id': eid}) as tx:
                tx.put('core_meta', {'key': audit_key, 'value_json': canonical({'checks': barrier_results})})
        # Read the persisted Evidence and compare canonical metadata, rather than
        # comparing the input object to itself or claiming the host AI replied.
        persisted_event = s.event(eid)
        stored = json.loads(s.artifact(persisted_event['artifact_id']))
        stored_host = stored['host_event']
        metadata_keys = ('event_id', 'timestamp', 'observation_source', 'conversation_id', 'platform')
        matches = {k: event.model_dump()[k] == stored_host[k] for k in metadata_keys}
        reconciliation = {'status': 'PASS' if all(matches.values()) else 'FAIL', 'matches': matches,
            'legacy': {k: event.model_dump()[k] for k in metadata_keys}, 'core': {k: stored_host[k] for k in metadata_keys},
            'core_event_id': eid, 'dedup_key': persisted_event['source_key'], 'decision_trace': audit_key,
            'legacy_scope': 'adapter-local synthetic metadata; no AstrBot AI reply or private stream',
            'chat_quality_assessed': False}
        if not all(matches.values()):
            raise CoreError('SHADOW_RECONCILIATION_FAILED')
        deadline = time.monotonic() + window_seconds
        samples = 0
        while True:
            if any(s.all(t) for t in ('actions', 'attempts', 'grants', 'budgets', 'strategies')):
                raise CoreError('SHADOW_EXECUTION_STATE_DETECTED')
            if s.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise CoreError('SHADOW_STORE_UNHEALTHY')
            samples += 1
            if stop_requested() or time.monotonic() >= deadline:
                break
            time.sleep(min(.1, max(0., deadline - time.monotonic())))
        counts = {t: len(s.all(t)) for t in ('actions', 'attempts', 'grants', 'budgets', 'strategies', 'goals', 'plans', 'jobs')}
        observer.uninstall()
        if observer.active:
            raise CoreError('OBSERVER_UNINSTALL_FAILED')
        if owner_before != s.one('core_meta', 'migration.execution_owner') or memory_before != s.one('core_meta', 'cloud.memory_protocol'):
            raise CoreError('AUTHORITY_DRIFT')
        report = {'status': 'PASS', 'scope': 'ENGINEERING_SHADOW', 'host_binding': 'UNVERIFIED',
            'FIRST_REAL_CLOUD_SHADOW': 'NOT_RUN', 'identity': identity_summary, 'identity_restored': identity_was_present,
            'memory_context_ids': result['decision']['memory_ids'],
            'probe_count_unique': 1, 'probe_delivery_attempts_this_run': 2, 'probe_external_delivery': False,
            'probe_event_id': eid, 'evidence_artifact_id': persisted_event['artifact_id'],
            'evidence_hash': digest(s.artifact(persisted_event['artifact_id'])), 'goal_candidate_id': candidate,
            'goal_candidate_state': candidate_body['state'], 'shadow_plan_count': 1, 'shadow_decision_count': 1,
            'plan_storage': 'ShadowBridge draft in memory_items, not executable plans table',
            'barrier': barrier_results, 'counts': counts, 'reconciliation': reconciliation,
            'observer_kind': 'adapter_local_probe_only', 'observer_lifecycle': observer.lifecycle,
            'observer_removed': True, 'health_samples': samples, 'execution_owner_changed': False,
            'memory_authority_changed': False, 'production_calls': 0, 'production_action_count': 0,
            'production_grant_count': 0, 'production_budget_count': 0, 'private_memory_records_read': 0,
            'private_message_plaintext_read': 0, 'profile_plaintext_read': 0, 'secret_values_read': 0,
            'external_messages_sent': 0, 'Iris_writes': 0, 'real_model_calls': 0, 'public_internet_calls': 0,
            'E12': 'NOT_RUN', 'AstrBot_restart': False, 'legacy_health_after': 'UNKNOWN',
            'production_source_drift': 'UNKNOWN; no production channel inspected', 'process_id': os.getpid()}
        return report
    finally:
        try:
            if observer is not None:
                observer.uninstall()
        finally:
            s.close()
