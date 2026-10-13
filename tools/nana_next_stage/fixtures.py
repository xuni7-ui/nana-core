"""Generated non-private fixtures matching native Iris field names."""
from nana_core.storage import canonical
from nana_core.migration.iris import IrisRecord
from .contracts import (CaptureScope, Coverage, SyntheticCapture, SyntheticIrisRecord, Claim,
                        Relationship, Commitment, SelfChangeCandidate)

DATASET = 'synthetic:next-stage'


def capture():
    payloads = (
        ('l1', 'old-preference', {'role': 'user', 'content': 'Fictional sister prefers long reading cards.',
            'timestamp': '2026-09-01T10:00:00+00:00', 'token_count': 12, 'source': 'synthetic:conversation'}),
        ('l1', 'new-preference', {'role': 'user', 'content': 'Fictional sister now prefers short reading cards with a locator.',
            'timestamp': '2026-09-03T10:00:00+00:00', 'token_count': 16, 'source': 'synthetic:conversation'}),
        ('l2', 'summary', {'id': 'synthetic-summary', 'content': 'Synthetic model summary of a shared paper observatory.',
            'metadata': {'source': 'l1_summary', 'timestamp': '2026-09-02T10:00:00+00:00'}}),
        ('kg_edge', 'relation', {'source_id': 'synthetic-nana', 'target_id': 'synthetic-sister',
            'relation_type': 'shares_project', 'source_memory_id': 'synthetic-summary'}),
        ('user_profile', 'profile', {'user_id': 'synthetic-sister', 'user_name': 'Fictional sister',
            'bot_relationship': 'sister', 'field_meta': {}, 'custom_fields': {}}),
        ('action_ledger', 'old-action', {'key': 'synthetic-old-action', 'state': 'VERIFIED',
            'updated_at': '2026-09-02T10:00:00+00:00', 'verify': 'legacy claim, not Core execution'}),
    )
    return SyntheticCapture(scope=CaptureScope(dataset_ids=(DATASET,),
        record_kinds=tuple(sorted({p[0] for p in payloads})), max_records=20),
        coverage=Coverage(source_instance=DATASET, observed_from='2026-09-01T00:00:00+00:00',
            observed_until='2026-09-04T00:00:00+00:00', event_scope='result_path',
            completeness='PARTIAL', dropped=2, disconnected=True),
        records=tuple(SyntheticIrisRecord(synthetic_only=True, dataset_id=DATASET, kind=kind,
            legacy_key=key, raw_json=canonical(value)) for kind, key, value in payloads))


def seed_phase_a(prototype):
    report = prototype.import_capture(capture())
    indexed = {__import__('json').loads(m['body_json'])['iris']['origin']['legacy_key']: m['memory_id']
        for m in prototype.memories()}
    for key, value, time in [('old-preference', 'long', '2026-09-01T10:00:00+00:00'),
                             ('new-preference', 'short-with-locator', '2026-09-03T10:00:00+00:00')]:
        prototype.claim(Claim(claim_id='synthetic:'+key, subject='synthetic:sister', predicate='reading.preference',
            value=value, scope=DATASET, epistemic_kind='USER_STATEMENT', valid_from=time,
            expressed_at=time, supporting_memory_ids=(indexed[key],)))
    prototype.relationship(Relationship(person_id='synthetic:sister', role='sister_fixture',
        address_term='姐姐（合成关系）', supporting_memory_ids=(indexed['profile'],)))
    prototype.commitment(Commitment(commitment_id='synthetic:reading-promise', beneficiary_id='synthetic:sister',
        outcome='Proposed synthetic follow-up reading card.', due_at='2026-09-05T10:00:00+00:00',
        status='OFFERED', supporting_memory_ids=(indexed['new-preference'],)))
    prototype.self_change(SelfChangeCandidate(change_id='synthetic:expression-change',
        dimension='expression_preference', proposed_value='concise with sources',
        supporting_memory_ids=(indexed['new-preference'],)))
    return report, indexed
