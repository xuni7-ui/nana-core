"""Synthetic Phase A projections in the original Store, never a second database.

Withdrawal suppresses retrieval and dependent projections. It does not purge
append-only source artifacts; physical private-data deletion remains blocked.
"""
import json
from nana_core.contracts import CoreError
from nana_core.migration.iris import IrisAdapter
from nana_core.storage import canonical, digest
from .contracts import (SyntheticCapture, Claim, Relationship, Commitment,
                        SelfChangeCandidate, utc_us)

PREFIX = 'next_stage.'
ZERO = ('actions', 'attempts', 'grants', 'budgets', 'strategies', 'goals')


class PhaseAPrototype:
    def __init__(self, store):
        self.store = store
        if any(store.all(t) for t in ZERO):
            raise CoreError('FIXTURE_MEMORY_STORE_ONLY')
        binding = {'domain': 'SYNTHETIC_ONLY', 'identity_id': store.identity['identity_id']}
        prior = store.one('core_meta', PREFIX+'binding')
        if prior and json.loads(prior['value_json']) != binding:
            raise CoreError('FIXTURE_BINDING_MISMATCH')
        if not prior:
            if store.all('memory_items') or any(e['kind'] != 'identity.created' for e in store.all('events')):
                raise CoreError('FRESH_FIXTURE_STORE_REQUIRED')
            with store.transaction(PREFIX+'fixture_bound') as tx:
                tx.put('core_meta', {'key': PREFIX+'binding', 'value_json': canonical(binding)})

    def _get(self, key, default=None):
        row = self.store.one('core_meta', PREFIX+key)
        return json.loads(row['value_json']) if row else default

    def _put(self, kind, key, value):
        old = self._get(key)
        if old is not None:
            if old != value:
                raise CoreError('PROTOTYPE_KEY_COLLISION')
            return key
        with self.store.transaction(PREFIX+kind, {'key': key}) as tx:
            tx.put('core_meta', {'key': PREFIX+key, 'value_json': canonical(value)})
        return key

    @staticmethod
    def source_key(iris):
        origin = iris['origin']
        return digest([origin['dataset_id'], origin['legacy_kind'], origin['legacy_key']])

    def memories(self):
        return [m for m in self.store.all('memory_items')
                if json.loads(m['body_json']).get('iris')]

    def import_capture(self, capture, *, fault=None):
        if type(capture) is not SyntheticCapture:
            raise CoreError('SYNTHETIC_CAPTURE_REQUIRED')
        capture = SyntheticCapture.model_validate_json(canonical(capture.model_dump(mode='json')))
        # Deep raw JSON is validated before importer writes. No hidden unknown
        # fields/secret containers are passed through the inherited opaque path.
        from .contracts import strict_json
        from nana_core.integration.exporter import _safe_payload
        for record in capture.records:
            payload = strict_json(record.raw_json.encode(), 150_000)
            try:
                _safe_payload(payload)
            except CoreError:
                raise CoreError('CAPTURE_SECRET_FIELD_BLOCKED') from None
        before = {t: self.store.all(t) for t in ZERO}
        report = IrisAdapter(self.store).import_batch(capture.records, fault=fault)
        key = 'capture:'+digest(capture.model_dump(mode='json'))
        self._put('capture_manifest', key, {'provenance': 'SYNTHETIC_FIXTURE',
            'scope': capture.scope.model_dump(mode='json'),
            'coverage': capture.coverage.model_dump(mode='json'), 'input_hash': digest(capture.model_dump(mode='json'))})
        self._enforce_withdrawals()
        if before != {t: self.store.all(t) for t in ZERO}:
            raise CoreError('IMPORT_SIDE_EFFECT_INVARIANT')
        return report

    def _support(self, ids, *, allow_withdrawn=False):
        if not ids:
            raise CoreError('SUPPORT_REQUIRED')
        output = []
        for mid in ids:
            row = self.store.one('memory_items', mid)
            if not row:
                raise CoreError('SUPPORT_MISSING')
            body = json.loads(row['body_json'])
            iris = body.get('iris')
            if not iris or not iris['origin']['dataset_id'].startswith('synthetic:'):
                raise CoreError('SUPPORT_SCOPE_REJECTED')
            if self.store.event(row['created_event_id'])['identity_id'] != self.store.identity['identity_id']:
                raise CoreError('SUPPORT_IDENTITY_MISMATCH')
            if not allow_withdrawn and (row['status'] != 'ACTIVE' or self.source_key(iris) in self._get('withdrawals', [])):
                raise CoreError('SUPPORT_WITHDRAWN')
            for ref in body['source_refs']:
                self.store.artifact(ref['artifact_id'])
            output.append(body)
        return output

    def claim(self, proposal):
        if type(proposal) is not Claim:
            raise CoreError('STRICT_CLAIM_REQUIRED')
        support = self._support(proposal.supporting_memory_ids)
        if any(s['epistemic_kind'] != proposal.epistemic_kind for s in support):
            raise CoreError('EPISTEMIC_PROMOTION_BLOCKED')
        if proposal.epistemic_kind == 'USER_STATEMENT' and proposal.valid_from is not None:
            times = {s['iris']['time']['underlying_event_time_us'] for s in support}
            if utc_us(proposal.valid_from) not in times:
                raise CoreError('CLAIM_TIME_NOT_SUPPORTED')
        self._put('claim', 'claim:'+proposal.claim_id, proposal.model_dump(mode='json'))
        return proposal.claim_id

    def claims(self):
        return [Claim.model_validate_json(r['value_json']) for r in self.store.all('core_meta')
                if r['key'].startswith(PREFIX+'claim:')]

    def assessments(self, scope, *, as_of):
        now = utc_us(as_of)
        groups = {}
        for c in self.claims():
            if c.scope != scope:
                continue
            try:
                self._support(c.supporting_memory_ids)
            except CoreError as exc:
                if exc.code == 'SUPPORT_WITHDRAWN':
                    continue
                raise
            if c.valid_from is None or utc_us(c.valid_from) <= now:
                groups.setdefault(c.family, []).append(c)
        output = []
        for family, group in sorted(groups.items()):
            direct = [c for c in group if c.epistemic_kind == 'USER_STATEMENT']
            dated = [c for c in direct if c.valid_from is not None]
            latest = max((utc_us(c.valid_from) for c in dated), default=None)
            current = [c for c in dated if utc_us(c.valid_from) == latest]
            values = {c.value for c in direct}
            disputed = len(values) > 1 and (len(dated) != len(direct) or len({c.value for c in current}) > 1)
            status = 'DISPUTED' if disputed else 'CURRENT_USER_STATEMENT' if current else 'UNASSESSED'
            output.append({'family': family, 'subject': group[0].subject,
                'predicate': group[0].predicate, 'scope': scope, 'as_of': as_of,
                'status': status, 'verified_fact': False,
                'current_claim_ids': [] if disputed else [c.claim_id for c in current],
                'supporting_claim_ids': [c.claim_id for c in group],
                'contradicting_claim_ids': [c.claim_id for c in direct if current and c.value not in {x.value for x in current}],
                'reason': 'unknown/tied chronology' if disputed else 'latest dated direct statement' if current else 'no dated direct statement'})
        return output

    def relationship(self, proposal):
        if type(proposal) is not Relationship:
            raise CoreError('STRICT_RELATIONSHIP_REQUIRED')
        self._support(proposal.supporting_memory_ids)
        self._put('relationship', 'relationship:'+proposal.person_id, proposal.model_dump(mode='json'))

    def commitment(self, proposal):
        if type(proposal) is not Commitment:
            raise CoreError('STRICT_COMMITMENT_REQUIRED')
        self._support(proposal.supporting_memory_ids)
        # This is a candidate persistence contract, not an acceptance/fulfilment
        # authority. Model output cannot assert ACCEPTED/FULFILLED here.
        if proposal.status != 'OFFERED':
            raise CoreError('COMMITMENT_AUTHORITY_NOT_IMPLEMENTED')
        self._put('commitment', 'commitment:'+proposal.commitment_id, proposal.model_dump(mode='json'))

    def self_change(self, proposal):
        if type(proposal) is not SelfChangeCandidate:
            raise CoreError('STRICT_SELF_CHANGE_REQUIRED')
        self._support(proposal.supporting_memory_ids)
        self._put('self_change_candidate', 'self_change:'+proposal.change_id, proposal.model_dump(mode='json'))

    def withdraw(self, memory_id):
        body = self._support((memory_id,), allow_withdrawn=True)[0]
        key = self.source_key(body['iris'])
        keys = sorted(set(self._get('withdrawals', [])) | {key})
        if self._get('withdrawals', []) != keys:
            with self.store.transaction(PREFIX+'retrieval_withdrawn', {'source_key': key}) as tx:
                tx.put('core_meta', {'key': PREFIX+'withdrawals', 'value_json': canonical(keys)})
        self._enforce_withdrawals()
        return self.withdrawal_checkpoint()

    def _enforce_withdrawals(self):
        keys = set(self._get('withdrawals', []))
        rows = [m for m in self.memories() if m['status'] == 'ACTIVE'
                and self.source_key(json.loads(m['body_json'])['iris']) in keys]
        if rows:
            with self.store.transaction(PREFIX+'retrieval_suppressed', {'count': len(rows)}) as tx:
                for row in rows:
                    tx.update('memory_items', row['memory_id'], status='RETRACTED')

    def withdrawal_checkpoint(self):
        value = {'schema_version': 1, 'provenance': 'SYNTHETIC_FIXTURE',
            'identity_id': self.store.identity['identity_id'], 'source_keys': self._get('withdrawals', [])}
        return {**value, 'digest': digest(value)}

    def apply_withdrawal_checkpoint(self, checkpoint):
        # Fixture-only trusted operator checkpoint. Hash is integrity, NOT an
        # authenticated production deletion anchor. Real signing is a blocker.
        expected = {'schema_version', 'provenance', 'identity_id', 'source_keys', 'digest'}
        if type(checkpoint) is not dict or set(checkpoint) != expected:
            raise CoreError('WITHDRAWAL_CHECKPOINT_REJECTED')
        value = {k: v for k, v in checkpoint.items() if k != 'digest'}
        if (value['schema_version'] != 1 or value['provenance'] != 'SYNTHETIC_FIXTURE'
            or value['identity_id'] != self.store.identity['identity_id'] or digest(value) != checkpoint['digest']
            or type(value['source_keys']) is not list or len(value['source_keys']) > 100 or any(type(k) is not str or len(k) != 64 for k in value['source_keys'])):
            raise CoreError('WITHDRAWAL_CHECKPOINT_REJECTED')
        keys = sorted(set(value['source_keys']) | set(self._get('withdrawals', [])))
        with self.store.transaction(PREFIX+'withdrawal_checkpoint_applied') as tx:
            tx.put('core_meta', {'key': PREFIX+'withdrawals', 'value_json': canonical(keys)})
        self._enforce_withdrawals()

    def self_frame(self, *, allowed_datasets=None):
        def visible(prefix):
            result = []
            for row in self.store.all('core_meta'):
                if not row['key'].startswith(PREFIX+prefix+':'):
                    continue
                value = json.loads(row['value_json'])
                try:
                    support = self._support(value['supporting_memory_ids'])
                    if allowed_datasets is not None and any(b['iris']['origin']['dataset_id'] not in allowed_datasets for b in support):
                        continue
                except CoreError as exc:
                    if exc.code == 'SUPPORT_WITHDRAWN':
                        continue
                    raise
                result.append(value)
            return result
        identity = self.store.identity
        return {'schema_version': 1, 'provenance': 'SYNTHETIC_FIXTURE',
            'identity_id': identity['identity_id'], 'identity_revision': identity['revision'],
            'identity_snapshot': json.loads(identity['body_json']),
            'relationships': visible('relationship'), 'commitments': visible('commitment'),
            'self_change_candidates': visible('self_change'),
            'identity_growth_applied': False, 'execution_authority': 'NONE'}

    def context(self, *, scope, as_of, destination='local_only', max_chars=8000):
        if destination != 'local_only':
            raise CoreError('CONTEXT_DESTINATION_BLOCKED')
        if type(max_chars) is not int or not 512 <= max_chars <= 16000:
            raise CoreError('CONTEXT_BOUND_REJECTED')
        utc_us(as_of)
        if not scope.startswith('synthetic:'):
            raise CoreError('CONTEXT_SCOPE_REJECTED')
        rows = []
        for m in self.memories():
            body = json.loads(m['body_json'])
            when = body['iris']['time']['underlying_event_time_us']
            if (body['iris']['origin']['dataset_id'] == scope and m['status'] == 'ACTIVE'
                    and (when is None or when <= utc_us(as_of))):
                self._support((m['memory_id'],))
                rows.append({'memory_id': m['memory_id'], 'content': body['content'],
                    'epistemic_kind': body['epistemic_kind'], 'source_refs': body['source_refs'],
                    'time': body['iris']['time'], 'coverage': body['content_coverage']})
        assessments = self.assessments(scope, as_of=as_of)
        # Conservative all-or-nothing contradiction/history bundle. Do not
        # silently make a definite statement from a one-sided truncated context.
        payload = {'self': self.self_frame(allowed_datasets={scope}), 'memories': rows, 'assessments': assessments}
        selected = [r['memory_id'] for r in rows]
        status = 'READY' if len(canonical(payload)) <= max_chars else 'INSUFFICIENT_CONTEXT'
        if status != 'READY':
            payload = {'self': {'identity_id': self.store.identity['identity_id']},
                       'memories': [], 'assessments': []}
        coverages = [r['value'] for r in self.capture_views() if scope in r['value']['scope']['dataset_ids']]
        manifest = {'schema_version': 1, 'provenance': 'SYNTHETIC_FIXTURE', 'status': status,
            'identity_id': self.store.identity['identity_id'], 'identity_revision': self.store.identity['revision'],
            'as_of': as_of, 'scope': scope, 'destination': destination,
            'event_cutoff': self.store.db.execute('SELECT COALESCE(MAX(seq),0) FROM events').fetchone()[0],
            'selected_memory_ids': selected if status == 'READY' else [],
            'dropped_memory_ids': [] if status == 'READY' else selected,
            'coverage': 'SELECTED_CONTEXT', 'observation_coverage': [v['coverage'] for v in coverages],
            'withdrawal_digest': self.withdrawal_checkpoint()['digest'],
            'payload_hash': digest(payload), 'context_chars': len(canonical(payload)),
            'token_accounting': 'CHARACTER_BOUND_ONLY_TOKENIZER_NOT_IMPLEMENTED',
            'semantic_quality': 'NOT_RUN_REAL_DEPENDENCY'}
        return {'manifest': manifest, 'payload': payload}

    def capture_views(self):
        return [{'key': r['key'], 'value': json.loads(r['value_json'])}
                for r in self.store.all('core_meta') if r['key'].startswith(PREFIX+'capture:')]

    def verify_context(self, context):
        try:
            m, p = context['manifest'], context['payload']
            if (digest(p) != m['payload_hash'] or m['provenance'] != 'SYNTHETIC_FIXTURE'
                or m['identity_id'] != self.store.identity['identity_id']
                or m['identity_revision'] != self.store.identity['revision']
                or m['withdrawal_digest'] != self.withdrawal_checkpoint()['digest']
                or m['event_cutoff'] != self.store.db.execute('SELECT COALESCE(MAX(seq),0) FROM events').fetchone()[0]):
                raise ValueError()
            for mid in m['selected_memory_ids']:
                self._support((mid,))
        except Exception:
            raise CoreError('STALE_OR_TAMPERED_CONTEXT') from None
        return True
