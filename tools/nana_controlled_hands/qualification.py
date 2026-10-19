"""Actual owned-process qualification. No GUI, paid model, private data or fake world."""
import argparse,json,os,signal,sqlite3,subprocess,sys,time,resource,hashlib
from datetime import datetime,timezone
from pathlib import Path
from nana_core.continuity.hands.host import OwnedApplication,default_tasks
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.config import LifeConfig,write_config
from nana_core.continuity.project_work.service import material_for


def initialize(home,repo,profile):
    cfg=LifeConfig(project_root=str(repo),materials=(material_for(repo,'src/nana_core/continuity/recurrence.py'),),practice=material_for(repo,'src/nana_core/continuity/identity.py'),heldout=material_for(repo,'src/nana_core/continuity/autonomy/requests.py'),transfer=material_for(repo,'src/nana_core/continuity/subject/social.py'),owned_application_profile=str(profile),allow_local_skills=True)
    write_config(home,cfg)
    from nana_core.life.application import LifeApplication
    with LifeApplication(home,bootstrap_grant=True) as app:return app.runtime.identity_id


def snapshot(home):
    with sqlite3.connect('file:'+str(home/'subject/self.db')+'?mode=ro',uri=True,timeout=2) as db:
        db.row_factory=sqlite3.Row
        def rows(sql):return [dict(x) for x in db.execute(sql)]
        return {'identity_id':db.execute('SELECT identity_id FROM identities').fetchone()[0],
            'goals':rows('SELECT goal_id,template,state,version FROM goals'),
            'actions':rows('SELECT action_id,capability,state,idempotency_key FROM actions'),
            'experiences':rows('SELECT experience_id,task_class,outcome FROM experiences'),
            'lessons':rows('SELECT lesson_id,task_class,state FROM lessons'),
            'assessments':rows('SELECT lesson_id,verdict,episode_key FROM strategy_assessments'),
            'skill_jobs':rows("SELECT j.job_id,j.state,j.cursor,json_extract(CAST(a.payload AS TEXT),'$.stage') AS stage FROM jobs j JOIN continuity_records r ON r.record_id=j.record_id JOIN artifacts a ON a.artifact_id=r.payload_artifact_id WHERE j.work_kind='CODE_DEVELOPMENT'"),
            'outcomes':[json.loads(x[0])['data'] for x in db.execute("SELECT data_json FROM events WHERE kind='living.goal_step_completed' AND json_extract(data_json,'$.data.operator_id')='apply' ORDER BY seq")],
            'grants':db.execute('SELECT count(*) FROM grants').fetchone()[0],
            'pending_intentions':db.execute("SELECT count(*) FROM subject_intentions WHERE state='PENDING'").fetchone()[0],
            'queue_depth':db.execute("SELECT count(*) FROM runtime_queue WHERE state NOT IN ('DONE','IGNORED','EXPIRED')").fetchone()[0],
            'no_action':db.execute("SELECT count(*) FROM subject_intentions WHERE kind='NO_ACTION'").fetchone()[0],
            'cognition_calls':db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0],
            'control':json.loads((db.execute("SELECT value_json FROM core_meta WHERE key='runtime.life_control'").fetchone() or ['{"paused":false,"messages":0}'])[0]),
            'fk_violations':rows('PRAGMA foreign_key_check')}


def process_sample(pid):
    root=Path('/proc')/str(pid);status={}
    for line in (root/'status').read_text().splitlines():
        if line.split(':')[0] in {'VmRSS','VmHWM','Threads'}:status[line.split(':')[0]]=line.split(':',1)[1].strip()
    parts=(root/'stat').read_text().rsplit(')',1)[1].split();ticks=os.sysconf('SC_CLK_TCK')
    return {**status,'cpu_seconds':(int(parts[11])+int(parts[12]))/ticks,'fd_count':len(list((root/'fd').iterdir()))}


