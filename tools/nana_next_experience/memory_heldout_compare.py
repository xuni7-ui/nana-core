"""Compare independently specified literal note queries on a disposable Store.

The source must be the synthetic.scale fixture made by memory_scale_compare.
No private Store, model, or network is used. Scores describe exact source
selection for these fixtures only, not semantic recall or conversational quality.
"""
import argparse
import json
import math
import shutil
import sqlite3
import statistics
import time
from pathlib import Path

from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity import ContinuityStore
from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from nana_core.continuity.memory import MemoryService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    sidecar = Path(str(source) + '.privacy.json')
    privacy = json.loads(sidecar.read_text())
    if 'anchor_path' in privacy:
        raise ValueError('EXTERNAL_PRIVACY_ANCHOR_NOT_SUPPORTED')
    if args.output.exists():
        parser.error('output must be a fresh path')
    args.output.mkdir(mode=0o700, parents=True)
    # A SQLite backup obtains a coherent private copy without editing the input.
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
        sources = src.execute('SELECT DISTINCT source_namespace FROM continuity_evidence').fetchall()
        if sources != [('synthetic.scale',)]:
            raise ValueError('SYNTHETIC_CORPUS_REQUIRED')
        with sqlite3.connect(args.output / 'self.db') as dst:
            src.backup(dst)
    shutil.copyfile(sidecar, args.output / 'self.db.privacy.json')
    samples = {'baseline': [], 'candidate': []}
    scores = {name: {'correct': 0, 'wrong_source': 0, 'missing': 0} for name in samples}
    with ContinuityStore(args.output / 'self.db', ManualClock(), schema_target=13) as store:
        memory = MemoryService(store, OperatorAuthority())
        initial = store.db.execute('SELECT count(*) FROM memories').fetchone()[0]
        cases = []
        # Distinct, labelled examples are never used for choosing the method.
        for i in range(24):
            token = ('约定星光' if i % 2 else 'projectneedle') + str(7319 + i)
            for entity in ('bench', 'other'):
                ref = f'note:heldout:{i}:{entity}'
                text = f'独立合成记录 {i}，关键内容是{token}，用于之后检索。'
                evidence = memory.capture(EvidenceInput(
                    provenance=Provenance(domain='CONSENTED_INTERACTION',
                        source_namespace='recorded.conversation.input', source_reference=ref,
                        source_kind='USER_STATEMENT'), retention_consent_ref=ref,
                    text=text, privacy_class='PROJECT', observed_time_us=101))
                mid = memory.add(MemoryCandidate(entity_id=entity, scope='bench',
                    memory_type=MemoryType.SEMANTIC, epistemic_kind='STATEMENT',
                    source_evidence_id=evidence, text=text, predicate_key=f'user-note.heldout{i}'))
                if entity == 'bench':
                    cases.append((token, mid))
        filters = dict(entity_ids=('bench',), scopes=('bench',), privacy_classes=('PROJECT',))
        for index, (term, expected) in enumerate(cases):
            order = ('baseline', 'candidate') if index % 2 == 0 else ('candidate', 'baseline')
            for name in order:
                started = time.perf_counter()
                if name == 'baseline':
                    rows = memory.query(**filters, query_terms=(term,))
                else:
                    rows = memory.literal_notes(**filters, terms=(term,))
                samples[name].append((time.perf_counter() - started) * 1000)
                ids = [row['memory_id'] for row in rows]
                scores[name]['correct'] += expected in ids
                scores[name]['missing'] += expected not in ids
                # For this known-unique literal candidate, any other row is wrong.
                if name == 'candidate':
                    scores[name]['wrong_source'] += bool(set(ids) - {expected})
        result = {
            'qualification': 'SYNTHETIC_EXACT_SOURCE_SELECTION_NOT_SEMANTIC_OR_LIVE',
            'initial_memories': initial, 'distinct_queries': len(cases),
            'query_families': ['Chinese literal', 'ASCII literal'],
            'models_or_paid_calls': 0, 'actual_tokens': None, 'actual_cost': None,
            'arms': {},
        }
        for name, durations in samples.items():
            result['arms'][name] = {**scores[name], 'p50_ms': statistics.median(durations),
                'p95_ms': sorted(durations)[math.ceil(.95 * len(durations)) - 1]}
        result['arms']['baseline']['wrong_source'] = 'NOT_MEASURED_RANKED_CANDIDATES'
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
