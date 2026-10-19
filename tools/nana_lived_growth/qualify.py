"""Actual bounded wall-process qualification; no provider/virtual clock/private data.

Uses public reviewed repository source and docs. Actual SIGKILL in I review tests
current-realm recovery. Final isolated data skill is dispatched by original Kernel
on an unseen document. No advance() or scripted model supplies any task result.
"""
import argparse,json,os,signal,sqlite3,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from tools.nana_independent_life.qualify import snapshot,wait_until


def detail(home):
    out=snapshot(home)
    with sqlite3.connect('file:'+str(home/'subject/self.db')+'?mode=ro',uri=True,timeout=1) as db:
        db.row_factory=sqlite3.Row
        out['skill_jobs']=[dict(x) for x in db.execute("SELECT j.job_id,j.state,j.cursor,json_extract(CAST(a.payload AS TEXT),'$.stage') AS stage FROM jobs j JOIN continuity_records r ON r.record_id=j.record_id JOIN artifacts a ON a.artifact_id=r.payload_artifact_id WHERE j.work_kind='CODE_DEVELOPMENT'")]
        out['task_domains']=[x[0] for x in db.execute('SELECT DISTINCT template FROM goals')]
        out['failure_experiences']=db.execute("SELECT count(*) FROM experiences WHERE outcome='FAILURE'").fetchone()[0]
        out['no_action_intentions']=db.execute("SELECT count(*) FROM subject_intentions WHERE kind='NO_ACTION'").fetchone()[0]
        out['skill_actions']=[dict(x) for x in db.execute("SELECT action_id,state,idempotency_key FROM actions WHERE capability='world.skill'")]
        out['subject_loops']=db.execute('SELECT count(*) FROM identities').fetchone()[0]
    return out


def resources(pid,home):
    proc=Path('/proc')/str(pid)
    status={}
    for line in (proc/'status').read_text().splitlines():
        if line.split(':')[0] in {'VmRSS','VmPeak','VmHWM','Threads'}:status[line.split(':')[0]]=line.split(':',1)[1].strip()
    status['fd_count']=len(list((proc/'fd').iterdir()))
    status['disk_bytes']=sum(p.stat().st_size for p in home.rglob('*') if p.is_file())
    io={}
    for line in (proc/'io').read_text().splitlines():
        name,value=line.split(':')
        if name in {'write_bytes','syscw'}:io[name]=int(value)
    return {**status,**io}


