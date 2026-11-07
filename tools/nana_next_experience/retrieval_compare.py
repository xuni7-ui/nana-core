"""Same-Store alternating lexical query comparison, no model or live-host claim.

Use only a disposable synthetic Store built by memory_scale_compare. This opens
one original Core Store, not another Subject or a production migration target.
"""
import argparse
import json
import math
import statistics
import time
import types
import sys
import subprocess
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


def compare_pinned(root):
    """Versioned old/new context on one Store; no second Runtime or model."""
    if not __debug__:raise ValueError('QUALIFICATION_REQUIRES_ASSERTIONS')
    root=Path(root).absolute()
    if root.resolve()!=root or not (root/'self.db').is_file() or not list(root.glob('result-*.json')):
        raise ValueError('EXISTING_DISPOSABLE_SYNTHETIC_STORE_REQUIRED')
    repo=Path(__file__).resolve().parents[2]
    source=subprocess.check_output(['git','show','fa1f3159ce6c8a4309265ff2934926872ae0fe3d:src/nana_core/continuity/context.py'],cwd=repo)
    module=types.ModuleType('nana_core.continuity._pinned_context_baseline')
    module.__package__='nana_core.continuity';sys.modules[module.__name__]=module
    exec(compile(source,'<pinned-context-fa1f315>','exec'),module.__dict__)
    samples={'baseline':[],'candidate':[]};reads={k:[] for k in samples};packages={}
    with ContinuityStore(root/'self.db',ManualClock(),schema_target=13) as store:
        if not store.db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace='synthetic.scale' LIMIT 1").fetchone():raise ValueError('SYNTHETIC_CORPUS_REQUIRED')
        primary=store.db.execute("SELECT memory_id FROM memories WHERE entity_id='bench' AND scope='bench' AND predicate_key IS NULL ORDER BY rowid DESC LIMIT 1").fetchone()[0]
        wanted=store.db.execute("SELECT memory_id FROM memories WHERE entity_id='bench' AND predicate_key='user-note.synthetic-scale'").fetchone()[0]
        req=ContextRequest(entity_id='bench',scopes=('bench',),task_class='world.social',task='Synthetic sourced recall',task_privacy_class='PROJECT',query_terms=('虹光约定',),max_input_tokens=16384,output_reserve_tokens=2048)
        policy=ContextPolicy(policy_id='synthetic.pinned',allowed_scopes=('bench',),readable_privacy=('PROJECT',))
        original_read=MemoryService.read
        for n in range(9):
            for arm in (tuple(samples) if n%2==0 else tuple(reversed(samples))):
                count=[0]
                def counted(self,*args,**kwargs):
                    count[0]+=1
                    return original_read(self,*args,**kwargs)
                cls=module.ContextAssembler if arm=='baseline' else ContextAssembler
                with patch.object(MemoryService,'read',counted):
                    start=time.perf_counter();assembler=cls(store,OperatorAuthority())
                    package=assembler.assemble(req,policy,required_memory_ids=(primary,),pinned_only=True,conversation_topic='synthetic')
                    assembler.validate(package,req,policy);samples[arm].append((time.perf_counter()-start)*1000)
                reads[arm].append(count[0]);packages[arm]=package.model_dump(mode='json')
            a,b=(packages[k] for k in samples)
            assert a['blocks']==b['blocks'],'SELECTED_SOURCE_CONTENT_CHANGED'
            assert {wanted,primary}<={mid for block in b['blocks'] for mid in block['source_memory_ids']}
        return {'qualification':'SYNTHETIC_SAME_STORE_PINNED_CONTEXT_NOT_MODEL_ABLATION',
                'memory_rows':store.db.execute('SELECT count(*) FROM memories').fetchone()[0],
                'baseline_source':'fa1f3159ce6c8a4309265ff2934926872ae0fe3d context with current same MemoryService/index',
                'arms':{k:{**stats(v),'payload_read_calls':reads[k]} for k,v in samples.items()},
                'selected_blocks_byte_equal':True,'manifest_change':'Truthful explicit-source omission/candidate counts only',
                'provider_calls':0,'tokenizer':'UTF8_BYTE_ESTIMATE_NOT_PROVIDER_TOKENIZER',
                'real_model_or_live_qualification':'NOT_RUN'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--pinned',action='store_true')
    args=parser.parse_args()
    print(json.dumps((compare_pinned if args.pinned else compare)(args.root),indent=2))
