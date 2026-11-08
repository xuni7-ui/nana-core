"""Frozen literal-source comparison on one disposable original Store.

This extends earlier scale/held-out probes; it is not semantic/model evaluation,
Nana learning, a live-index assertion, or permission to open a private Store.
"""
import argparse
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
import time
import types
from pathlib import Path

from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from nana_core.continuity.memory import MemoryService
from nana_core.contracts import CoreError

BASELINE = '43a5662563fdf929fe7eb29889bc678f3ab3320d'
FAMILIES = ('meeting', 'garden', 'recipe', 'astronomy')
FORMS = ('beacon', '星河约定', 'café')


def frozen_spec():
    cases = []
    for family in FAMILIES:
        for index, form in enumerate(FORMS):
            stem = family + str(index)
            for kind in ('eligible', 'corrected', 'withdrawn', 'absent'):
                cases.append({'case': stem + '.' + kind, 'family': family, 'kind': kind,
                    'query': form + '-' + stem + '-' + kind,
                    'expected_refs': [stem + '.eligible'] if kind == 'eligible' else
                                     [stem + '.new'] if kind == 'corrected' else []})
    return {'schema_version': 1, 'qualification': 'DIVERSE_LITERAL_SOURCE_NOT_SEMANTIC',
            'baseline': BASELINE, 'timeout_ms': 100, 'limit': 4, 'repetitions': 3,
            'privacy': ['PROJECT'], 'entity': 'bench', 'scope': 'bench', 'cases': cases}


def add(memory, ref, text, *, entity='bench', scope='bench', privacy='PROJECT',
        note=True, predicate=None, correction=None):
    provenance = Provenance(domain='CONSENTED_INTERACTION' if note else 'SYNTHETIC_ONLY',
        source_namespace='recorded.conversation.input' if note else 'synthetic.diverse',
        source_reference='note:' + ref if note else ref, source_kind='USER_STATEMENT' if note else 'DIRECT_OBSERVATION')
    eid = memory.capture(EvidenceInput(provenance=provenance, text=text, privacy_class=privacy,
        retention_consent_ref='note:' + ref if note else None, event_time_us=101 + bool(correction),
        observed_time_us=101 + bool(correction)))
    return memory.add(MemoryCandidate(entity_id=entity, scope=scope, memory_type=MemoryType.SEMANTIC,
        epistemic_kind='STATEMENT' if note else 'OBSERVATION', source_evidence_id=eid, text=text,
        predicate_key=predicate or 'user-note.' + ref, correction_of=correction))


