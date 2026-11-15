from pathlib import Path
import hashlib,json,statistics,time,sys
from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity import ContinuityStore
from nana_core.continuity.memory import MemoryService,NOTE_END_PREFIX,NOTE_GRAM_COMPLETE
from tools.nana_next_experience.literal_two_prefix_probe import original
import sqlite3
root=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists()
spec=json.loads((root/'FROZEN_SPEC.json').read_text());assert spec['qualification']=='ISOLATED_PREFIX_TAIL_LITERAL_NOT_CORE_RELEASE' and spec['schema_version']==2
expected=json.loads((root/'expected-bindings.json').read_text());authority=OperatorAuthority()
def family(path):return sum(p.stat().st_blocks*512 for p in (path,Path(str(path)+'-wal'),Path(str(path)+'-shm')) if p.exists())
with ContinuityStore(root/'self.db',ManualClock(),schema_target=13) as store:
    db=store.db
    assert {r[0] for r in db.execute('SELECT DISTINCT source_namespace FROM continuity_evidence')}<={'recorded.conversation.input','synthetic.diverse'}
    tables=('events','memories','continuity_evidence','artifacts','continuity_records','memory_dependencies')
    counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in tables};identity=store.identity['identity_id']
    def cache_only(action,table,column,schema,trigger):
        return sqlite3.SQLITE_DENY if schema=='main' and action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_UPDATE) and not (action==sqlite3.SQLITE_INSERT and table=='memory_terms') else sqlite3.SQLITE_OK
    db.set_authorizer(cache_only);before_alloc=family(root/'self.db');before=db.total_changes;began=time.perf_counter()
    # Equivalent to the new _index end-key contribution only, in this owned
    # synthetic corpus. No full-index rebuild, fact update or production scan.
    rows=db.execute('SELECT t.memory_id,a.payload FROM memory_terms t INDEXED BY memory_terms_term_lookup JOIN memories m ON m.memory_id=t.memory_id JOIN artifacts a ON a.artifact_id=m.payload_artifact_id WHERE t.term=?',(NOTE_GRAM_COMPLETE,)).fetchall()
    db.execute('BEGIN IMMEDIATE')
    db.executemany('INSERT OR IGNORE INTO memory_terms VALUES(?,?)',((r[0],NOTE_END_PREFIX+r[1].decode().casefold()[-2:]) for r in rows));db.commit()
    inserted=db.total_changes-before;cache_seconds=time.perf_counter()-began;db.execute('PRAGMA wal_checkpoint(TRUNCATE)');after_alloc=family(root/'self.db')
    def readonly(action,table,column,schema,trigger):return sqlite3.SQLITE_DENY if schema=='main' and action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_UPDATE) else sqlite3.SQLITE_OK
    db.set_authorizer(readonly);baseline=original.MemoryService(store,authority);native=MemoryService(store,authority)
    cases=[(q,) for q in spec['queries']]+[('晚风',),('旧梦',),('未有',),('not-present-two',),('归途','星月')]
    expect=lambda ts:sorted({mid for term in ts for mid in expected.get(term,[])})
    arms={name:{'samples':[],'correct':0,'false_results':0,'timeouts':0} for name in ('original','native')};before=db.total_changes
    for repeat in range(3):
        for terms in cases:
            for name,service in (('original',baseline),('native',native)) if repeat%2==0 else (('native',native),('original',baseline)):
                began=time.perf_counter();error=None
                try:ids=sorted(m['memory_id'] for m in service.literal_notes(entity_ids=('bench',),scopes=('bench',),privacy_classes=('PROJECT',),terms=terms,limit=4,timeout_ms=100))
                except Exception as exc:
                    if getattr(exc,'code',None)!='NOTE_RECALL_TIME_BOUND':raise
                    error=exc.code;ids=[]
                item={'terms':terms,'milliseconds':(time.perf_counter()-began)*1000,'error':error,'actual_memory_ids':ids,'expected_memory_ids':expect(terms),'correct':not error and ids==expect(terms)}
                arm=arms[name];arm['samples'].append(item);arm['correct']+=int(item['correct']);arm['false_results']+=len(set(ids)-set(expect(terms)));arm['timeouts']+=int(error is not None)
    assert db.total_changes==before and store.identity['identity_id']==identity and {t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in tables}==counts
    for v in arms.values():
        times=[s['milliseconds'] for s in v['samples']];v['p50_ms']=statistics.median(times);v['p95_ms']=statistics.quantiles(times,n=100,method='inclusive')[94]
result={'qualification':'NATIVE_ORIGINAL_STORE_TWO_CODEPOINT_LITERAL_NOT_SEMANTIC','arms':arms,'cache_only_backfill':{'inserted_end_keys':inserted,'wall_seconds':cache_seconds,'family_allocated_before':before_alloc,'family_allocated_after':after_alloc,'allocated_delta':after_alloc-before_alloc,'main_write_authorizer':'ONLY_INSERT_MEMORY_TERMS'},'query_main_writes':0,'primary_counts_unchanged':counts,'identity_unchanged':True,'provider_calls':0,'provider_tokens':None,'actual_cost':None,'sqlite':sqlite3.sqlite_version,'memory_sha256':hashlib.sha256(Path(sys.modules[MemoryService.__module__].__file__).read_bytes()).hexdigest(),'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'spec_sha256':hashlib.sha256((root/'FROZEN_SPEC.json').read_bytes()).hexdigest()}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'arms':{k:{x:v[x] for x in ('correct','false_results','timeouts','p50_ms','p95_ms')} for k,v in arms.items()},'cache':result['cache_only_backfill']}))
