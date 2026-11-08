"""Frozen later-query comparison on the original Store/G, with no provider calls."""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import time

from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.retrieval_growth import NoteRetrievalEvaluator, qualified_note_limit
from nana_core.storage import digest
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_retrieval_growth import notes, advance, selected
from tests.independent_life.test_retrieval_growth_expanded import initialize_expanded, fillers

BASELINE = '4123b6b035705aeceec67a88b91275b96479fd3a'
# Labels are fixed here and never given to the G practice competitor. The three
# later notes do not exist until after practice/evaluation/transfer complete.
LATER = ('ALTAIR', 'CERES', 'PALLAS')
NEGATIVE = ('NEBULA', 'ALTAIR9', 'CERES9', 'PALLAS9', 'MISSING', 'SIRIUS')


def frozen_cases():
    cases = []
    for index, word in enumerate(LATER):
        for query in (word, word.lower(), word[:1] + word[1:].lower(),
                      ''.join(chr(ord(c) + 0xFEE0) for c in word), word[:4], word[-4:]):
            cases.append({'query': query, 'expected_later_index': index})
    cases += [{'query': query, 'expected_later_index': None} for query in NEGATIVE]
    return cases


def run(home, output, baseline=BASELINE):
    spec = {'schema_version': 1, 'qualification': 'NOTE_SCOPE32_LATER_QUERY_V1',
            'source_bound': 32, 'timeout_ms': 100, 'result_limit': 4, 'provider_calls': 0,
            'later_notes': LATER, 'queries': frozen_cases()}
    frozen_digest = digest(spec)
    # Preserve the real baseline source, not a hand-coded weaker substitute.
    source = subprocess.check_output(['git', 'show', baseline + ':src/nana_core/continuity/retrieval_growth.py'])
    baseline_path = output.parent / 'baseline-retrieval-growth.py'
    baseline_path.write_bytes(source)
    module_spec = importlib.util.spec_from_file_location('nana_core.continuity._scope32_baseline', baseline_path)
    old = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(old)
    initialize_expanded(home)
    clock = VirtualClock()
    with LifeApplication(home, clock=clock) as app:
        train = notes(app)
        fillers(app)
        growth = app.runtime.work.note_retrieval_growth
        growth.slice('project-work'); advance(app)
        assert selected(app)[1] == 'UNICODE_WORDS'
        # Original independently checked counterexample, then G chooses using
        # practice only. No later-query labels are exposed during competition.
        notes(app, ('ＡＬＰＨＡＢＥＴ', 'ＢＥＴＡＭＡＸ', 'ＧＡＭＭＡＲＡＹ'), prefix='counter')
        growth.slice('project-work'); advance(app)
        assert selected(app)[1] == 'JOIN'
        assert qualified_note_limit(app.runtime.store, selected(app)) == 32
        later = notes(app, tuple(''.join(chr(ord(c) + 0xFEE0) for c in word) for word in LATER), prefix='heldout-later')
        before = {mid: MemoryService(app.runtime.store).read(mid) for mid in train + later}
        new_eval = growth.evaluator
        old_eval = old.NoteRetrievalEvaluator(app.runtime.store, 'project-user', ('project-work',), ('PROJECT',))
        results = {'baseline': [], 'candidate': []}
        timings = {'baseline': [], 'candidate': []}
        for index, case in enumerate(spec['queries']):
            expected = [] if case['expected_later_index'] is None else [later[case['expected_later_index']]]
            # Alternate order on the same Store/hardware; same100ms snapshot
            # guard, result bound, permissions and zero provider budget.
            for arm in (('baseline', 'candidate') if index % 2 == 0 else ('candidate', 'baseline')):
                started = time.perf_counter_ns(); gap = None
                try:
                    actual = MemoryService(app.runtime.store).literal_notes(entity_ids=('project-user',),
                        scopes=('project-work',), privacy_classes=('PROJECT',), terms=(case['query'],))
                    if not actual:
                        evaluator = old_eval if arm == 'baseline' else new_eval
                        snapshot = evaluator.snapshot('project-work') if arm == 'baseline' else evaluator.snapshot('project-work', max_notes=32)
                        actual = evaluator.lookup('JOIN', (case['query'],), snapshot)
                    actual = sorted(row['memory_id'] for row in actual)
                except CoreError as exc:
                    assert exc.code == 'NOTE_STRATEGY_SCOPE_BOUND'
                    actual, gap = [], exc.code
                timings[arm].append((time.perf_counter_ns() - started) / 1_000_000)
                results[arm].append({'query': case['query'], 'expected': expected, 'actual': actual,
                                     'gap': gap, 'correct': actual == expected})
        for mid, value in before.items():
            after = MemoryService(app.runtime.store).read(mid)
            assert tuple(after[k] for k in ('assessment', 'confidence', 'text')) == tuple(value[k] for k in ('assessment', 'confidence', 'text'))
        assert all(row['correct'] for row in results['candidate'])
        app.forget(train[0]); assert selected(app) is None
        assert not app.runtime.store.all('cognitive_requests')
        summary = {}
        for arm, rows in results.items():
            durations = sorted(timings[arm])
            summary[arm] = {'queries': len(rows), 'correct': sum(r['correct'] for r in rows),
                'false_positive_queries': sum(bool(set(r['actual']) - set(r['expected'])) for r in rows),
                'positive_queries': sum(bool(r['expected']) for r in rows),
                'positive_queries_recalled': sum(bool(r['expected']) and r['actual'] == r['expected'] for r in rows),
                'scope_deferrals': sum(r['gap'] is not None for r in rows),
                'p50_ms': statistics.median(durations), 'p95_ms': durations[int((len(durations)-1)*.95)]}
        result = {'scope': 'SYNTHETIC_ORIGINAL_STORE_G_NO_REAL_MODEL', 'baseline_source': baseline,
            'frozen_spec': spec, 'frozen_spec_digest': frozen_digest, 'summaries': summary,
            'results': results, 'latency_samples_ms': timings, 'new_provider_calls': 0,
            'model_tokens': 'NOT_RUN', 'actual_model_cost': 'NOT_RUN',
            'virtual_time_not_residency': True, 'source_withdrawal_removes_strategy': True,
            'fact_assessment_unchanged': True}
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.home, args.output)
    print(json.dumps({'frozen_spec_digest': result['frozen_spec_digest'], 'summaries': result['summaries']}, indent=2))
