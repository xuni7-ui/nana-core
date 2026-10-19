"""Actual cloud-like dev residency; shadow surfaces, real owned app effects.

No virtual clock, provider, user desktop, private data, social sends or production.
The orchestrator supplies environments/control inputs, never chooses C actions.
"""
import argparse,json,os,signal,sqlite3,subprocess,sys,time,hashlib
from pathlib import Path
from uuid import uuid4
from nana_core.life.config import LifeConfig,write_config
from nana_core.life.application import LifeApplication
from nana_core.life.control import request
from nana_core.life.cloud import health,transfer,receive
from nana_core.life.surfaces import SurfaceBinding
from nana_core.continuity import ContinuityStore
from nana_core.continuity.hands.host import OwnedApplication,daily_tasks
from nana_core.continuity.project_work.service import material_for
from tools.nana_controlled_hands.qualification import snapshot,process_sample


def configuration(repo,profile=None):
 return LifeConfig(project_root=str(repo),materials=(material_for(repo,'src/nana_core/continuity/recurrence.py'),),practice=material_for(repo,'src/nana_core/continuity/identity.py'),heldout=material_for(repo,'src/nana_core/continuity/autonomy/requests.py'),transfer=material_for(repo,'src/nana_core/continuity/subject/social.py'),owned_application_profile=str(profile) if profile else None,allow_local_skills=bool(profile),max_autonomous_materials=0,shared_presence=True,timezone='Asia/Shanghai',surface_bindings=tuple(SurfaceBinding(binding_id=k,platform=k,surface='chat.direct',adapter='shadow.local') for k in ('cloud.cli','qq.shadow','bili.shadow')))


