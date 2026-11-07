"""Synthetic original-Core SQL ranking comparison; not semantic or live-host qualification.

Creates a fresh private Store via the original public memory services. No network,
private history, direct row seeding, production config or model calls.
"""
import time,json,statistics,sys,hashlib
from pathlib import Path
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--count',type=int,default=1000)
parser.add_argument('--note-recall',action='store_true',help='Also compare a retained old CJK note against the lexical candidate bound.')
args=parser.parse_args()
source_fingerprints={'benchmark_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     'memory_runtime_sha256':hashlib.sha256(Path(sys.modules[MemoryService.__module__].__file__).read_bytes()).hexdigest()}
if not 1000 <= args.count <= 500000:parser.error('count must be 1000..500000')
root=args.root
if root.exists():parser.error('fresh synthetic root required')
root.mkdir(mode=0o700,parents=True)
a=OperatorAuthority()
old="SELECT m.memory_id FROM memories m WHERE {where} ORDER BY (SELECT count(*) FROM memory_terms t WHERE t.memory_id=m.memory_id AND t.term IN (?,?)) DESC,(m.authority='DIRECT') DESC,m.importance DESC,m.significance DESC,m.event_time_us DESC,m.rowid LIMIT ?"
new="WITH matches AS (SELECT memory_id,count(*) AS hits FROM memory_terms WHERE term IN (?,?) GROUP BY memory_id) SELECT m.memory_id FROM memories m LEFT JOIN matches ON matches.memory_id=m.memory_id WHERE {where} ORDER BY coalesce(matches.hits,0) DESC,(m.authority='DIRECT') DESC,m.importance DESC,m.significance DESC,m.event_time_us DESC,m.rowid LIMIT ?"
with ContinuityStore(root/'self.db',ManualClock(),schema_target=13) as s:
 IdentityService(s,a);m=MemoryService(s,a);m.entity('bench','PERSON');m.entity('other','PERSON')
 note_id=None
 if args.note_recall:
  text='合成资料：这次约定的暗号是虹光约定请保留。'
  for entity in ('bench','other'):
   reference='note:synthetic-scale-'+entity
   e=m.capture(EvidenceInput(provenance=Provenance(domain='CONSENTED_INTERACTION',source_namespace='recorded.conversation.input',source_reference=reference,source_kind='USER_STATEMENT'),retention_consent_ref=reference,text=text,privacy_class='PROJECT',observed_time_us=101))
   mid=m.add(MemoryCandidate(entity_id=entity,scope='bench',memory_type=MemoryType.SEMANTIC,epistemic_kind='STATEMENT',source_evidence_id=e,text=text,predicate_key='user-note.synthetic-scale'))
   if entity=='bench':note_id=mid
 rows=s.db.execute('SELECT count(*) FROM memories').fetchone()[0];t=time.perf_counter()
 for i in range(rows,args.count):
  text=f'Synthetic project {i} '+('needle shared commitment' if i%100==0 else 'ordinary unrelated noise')
  e=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.scale',source_reference=str(i),source_kind='DIRECT_OBSERVATION'),text=text,privacy_class='PROJECT',event_time_us=100,observed_time_us=101))
  m.add(MemoryCandidate(entity_id='other' if i%3==0 else 'bench',scope='bench',memory_type=MemoryType.SEMANTIC,epistemic_kind='BELIEF',source_evidence_id=e,text=text,importance=(i%10)/10))
  n=i+1
  if n in {1000,10000,100000,args.count}:
   where,filter_args=m._query_filter(('bench',),('bench',),('PROJECT',),False);samples={}
   orders=[]
   for name,sql,params in [('baseline',old.format(where=where),[*filter_args,'needle','commitment',128]),('candidate',new.format(where=where),['needle','commitment',*filter_args,128])]:
    times=[]
    for j in range(21):
     start=time.perf_counter();result=[r[0] for r in s.db.execute(sql,params)];times.append((time.perf_counter()-start)*1000)
    orders.append(result);samples[name]={'p50_ms':statistics.median(times),'p95_ms':sorted(times)[19]}
   assert orders[0]==orders[1]
   samples.update(size=n,exact_rank_equivalence=True,wall_seconds=time.perf_counter()-t,provider_calls=0,sqlite=__import__('sqlite3').sqlite_version,source_fingerprints=source_fingerprints)
   if note_id is not None:
    lookup={'entity_ids':('bench',),'scopes':('bench',),'privacy_classes':('PROJECT',)}
    baseline_ids=[row['memory_id'] for row in m.query(**lookup,query_terms=('虹光约定',))]
    timings=[];hits=wrong=timeouts=0
    from nana_core.contracts import CoreError
    for _ in range(9):
     began=time.perf_counter()
     try:
      found=m.literal_notes(**lookup,terms=('虹光约定',))
     except CoreError as exc:
      if exc.code!='NOTE_RECALL_TIME_BOUND':raise
      timeouts+=1;found=[]
     timings.append((time.perf_counter()-began)*1000)
     ids=[row['memory_id'] for row in found];hits+=ids==[note_id];wrong+=bool(ids and ids!=[note_id])
    samples['literal_note_recall']={'samples':9,'baseline_top128_contains_correct_source':note_id in baseline_ids,'correct_source_samples':hits,'wrong_source_samples':wrong,'bounded_timeout_samples':timeouts,'p50_ms':statistics.median(timings),'p95_ms':max(timings),'eligible_sources':1,'distinct_query_fixtures':1,'foreign_source_excluded':wrong==0,'qualification':'SYNTHETIC_LITERAL_SOURCE_SELECTION_NOT_SEMANTIC_OR_LIVE_RECALL','real_model_calls':0,'real_cost_micro':0}
   print(json.dumps(samples),flush=True)
   (root/f'result-{n}.json').write_text(json.dumps(samples,indent=2))
