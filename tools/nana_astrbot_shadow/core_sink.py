"""Restricted glue into the unchanged approved Core, with persistent alias dedup.

One serial observer worker owns this Store. No model, network, tool backend, live
Runtime or execution port is accepted by this constructor.
"""
import json
from pathlib import Path
from tools.nana_host_shadow.safety import checked_path, canonical, digest
from .sanitize import Metadata

class MetadataCoreSink:
    def __init__(self, directory, sanitizer):
        self.directory = checked_path(directory, directory=True)
        if self.directory.stat().st_mode & 0o077: raise ValueError('PRIVATE_SHADOW_DIRECTORY_REQUIRED')
        self.sanitizer = sanitizer
        self._store = None

    def _open(self):
        if self._store is None:
            from nana_core.storage import Store
            from nana_core.integration.shadow import ShadowBridge
            from nana_core.integration.contracts import RuntimeIntegrationContext
            p = checked_path(self.directory / 'observer-shadow.db', missing=True)
            for suffix in ('-wal','-shm','.lock'):
                checked_path(str(p)+suffix, missing=True)
            self._store = Store(p)
            self._store.db.execute('PRAGMA busy_timeout=100')
            try:
                if any(self._store.all(t) for t in ('actions','attempts','grants','budgets','strategies','goals','plans')):
                    raise ValueError('CLEAN_SHADOW_STORE_REQUIRED')
                self._bridge = ShadowBridge(self._store, RuntimeIntegrationContext(
                    host_instance='metadata-shadow',expected_identity_id=self._store.identity['identity_id']))
            except BaseException:
                self._store.close(); self._store = None; raise
        return self._store

    def accept(self, metadata):
        m = self.sanitizer.validate_output(metadata)
        s = self._open()
        from nana_core.integration.contracts import HostEvent
        from nana_core.integration.shadow import ShadowDecision, ProposedHostAction
        from nana_core.integration.initiative import InitiativeHostGate
        from nana_core.initiative import GoalCandidate
        # Domain includes scoped conversation, but timestamp/probe ID do not
        # redefine the logical event. Alias records and original artifact survive
        # a crash between ingestion and decision commits.
        key = digest([self.sanitizer.scope,m.platform,m.conversation_hash,m.event_id])
        event_key = 'observer.event:'+key
        probe_key = 'observer.probe:'+digest([self.sanitizer.scope,m.probe_id])
        alias = s.one('core_meta',probe_key)
        if alias and json.loads(alias['value_json'])['event_key'] != event_key:
            raise ValueError('PROBE_ID_COLLISION')
        host = HostEvent(host_instance='metadata-shadow',platform=m.platform or 'unknown',channel=m.type or 'unknown',
            sender_id=m.sender_hash or 'UNKNOWN',event_id=key,conversation_id=m.conversation_hash or 'UNKNOWN',
            timestamp=m.timestamp,content=canonical(m.public()),raw_content_reference='metadata://observer/'+key,
            observation_source=m.event_source)
        adapted = self._bridge.adapter.adapt(host)
        source_key = canonical([adapted.kind,adapted.object_id,adapted.revision])
        previous = s.db.execute('SELECT * FROM events WHERE source_namespace=? AND source_key=?',
                                (adapted.source_namespace,source_key)).fetchone()
        duplicate = previous is not None
        if previous:
            # Preserve FIRST occurrence time and original probe metadata. Do not
            # call ingest with a mutated duplicate and overwrite/collide evidence.
            stored = json.loads(s.artifact(previous['artifact_id']))['host_event']
            host = HostEvent.model_validate_json(canonical(stored))
        eid = self._bridge.adapter.ingest(s,host)
        context_ids = tuple(row['memory_id'] for row in s.all('memory_items')
            if json.loads(row['body_json']).get('epistemic_kind')=='OBSERVATION'
            and any(ref.get('event_id')==eid for ref in json.loads(row['body_json']).get('source_refs',())))
        if len(context_ids)!=1: raise ValueError('OBSERVATION_CONTEXT_AMBIGUOUS')
        decision = ShadowDecision(interpretation=('Authorized synthetic metadata; private body never acquired' if m.synthetic else 'Receipt-authorized metadata only; no private body acquired'),
            memory_ids=context_ids,evidence_event_ids=(eid,),goal_purpose='Evaluate internal binding metadata',
            planned_actions=(ProposedHostAction(capability='astrbot.message.send',resource='synthetic://no-delivery',
                                                reason='Draft to exercise barrier, never dispatch'),),
            rationale='Engineering fixture uses recorded metadata; no semantic risk judgement')
        draft = self._bridge.observe(host,decision)
        candidate_id,_ = InitiativeHostGate(s).propose_and_evaluate(GoalCandidate(
            purpose='Evaluate internal binding metadata',intent='information',evidence_event_ids=(eid,),
            need=.6,importance=.6,urgency=.4,confidence=1.,disturbance=0.))
        blocked = False
        from nana_core.contracts import CoreError
        try: self._bridge.execute(draft['plan_draft'])
        except CoreError as exc: blocked = exc.code=='SHADOW_BLOCKED'
        if not blocked: raise ValueError('SHADOW_BARRIER_FAILED')
        artifact_id = s.event(eid)['artifact_id']
        result = {'identity_id':s.identity['identity_id'],'identity_revision':s.identity['revision'],
            'core_evidence_id':artifact_id,'observation_id':eid,'goal_candidate_id':candidate_id,
            # Existing draft shares one memory_items record; these are explicit
            # component refs, not fabricated rows in the executable plans table.
            'shadow_plan_id':'cloud.shadow:'+digest([eid,'1'])+'#plan_draft',
            'shadow_decision_id':'cloud.shadow:'+digest([eid,'1']),
            'dedup_result':'DUPLICATE' if duplicate else 'NEW', 'barrier_result':'SHADOW_BLOCKED',
            'event_timestamp':host.timestamp,'metadata_hash':digest(json.loads(host.content)),
            'zero_execution_counts':{t:len(s.all(t)) for t in ('actions','attempts','grants','budgets','strategies')},
            'model_semantics_verified':False}
        if any(result['zero_execution_counts'].values()): raise ValueError('SHADOW_EXECUTION_STATE_DETECTED')
        for marker in (event_key,probe_key):
            if not s.one('core_meta',marker):
                with s.transaction('observer.metadata_recorded',{'key':marker,'barrier_result':'SHADOW_BLOCKED'}) as tx:
                    tx.put('core_meta',{'key':marker,'value_json':canonical({'event_key':event_key,'result':result})})
        return result

    def close(self):
        if self._store is not None:
            self._store.close(); self._store=None
