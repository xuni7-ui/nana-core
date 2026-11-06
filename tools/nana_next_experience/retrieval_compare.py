"""Same-Store alternating lexical query comparison, no model or live-host claim.

Use only a disposable synthetic Store built by memory_scale_compare. This opens
one original Core Store, not another Subject or a production migration target.
"""
import argparse
import json
import math
import statistics
import time
from unittest.mock import patch
from pathlib import Path
from nana_core.continuity import ContinuityStore
from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.context import ContextAssembler, ContextRequest, ContextPolicy


class BaselineMemory(MemoryService):
    def query(self, *, entity_ids=(), scopes=(), privacy_classes=('PUBLIC',), include_conflicts=False,
              limit=128, query_terms=(), memory_types=()):
        self._fresh()
        where, args = self._query_filter(entity_ids, scopes, privacy_classes, include_conflicts, memory_types)
        if query_terms:
            relevance = '(SELECT count(*) FROM memory_terms t WHERE t.memory_id=m.memory_id AND t.term IN (' + ','.join('?' for _ in query_terms) + '))'
            terms = [t.casefold() for t in query_terms]
        else:
            relevance, terms = '0+0', []
        rows = self.store.db.execute('SELECT m.memory_id FROM memories m WHERE ' + where + ' ORDER BY ' + relevance + " DESC,(m.authority='DIRECT') DESC,m.importance DESC,m.significance DESC,m.event_time_us DESC,m.rowid LIMIT ?", [*args, *terms, limit]).fetchall()
        return [self.read(r[0], include_inactive=include_conflicts) for r in rows]


def stats(values):
    return {'samples': len(values), 'p50_ms': statistics.median(values),
            'p95_ms': sorted(values)[math.ceil(.95 * len(values))-1]}


def compare(root):
    if not (root / 'self.db').is_file():
        raise ValueError('EXISTING_DISPOSABLE_SYNTHETIC_STORE_REQUIRED')
    with ContinuityStore(root/'self.db', ManualClock(), schema_target=13) as store:
        if not store.db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace='synthetic.scale' LIMIT 1").fetchone():
            raise ValueError('SYNTHETIC_CORPUS_REQUIRED')
        request = ContextRequest(entity_id='bench', scopes=('bench',), task_class='synthetic.scale',
            task='Review sourced commitments', task_privacy_class='PROJECT', query_terms=('needle','commitment'),
            max_input_tokens=8192, output_reserve_tokens=512)
        policy = ContextPolicy(policy_id='synthetic.scale', allowed_scopes=('bench',), readable_privacy=('PROJECT',), remote_privacy=())
        out = {'qualification':'SYNTHETIC_ORIGINAL_CORE_LEXICAL_NOT_LIVE_HOST',
               'memory_rows': store.db.execute('SELECT count(*) FROM memories').fetchone()[0],
               'provider_calls':0, 'provider_reported_input_tokens':None,
               'provider_reported_output_tokens':None, 'semantic_error_rate':'NOT_MEASURED',
               'live_index_mapping':'NOT_RUN'}
        for phase in ('retrieval', 'context_assembly'):
            samples = {'baseline':[], 'candidate':[]}; results = {}
            for n in range(9):
                order = ('baseline','candidate') if n % 2 == 0 else ('candidate','baseline')
                for name in order:
                    cls = BaselineMemory if name == 'baseline' else MemoryService
                    with patch('nana_core.continuity.context.MemoryService', cls):
                        started = time.perf_counter()
                        if phase == 'retrieval':
                            rows = cls(store).query(entity_ids=('bench',), scopes=('bench',), privacy_classes=('PROJECT',), query_terms=('needle','commitment'))
                            result = [r['memory_id'] for r in rows]
                        else:
                            assembler = ContextAssembler(store, OperatorAuthority())
                            package = assembler.assemble(request, policy)
                            assembler.validate(package, request, policy)
                            result = package.model_dump(mode='json')
                        samples[name].append((time.perf_counter()-started)*1000)
                        results[name] = result
                if results['baseline'] != results['candidate']:
                    raise AssertionError('QUERY_OR_CONTEXT_CHANGED')
            out[phase] = {name:stats(values) for name,values in samples.items()}
        out['exact_context_equivalence'] = True
        out['counter'] = package.manifest.counter
        out['estimated_input_units'] = package.manifest.input_tokens
        out['context_limit'] = package.manifest.input_limit
        return out


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    print(json.dumps(compare(parser.parse_args().root),indent=2))