def compare(store, baseline, spec, expected):
    methods = {'baseline': baseline(store), 'candidate': MemoryService(store)}
    arms = {name: {'correct': 0, 'false_result_cases': 0, 'missed_cases': 0,
                   'timeouts': 0, 'timings_ms': [], 'outcomes': []} for name in methods}
    for index, case in enumerate(spec['cases']):
        wanted = set(expected[ref] for ref in case['expected_refs'])
        for rep in range(spec['repetitions']):
            for name in (('baseline', 'candidate') if (index + rep) % 2 else ('candidate', 'baseline')):
                arm = arms[name]; began = time.perf_counter(); timeout = False
                try:
                    result = methods[name].literal_notes(entity_ids=('bench',), scopes=('bench',),
                        privacy_classes=('PROJECT',), terms=(case['query'],), limit=spec['limit'],
                        timeout_ms=spec['timeout_ms'])
                    found = {row['memory_id'] for row in result}
                except CoreError as exc:
                    if exc.code != 'NOTE_RECALL_TIME_BOUND': raise
                    arm['timeouts'] += 1; found = set(); timeout = True
                arm['timings_ms'].append((time.perf_counter() - began) * 1000)
                correct = found == wanted and not timeout
                arm['correct'] += correct
                arm['false_result_cases'] += bool(found - wanted)
                arm['missed_cases'] += bool(wanted - found)
                arm['outcomes'].append({'case': case['case'], 'rep': rep,
                    'correct': correct, 'timeout': timeout, 'returned': len(found),
                    'expected': len(wanted), 'false_results': len(found - wanted)})
    for arm in arms.values():
        durations = arm['timings_ms']
        arm.update(p50_ms=statistics.median(durations),
                   p95_ms=statistics.quantiles(durations, n=100, method='inclusive')[94])
    return arms


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--sizes', type=int, nargs='+', default=[1000, 10000, 100000, 200000])
    args = p.parse_args()
    if args.root.exists() or args.sizes != sorted(set(args.sizes)) or not all(1000 <= n <= 200000 for n in args.sizes):
        p.error('fresh root and increasing unique sizes 1000..200000 required')
    args.root.mkdir(parents=True, mode=0o700)
    repo = Path(__file__).resolve().parents[2]
    source = subprocess.check_output(['git', 'show', BASELINE + ':src/nana_core/continuity/memory.py'], cwd=repo)
    module = types.ModuleType('nana_core.continuity._diverse_baseline'); module.__package__ = 'nana_core.continuity'
    sys.modules[module.__name__] = module
    exec(compile(source, '<pinned-memory-43a>', 'exec'), module.__dict__)
    spec = frozen_spec(); encoded = json.dumps(spec, ensure_ascii=False, sort_keys=True).encode()
    (args.root / 'FROZEN_SPEC.json').write_bytes(encoded)
    fingerprints = {'spec_sha256': hashlib.sha256(encoded).hexdigest(),
        'baseline_memory_sha256': hashlib.sha256(source).hexdigest(),
        'candidate_memory_sha256': hashlib.sha256(Path(sys.modules[MemoryService.__module__].__file__).read_bytes()).hexdigest(),
        'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    authority = OperatorAuthority(); began = time.perf_counter()
    with ContinuityStore(args.root / 'self.db', ManualClock(), schema_target=13) as store:
        IdentityService(store, authority); memory = MemoryService(store, authority)
        for entity in ('bench', 'other'): memory.entity(entity, 'PERSON')
        expected = {}
        for case in spec['cases']:
            stem, kind = case['case'].rsplit('.', 1); query = case['query']
            text = f'SYNTHETIC {case["family"]}: {query}; reported detail, not verified world truth.'
            if kind == 'eligible': expected[stem + '.eligible'] = add(memory, stem + '.eligible', text)
            elif kind == 'corrected':
                old = add(memory, stem + '.old', text + ' earlier report', predicate='user-note.' + stem + '.corrected')
                expected[stem + '.new'] = add(memory, stem + '.new', text + ' corrected report',
                    predicate='user-note.' + stem + '.corrected', correction=old)
            elif kind == 'withdrawn':
                mid = add(memory, stem + '.withdrawn', text); memory.forget(mid, authority)
            # Same words from another entity/scope/privacy and non-note provenance.
            add(memory, stem + '.' + kind + '.foreign', text, entity='other')
            add(memory, stem + '.' + kind + '.scope', text, scope='elsewhere')
            add(memory, stem + '.' + kind + '.private', text, privacy='PERSONAL')
            for i in range(4): add(memory, stem + '.' + kind + '.lookalike' + str(i), text, note=False)
        initial = store.db.execute('SELECT count(*) FROM memories').fetchone()[0]
        for index in range(initial, args.sizes[-1]):
            family = FAMILIES[index % len(FAMILIES)]
            text = f'SYNTHETIC {family} unrelated report {index}; ' + ('ordinary context' if index % 2 else '普通日常记录')
            add(memory, 'noise.' + str(index), text, entity='other' if index % 5 == 0 else 'bench',
                scope='elsewhere' if index % 7 == 0 else 'bench', privacy='PERSONAL' if index % 11 == 0 else 'PROJECT',
                note=index % 3 == 0)
            count = index + 1
            if count not in args.sizes: continue
            if shutil.disk_usage(args.root).free < 512 * 1024 * 1024: raise RuntimeError('SYNTHETIC_DISK_HEADROOM')
            arms = compare(store, module.MemoryService, spec, expected)
            store.db.execute('PRAGMA wal_checkpoint(PASSIVE)')
            files = {p.name: {'bytes': p.stat().st_size, 'allocated_bytes': p.stat().st_blocks * 512}
                     for p in args.root.glob('self.db*') if p.is_file()}
            result = {'qualification': spec['qualification'], 'fingerprints': fingerprints,
                'memory_rows': count, 'distinct_queries': len(spec['cases']),
                'trials_per_arm': len(spec['cases']) * spec['repetitions'], 'arms': arms,
                'temperature': 'SHARED_CONNECTION_FIRST_SAMPLE_AND_ALTERNATING_WARM_NOT_OS_COLD',
                'percentile': 'LINEAR_INCLUSIVE', 'wall_seconds': time.perf_counter() - began,
                'sqlite': __import__('sqlite3').sqlite_version, 'provider_calls': 0,
                'provider_tokens': None, 'actual_cost': None, 'semantic_or_naturalness': 'NOT_RUN',
                'context_assembly': 'NOT_MEASURED', 'live_index_mapping': 'NOT_RUN', 'disk': files}
            (args.root / f'result-{count}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps({k: result[k] for k in ('memory_rows', 'wall_seconds')} |
                {'scores': {n: {k: v[k] for k in ('correct', 'false_result_cases', 'timeouts', 'p50_ms', 'p95_ms')}
                            for n, v in arms.items()}}), flush=True)


if __name__ == '__main__': main()
