"""Use an already stopped synthetic DEV home to exercise the installed CLI.

An isolated child simulates a persisted in-flight state, then actually exits
without releasing its lease. No real provider, credentials or network call.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--prior',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    bundle=args.bundle.resolve();home=(args.work/'life').resolve()
    report=json.loads(args.prior.read_text())
    marker=json.loads((home/'nana-space-development.json').read_text())
    manifest=json.loads((bundle/'runtime.json').read_text())
    if (report.get('execution')!='ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD'
            or report.get('source_commit')!=manifest['source_commit']
            or marker!={'realm':'OWNED_DEVELOPMENT_ONLY','identity_id':report.get('subject_id')}):
        raise ValueError('INSTALLED_DEV_BINDING_REQUIRED')
    python=bundle/'.venv/bin/python'
    child_code='''
import json,os,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,sys.argv[1])
from nana_core.life.application import LifeApplication
app=LifeApplication(Path(sys.argv[2]));app.pause()
row=app.runtime.store.db.execute("SELECT * FROM cognitive_requests WHERE state='PROPOSED' ORDER BY rowid LIMIT 1").fetchone()
if not row:raise ValueError('SYNTHETIC_FIXTURE_PROPOSAL_REQUIRED')
with app.runtime.store.transaction('synthetic.installed_interruption') as tx:
 tx.update('cognitive_requests',row['request_id'],state='CALLING')
print(json.dumps({'request_id':row['request_id'],'reserved_cost_micro':row['reserved_cost_micro'],
 'reserved_bytes':row['reserved_bytes'],'epoch':app.runtime.lease.epoch}),flush=True)
os._exit(0)
'''
    child=subprocess.run([str(python),'-I','-c',child_code,str(bundle/'src'),str(home)],text=True,capture_output=True,timeout=30,check=True)
    before=json.loads(child.stdout.strip().splitlines()[-1])
    cmd=[str(python),'-I',str(bundle/'bootstrap.py'),'recover-interrupted','--home',str(home),
         '--expected-epoch',str(before['epoch']),'--expected-subject',report['subject_id'],
         '--expected-lineage',report['lineage_binding'],'--acknowledge-interruption']
    recovered=json.loads(subprocess.run(cmd,text=True,capture_output=True,timeout=30,check=True).stdout)
    with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
        state=db.execute('SELECT state,reserved_cost_micro,reserved_bytes FROM cognitive_requests WHERE request_id=?',(before['request_id'],)).fetchone()
        epoch=db.execute('SELECT epoch FROM runtime_lease').fetchone()[0]
    assert state==('UNKNOWN',before['reserved_cost_micro'],before['reserved_bytes'])
    assert recovered['state']=='INTERRUPTED_ATTEMPTS_UNKNOWN' and recovered['changed']==1
    assert recovered['provider_calls']==recovered['retries']==0 and not recovered['reservations_refunded']
    again=[str(python),'-I',str(bundle/'bootstrap.py'),'recover-interrupted','--home',str(home),
         '--expected-epoch',str(epoch),'--expected-subject',report['subject_id'],
         '--expected-lineage',report['lineage_binding'],'--acknowledge-interruption']
    retry=json.loads(subprocess.run(again,text=True,capture_output=True,timeout=30,check=True).stdout)
    assert retry['state']=='NO_INTERRUPTED_ATTEMPTS' and retry['changed']==0
    result={'execution':'INSTALLED_SYNTHETIC_CRASH_RECOVERY_NOT_CLOUD',
        'source_commit':manifest['source_commit'],'same_subject_and_lineage':True,
        'previous_process_actual_exit':True,'calling_state':'SYNTHETIC_INJECTED_NOT_LIVE_PROVIDER',
        'result':'UNKNOWN','reservation_preserved':True,'repeat_no_op':True,
        'provider_calls':0,'automatic_retries':0,'provider_billing_reconciled':False,
        'production_changed':False,'physical_phone':'NOT_RUN'}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
