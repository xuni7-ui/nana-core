import sqlite3,time,statistics,json

def case(total,cues):
 db=sqlite3.connect(':memory:')
 db.executescript("CREATE TABLE memories(memory_id TEXT PRIMARY KEY,entity_id TEXT,scope TEXT,privacy_class TEXT,lifecycle TEXT,assessment TEXT,predicate_key TEXT,updated_at_us INTEGER,event_id TEXT);CREATE TABLE events(seq INTEGER PRIMARY KEY,event_id TEXT UNIQUE);CREATE INDEX memory_family ON memories(entity_id,scope,predicate_key,assessment,lifecycle);CREATE INDEX memory_scope_visibility ON memories(scope,lifecycle,assessment,privacy_class,entity_id);")
 db.executemany('INSERT INTO events VALUES(?,?)',((i,'event.'+str(i)) for i in range(1,total+1)))
 db.executemany('INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?)',((f'{i:09d}','project-user','project-work','PROJECT','ACTIVE','CURRENT',('concern.' if i<=cues else 'note.')+str(i),1,'event.'+str(i)) for i in range(1,total+1)))
 where="m.scope='project-work' AND m.entity_id IN ('project-user','subject') AND m.privacy_class='PROJECT' AND m.lifecycle='ACTIVE' AND m.assessment IN ('CURRENT','UNASSESSED')"
 queries={'original':"SELECT m.memory_id,m.updated_at_us,m.assessment FROM memories m WHERE "+where+" AND substr(m.predicate_key,1,8)='concern.' ORDER BY m.memory_id LIMIT 129",
          'cohort':"SELECT count(*),coalesce(max(e.seq),0),coalesce(max(m.updated_at_us),0) FROM memories m JOIN events e ON e.event_id=m.event_id WHERE "+where+" AND m.predicate_key>= 'concern.' AND m.predicate_key<'concern/'"}
 samples={k:[] for k in queries};plans={}
 for key,q in queries.items():
  plans[key]=db.execute('EXPLAIN QUERY PLAN '+q).fetchall();db.execute(q).fetchall()
 for n in range(7):
  for key in (queries if n%2==0 else reversed(queries)):
   start=time.perf_counter_ns();rows=db.execute(queries[key]).fetchall();samples[key].append((time.perf_counter_ns()-start)/1e6)
   if key=='cohort':assert rows==[(cues,cues if cues else 0,1 if cues else 0)]
 db.close()
 return {'total_headers':total,'concern_headers':cues,'samples_ms':samples,'median_ms':{k:statistics.median(v) for k,v in samples.items()},'plans':plans}
print(json.dumps({'scope':'isolated metadata SQL only, not a Core Store or complete memory benchmark','sqlite':sqlite3.sqlite_version,'cases':[case(1000,131),case(10000,131),case(100000,131),case(100000,100000)],'model_calls':0,'actual_provider_tokens':None},indent=2))
