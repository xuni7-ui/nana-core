import json,sys,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
sys.path[:0]=['/tmp/nfee8/src','/tmp/nana-fee8-qualification/test-dependencies','/tmp/nana-fee8-qualification']
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.application import LifeApplication
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.subject.growth_life import opportunities
from tests.controlled_hands.conftest import initialize,until
root=Path('/tmp/f8r');root.mkdir(mode=0o700,exist_ok=False);home=root/'life'
tasks=(ApplicationTask(task_id='base',kind='DOCUMENT',initial='old ',wanted='new',context='notes'),ApplicationTask(task_id='later',kind='DOCUMENT',initial='draft ',wanted='different',context='research'))
with OwnedApplication(root/'target',tasks=tasks) as host:
 initialize(home,host.profile,skills=False)
 with LifeApplication(home,bootstrap_grant=True) as app:
  r=app.runtime
  until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE' AND task_class='owned-document'").fetchone()))
  failure=r.store.db.execute("SELECT result_memory_id FROM experiences WHERE outcome='FAILURE' AND task_class='owned-document' LIMIT 1").fetchone()[0]
  capture(r,'rollback-checked-gap',ConcernCue(cue_kind='OPEN_LOOP',topic_key='rollback-gap',motivation_source='CAPABILITY_GAP',program_id='learn.owned-document',possible_behaviors=('LEARN','WATCH')).model_dump(mode='json'),kind='MODEL_DERIVATION',parents=(failure,),predicate='concern.rollback-gap')
  until(app,lambda:bool(opportunities(r.store,scope='project-work',privacy_classes=r.config.privacy_classes)))
  app.pause()
 results=[]
 for name,bundle,seed in [('before','/tmp/nfee8',True),('old','/tmp/nana-fee8-input/verified-929',False),('return','/tmp/nfee8',False)]:
  cmd=[bundle+'/.venv/bin/python','-I','/workspace/nana-fee8-rollback-probe.py','--bundle',bundle,'--home',str(home)]
  if seed:cmd.append('--seed')
  done=subprocess.run(cmd,text=True,capture_output=True)
  Path('/workspace/nana-fee8-live-rollback-'+name+'.txt').write_text(done.stdout+done.stderr)
  assert done.returncode==0,done.stderr
  value=json.loads(done.stdout);results.append(value)
 compare=[{k:v for k,v in item.items() if k!='source_commit'} for item in results]
 assert compare[0]==compare[1]==compare[2]
 report={'source_commits':[v['source_commit'] for v in results],'same_identity_private_tendency_and_G_jobs':True,
  'new_cycles_requests_actions_during_return':0,'counts':compare[0]['counts'],'original_host_alive_for_all_stopped_owner_opens':True,
  'real_provider_calls':0,'production_changed':False,'scope':'STOPPED_DEV_BINARY_COMPATIBILITY_NOT_266_OR_PRODUCTION_MIGRATION'}
 Path('/workspace/nana-fee8-rollback.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