def run(root,repo,seconds=90):
    if root.exists():raise ValueError('fresh root required')
    root.mkdir(mode=0o700,parents=True);home=root/'life';started_at=datetime.now(timezone.utc).isoformat();begin=time.monotonic()
    env={**os.environ,'PYTHONPATH':str(repo/'src')}
    initial=subprocess.run([sys.executable,'-m','nana_core.life','init','--home',str(home),'--project',str(repo),'--demo-materials','--document-work','--allow-local-artifacts','--allow-local-skills','--json'],cwd=repo,env=env,capture_output=True,text=True,timeout=15,check=True)
    ident=json.loads(initial.stdout)['identity_id']
    def start(name):
        log=root/name;stream=log.open('w')
        p=subprocess.Popen([sys.executable,'-m','nana_core.life','run','--home',str(home),'--seconds','180','--json'],cwd=repo,env=env,stdin=subprocess.PIPE,stdout=stream,stderr=stream,text=True)
        return p,stream,log
    first,stream,log=start('before-kill.jsonl')
    try:
        before=wait_until(lambda:(s if any(j['stage']=='REVIEW' and j['state']=='WAITING' for j in s['skill_jobs']) else None) if (s:=detail(home)) else None,60,first)
        assert before['user_events']==0 and len(before['task_domains'])==2
        os.kill(first.pid,signal.SIGKILL);first.wait(timeout=5)
        assert first.returncode==-signal.SIGKILL
    finally:
        if first.poll() is None:first.kill();first.wait(timeout=5)
        stream.close()
    second,stream,log=start('after-restart.jsonl')
    wait_until(lambda:log.exists() and '"state": "STARTED"' in log.read_text(),5,second)
    second_start=time.monotonic()
    try:
        complete=wait_until(lambda:(s if len(s['goals'])==4 and all(g['state']=='COMPLETED' for g in s['goals']) and len(s['assessments'])==2 and len(s['skill_actions'])==1 else None) if (s:=detail(home)) else None,60,second)
        assert complete['user_events']==0 and complete['identity_id']==ident and complete['grants']==before['grants']==1
        assert len(complete['actions'])==16 and len({a['idempotency_key'] for a in complete['actions']})==16
        assert all(a['state']=='SUCCEEDED' for a in complete['actions'])
        work_resource=resources(second.pid,home)
        second.stdin.write('/pause\n');second.stdin.flush()
        wait_until(lambda:detail(home)['control']['paused'],3,second)
        paused=detail(home)['jobs'];time.sleep(.4);assert detail(home)['jobs']==paused
        sent=time.monotonic();second.stdin.write('今天只是吐槽一下 V2_PROCESS_ANON_CANARY\n/busy\n');second.stdin.flush()
        wait_until(lambda:detail(home)['control'].get('messages',0)==1,3,second);latency=time.monotonic()-sent
        second.stdin.write('/life\n/available\n/resume\n');second.stdin.flush()
        wait_until(lambda:not detail(home)['control']['paused'],3,second)
        idle_start=resources(second.pid,home)
        while time.monotonic()-second_start<seconds:
            if second.poll() is not None:raise RuntimeError('runtime exited during soak')
            time.sleep(.1)
        idle_end=resources(second.pid,home)
        assert len(detail(home)['actions'])==16
        second.stdin.write('/quit\n');second.stdin.flush();second.wait(timeout=6);assert second.returncode==0
    finally:
        if second.poll() is None:second.kill();second.wait(timeout=5)
        stream.close()
    lines=[json.loads(line) for line in log.read_text().splitlines() if line.startswith('{')]
    final=detail(home);stop=next(x for x in reversed(lines) if x.get('state')=='STOPPING');start=next(x for x in lines if x.get('state')=='STARTED')
    with sqlite3.connect('file:'+str(home/'subject/self.db')+'?mode=ro',uri=True) as db:
        assert not db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'V2_PROCESS_ANON_CANARY')>0").fetchone()
    assert not final['fk_violations'] and final['model_requests']==0 and final['subject_loops']==1 and final['no_action_intentions']>0
    return {'mode':'ACTUAL_LOCAL_DEV_PROCESS_NOT_REAL_MODEL_OR_HUMAN_REVIEW','started_at':started_at,'finished_at':datetime.now(timezone.utc).isoformat(),'total_journey_wall_seconds':time.monotonic()-begin,
        'base_identity':ident,'final_identity':final['identity_id'],'sigkill':'PASS_AFTER_I_TEST_BEFORE_REVIEW','before_kill':before,'completed_no_input':complete,'final':final,
        'pause_preserved_jobs':True,'foreground_offline_response_latency_seconds':latency,'no_new_actions_during_idle':True,
        'independent_runtime_soak_seconds':stop['wall_seconds'],'process_cpu_seconds':stop['cpu_seconds'],'isolated_children_cpu_seconds':stop['children_cpu_seconds'],'isolated_children_max_rss_kib':stop['children_max_rss_kib'],'max_rss_kib':stop['max_rss_kib'],'limits':start['resources'],'work_resources':work_resource,'idle_start_resources':idle_start,'idle_end_resources':idle_end,
        'first_life_experience_ready':'NOT_READY','real_provider_qualified':'BLOCKED_BY_AUTHORIZATION','human_dialogue_quality':'NOT_RUN','real_provider_calls':0,'social_sends':0,'production_changes':0,
        'reports':[p.name for p in (home/'reports').glob('*.md')],'life_board_present':any('life' in x for x in lines)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=90);a=p.parse_args()
    if not 30<=a.seconds<=120:p.error('30–120 second bounded second-process soak')
    result=run(a.root,a.repo,a.seconds);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('sigkill','independent_runtime_soak_seconds','process_cpu_seconds','max_rss_kib','foreground_offline_response_latency_seconds','real_provider_calls')}))
if __name__=='__main__':main()
