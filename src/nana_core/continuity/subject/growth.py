"""Evidence-backed assertion/relationship transitions, never identity mutations."""
import json
from ...contracts import CoreError
from ...storage import canonical, digest, uid
from ..records import RecordService


def live_record(store, record_id):
    row = store.one('continuity_records', record_id)
    return bool(row and row['lifecycle'] == 'ACTIVE' and RecordService(store).current_support(record_id))


class Growth:
    def __init__(self, store):
        self.store, self.records = store, RecordService(store)

    def assertion_view(self, row):
        signals = [s for s in self.store.all('assertion_signals')
                   if s['assertion_id'] == row['assertion_id'] and live_record(self.store, s['record_id'])]
        eligible = [s for s in signals if s['independent']]
        support = {s['root_evidence_id'] for s in eligible if s['direction'] == 'SUPPORT'}
        counter = {s['root_evidence_id'] for s in eligible if s['direction'] == 'COUNTER'}
        # A contradictory interpretation of the same occurrence is not two votes.
        support -= counter
        state = 'ADOPTED' if len(support) >= 2 and len(support) > len(counter) else (
            'DISPUTED' if counter else 'CANDIDATE')
        topic = None
        for s in reversed(signals):
            topic = self.records.read(s['record_id'])['payload']['topic']
            break
        return {'assertion_id': row['assertion_id'], 'kind': row['assertion_kind'], 'topic': topic,
            'state': state, 'revision': row['revision'], 'independent_support_count': len(support),
            'supporting_evidence': tuple(sorted(support)), 'counter_evidence': tuple(sorted(counter)),
            'confidence': min(0.9, len(support) / (len(support) + len(counter) + 1)),
            'stability': 'ESTABLISHED' if state == 'ADOPTED' and len(support) >= 3 else 'PROVISIONAL',
            'last_reinforced': max((s['created_at_us'] for s in eligible if s['direction'] == 'SUPPORT'), default=None),
            'last_challenged': max((s['created_at_us'] for s in eligible if s['direction'] == 'COUNTER'), default=None),
            'source_record_ids': tuple(s['record_id'] for s in signals)}

    def assertions(self, scope, kind=None):
        return tuple(self.assertion_view(r) for r in self.store.all('self_assertions')
                     if r['scope'] == scope and (kind is None or r['assertion_kind'] == kind))

    def _roots(self, memory_id):
        """Resolve inherited evidence: own derivations do not create new roots."""
        seen, pending, roots = set(), [memory_id], set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            memory = self.records.memory.read(current)
            deps = list(self.store.db.execute("SELECT * FROM memory_dependencies WHERE memory_id=? AND parent_kind='MEMORY'", (current,)))
            if deps:
                pending.extend(d['parent_id'] for d in deps)
            else:
                roots.add(memory['source_evidence_id'])
        return tuple(sorted(roots))

    def apply(self, tx, event, row):
        if not row['record_id'] or not row['memory_id']:
            return
        signal = event.preference_signal
        if signal:
            # Derivations may cite a signal, but cannot increase independent count.
            roots = self._roots(row['memory_id'])
            if not roots:
                return
            key = digest(canonical([signal.kind, signal.topic, event.scope, self.store.identity['identity_id']]).encode())
            old = self.store.one('self_assertions', key)
            signal_record = self.records.create(tx, kind='ASSERTION_SIGNAL', scope=event.scope,
                payload={'topic': signal.topic, 'interpretation': signal.interpretation, 'direction': signal.direction},
                records=(row['record_id'],))
            if not old:
                tx.put('self_assertions', {'assertion_id': key, 'assertion_kind': signal.kind,
                    'topic_key': digest(signal.topic.encode()), 'scope': event.scope,
                    'entity_id': self.store.identity['identity_id'], 'revision': 1,
                    'state': 'CANDIDATE', 'record_id': signal_record, 'updated_at_us': self.store.clock.utc_now_us()})
            source = self.records.memory.evidence(roots[0])
            # Source supports must be direct, and observations cannot derive their
            # independence from earlier own choices/model/reflection outcomes.
            independent = int(event.origin == 'ENVIRONMENT' and event.kind in {'PLAY','OUTCOME'}
                and not event.source_memory_ids and source['source_kind'] == 'DIRECT_OBSERVATION')
            tx.put('assertion_signals', {'signal_id': uid(), 'assertion_id': key,
                'subject_event_id': row['subject_event_id'], 'direction': signal.direction,
                'root_evidence_id': roots[0], 'independent': independent,
                'record_id': signal_record, 'created_at_us': event.occurred_at_us or event.observed_at_us})
            current = self.store.one('self_assertions', key)
            view = self.assertion_view(current)
            parent_records = view['source_record_ids']
            prior_record = self.store.one('continuity_records', current['record_id'])
            record = self.records.create(tx, kind='ASSERTION', scope=event.scope, payload=view,
                records=parent_records, supersedes=current['record_id'] if old and prior_record['lifecycle'] != 'DELETED' else None)
            tx.update('self_assertions', key, revision=current['revision'] + int(old is not None),
                state=view['state'], record_id=record, updated_at_us=self.store.clock.utc_now_us())
        if event.relationship_kind:
            tx.put('relationship_events', {'relationship_event_id': uid(),
                'subject_event_id': row['subject_event_id'], 'from_entity_id': self.store.identity['identity_id'],
                'to_entity_id': event.entity_id, 'relation_kind': event.relationship_kind,
                'record_id': self.records.create(tx, kind='RELATIONSHIP_EVENT', scope=event.scope,
                    payload={'meaning': event.text, 'kind': event.relationship_kind}, records=(row['record_id'],)),
                'occurred_at_us': event.occurred_at_us or event.observed_at_us})

    def relationship(self, entity_id, scope):
        rows = [r for r in self.store.all('relationship_events') if r['to_entity_id'] == entity_id
                and live_record(self.store, r['record_id'])
                and self.store.one('continuity_records', r['record_id'])['scope'] == scope]
        rows.sort(key=lambda r: (r['occurred_at_us'], r['relationship_event_id']))
        kinds = [r['relation_kind'] for r in rows]
        unresolved_conflict = 'CONFLICT' in kinds and ('REPAIR' not in kinds or
            max(i for i,x in enumerate(kinds) if x == 'CONFLICT') > max(i for i,x in enumerate(kinds) if x == 'REPAIR'))
        boundary = 'BOUNDARY' in kinds
        familiar = len(set(kinds) & {'SHARED_HISTORY','SHARED_PROJECT','TRUST','SHARED_JOKE'}) >= 2
        return {'entity_id': entity_id, 'familiarity': 'FAMILIAR' if familiar else 'ACQUAINTED' if rows else 'UNKNOWN',
            'social_distance': 'CAUTIOUS' if unresolved_conflict else 'NEAR' if familiar else 'RESPECTFUL',
            'playfulness_permission': 'WITHHELD' if boundary or unresolved_conflict else 'CONTEXTUAL' if familiar and 'SHARED_JOKE' in kinds else 'UNESTABLISHED',
            'self_disclosure_comfort': 'LIMITED' if boundary or not familiar else 'CONTEXTUAL',
            'challenge_comfort': 'DIRECT_WITH_CARE' if familiar and not unresolved_conflict else 'EXPLAIN_FIRST',
            'interaction_style': 'REPAIR_FIRST' if unresolved_conflict else 'WARM_PLAYFUL' if familiar and 'SHARED_JOKE' in kinds and not boundary else 'WARM_DIRECT' if familiar else 'RESPECTFUL_EXPLICIT',
            'source_record_ids': tuple(r['record_id'] for r in rows)}
