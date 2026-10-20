"""Bounded dev residency supervisor. One original Runtime, not a second brain.

Progress is operational metadata, never Subject authority. No provider, private
content, production service or real platform. Incomplete duration stays PARTIAL.
"""
import argparse,json,os,signal,sqlite3,subprocess,sys,time
from pathlib import Path
from nana_core.life.durability import _atomic
from tools.nana_controlled_hands.qualification import process_sample


def run(repo,root,seconds):
 import nana_core
 if Path(nana_core.__file__).resolve().parent.parent!=(repo/'src').resolve():raise ValueError('loaded Core source does not match pinned staging repo')
 if root.exists():raise ValueError('fresh staging root required')
 root.mkdir(parents=True,mode=0o700);started=time.monotonic();stop=False
 args=[sys.executable,'-u','-m','tools.nana_cloud_daily_life.qualification','--repo',str(repo),'--root',str(root/'journey'),'--output',str(root/'result.json'),'--seconds',str(seconds)]
 with (root/'qualification.log').open('w') as log:
  child=subprocess.Popen(args,cwd=repo,stdout=log,stderr=log)
  def stopping(*unused):
   nonlocal stop
   stop=True
  signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
  state={}
  try:
   while child.poll() is None:
    if stop:child.send_signal(signal.SIGINT);child.wait(15);break
    elapsed=time.monotonic()-started
    state={'state':'RUNNING_NOT_QUALIFIED','supervisor_pid':os.getpid(),'qualification_pid':child.pid,'target_seconds':seconds,'elapsed_seconds':elapsed,'provider_calls':0,'real_social_sends':0,'production':False,'loaded_core_source_directory':str(Path(nana_core.__file__).resolve().parent),'durable_cloud_host':'NOT_ATTESTED_MANAGED_DEV_WORKSPACE','home':str(root/'journey/life')}
    db=root/'journey/life/subject/self.db'
    if db.exists():
     try:
      with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True,timeout=1) as d:
       lease=d.execute('SELECT pid,epoch,state FROM runtime_lease').fetchone()
       state['runtime']={'pid':lease[0],'epoch':lease[1],'state':lease[2]};state['actions']=d.execute('SELECT count(*) FROM actions').fetchone()[0];state['queue']=d.execute("SELECT count(*) FROM runtime_queue WHERE state NOT IN ('DONE','IGNORED','EXPIRED')").fetchone()[0]
       try:state['resources']=process_sample(lease[0])
       except FileNotFoundError:state['resources']='TRANSITION'
     except sqlite3.Error:state['runtime']='STARTING_OR_TRANSITION'
    _atomic(root/'progress.json',json.dumps(state))
    # Short waits keep interruption bounded; no model/task decisions occur here.
    for _ in range(30):
     if stop or child.poll() is not None:break
     time.sleep(.5)
  finally:
   if child.poll() is None:child.send_signal(signal.SIGINT);child.wait(15)
  state.update(state='PARTIAL_INTERRUPTED' if stop else 'FAILED_REVIEW_REQUIRED',exit_code=child.returncode,elapsed_seconds=time.monotonic()-started)
  if not stop and child.returncode==0 and (root/'result.json').exists():
   result=json.loads((root/'result.json').read_text())
   if result['selected_source_unchanged']:
    state['state']='PASS_24H_DEV' if result['actual_residency_seconds']>=86400 else 'SHORT_DEV_PROCESS_NOT_24H'
  state['last_runtime_observation']=state.pop('runtime',None)
  try:
   from nana_core.presence.cli import status
   state['runtime_final']=status(root/'journey/life/subject/self.db')
  except (OSError,sqlite3.Error):state['runtime_final']={'status':'UNKNOWN_REQUIRES_INSPECTION'}
  _atomic(root/'progress.json',json.dumps(state));return state

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--seconds',type=float,default=86405);a=p.parse_args()
 if not 70<=a.seconds<=259200:p.error('bounded70s to72h')
 print(json.dumps(run(a.repo,a.root,a.seconds)),flush=True)
