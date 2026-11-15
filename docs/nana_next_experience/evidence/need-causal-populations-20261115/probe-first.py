from pathlib import Path
import sqlite3,subprocess,importlib.util,sys,time,json,hashlib,resource
from nana_core.continuity import ContinuityStore
from nana_core.continuity.subject.experience_need import project_need
root=Path('/workspace/scratch/nana-need-causal-probe');root.mkdir(exist_ok=False)
source=Path('/dev/shm/ncaold/test_other_same_domain_lesson_0/life/subject/self.db')
with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as old,sqlite3.connect(root/'self.db') as dest:old.backup(dest)
code=subprocess.check_output(['git','show','1d446ca:src/nana_core/continuity/subject/experience_need.py'])
(root/'old_need.py').write_bytes(code)
spec=importlib.util.spec_from_file_location('nana_core.continuity.subject._old_causal_probe',root/'old_need.py');oldmodule=importlib.util.module_from_spec(spec);sys.modules[spec.name]=oldmodule;spec.loader.exec_module(oldmodule)
with ContinuityStore(root/'self.db',schema_target=13) as store:
    mid=store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='recorded.project.material' AND e.source_reference='settled-interest'").fetchone()[0]
    counts={table:store.db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('events','memories','experiences','strategy_assessments','subject_cycles','cognitive_requests')}
    identity=store.identity['identity_id'];changes=store.db.total_changes
    writes={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_CREATE_INDEX,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_DROP_INDEX}
    store.db.set_authorizer(lambda action,*args: sqlite3.SQLITE_DENY if action in writes else sqlite3.SQLITE_OK)
    rows=[]
    for trial in range(3):
        for arm,fn in [('old',oldmodule.project_need),('new',project_need)]:
            started=time.perf_counter();cpu=time.process_time();view=fn(store,'owned-document',scope='project-work',privacy_classes=('PUBLIC','PROJECT'),source_memory_ids=(mid,))
            rows.append(dict(trial=trial,arm=arm,state=view.state,elapsed_ms=(time.perf_counter()-started)*1000,cpu_ms=(time.process_time()-cpu)*1000,source_records=len(view.source_record_ids)))
    assert all(row['state']==('UNKNOWN' if row['arm']=='old' else 'SETTLED') for row in rows)
    assert changes==store.db.total_changes
    assert identity==store.identity['identity_id']
    assert counts=={table:store.db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in counts}
    store.db.set_authorizer(None)
result=dict(baseline='1d446ca70c04b266ce9170c8c6570ecc3622e071',baseline_source_sha256=hashlib.sha256(code).hexdigest(),candidate_source_sha256=hashlib.sha256(Path('src/nana_core/continuity/subject/experience_need.py').read_bytes()).hexdigest(),counts=counts,read_only_main_writes=0,extra_model_calls=0,rows=rows,bytes=(root/'self.db').stat().st_size,original_fixture='40 independent same-domain reviews, other G problem, original actual failure/G/later-use/restart')
(root/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
