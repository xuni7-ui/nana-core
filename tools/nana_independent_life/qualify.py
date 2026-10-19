"""Real wall-clock CLI journey, SIGKILL/restart, no-input work and local controls.

Only fresh dedicated homes, approved repository materials and anonymous locally
written dialogue. No provider credentials/network, AstrBot, QQ or private history.
"""
import argparse,json,os,signal,sqlite3,subprocess,sys,time
from pathlib import Path


def snapshot(home):
    path=home/'subject/self.db'
    with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True,timeout=1) as db:
        db.row_factory=sqlite3.Row
        return {'identity_id':db.execute('SELECT identity_id FROM identities').fetchone()[0],
            'goals':[dict(x) for x in db.execute('SELECT goal_id,state FROM goals')],
            'jobs':[dict(x) for x in db.execute("SELECT job_id,work_kind,state,cursor FROM jobs WHERE work_kind IN ('GOAL','LEARNING')")],
            'actions':[dict(x) for x in db.execute('SELECT action_id,state,idempotency_key FROM actions')],
            'lessons':[dict(x) for x in db.execute('SELECT lesson_id,state FROM lessons')],
            'assessments':[dict(x) for x in db.execute('SELECT assessment_id,verdict FROM strategy_assessments')],
            'grants':db.execute('SELECT count(*) FROM grants').fetchone()[0],
            'model_requests':db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0],
            'user_events':db.execute("SELECT count(*) FROM subject_events WHERE origin='USER'").fetchone()[0],
            'control':json.loads(db.execute("SELECT value_json FROM core_meta WHERE key='runtime.life_control'").fetchone()[0]) if db.execute("SELECT 1 FROM core_meta WHERE key='runtime.life_control'").fetchone() else {'paused':False},
            'fk_violations':db.execute('pragma foreign_key_check').fetchall()}


def wait_until(predicate,timeout,process):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if process.poll() is not None:raise RuntimeError('independent runtime exited before checkpoint')
        try:
            value=predicate()
            if value:return value
        except (sqlite3.Error,KeyError,OSError):pass
        time.sleep(.05)
    raise RuntimeError('bounded process checkpoint not reached')


def run(root,repo,*,soak_seconds=30):
    if root.exists():raise ValueError('fresh dedicated development root required')
    root.mkdir(mode=0o700,parents=True);home=root/'home';env={**os.environ,'PYTHONPATH':str(repo/'src')}
    init=subprocess.run([sys.executable,'-m','nana_core.life','init','--home',str(home),'--project',str(repo),'--demo-materials','--allow-local-artifacts','--json'],cwd=repo,env=env,capture_output=True,text=True,timeout=10,check=True)
    initial=json.loads(init.stdout);log1=root/'before-kill.jsonl';log2=root/'after-restart.jsonl'
    def start(log):
        stream=log.open('w');process=subprocess.Popen([sys.executable,'-m','nana_core.life','run','--home',str(home),'--seconds',str(max(45,soak_seconds+15)),'--json'],cwd=repo,env=env,stdin=subprocess.PIPE,stdout=stream,stderr=stream,text=True)
        return process,stream
    first,stream=start(log1)
    try:
        checkpoint=wait_until(lambda: any(j['work_kind']=='LEARNING' and 1<=j['cursor']<9 for j in snapshot(home)['jobs']),15,first)
        before=snapshot(home);assert before['user_events']==0
        os.kill(first.pid,signal.SIGKILL);first.wait(timeout=5);assert first.returncode==-signal.SIGKILL
    finally:
        if first.poll() is None:first.kill();first.wait(timeout=5)
        stream.close()
    second,stream=start(log2)
    wait_until(lambda:log2.exists() and '"state": "STARTED"' in log2.read_text(),5,second)
    started=time.monotonic()
    try:
        no_input=wait_until(lambda:(s if len(s['goals'])==2 and all(g['state']=='COMPLETED' for g in s['goals']) and s['assessments'] else None) if (s:=snapshot(home)) else None,20,second)
        assert no_input['identity_id']==before['identity_id']==initial['identity_id'] and no_input['user_events']==0
        assert no_input['grants']==before['grants']==1 and len(no_input['actions'])==8
        assert len({a['idempotency_key'] for a in no_input['actions']})==8
        second.stdin.write('/pause\n');second.stdin.flush()
        wait_until(lambda:snapshot(home)['control']['paused'],3,second);paused=snapshot(home)['jobs'];time.sleep(.4)
        assert snapshot(home)['jobs']==paused
        second.stdin.write('今天只是吐槽一下 LOCAL_PROCESS_CANARY\n/busy\n');second.stdin.flush()
        wait_until(lambda:snapshot(home)['control'].get('messages',0)==1,3,second)
        second.stdin.write('/available\n/resume\n/status\n');second.stdin.flush()
        wait_until(lambda:not snapshot(home)['control']['paused'],3,second)
        while time.monotonic()-started<soak_seconds:
            if second.poll() is not None:raise RuntimeError('runtime stopped during bounded soak')
            time.sleep(.1)
        second.stdin.write('/quit\n');second.stdin.flush();second.wait(timeout=5);assert second.returncode==0
    finally:
        if second.poll() is None:second.terminate();second.wait(timeout=5)
        stream.close()
    lines=[json.loads(line) for line in log2.read_text().splitlines() if line.startswith('{')]
    stopped=next(x for x in reversed(lines) if x.get('state')=='STOPPING');final=snapshot(home)
    with sqlite3.connect('file:'+str(home/'subject/self.db')+'?mode=ro',uri=True) as db:
        assert not db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'LOCAL_PROCESS_CANARY')>0").fetchone()
    assert all(a['state']=='SUCCEEDED' for a in final['actions']) and len(final['actions'])==8
    assert not final['fk_violations'] and final['model_requests']==0
    return {'initial_identity':initial['identity_id'],'after_restart_identity':final['identity_id'],'real_sigkill':'PASS_DURING_EXISTING_LEARNING_STAGE','restart_grants_recreated':False,
        'no_user_input_until_two_real_tasks_complete':True,'before_kill':before,'no_input_completed':no_input,'after_local_interaction':final,
        'local_dialogue':'OFFLINE_LITERAL_BASELINE_ONLY','raw_body_persisted':False,'pause_preserved_jobs':True,'real_provider_calls':0,'external_social_send':0,
        'wall_soak_seconds':stopped['wall_seconds'],'cpu_seconds':stopped['cpu_seconds'],'max_rss_kib':stopped['max_rss_kib'],
        'resources':next(x for x in lines if x.get('state')=='STARTED')['resources'],'reports':sorted(p.name for p in (home/'reports').glob('*.md')),
        'real_provider_qualified':'NOT_RUN','first_life_experience_ready':'NOT_READY_PENDING_REAL_SEMANTIC_PROVIDER_AND_USER_REVIEW'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=30);a=p.parse_args()
    if not 10<=a.seconds<=60:p.error('bounded soak10–60 seconds')
    result=run(a.root,a.repo,soak_seconds=a.seconds);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('real_sigkill','no_user_input_until_two_real_tasks_complete','wall_soak_seconds','cpu_seconds','max_rss_kib','real_provider_calls')}))
if __name__=='__main__':main()
