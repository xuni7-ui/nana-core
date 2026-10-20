"""Read-only metadata snapshot of the original pinned staging run; never control it."""
import hashlib,json,sqlite3,subprocess
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path('/workspace/nana-staging/first-life-24h-01')
PIN=Path('/workspace/nana-staging/first-life-source-645899b3')


def observe():
    progress=json.loads((ROOT/'progress.json').read_text())
    pin=subprocess.check_output(['git','rev-parse','HEAD'],cwd=PIN,text=True).strip()
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'mode':'READ_ONLY_EXISTING_RUN_NO_CONTROL','progress':progress,'pinned_head':pin,'result_exists':(ROOT/'result.json').is_file(),'qualification':'PENDING_ACTUAL_RESULT','runtime_restarted_by_this_mission':False}
    names=subprocess.check_output(['git','ls-files','src/nana_core','tools/nana_cloud_daily_life','tools/nana_first_life/staging.py'],cwd=PIN,text=True).splitlines()
    mismatch=[];count=0
    for name in names:
        if not name.endswith('.py'):continue
        raw=(PIN/name).read_bytes();original=subprocess.check_output(['git','show','HEAD:'+name],cwd=PIN)
        count+=1
        if hashlib.sha256(raw).digest()!=hashlib.sha256(original).digest():mismatch.append(name)
    result['pinned_files']={'checked':count,'mismatches':mismatch,'note':'Current on-disk pin; start/end loaded-source attestation still requires final run result'}
    home=ROOT/'journey/life';db=home/'subject/self.db'
    with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True,timeout=1) as conn:
        result['database']={'integrity':conn.execute('PRAGMA quick_check').fetchone()[0],'foreign_key_violations':len(conn.execute('PRAGMA foreign_key_check').fetchall()),'page_count':conn.execute('PRAGMA page_count').fetchone()[0],'page_size':conn.execute('PRAGMA page_size').fetchone()[0]}
        for table in ('actions','goals','runtime_queue','subject_cycles','cognitive_requests'):
            result['database'][table]=conn.execute('SELECT count(*) FROM '+table).fetchone()[0]
        result['database']['unknown_actions']=conn.execute("SELECT count(*) FROM actions WHERE state='UNKNOWN'").fetchone()[0]
        result['database']['duplicate_idempotency_keys']=conn.execute('SELECT count(*) FROM (SELECT idempotency_key FROM actions GROUP BY idempotency_key HAVING count(*)>1)').fetchone()[0]
    result['storage_guard']=json.loads((home/'storage-monitor.json').read_text())
    result['db_family_bytes']={suffix or 'db':Path(str(db)+suffix).stat().st_size for suffix in ('','-wal','-shm') if Path(str(db)+suffix).exists()}
    if result['result_exists']:
        final=json.loads((ROOT/'result.json').read_text())
        result['final']={k:final.get(k) for k in ('source_head','actual_residency_seconds','selected_source_unchanged','residency_status','actual_external_effects','new_provider_calls')}
        result['qualification']='FINAL_RESULT_REQUIRES_COMPLETE_REVIEW'
    return result

if __name__=='__main__':print(json.dumps(observe(),ensure_ascii=False,indent=2))
