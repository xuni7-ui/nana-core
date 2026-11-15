from pathlib import Path
import hashlib,json,statistics,time,sys
from nana_core.actions import OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.continuity import ContinuityStore
from nana_core.continuity.memory import MemoryService,NOTE_GRAM_COMPLETE
from nana_core.contracts import CoreError
from tools.nana_next_experience import literal_two_prefix_probe as probe
root=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists()
spec=json.loads((root/'FROZEN_SPEC.json').read_text());assert spec['schema_version']==2 and spec['qualification']=='ISOLATED_PREFIX_TAIL_LITERAL_NOT_CORE_RELEASE'
expected=json.loads((root/'expected-bindings.json').read_text());db_path=root/'self.db';before_hash=hashlib.sha256(db_path.read_bytes()).hexdigest()
candidate,patch=probe.candidate_class();authority=OperatorAuthority()
with ContinuityStore(db_path,ManualClock(),schema_target=13) as store:
    assert {r[0] for r in store.db.execute('SELECT DISTINCT source_namespace FROM continuity_evidence')}<={'recorded.conversation.input','synthetic.diverse'}
    normal=probe.original.MemoryService(store,authority);new=candidate(store,authority);db=store.db
    late=db.execute("SELECT memory_id FROM memories WHERE predicate_key='user-note.late-tail-gap'").fetchone()[0]
    dead=db.execute("SELECT memory_id FROM memories WHERE predicate_key='user-note.withdraw-tail'").fetchone()[0]
    db.execute('CREATE TEMP TABLE probe_note_tails(memory_id TEXT PRIMARY KEY,tail TEXT NOT NULL) WITHOUT ROWID');db.execute('CREATE INDEX temp.probe_tail_lookup ON probe_note_tails(tail,memory_id)')
    began=time.perf_counter();rows=0
    for row in db.execute('SELECT t.memory_id,a.payload FROM memory_terms t INDEXED BY memory_terms_term_lookup JOIN memories m ON m.memory_id=t.memory_id JOIN artifacts a ON a.artifact_id=m.payload_artifact_id WHERE t.term=?',(NOTE_GRAM_COMPLETE,)).fetchall():
        if row[0]==late:continue
        db.execute('INSERT INTO temp.probe_note_tails VALUES(?,?)',(row[0],row[1].decode().casefold()[-2:]));rows+=1
    db.execute('INSERT INTO temp.probe_note_tails VALUES(?,?)',(dead,'旧梦'));cache_time=time.perf_counter()-began
    cases=[(q,) for q in spec['queries']]+[('晚风',),('旧梦',),('未有',),('not-present-two',),('归途','星月')]
    expect=lambda terms:sorted({mid for term in terms for mid in expected.get(term,[])})
    arms={k:{'samples':[],'correct':0,'false_results':0,'timeouts':0} for k in ('original','adaptive_prefix_tail')};before=db.total_changes
    for repeat in range(3):
        for terms in cases:
            for name,service in (('original',normal),('adaptive_prefix_tail',new)) if repeat%2==0 else (('adaptive_prefix_tail',new),('original',normal)):
                began=time.perf_counter();error=None
                try:ids=sorted(m['memory_id'] for m in service.literal_notes(entity_ids=('bench',),scopes=('bench',),privacy_classes=('PROJECT',),terms=terms,limit=4,timeout_ms=100))
                except CoreError as exc:
                    if exc.code!='NOTE_RECALL_TIME_BOUND':raise
                    ids=[];error=exc.code
                item={'terms':terms,'milliseconds':(time.perf_counter()-began)*1000,'error':error,'actual_memory_ids':ids,'expected_memory_ids':expect(terms),'correct':not error and ids==expect(terms)}
                arm=arms[name];arm['samples'].append(item);arm['correct']+=int(item['correct']);arm['false_results']+=len(set(ids)-set(expect(terms)));arm['timeouts']+=int(error is not None)
    assert db.total_changes==before
    for arm in arms.values():
        values=[s['milliseconds'] for s in arm['samples']];arm['p50_ms']=statistics.median(values);arm['p95_ms']=statistics.quantiles(values,n=100,method='inclusive')[94]
result={'qualification':'SAME_CORPUS_ISOLATED_ADAPTIVE_PREFIX_TAIL_NOT_CORE','arms':arms,'cache':{'rows':rows,'build_seconds':cache_time},'runtime_integrated':False,'provider_calls':0,'provider_tokens':None,'probe_sha256':hashlib.sha256(Path(probe.__file__).read_bytes()).hexdigest(),'replay_driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_memory_sha256':hashlib.sha256(probe.BASELINE_SOURCE.encode()).hexdigest(),'spec_sha256':hashlib.sha256((root/'FROZEN_SPEC.json').read_bytes()).hexdigest(),'main_database_sha256_before':before_hash,'main_database_sha256_after':hashlib.sha256(db_path.read_bytes()).hexdigest()}
assert result['main_database_sha256_before']==result['main_database_sha256_after']
out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:{x:v[x] for x in ('correct','false_results','timeouts','p50_ms','p95_ms')} for k,v in arms.items()}))
