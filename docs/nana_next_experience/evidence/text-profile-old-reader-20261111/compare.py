import json,subprocess,shutil
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.life.memory_notes import save
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.records import RecordService
from tests.independent_life.conftest import initialize
from tests.independent_life.test_retrieval_growth import advance,selected
from tests.independent_life.test_retrieval_text_profile import TRAIN
root=Path('/tmp/nana-text-old-reader');root.mkdir(mode=0o700)
all_results=[]
for state in ('completed','pending-c','pending-g'):
 base=root/state;base.mkdir(mode=0o700);home=base/'source';initialize(home,active=0);clock=VirtualClock()
 with LifeApplication(home,clock=clock) as app:
  for i,text in enumerate(TRAIN):save(app,text=text,privacy='PROJECT',request_id='reader-training-'+str(i))
  growth=app.runtime.work.note_retrieval_growth;growth.slice('project-work');advance(app);assert selected(app)[1]=='UNICODE_WORDS'
  growth.slice('project-work')
  if state=='completed':advance(app);assert selected(app)[1]=='NFKC_CASEFOLD'
  elif state=='pending-g':
   for _ in range(12):
    clock.advance(1_000_000);app.runtime.step()
    jobs=[]
    for row in app.runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' AND state='WAITING'"):
     body=RecordService(app.runtime.store).read(row['record_id'])['payload']
     if 'NFKC_CASEFOLD' in body['spec']['hypotheses']:jobs.append(body['stage'])
    if jobs:break
   assert jobs
  initial={'state':state,'identity':app.runtime.identity_id,'selected':selected(app),'calls':len(app.runtime.store.all('cognitive_requests')),'cycles':len(app.runtime.store.all('subject_cycles')),'actions':len(app.runtime.store.all('actions')),'now_us':app.runtime.clock.utc_now_us()}
 clone=base/'isolated-copy';shutil.copytree(home,clone)
 result=subprocess.run(['/tmp/nc63/.venv/bin/python','-I','/tmp/nana_old_text_reader.py','/tmp/nc63',str(clone),str(base/'old-report.json'),str(initial['now_us']+1_000_000)],cwd='/tmp',capture_output=True,text=True,timeout=40)
 (base/'old-stdout.log').write_text(result.stdout);(base/'old-stderr.log').write_text(result.stderr)
 old=json.loads((base/'old-report.json').read_text());old['returncode']=result.returncode
 now=max(initial['now_us'],old.get('now_us',initial['now_us']))+1_000_000
 restored={}
 try:
  with LifeApplication(clone,clock=VirtualClock(now)) as app:
   r=app.runtime;restored={'identity':r.identity_id,'epoch':r.lease.epoch,'selected_before':selected(app)}
   advance(app);restored.update(selected_after=selected(app),calls=len(r.store.all('cognitive_requests')),cycles=len(r.store.all('subject_cycles')),actions=len(r.store.all('actions')))
 except Exception as exc:restored.update(error_type=type(exc).__name__,error_code=getattr(exc,'code',None))
 report={'initial':initial,'old':old,'new_return':restored};(base/'result.json').write_text(json.dumps(report,indent=2)+'\n');all_results.append(report)
 print(json.dumps(report),flush=True)
(root/'result.json').write_text(json.dumps(all_results,indent=2)+'\n')
