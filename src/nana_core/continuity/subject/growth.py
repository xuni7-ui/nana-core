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

    def assertion_view(self, row, *, privacy_classes=None):
        signals=[];hidden=False
        for s in self.store.all('assertion_signals'):
            if s['assertion_id']!=row['assertion_id']:continue
            head=self.store.one('continuity_records',s['record_id'])
            if privacy_classes is not None and head['privacy_class'] not in privacy_classes:
                hidden=hidden or head['lifecycle']=='ACTIVE'
                continue  # Privacy before current_support(), which reads bodies.
            if live_record(self.store,s['record_id']):signals.append(s)
        eligible = [s for s in signals if s['independent']]
        support = {s['root_evidence_id'] for s in eligible if s['direction'] == 'SUPPORT'}
        counter = {s['root_evidence_id'] for s in eligible if s['direction'] == 'COUNTER'}
        # A contradictory interpretation of the same occurrence is not two votes.
        support -= counter
        state = 'ADOPTED' if len(support) >= 2 and len(support) > len(counter) else (
            'DISPUTED' if counter else 'CANDIDATE')
        if hidden:state='UNKNOWN'
        topic = None
        for s in reversed(signals):
            topic = self.records.read(s['record_id'])['payload']['topic']
            break
        return {'assertion_id': row['assertion_id'], 'kind': row['assertion_kind'], 'topic': topic,
            'state': 'SUPERSEDED' if row['state'] == 'SUPERSEDED' else state, 'revision': row['revision'], 'independent_support_count': len(support),
            'supporting_evidence': tuple(sorted(support))[:16], 'counter_evidence': tuple(sorted(counter))[:16],
            'support_evidence_total': len(support), 'counter_evidence_total': len(counter),
            'omitted_signal_count': max(0, len(signals) - 32),
            'confidence': min(0.9, len(support) / (len(support) + len(counter) + 1)),
            'stability': 'ESTABLISHED' if state == 'ADOPTED' and len(support) >= 3 else 'PROVISIONAL',
            'last_reinforced': max((s['created_at_us'] for s in eligible if s['direction'] == 'SUPPORT'), default=None),
            'last_challenged': max((s['created_at_us'] for s in eligible if s['direction'] == 'COUNTER'), default=None),
            'source_record_ids': tuple(dict.fromkeys(s['record_id'] for s in
                ([next(s for s in eligible if s['root_evidence_id'] == root and s['direction'] == direction)
                  for direction in ('SUPPORT','COUNTER')
                  for root in sorted({s['root_evidence_id'] for s in eligible if s['direction'] == direction})[:16]]
                 or signals[:1])))}

    def assertions(self, scope, kind=None, *, privacy_classes=('PUBLIC','PROJECT','PERSONAL','SECRET')):
        return tuple(self.assertion_view(r,privacy_classes=privacy_classes) for r in self.store.all('self_assertions')
                     if r['scope'] == scope and (kind is None or r['assertion_kind'] == kind)
                     and self.store.one('continuity_records', r['record_id'])['privacy_class'] in privacy_classes)

    def _roots(self, memory_id):
        """Resolve inherited evidence: own derivations do not create new roots."""
        return self.source_roots((memory_id,))

    def source_roots(self, memory_ids, *, max_nodes=None):
        """Reuse source ancestry for independent encounters, with an optional bound.

        Existing assertion counting keeps its original semantics. Bounded callers
        must defer ambiguous ancestry rather than pretend it is a new encounter.
        No facts, drive values or second source registry are written here.
        """
        seen, pending, roots = set(), list(memory_ids), set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            if max_nodes is not None and len(seen)>=max_nodes:
                raise CoreError('SOURCE_ROOT_HORIZON_REQUIRES_REVIEW')
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
            if old and old['state'] == 'SUPERSEDED':
                raise CoreError('SUPERSEDED_ASSERTION_CANNOT_SELF_REVIVE')
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
                and not event.source_memory_ids and source['source_kind'] == 'DIRECT_OBSERVATION'
                and (signal.kind!='PERSONALITY_TENDENCY' or not event.result_for_intention_id))
            tx.put('assertion_signals', {'signal_id': uid(), 'assertion_id': key,
                'subject_event_id': row['subject_event_id'], 'direction': signal.direction,
                'root_evidence_id': roots[0], 'independent': independent,
                'record_id': signal_record, 'created_at_us': event.occurred_at_us if event.occurred_at_us is not None else event.observed_at_us})
            current = self.store.one('self_assertions', key)
            view = self.assertion_view(current)
            parent_records = view['source_record_ids']
            prior_record = self.store.one('continuity_records', current['record_id'])
            record = self.records.create(tx, kind='ASSERTION', scope=event.scope, payload=view,
                records=parent_records, supersedes=current['record_id'] if old and prior_record['lifecycle'] != 'DELETED' else None)
            if self.store.schema_target>=7:
                # Explanatory refs are bounded; classification must cover ALL
                # source headers, not merely the displayed subset of roots.
                from ..memory import PRIVACY_RANK
                headers=[self.store.one('continuity_records',s['record_id']) for s in self.store.all('assertion_signals') if s['assertion_id']==key]
                privacy=max((h['privacy_class'] for h in headers if h['lifecycle']=='ACTIVE'),key=PRIVACY_RANK.get)
                tx.update('continuity_records',record,privacy_class=privacy)
            tx.update('self_assertions', key, revision=current['revision'] + int(old is not None),
                state=view['state'], record_id=record, updated_at_us=self.store.clock.utc_now_us())
        if event.relationship_kind:
            extra={}
            if self.store.schema_target>=9:
                details=event.relationship_details
                target=(details.target_event_id or details.supersedes_event_id) if details else None
                if target:
                    prior=self.store.one('relationship_events',target)
                    if not prior or prior['to_entity_id']!=event.entity_id or not live_record(self.store,prior['record_id']):raise CoreError('RELATIONSHIP_TARGET_INVALID')
                    rec=self.records.read(prior['record_id'])
                    if rec['scope']!=event.scope or (prior.get('relation_domain') or 'interaction')!=details.domain:raise CoreError('RELATIONSHIP_TARGET_SCOPE_MISMATCH')
                    if event.relationship_kind=='REPAIR' and prior['relation_kind']!='CONFLICT':raise CoreError('REPAIR_TARGET_NOT_CONFLICT')
                    if details.supersedes_event_id and (event.relationship_kind!='BOUNDARY' or prior['relation_kind']!='BOUNDARY'):raise CoreError('BOUNDARY_REVISION_INVALID')
                if details and details.boundary_state=='WITHDRAWN' and not details.supersedes_event_id:raise CoreError('BOUNDARY_WITHDRAWAL_TARGET_REQUIRED')
                extra={'related_event_id':target,'relation_domain':details.domain if details else 'interaction',
                    'relation_effect':'WITHDRAWN' if details and details.boundary_state=='WITHDRAWN' else 'SUPERSEDES' if details and details.supersedes_event_id else None}
            tx.put('relationship_events', {'relationship_event_id': uid(),
                'subject_event_id': row['subject_event_id'], 'from_entity_id': self.store.identity['identity_id'],
                'to_entity_id': event.entity_id, 'relation_kind': event.relationship_kind,
                'record_id': self.records.create(tx, kind='RELATIONSHIP_EVENT', scope=event.scope,
                    payload={'meaning': event.text, 'kind': event.relationship_kind,
                        **({'details':event.relationship_details.model_dump(mode='json')} if event.relationship_details else {})}, records=(row['record_id'],)),
                'occurred_at_us': event.occurred_at_us if event.occurred_at_us is not None else event.observed_at_us,**extra})

    def relationship(self, entity_id, scope, *, privacy_classes=('PUBLIC','PROJECT','PERSONAL','SECRET')):
        rows = [r for r in self.store.all('relationship_events') if r['to_entity_id'] == entity_id
                and self.store.one('continuity_records', r['record_id'])['scope'] == scope
                and self.store.one('continuity_records', r['record_id'])['privacy_class'] in privacy_classes
                and live_record(self.store, r['record_id'])]
        revisions = {r['subject_event_id']: r['revision'] for r in self.store.all('subject_cycles')}
        next_revision = max(revisions.values(), default=0) + 1
        rows.sort(key=lambda r: (r['occurred_at_us'], revisions.get(r['subject_event_id'], next_revision)))
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
            'source_record_ids': tuple(r['record_id'] for r in rows if r in [x for kind in set(kinds) for x in [a for a in rows if a['relation_kind'] == kind][-2:]])}

    def supersede(self, assertion_id, replacement_id, *, expected_revision):
        """Explicit evidence-backed replacement; never changes canonical identity.

        Both assertions must already exist, and the replacement must have its
        own independently adopted support. A model cannot invent a new value in
        this transition. Old assertion stays terminal even if new support arrives.
        """
        with self.store.transaction('subject.assertion_superseded') as tx:
            old, replacement = self.store.one('self_assertions', assertion_id), self.store.one('self_assertions', replacement_id)
            if not old or not replacement or old['revision'] != expected_revision or old['state'] == 'SUPERSEDED':
                raise CoreError('STALE_OR_TERMINAL_ASSERTION')
            if assertion_id == replacement_id or (old['scope'],old['entity_id'],old['assertion_kind']) != (replacement['scope'],replacement['entity_id'],replacement['assertion_kind']):
                raise CoreError('ASSERTION_REPLACEMENT_MISMATCH')
            if self.assertion_view(replacement)['state'] != 'ADOPTED':
                raise CoreError('ASSERTION_REPLACEMENT_NOT_SUPPORTED')
            self.records.read(old['record_id'])
            record = self.records.create(tx, kind='ASSERTION', scope=old['scope'],
                payload={'state':'SUPERSEDED','superseded_by':replacement_id},
                records=(replacement['record_id'],), supersedes=old['record_id'])
            tx.update('self_assertions', assertion_id, state='SUPERSEDED', record_id=record,
                revision=expected_revision + 1, updated_at_us=self.store.clock.utc_now_us())
