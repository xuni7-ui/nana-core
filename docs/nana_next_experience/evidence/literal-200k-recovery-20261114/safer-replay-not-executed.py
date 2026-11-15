"""Read-only SQL-shape experiment; reuse original frozen cases and compare()."""
import json,sys,types,hashlib,subprocess,time
from pathlib import Path
from nana_core.clock import ManualClock
from nana_core.continuity import ContinuityStore
from tools.nana_next_experience.memory_diverse_compare import compare
root=Path('/dev/shm/nana-diverse-200k-20261114')
if not (root/'result-200000.json').exists():raise SystemExit('Original generation/control run must complete first')
spec=json.loads((root/'FROZEN_SPEC.json').read_text())
old_spec=json.loads(Path('docs/nana_next_experience/evidence/diverse-literal-20261109/final-FROZEN_SPEC.json').read_text())
assert spec['cases']==old_spec['cases'] and spec['timeout_ms']==old_spec['timeout_ms']==100
pinned='f93bcfa';code=subprocess.check_output(['git','show',pinned+':src/nana_core/continuity/memory.py']).decode()
assert code==Path('src/nana_core/continuity/memory.py').read_text(),'Do not edit source while collecting fixed-source evidence'
fragment='''" AND m.memory_type='SEMANTIC' EXCEPT "
                    "SELECT memory_id FROM memory_terms INDEXED BY memory_terms_term_lookup WHERE term=?), "'''
assert code.count(fragment)==1
variants={
 'not_exists':'''" AND m.memory_type='SEMANTIC' AND NOT EXISTS (SELECT 1 "
                    "FROM memory_terms INDEXED BY memory_terms_term_lookup WHERE term=? AND memory_id=m.memory_id)), "''',
 'not_in':'''" AND m.memory_type='SEMANTIC' AND m.memory_id NOT IN ("
                    "SELECT memory_id FROM memory_terms INDEXED BY memory_terms_term_lookup WHERE term=?)), "'''}
modules={}
for name,replacement in variants.items():
 src=code.replace(fragment,replacement);module=types.ModuleType('nana_core.continuity._literal_'+name);module.__package__='nana_core.continuity';sys.modules[module.__name__]=module
 exec(compile(src,'<isolated-literal-'+name+'>','exec'),module.__dict__);modules[name]=(module,hashlib.sha256(src.encode()).hexdigest())
 (root/('prototype-'+name+'.py')).write_text(src)
small={**spec,'cases':[v for v in spec['cases'] if v['case'] in {'astronomy0.absent','astronomy2.eligible'}]};assert len(small['cases'])==2
result={'scope':'OWNED_SYNTHETIC_SQL_SHAPE_DIAGNOSTIC_NOT_FULL_QUALIFICATION','base_commit':pinned,'base_memory_sha256':hashlib.sha256(code.encode()).hexdigest(),'timeout_ms':100,'cases':[v['case'] for v in small['cases']],'temperature':'SHARED_CONNECTION_ALTERNATING_WARM_NOT_OS_COLD','arms':{}}
with ContinuityStore(root/'self.db',ManualClock(),schema_target=13) as store:
 expected={}
 for case in spec['cases']:
  for ref in case['expected_refs']:
   rows=store.db.execute('SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_reference=? AND m.entity_id=? AND m.scope=?',('note:'+ref,'bench','bench')).fetchall();assert len(rows)==1;expected[ref]=rows[0][0]
 store.db.execute('PRAGMA query_only=ON')
 writes=store.db.total_changes;before=store.db.execute('PRAGMA data_version').fetchone()[0]
 for name,(module,sha) in modules.items():
  sql=[]
  def capture(statement):
   if statement.startswith('WITH unindexed AS MATERIALIZED'):sql.append(statement)
  store.db.set_trace_callback(capture)
  measured=compare(store,module.MemoryService,small,expected)
  store.db.set_trace_callback(None)
  plans=[{'sql':query,'plan':[tuple(row) for row in store.db.execute('EXPLAIN QUERY PLAN '+query)]} for query in dict.fromkeys(sql)]
  result['arms'][name]={'prototype_source_sha256':sha,'prototype':measured['baseline'],'original_except':measured['candidate'],'plans':plans}
  print(json.dumps({'variant':name,'scores':{key:{field:value[field] for field in ('correct','false_result_cases','timeouts','p50_ms','p95_ms')} for key,value in measured.items()}},sort_keys=True),flush=True)
 assert store.db.execute('PRAGMA data_version').fetchone()[0]==before and store.db.total_changes==writes,'Diagnostic must not mutate the Store'
 result['same_store_rows']=store.db.execute('SELECT count(*) FROM memories').fetchone()[0]
 result['extra_model_calls']=0;result['provider_tokens']=None;result['commercial_cost']=None
(root/'two-query-variants.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
