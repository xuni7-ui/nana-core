"""Reproducible synthetic comparison, no Graphiti runtime or model calls.

Run from the repository root with the existing development dependencies:
  python -m tools.nana_next_experience.association_compare --output result.json
The eight roots and 24 target paths are fixed before either retrieval runs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
import time
import tracemalloc

from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.world import WorldModel, SourcedClaim
from nana_core.presence.authority import VirtualClock
from nana_core.storage import canonical
from .association_probe import linked_recall
from .association_direct_baseline import direct_two_hop

PREDICATES = ('interest.a', 'interest.b', 'interest.c', 'needs')
PATTERNS = tuple((first, 'needs') for first in PREDICATES[:-1])


def add_link(store, key, source, target, predicate, *, privacy='PUBLIC', **changes):
    memory = MemoryService(store)
    for entity in (source, target, 'fixture.observer'):
        memory.entity(entity, 'OBJECT')
    claim = SourcedClaim(entity_id=source, predicate=predicate, value={'entity_id': target},
        kind='RAW_OBSERVATION', valid_from_us=store.clock.utc_now_us(), **changes)
    text = canonical({'world_claim': claim.model_dump(mode='json')})
    evidence = memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.association-probe',
        source_reference=key, source_kind='DIRECT_OBSERVATION'), text=text, privacy_class=privacy,
        observed_time_us=store.clock.utc_now_us(), event_time_us=store.clock.utc_now_us()))
    mid = memory.add(MemoryCandidate(entity_id='fixture.observer', scope='world', memory_type=MemoryType.EPISODIC,
        epistemic_kind='OBSERVATION', source_evidence_id=evidence, text=text))
    world = WorldModel(store, scopes=('world',), privacy_classes=(privacy,))
    belief = world.ingest(mid)
    store.clock.advance(1000)
    return mid, belief


def corpus(store):
    expected = {}
    for i in range(8):
        if i == 4:
            for d in range(32):
                add_link(store, f'distractor.{d}', f'noise.{d}', f'unrelated.{d}', 'needs')
        seed = f'seed.{i}'
        expected[seed] = []
        for suffix in ('a', 'b', 'c'):
            topic, resource = f'topic.{i}.{suffix}', f'resource.{i}.{suffix}'
            _, belief = add_link(store, f'interest.{i}.{suffix}', seed, topic, f'interest.{suffix}')
            first = store.one('world_beliefs', belief)['record_id']
            _, belief = add_link(store, f'need.{i}.{suffix}', topic, resource, 'needs')
            second = store.one('world_beliefs', belief)['record_id']
            expected[seed].append({'entities': (seed, topic, resource), 'supports': {first, second}})
    for d in range(8):
        add_link(store, f'latest.{d}', f'recent.noise.{d}', f'recent.unrelated.{d}', 'needs')
    return expected


def run(repeats=5):
    with tempfile.TemporaryDirectory(prefix='nana-association-') as folder:
        clock = VirtualClock()
        with ContinuityStore(Path(folder)/'original.db', clock, schema_target=13) as store:
            IdentityService(store, OperatorAuthority())
            expected = corpus(store)
            world = WorldModel(store, scopes=('world',), privacy_classes=('PUBLIC',))
            changes = store.db.total_changes
            events = store.db.execute('SELECT count(*) FROM events').fetchone()[0]
            def allocated():
                return sum(p.stat().st_blocks*512 for p in Path(folder).iterdir() if p.is_file())
            disk_before = allocated()
            samples = {'snapshot32': [], 'linked32': [], 'direct32': []}
            cpu = {key: 0.0 for key in samples}
            scores = {}
            for repeat in range(repeats):
                for seed, goals in expected.items():
                    methods = tuple(samples)
                    shift = repeat % len(methods)
                    order = methods[shift:] + methods[:shift]
                    for method in order:
                        start, process = time.perf_counter_ns(), time.process_time_ns()
                        if method == 'snapshot32':
                            snapshot = world.snapshot(limit=32)
                            supports = {rid for view in snapshot for rid in view.support_records}
                            correct = sum(goal['supports'] <= supports for goal in goals)
                            views = len(snapshot)
                            false_positive = None  # Flat snapshots are not answer classifiers.
                        else:
                            result = (linked_recall(world, seed, predicates=PREDICATES) if method == 'linked32'
                                else direct_two_hop(world, seed, patterns=PATTERNS))
                            leaves = {path.entities for path in result.paths if len(path.predicates) == 2}
                            correct = len(leaves & {goal['entities'] for goal in goals})
                            false_positive = len(leaves - {goal['entities'] for goal in goals})
                            views = result.views_read
                            assert not result.deadline_exceeded and not result.source_changed
                        cpu[method] += (time.process_time_ns()-process)/1e6
                        samples[method].append((time.perf_counter_ns()-start)/1e6)
                        if repeat == 0:
                            scores.setdefault(method, []).append({'seed': seed, 'correct_paths': correct,
                                'views_read': views, 'false_positive_paths': false_positive})
            peak = {}
            for method in samples:
                tracemalloc.start()
                for seed in expected:
                    if method == 'snapshot32':
                        world.snapshot(limit=32)
                    elif method == 'linked32':
                        linked_recall(world, seed, predicates=PREDICATES, timeout_ms=1000)
                    else:
                        direct_two_hop(world, seed, patterns=PATTERNS, timeout_ms=1000)
                peak[method] = tracemalloc.get_traced_memory()[1]
                tracemalloc.stop()
            assert store.db.total_changes == changes
            assert store.db.execute('SELECT count(*) FROM events').fetchone()[0] == events
            disk_after = allocated()
            metrics = {}
            for method, values in samples.items():
                ordered = sorted(values)
                metrics[method] = {'correct_paths': sum(row['correct_paths'] for row in scores[method]),
                    'cases': scores[method], 'p50_ms': statistics.median(values),
                    'p95_ms': ordered[int((len(ordered)-1)*.95)], 'cpu_ms_all_samples': cpu[method],
                    'python_tracemalloc_peak_bytes_separate_pass': peak[method], 'raw_latency_ms': values}
            return {'scope': 'SYNTHETIC_EXPLICIT_WORLD_LINKS_ONLY', 'nana_subjects': 1,
                'world_keys': 88, 'unique_roots': 8, 'expected_two_hop_paths': 24,
                'max_original_views': 32, 'candidate_safe_point_deadline_ms': 100,
                'frozen_target_paths_sha256': hashlib.sha256(json.dumps(
                    [goal['entities'] for rows in expected.values() for goal in rows],
                    separators=(',', ':')).encode()).hexdigest(),
                'repeats': repeats, 'methods': metrics, 'model_calls': 0, 'real_tokens': None,
                'store_mutations_during_retrieval': 0, 'new_persistent_index': False,
                'store_family_allocated_bytes_before': disk_before,
                'store_family_allocated_bytes_after': disk_after,
                'production_integrated': False,
                'limits': ['structured entity links, not natural-language extraction or semantic recall',
                    'direct32 uses the question ordered predicates; linked32 gets their union and ignores order',
                    'Python allocation peak is not RSS; scratch ingestion/storage is not a disk saving',
                    'no C choice, learned skill, long-term behavior or Graphiti runtime comparison proven']}


def adverse_query():
    """A known pattern amid newer unrelated branches; no method is tuned here."""
    with tempfile.TemporaryDirectory(prefix='nana-association-adverse-') as folder:
        with ContinuityStore(Path(folder)/'original.db', VirtualClock(), schema_target=13) as store:
            IdentityService(store, OperatorAuthority())
            add_link(store, 'old-interest', 'seed', 'topic', 'interest.a')
            add_link(store, 'old-need', 'topic', 'resource', 'needs')
            predicates = ('interest.a', 'noise.b', 'noise.c', 'noise.d', 'noise.e', 'noise.f', 'noise.g', 'needs')
            for number, predicate in enumerate(predicates[1:]):
                hub = f'hub.{number}'
                add_link(store, f'root.{number}', 'seed', hub, predicate)
                for j, tail in enumerate(predicates):
                    add_link(store, f'tail.{number}.{j}', hub, f'noise-target.{number}.{j}', tail)
            world = WorldModel(store, scopes=('world',), privacy_classes=('PUBLIC',))
            changes = store.db.total_changes
            results = {}
            for method in ('linked32', 'direct32'):
                result = (linked_recall(world, 'seed', predicates=predicates) if method == 'linked32'
                    else direct_two_hop(world, 'seed', patterns=(('interest.a', 'needs'),)))
                leaves = {p.entities for p in result.paths if len(p.predicates) == 2}
                target = {('seed', 'topic', 'resource')}
                results[method] = {'matching_paths': len(leaves & target),
                    'raw_nonmatching_paths': len(leaves-target), 'views_read': result.views_read,
                    'budget_exhausted': result.budget_exhausted, 'deadline_exceeded': result.deadline_exceeded}
            assert store.db.total_changes == changes
            return {'world_keys': 65, 'max_views': 32, 'pattern': ['interest.a', 'needs'],
                'methods': results, 'store_mutations': 0, 'model_calls': 0,
                'interpretation': 'nonmatching graph paths are not false facts; they spend query budget without answering this pattern'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run()
    result['adverse_query'] = adverse_query()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({method: data['correct_paths'] for method, data in result['methods'].items()}))
