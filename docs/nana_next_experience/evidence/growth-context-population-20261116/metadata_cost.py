"""Query-only synthetic metadata cost probe; no Core/G semantic qualification."""
import ast,hashlib,json,sqlite3,statistics,subprocess,time,sys
from pathlib import Path
from types import SimpleNamespace
from nana_core.continuity.subject import growth_life
from nana_core.continuity.store import REBUILDABLE_LOOKUP_INDEXES
BASE='35740e7f2f518b9b2607bbd952759aa80683cf4c'
code=subprocess.check_output(['git','show',BASE+':src/nana_core/continuity/subject/growth_life.py'],text=True)
f=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name=='opportunities');ns={}
exec(compile(ast.Module(body=[f],type_ignores=[]),'<exact-'+BASE+'>','exec'),ns)
LESSON='00000000-0000-0000-0000-000000000001'
CONTEXT=hashlib.sha256(b'0').hexdigest()
class Captured(Exception):pass
class Cursor:
 def fetchall(self):return [{'lesson_id':LESSON,'context_digest':CONTEXT}]
def capture(fn,number):
 class DB:
  def execute(self,q,args):
   self.count+=1
   if self.count==number:self.query,self.args=q,args;raise Captured()
   return Cursor()
 db=DB();db.count=0
 try:fn(SimpleNamespace(schema_target=13,db=db),scope='world',privacy_classes=('PUBLIC',))
 except Captured:pass
 return db.query,db.args
queries={'original':capture(ns['opportunities'],1),'group_heads':capture(growth_life.opportunities,1),
         'one_group_members':capture(growth_life.opportunities,2)}
root=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/nana-growth-context-metadata');root.mkdir(exist_ok=False)
results=[]
for size,groups,tied in [(1000,1000,False),(100000,100000,False),(100000,31,True)]:
 path=root/f'n{size}-g{groups}-t{int(tied)}.db';db=sqlite3.connect(path);db.row_factory=sqlite3.Row
 db.executescript('''CREATE TABLE strategy_assessments(assessment_id TEXT PRIMARY KEY,lesson_id TEXT,record_id TEXT,context_digest TEXT,verdict TEXT,created_at_us INTEGER);
 CREATE TABLE lessons(lesson_id TEXT PRIMARY KEY,record_id TEXT,state TEXT);
 CREATE TABLE continuity_records(record_id TEXT PRIMARY KEY,scope TEXT,privacy_class TEXT,lifecycle TEXT);
 CREATE INDEX strategy_history ON strategy_assessments(lesson_id,created_at_us DESC);''')
 db.execute('INSERT INTO lessons VALUES(?,?,?)',(LESSON,'lesson-record','ACTIVE'))
 db.execute('INSERT INTO continuity_records VALUES(?,?,?,?)',('lesson-record','world','PUBLIC','ACTIVE'))
 db.executemany('INSERT INTO continuity_records VALUES(?,?,?,?)',((f'record-{i:032d}','world','PUBLIC','ACTIVE') for i in range(size)))
 db.executemany('INSERT INTO strategy_assessments VALUES(?,?,?,?,?,?)',((f'assessment-{i:028d}',LESSON,f'record-{i:032d}',hashlib.sha256(str(i%groups).encode()).hexdigest(),'SUCCESS',1000 if tied else i) for i in range(size)));db.commit()
 phases=[]
 for phase in ['original_indexes','order_lookup','both_lookups']:
  if phase=='order_lookup':db.execute(REBUILDABLE_LOOKUP_INDEXES['strategy_growth_order_lookup']);db.commit()
  if phase=='both_lookups':db.execute(REBUILDABLE_LOOKUP_INDEXES['strategy_growth_context_lookup']);db.commit()
  outputs={}
  for name,(query,args) in queries.items():
   if phase=='original_indexes' and name!='original' and size>1000:
    outputs[name]={'status':'NOT_RUN_UNINDEXED_RANGE_AT_SCALE'};continue
   times=[];cpu=[];status='PASS';count=None
   for sample in range(3):
    deadline=time.monotonic()+2
    db.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
    start=time.perf_counter();c=time.process_time()
    try:rows=db.execute(query,args).fetchall()
    except sqlite3.OperationalError as exc:
     if str(exc)!='interrupted':raise
     status='TIMEOUT_2S';break
    finally:db.set_progress_handler(None,0)
    times.append((time.perf_counter()-start)*1000);cpu.append((time.process_time()-c)*1000);count=len(rows)
   if status=='PASS':
    expected=min(32,size) if name=='original' else min(32,groups) if name=='group_heads' else min(32,(size+groups-1)//groups)
    assert count==expected,(name,count,expected)
   outputs[name]={'status':status,'rows':count,'wall_ms':times,'cpu_ms':cpu,
                  'median_ms':statistics.median(times) if times else None}
  phases.append({'phase':phase,'file_bytes':path.stat().st_size,'allocated_bytes':path.stat().st_blocks*512,'queries':outputs})
 plan=[tuple(row) for row in db.execute('EXPLAIN QUERY PLAN '+queries['group_heads'][0],queries['group_heads'][1])]
 results.append({'rows':size,'contexts':groups,'equal_clock':tied,'phases':phases,'indexed_plan':plan})
 db.close()
print(json.dumps({'scope':'SYNTHETIC_SQL_METADATA_ONLY_NOT_CORE_STORE_OR_SEMANTIC_BENCHMARK',
 'sqlite':sqlite3.sqlite_version,'dataset_directory':str(root),'base':BASE,'samples_per_query':3,
 'extra_provider_calls':0,'schema_migrations':0,'results':results},indent=2))
