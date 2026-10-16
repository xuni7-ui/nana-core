"""Bounded SIGKILL/reap/reopen protocol; no background host/process discovery."""
import json,os,signal,sys,subprocess,time
from pathlib import Path
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.relational.bootstrap import anchor_view
from nana_core.continuity.relational.projections import personality_tendencies,self_narrative
from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService


def run(directory):
 reports=[]
 for cut in ('C1','C2','C3_BEFORE','C3_AFTER','C4','C5','C6'):
  root=Path(directory)/cut;root.mkdir(mode=0o700,parents=True);path,marker=root/'self.db',root/'ready.json'
  p=subprocess.Popen([sys.executable,str(Path(__file__).with_name('process_case.py')),str(path),str(marker),cut],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   until=time.monotonic()+15
   while not marker.exists() and p.poll() is None and time.monotonic()<until:time.sleep(.01)
   if not marker.exists():raise AssertionError((cut,'missing checkpoint',p.communicate(timeout=2)))
   meta=json.loads(marker.read_text());os.kill(p.pid,signal.SIGKILL);stdout,stderr=p.communicate(timeout=10)
   assert p.returncode==-signal.SIGKILL and not stdout and not stderr
  finally:
   if p.poll() is None:p.kill();p.communicate(timeout=10)
  with NanaRuntime(path,RuntimeConfig.model_validate_json(json.dumps(meta['config'])),clock=VirtualClock(meta['clock_us'])) as r:
   assert r.store.identity['identity_id']==meta['identity_id'] and r.lease.epoch==meta['epoch']+1
   if cut=='C1':
    a=anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',));assert a and a.spec.revision==1
    assert r.store.db.execute("SELECT count(*) FROM continuity_records WHERE record_kind='SUBJECT_BOOTSTRAP' AND target_id='anchor:lab' AND lifecycle='ACTIVE'").fetchone()[0]==1
   if cut=='C2':
    s=VoluntaryAccommodationService(r.store,r.authority);cid=s.materialize(meta['cycle_id'],r.authority)
    assert s.materialize(meta['cycle_id'],r.authority)==cid and len(r.store.all('commitments'))==1
    assert s.commitments.get(cid).state=='ACTIVE'
   if cut.startswith('C3'):
    e=SubjectInput.model_validate_json(json.dumps(meta['event']));c=r.subject.run(e)
    assert c.replayed==(cut=='C3_AFTER') and c.relational_decision.review_choice=='CONTINUE'
    s=VoluntaryAccommodationService(r.store,r.authority);cid=s.materialize(c.cycle_id,r.authority);revision=s.commitments.get(cid).revision
    replay=r.subject.run(e);assert replay.replayed and replay.cycle_id==c.cycle_id
    assert s.materialize(c.cycle_id,r.authority)==cid and s.commitments.get(cid).revision==revision
    assert r.store.db.execute("SELECT count(*) FROM events WHERE kind='commitment.voluntary_reviewed'").fetchone()[0]==1
   if cut=='C4':
    before=len(r.store.all('assertion_signals'));e=SubjectInput.model_validate_json(json.dumps(meta['event']))
    assert r.subject.run(e).replayed and len(r.store.all('assertion_signals'))==before==2
    f=next(f for f in personality_tendencies(r.store,scope='lab',privacy_classes=('PERSONAL',)).facets if f.name=='relational_accommodation')
    assert f.independent_support_count==2
   if cut=='C5':
    assert anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',)) is None
    a=anchor_view(r.store,'friend-person',scope='lab',privacy_classes=('PERSONAL',));assert a.spec.revision==2
   if cut=='C6':assert not self_narrative(r.store,scope='lab',privacy_classes=('PERSONAL',)).entries
   assert not any(r.store.all(t) for t in ('actions','attempts','grants','budgets'))
   assert r.store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
   reports.append({'cut':cut,'result':'PASS','sigkill':True,'reopened_epoch':r.lease.epoch,'identity_continuous':True,'zero_external_actions':True})
 return {'result':'PASS','origin':'REAL_LOCAL_PROCESS_SYNTHETIC_STATE','cuts':reports}