def run(root,repo,seconds):
 if root.exists():raise ValueError('fresh development qualification root required')
 root.mkdir(parents=True,mode=0o700);home=root/'life';started=time.monotonic();result={'mode':'ACTUAL_OWNED_OS_APPLICATION_AND_SHADOW_SURFACES_NOT_PRODUCTION','new_provider_calls':0,'human_review':'NOT_RUN','source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'samples':[],'controls':[]}
 files=sorted((repo/'src/nana_core').rglob('*.py'))+sorted((repo/'tools/nana_cloud_daily_life').glob('*.py'))
 def hashes():return {str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
 result['source_hashes_start']=hashes()
 with OwnedApplication(root/'target',tasks=daily_tasks()) as target:
  config=configuration(repo,target.profile);write_config(home,config)
  with LifeApplication(home,bootstrap_grant=True) as app:identity=app.runtime.identity_id
  log=(root/'process.jsonl').open('w');args=[sys.executable,'-m','nana_core.life','run','--home',str(home),'--seconds',str(seconds+120),'--headless','--control','--json'];p=None
  def launch():
   child=subprocess.Popen(args,cwd=repo,stdout=log,stderr=log)
   until=time.monotonic()+8
   while time.monotonic()<until:
    if child.poll() is not None:raise RuntimeError('runtime startup failed')
    if (home/'control.sock').exists() and health(home)['process_ready']:return child
    time.sleep(.03)
   raise RuntimeError('runtime did not become ready')
  def command(data):
   value=request(home,data)
   if not value['ok']:raise RuntimeError('controlled operation rejected: '+value.get('code','unknown'))
   result['controls'].append({'elapsed_seconds':time.monotonic()-started,'operation':data['operation'],'result':value['result']})
   return value['result']
  p=launch();next_sample=0;flags=set();complete=None;withdrawn=None;restart_at=min(600,seconds*.7)
  try:
   while time.monotonic()-started<seconds:
    elapsed=time.monotonic()-started
    if p.poll() is not None:raise RuntimeError('runtime exited before residency target')
    if elapsed>=next_sample:
     s=snapshot(home);result['samples'].append({'elapsed_seconds':elapsed,'runtime':process_sample(p.pid),'application':process_sample(target.proc.pid),'actions':len(s['actions']),'goals':len(s['goals']),'pending_intentions':s['pending_intentions'],'queue':s['queue_depth'],'model_calls':s['cognition_calls'],'db_bytes':sum(x.stat().st_size for x in (home/'subject').glob('self.db*') if x.is_file())});next_sample=elapsed+(2 if elapsed<50 else 60)
     if complete is None and len(s['goals'])==12 and all(g['state'] in {'COMPLETED','FAILED'} for g in s['goals']):
      complete=s;result['work_complete_at_seconds']=elapsed;result['at_work_complete']=s
    if elapsed>5 and 'surface-a' not in flags:
     command({'operation':'surface','observation':{'binding_id':'qq.shadow','event_id':'project-a','topic':'shared-project','text':'和你分享公开项目进展','approved_summary':'The public project concerns continuity and verified owned work.','summary_authorization':'EXPLICIT_PROJECT_SUMMARY'}});flags.add('surface-a')
    if elapsed>10 and 'surface-b' not in flags:
     command({'operation':'surface','observation':{'binding_id':'bili.shadow','event_id':'project-b','topic':'shared-project','text':'只是吐槽，接口名有点长'}})
     result['cross_surface_l1']=command({'operation':'continuity','binding_id':'bili.shadow','tier':'L1_RECENT'});flags.add('surface-b')
    if complete and 'pause' not in flags:
     command({'operation':'control','command':'pause'});command({'operation':'control','command':'busy'});before=len(snapshot(home)['actions']);time.sleep(.25);assert len(snapshot(home)['actions'])==before
     command({'operation':'control','command':'available'});command({'operation':'control','command':'resume'});flags.add('pause')
    if complete and elapsed>min(90,seconds*.4) and 'backup' not in flags:
     result['backup']=command({'operation':'backup','name':'checkpoint'});flags.add('backup')
    if complete and elapsed>min(180,seconds*.5) and 'withdraw' not in flags:
     with sqlite3.connect('file:'+str(home/'subject/self.db')+'?mode=ro',uri=True) as db:
      row=db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_reference='owned-source:hands.form-batch-gap' AND m.lifecycle='ACTIVE' LIMIT 1").fetchone()
     assert row;withdrawn=row[0];command({'operation':'forget','memory_id':withdrawn});command({'operation':'control','command':'revoke'});flags.add('withdraw')
    if complete and elapsed>restart_at and 'restart' not in flags:
     previous=snapshot(home);old_epoch=health(home)['runtime']['lease']['epoch'];p.kill();p.wait(5);assert p.returncode==-signal.SIGKILL
     p=launch();new=snapshot(home);assert new['identity_id']==identity and new['grants']==previous['grants'];assert new['actions']==previous['actions']
     result['actual_sigkill_restart']={'same_identity':True,'old_epoch':old_epoch,'new_epoch':health(home)['runtime']['lease']['epoch'],'no_new_grant':True,'no_action_replay':True};flags.add('restart')
    time.sleep(.1)
   result['before_stop']=snapshot(home);result['final_life']=command({'operation':'view','view':'life'})
   command({'operation':'control','command':'stop'});p.wait(8);assert p.returncode==0
  finally:
   if p and p.poll() is None:p.kill();p.wait(5)
   log.close()
  result['actual_residency_seconds']=time.monotonic()-started;final=snapshot(home);result['final']=final
  assert complete and len(final['actions'])==len(complete['actions'])==42 and len(final['goals'])==12
  assert final['identity_id']==identity and final['grants']==1 and not final['cognition_calls'] and not final['fk_violations']
  external=json.loads((Path(target.target.workspace)/'application-state.json').read_text());assert len(external['effects'])==14
  result['actual_external_effects']=14;result['real_task_classes']=sorted({x.kind for x in daily_tasks()})
  with ContinuityStore(home/'backups/checkpoint.db',schema_target=13) as copy:
   assert withdrawn and copy.one('memories',withdrawn)['lifecycle']=='DELETED';result['backup_delete_propagation']=True
  dest=str(uuid4());package=root/'transfer.zip';packed=transfer(home,package,destination_id=dest,source_commit=result['source_head'])
  result['transfer']={'sha256':packed['sha256'],'manifest':packed['manifest']}
  result['received']=receive(package,root/'fresh-host',sha256=packed['sha256'],destination_id=dest,config=configuration(repo))
  with LifeApplication(root/'fresh-host') as app:
   assert app.runtime.identity_id==identity;app.pause()
   result['restored_l1']=app.surfaces.view('cloud.cli').model_dump(mode='json')
   assert len(app.runtime.store.all('actions'))==42 and all(g['revoked'] for g in app.runtime.store.all('grants'))
   result['restored_subject']={'identity_id':app.runtime.identity_id,'grants_all_revoked':True,'same_history':True,'host_profiles_separately_supplied':True,'provider_configuration_transferred':False}
 result['source_hashes_end']=hashes();result['selected_source_unchanged']=result['source_hashes_start']==result['source_hashes_end'];result['human_review']='NOT_RUN';result['production_changes']=0;result['real_social_sends']=0
 result['residency_status']='PASS_GE_TWO_HOURS' if result['actual_residency_seconds']>=7200 else 'SHORT_PROCESS_INTEGRATION_NOT_TWO_HOURS'
 return result


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--seconds',type=float,default=7205);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if not 70<=a.seconds<=259200:p.error('70sec to72h bounded qualification; longer runs require explicit foreground ownership')
 r=run(a.root,a.repo,a.seconds);a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'residency_status':r['residency_status'],'seconds':r['actual_residency_seconds'],'effects':r['actual_external_effects'],'source_unchanged':r['selected_source_unchanged']}))
if __name__=='__main__':main()
