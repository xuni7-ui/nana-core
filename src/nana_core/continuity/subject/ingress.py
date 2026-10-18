"""Admission is a policy decision before long-term capture, not capture-all."""
import json
from ...contracts import CoreError
from ...storage import canonical, digest, uid
from ..contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from ..memory import MemoryService
from ..records import RecordService
from .contracts import SubjectInput


def admission(event: SubjectInput):
    if event.retention == 'DO_NOT_REMEMBER':
        return 'IGNORE', ('explicit non-retention takes priority',)
    if event.kind == 'WAKE':
        return 'TEMPORARY', ('wake is a condition, not a new lived experience',)
    if event.preference_signal or event.relationship_kind or event.constraint_memory_ids or event.positive_request or event.relational_request or (event.interaction_signal and event.interaction_signal.basis=='EXPLICIT' and event.interaction_signal.kind in {'DECLINE_DEPTH','REOPEN'}):
        return 'KEEP', ('future self/relationship/project relevance',)
    if event.significance in {'RELEVANT', 'HIGH'} or event.novelty == 'HIGH':
        return 'KEEP', ('significant or novel source occurrence',)
    if event.risk == 'HIGH':
        return 'FORGET_LATER', ('sensitive transient assessment; no long-term payload in v1',)
    return 'TEMPORARY', ('ordinary low-salience input needs no permanent body',)


class SubjectIngress:
    def __init__(self, store):
        self.store, self.memory, self.records = store, MemoryService(store), RecordService(store)

    def ingest(self, event: SubjectInput):
        if event.interaction_signal and self.store.schema_target<9:raise CoreError('CONTEXT_FIT_SCHEMA_REQUIRED')
        now = self.store.clock.utc_now_us()
        if event.surface:
            from ..surfaces import source_key
            if event.surface.subject_id != self.store.identity['identity_id'] or event.source_key != source_key(event.surface):
                raise CoreError('SURFACE_BINDING_INVALID')
        if event.observed_at_us > now or (event.occurred_at_us is not None and event.occurred_at_us > event.observed_at_us):
            raise CoreError('INVALID_SUBJECT_TIME')
        if not self.store.one('entities', event.entity_id):
            raise CoreError('UNKNOWN_SUBJECT_ENTITY')
        previous = self.store.db.execute('SELECT * FROM subject_events WHERE source_key=?', (event.source_key,)).fetchone()
        if previous:
            row = dict(previous)
            if row['entity_id'] != event.entity_id or row['scope'] != event.scope or row['kind'] != event.kind or row['origin'] != event.origin:
                raise CoreError('SUBJECT_SOURCE_COLLISION')
            if row['record_id']:
                try:
                    old = self.records.read(row['record_id'])['payload']['input']
                except CoreError:
                    raise CoreError('SUBJECT_SOURCE_RETIRED') from None
                if SubjectInput.model_validate_json(canonical(old)).model_dump(mode='json') != json.loads(event.model_dump_json()):
                    raise CoreError('SUBJECT_SOURCE_COLLISION')
            # Nonretained input intentionally has no content hash that might leak it.
            return row
        request_target=None
        if self.store.schema_target>=10 and event.relational_request:
            request_target='relational-request:'+digest([event.scope,event.entity_id,event.relational_request.request_id])
            if self.store.db.execute("SELECT 1 FROM continuity_records WHERE record_kind='SUBJECT_EVENT' AND target_id=? LIMIT 1",(request_target,)).fetchone():
                raise CoreError('RELATIONAL_REQUEST_ID_REUSED')
        if event.interaction_signal and event.interaction_signal.basis=='EXPLICIT' and event.interaction_signal.kind in {'DECLINE_DEPTH','REOPEN'}:
            from .context_fit import boundary_key
            request_target=boundary_key(event.entity_id,event.scope,event.interaction_signal.topic_key)
        support = tuple(dict.fromkeys((*event.source_memory_ids, *event.constraint_memory_ids)))
        for memory_id in support:
            item = self.memory.read(memory_id)
            if item['scope'] != event.scope:
                raise CoreError('CROSS_SCOPE_SUBJECT_INPUT')
            if event.retention == 'DO_NOT_REMEMBER':
                raise CoreError('NONRETENTION_INPUT_CANNOT_PERSIST_DERIVATION')
        outcome, reasons = admission(event)
        memory_id = None
        if outcome == 'KEEP' and event.text:
            source = self.memory.capture(EvidenceInput(provenance=Provenance(
                source_namespace='synthetic.subject', source_reference=digest(event.source_key.encode()),
                source_kind='USER_STATEMENT' if event.origin == 'USER' else 'DIRECT_OBSERVATION'),
                text=event.text, privacy_class=event.privacy_class, event_time_us=event.occurred_at_us,
                observed_time_us=event.observed_at_us))
            memory_id = self.memory.add(MemoryCandidate(entity_id=event.entity_id, scope=event.scope,
                memory_type=MemoryType.RELATIONAL if event.relationship_kind else MemoryType.EPISODIC,
                epistemic_kind='STATEMENT' if event.origin == 'USER' else 'OBSERVATION',
                source_evidence_id=source, text=event.text, confidence=0.8,
                importance=0.8 if event.significance == 'HIGH' else 0.5,
                significance=0.7 if event.significance in {'RELEVANT','HIGH'} else 0.2,
                derived_from=support))
        # No body in an immutable event; text and structured source facets are
        # deletable and dependency-bound. Wake copies no user text.
        with self.store.transaction('subject.input_ingested') as tx:
            event_id, record = uid(), None
            if memory_id or (event.kind=='WAKE' and support):
                record = self.records.create(tx, kind='SUBJECT_EVENT', scope=event.scope,
                    payload={'input': json.loads(event.model_dump_json()), 'admission_reasons': reasons},target_id=request_target,
                    memories=(*support, *((memory_id,) if memory_id else ())))
            tx.put('subject_events', {'subject_event_id': event_id, 'source_key': event.source_key,
                'entity_id': event.entity_id, 'scope': event.scope, 'kind': event.kind, 'origin': event.origin,
                'record_id': record, 'memory_id': memory_id, 'occurred_at_us': event.occurred_at_us,
                'observed_at_us': event.observed_at_us, 'ingested_at_us': now, 'admission': outcome})
        return self.store.one('subject_events', event_id)