def run(root,repo,seconds,*,real_heldout=False):
    if root.exists():raise ValueError('fresh qualification root required')
    root.mkdir(mode=0o700,parents=True);start=time.monotonic();now=lambda:datetime.now(timezone.utc).isoformat();result={'started_at':now(),'mode':'ACTUAL_OWNED_APPLICATION_PROCESS_NOT_GUI_NOT_USER_DESKTOP','model_calls_new':0,'provider_old_unknown':'PARKED_UNCHANGED','source_head_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'samples':[]}
    executable=list((repo/'src/nana_core/continuity/hands').glob('*.py'))+[repo/'src/nana_core/life/application.py',repo/'src/nana_core/continuity/open_agency/service.py']
    result['source_fingerprints_at_start']={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in executable}
    home=root/'life'
    tasks=list(default_tasks())
    if real_heldout:
        tasks.insert(1,ApplicationTask(task_id='document-heldout',kind='DOCUMENT',initial='Superseded heading: ',wanted='Independent document note',context='notes'))
        tasks.insert(4,ApplicationTask(task_id='form-heldout',kind='FORM',wanted={'language':'plain'},fields=('theme','language'),context='preferences'))
    result['actual_task_manifest']=[t.model_dump(mode='json') for t in tasks]
    result['heldout_kind']='REAL_OWNED_APPLICATION_TASKS_PLUS_SEPARATE_G_PREPARATION_TRIALS' if real_heldout else 'G_PREPARATION_TRIALS_WITH_REAL_LATER_TRANSFER'
    with OwnedApplication(root/'target',tasks=tuple(tasks)) as target:
        identity=initialize(home,repo,target.profile)
        log=root/'runtime.jsonl';stream=log.open('w');p=subprocess.Popen([sys.executable,'-m','nana_core.life','run','--home',str(home),'--seconds',str(seconds+60),'--json'],cwd=repo,stdin=subprocess.PIPE,stdout=stream,stderr=stream,text=True)
        runtime_start=time.monotonic();next_sample=0;complete_at=None;pause_done=False;withdrawal_done=False
        try:
            while time.monotonic()-runtime_start<seconds:
                if p.poll() is not None:raise RuntimeError('actual runtime exited early')
                elapsed=time.monotonic()-runtime_start
                if elapsed>=next_sample:
                    s=snapshot(home);result['samples'].append({'elapsed_seconds':elapsed,'runtime':process_sample(p.pid),'application':process_sample(target.proc.pid),'actions':len(s['actions']),'goals':len(s['goals']),'pending_intentions':s['pending_intentions'],'queue_depth':s['queue_depth'],'model_calls':s['cognition_calls'],'db_bytes':sum(x.stat().st_size for x in (home/'subject').glob('self.db*') if x.is_file())});next_sample=elapsed+(2 if elapsed<35 else 30)
                    if complete_at is None and len(s['goals'])==len(tasks)+1 and all(g['state'] in {'COMPLETED','FAILED'} for g in s['goals']):
                        complete_at=elapsed;result['completed_without_user_input']=s;result['work_completed_at_seconds']=elapsed
                if complete_at is not None and not pause_done:
                    p.stdin.write('/pause\n/status\n/busy\n/life\n');p.stdin.flush();time.sleep(.5)
                    assert snapshot(home)['control']['paused'];paused_actions=len(snapshot(home)['actions']);time.sleep(.5);assert len(snapshot(home)['actions'])==paused_actions
                    p.stdin.write('/available\n/resume\n');p.stdin.flush();result['pause_resume_no_effect_replay']=True;pause_done=True
                if complete_at is not None and elapsed>min(180,seconds*.7) and not withdrawal_done:
                    # One scoped source withdrawal, original privacy lifecycle, no raw transcript.
                    with sqlite3.connect('file:'+str(home/'subject/self.db')+'?mode=ro',uri=True) as db:
                        row=db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_reference='owned-source:hands.form-batch-gap' AND m.lifecycle='ACTIVE' LIMIT 1").fetchone()
                    if row:p.stdin.write('/forget '+row[0]+'\n/life\n');p.stdin.flush();result['source_withdrawn']=row[0]
                    withdrawal_done=True
                time.sleep(.1)
            p.stdin.write('/life\n/quit\n');p.stdin.flush();p.wait(timeout=8)
            assert p.returncode==0
        finally:
            if p.poll() is None:p.kill();p.wait(timeout=5)
            stream.close()
        result['final']=snapshot(home);result['runtime_residency_seconds']=time.monotonic()-runtime_start
        lines=[json.loads(x) for x in log.read_text().splitlines() if x.startswith('{')];stop=next(x for x in reversed(lines) if x.get('state')=='STOPPING');result['runtime_exit_metrics']={k:stop[k] for k in ['wall_seconds','cpu_seconds','max_rss_kib','children_cpu_seconds','children_max_rss_kib']};result['limits']=next(x for x in lines if x.get('state')=='STARTED')['resources'];result['final_life_view']=next(x['life'] for x in reversed(lines) if 'life' in x)
        final=result['final'];initial=result.get('completed_without_user_input');assert initial and initial['identity_id']==identity==final['identity_id'];assert initial['grants']==final['grants']==1
        assert len(initial['actions'])==len(final['actions']) and not final['cognition_calls'] and not final['fk_violations']
        assert len({a['idempotency_key'] for a in final['actions']})==len(final['actions'])
        external=json.loads((Path(target.target.workspace)/'application-state.json').read_text());result['external_effects_count']=len(external['effects']);result['external_state_summary']={k:{'revision':v['revision'],'submitted':v['submitted'],'document_digest':hashlib.sha256(v['text'].encode()).hexdigest() if v['text'] else None} for k,v in external['state'].items()}
        result['finished_at']=now();result['total_wall_seconds']=time.monotonic()-start;result['resource_soak']='PASS_GE_30_MINUTES' if result['runtime_residency_seconds']>=1800 else 'BOUNDED_SHORT_RUN_NOT_LONG_QUALIFICATION'
    result['source_fingerprints_at_end']={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in executable};result['executed_source_files_unchanged']=result['source_fingerprints_at_end']==result['source_fingerprints_at_start']
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--seconds',type=float,default=1805);p.add_argument('--output',type=Path,required=True);p.add_argument('--real-heldout',action='store_true');a=p.parse_args()
    if not 30<=a.seconds<=10800:p.error('bounded30s–3h actual residency')
    result=run(a.root,a.repo,a.seconds,real_heldout=a.real_heldout);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'resource_soak':result['resource_soak'],'wall_seconds':result['runtime_residency_seconds'],'effects':result['external_effects_count'],'source_unchanged':result['executed_source_files_unchanged']}))
if __name__=='__main__':main()
