"""Actual-process one-owner transition and rollback on a fresh synthetic home."""
import json,subprocess,sys,time
from pathlib import Path
from uuid import uuid4
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.config import write_config
from nana_core.life.cloud import transfer,receive,health
from nana_core.life.control import request
from tools.nana_cloud_daily_life.qualification import configuration


def run(repo,root):
 if root.exists():raise CoreError('FRESH_REHEARSAL_ROOT_REQUIRED')
 root.mkdir(parents=True,mode=0o700);source=root/'legacy-role';cfg=configuration(repo);write_config(source,cfg)
 with LifeApplication(source) as app:identity=app.runtime.identity_id
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();children=[];logs=[];epochs=[]
 def launch(home):
  log=(root/(home.name+'.log')).open('a');logs.append(log)
  p=subprocess.Popen([sys.executable,'-m','nana_core.life','run','--home',str(home),'--seconds','90','--headless','--control','--json'],cwd=repo,stdout=log,stderr=log);children.append(p)
  until=time.monotonic()+8
  while time.monotonic()<until:
   if p.poll() is not None:raise RuntimeError('rehearsal runtime failed')
   if (home/'control.sock').exists() and health(home)['process_ready']:
    epochs.append(health(home)['runtime']['lease']['epoch']);return p
   time.sleep(.025)
  raise RuntimeError('rehearsal readiness timeout')
 def command(home,data):
  r=request(home,data)
  if not r['ok']:raise CoreError(r['code'])
  return r['result']
 def stop(home,p):command(home,{'operation':'control','command':'stop'});p.wait(8);assert p.returncode==0
 def moved(home,dest,label):
  destination=str(uuid4());package=root/(label+'.zip')
  export=transfer(home,package,destination_id=destination,source_commit=head)
  result=receive(package,dest,sha256=export['sha256'],destination_id=destination,config=cfg)
  assert result['identity_id']==identity
  try:LifeApplication(home)
  except CoreError as e:assert e.code=='PORTABLE_SOURCE_RETIRED'
  else:raise AssertionError('retired source resumed as writer')
  return result
 try:
  old=launch(source);command(source,{'operation':'control','command':'pause'})
  try:transfer(source,root/'must-not-export.zip',destination_id=str(uuid4()),source_commit=head)
  except CoreError as e:assert e.code=='RUNTIME_ALREADY_ACTIVE'
  else:raise AssertionError('active owner transfer was permitted')
  stop(source,old)
  next_home=root/'core-owner';new=moved(source,next_home,'cutover');p=launch(next_home)
  inbound=command(next_home,{'operation':'surface','observation':{'binding_id':'qq.shadow','event_id':'canary-one','topic':'synthetic-canary','text':'只是吐槽，这是公开合成输入','privacy_class':'PROJECT'}})
  assert inbound['delivered'] is False and inbound['execution_authority'] is False
  status=command(next_home,{'operation':'view','view':'status'});assert status['identity_id']==identity
  stop(next_home,p)
  rollback_home=root/'rollback-owner';rolled=moved(next_home,rollback_home,'rollback');p=launch(rollback_home)
  assert command(rollback_home,{'operation':'view','view':'status'})['identity_id']==identity
  recent=command(rollback_home,{'operation':'continuity','binding_id':'cloud.cli','tier':'L1_RECENT'})
  assert recent['source_event_ids']
  stop(rollback_home,p)
  assert epochs==sorted(set(epochs))
  return {'level':'ACTUAL_PROCESS_SYNTHETIC_LEGACY_ROLE_NOT_PRODUCTION','identity_id':identity,'source_head':head,'epochs':epochs,'all_owned_pids':[p.pid for p in children],'source_retired_before_new_owner':True,'old_writer_resume_rejected':True,'active_owner_transfer_rejected':True,'same_identity':True,'rollback':'B8_TRANSFER_TO_FRESH_ROLLBACK_HOME_NOT_STALE_SNAPSHOT_OVERWRITE','recent_continuity_survives':True,'execution_grants_inherited':False,'real_social_sends':0,'production_inventory':'NOT_RUN','production_cutover':False,'new_owner':new,'rollback_owner':rolled}
 finally:
  for p in children:
   if p.poll() is None:p.terminate();p.wait(8)
  for f in logs:f.close()

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run(a.repo,a.root);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
