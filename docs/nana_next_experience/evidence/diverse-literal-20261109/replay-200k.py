from pathlib import Path
import sys,json,subprocess,types,hashlib,time
from nana_core.continuity import ContinuityStore
from nana_core.clock import ManualClock
from tools.nana_next_experience.memory_diverse_compare import compare
from nana_core.continuity.memory import MemoryService
root=Path('/workspace/scratch/nana-memory-diverse-v3')
spec=json.loads((root/'FROZEN_SPEC.json').read_text())
assert spec['schema_version']==1 and spec['qualification']=='DIVERSE_LITERAL_SOURCE_NOT_SEMANTIC'
ref='c9f7518e7ac61e469ec129ce3cc6e553fd1b094b'
source=subprocess.check_output(['git','show',ref+':src/nana_core/continuity/memory.py'])
m=types.ModuleType('nana_core.continuity._before_materialization');m.__package__='nana_core.continuity';sys.modules[m.__name__]=m
exec(compile(source,'<pinned-c9-memory>', 'exec'),m.__dict__)
print('Opening original synthetic Store with completed derived index',flush=True)
with ContinuityStore(root/'self.db',ManualClock(),schema_target=13) as store:
 print('Original Store opened',flush=True)
 assert [r[0] for r in store.db.execute('SELECT DISTINCT source_namespace FROM continuity_evidence ORDER BY source_namespace')]==['recorded.conversation.input','synthetic.diverse']
 expected={}
 for case in spec['cases']:
  for r in case['expected_refs']:
   rows=store.db.execute('SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_reference=? AND m.entity_id=? AND m.scope=?',('note:'+r,'bench','bench')).fetchall()
   assert len(rows)==1;expected[r]=rows[0][0]
 print('Frozen expected source bindings checked',flush=True)
 result={'baseline_source':ref,'baseline_memory_sha256':hashlib.sha256(source).hexdigest(),'candidate_memory_sha256':hashlib.sha256(Path(sys.modules[MemoryService.__module__].__file__).read_bytes()).hexdigest(),'spec_sha256':hashlib.sha256((root/'FROZEN_SPEC.json').read_bytes()).hexdigest(),'same_store_rows':store.db.execute('SELECT count(*) FROM memories').fetchone()[0],'timeout_ms':spec['timeout_ms'],'distinct_queries':len(spec['cases']),'trials_per_arm':len(spec['cases'])*spec['repetitions'],'arms':compare(store,m.MemoryService,spec,expected),'calls':0,'provider_tokens':None,'billing':None,'context_assembly':'NOT_MEASURED','temperature':'SHARED_CONNECTION_ALTERNATING_WARM_NOT_OS_COLD'}
 Path('/workspace/scratch/memory-diverse-gram-covering-replay.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({n:{k:a[k] for k in ('correct','false_result_cases','timeouts','p50_ms','p95_ms')} for n,a in result['arms'].items()}))
