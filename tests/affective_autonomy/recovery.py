"""Crash matrix invokes/reaps actual SIGKILL children and reopens authoritative Store."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.contracts import CoreError
from nana_core.continuity.subject import SubjectInput
from .life import equip,rule,TARGET


def run(directory):
 reports=[]
 for cut in ('C1','C2','C3','C4','C5','C6'):
  root=Path(directory)/cut;root.mkdir(parents=True,mode=0o700)
  path,marker=root/'self.db',root/'ready.json'
  p=subprocess.Popen([sys.executable,str(Path(__file__).with_name('process_case.py')),str(path),str(marker),cut],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   until=time.monotonic()+15
   while not marker.exists() and p.poll() is None and time.monotonic()<until:time.sleep(.01)
   if not marker.exists():raise AssertionError(('checkpoint not reached',cut,p.communicate(timeout=2)))
   m=json.loads(marker.read_text());os.kill(p.pid,signal.SIGKILL);stdout,stderr=p.communicate(timeout=10)
   assert p.returncode==-signal.SIGKILL and not stdout and not stderr
  finally:
   if p.poll() is None:p.kill();p.communicate(timeout=10)
  with NanaRuntime(path,RuntimeConfig.model_validate_json(json.dumps(m['config']))) as r:
   r.drain();realizer,ctrl=equip(r)
   assert r.store.identity['identity_id']==m['identity_id'] and r.lease.epoch==m['epoch']+1
   original=r.subject.result(dict(r.store.db.execute('SELECT * FROM subject_cycles WHERE cycle_id=?',(m['cycle_id'],)).fetchone()))
   assert original.evaluation.normative=='ENDORSED'
   if cut=='C1':
    assert not r.store.all('actions')
    assert not r.store.db.execute("SELECT 1 FROM events WHERE kind='governance.outcome'").fetchone()
    assert realizer.gate.gate(m['intention_id'],expected_revision=1).result=='PASS'
   if cut=='C2':
    before=len(r.store.all('experiences'))
    assert realizer.gate.gate(m['intention_id'],expected_revision=1).record_id==m['outcome_id']
    assert r.store.db.execute("SELECT count(*) FROM events WHERE kind='governance.outcome'").fetchone()[0]==1
    assert not r.store.all('actions') and len(r.store.all('experiences'))==before==0
   if cut=='C3':
    old=realizer.gate.read(m['outcome_id'])
    try:realizer.gate.require_current(old);raise AssertionError('old epoch PASS reused')
    except CoreError as e:assert e.code=='STALE_MANAGER_PASS'
    new=realizer.gate.gate(m['intention_id'],expected_revision=1)
    assert new.runtime_epoch==r.lease.epoch and not r.store.all('actions')
   if cut=='C4':
    aid=m['action_id'];assert r.store.one('actions',aid)['state']=='PROPOSED'
    assert realizer.dispatch(m['intention_id'],aid,expected_revision=1)=='INTENTION_BLOCKED_MANAGER'
    assert r.store.one('actions',aid)['state']=='CANCELLED' and not r.store.all('attempts')
   if cut=='C5':
    aid=m['action_id'];assert r.store.one('actions',aid)['state']=='DISPATCHING'
    ctrl.install(rule(r),r.authority)
    blocked=realizer.gate.gate(m['intention_id'],expected_revision=1)
    assert blocked.result=='BLOCK' and blocked.actual_effect=='UNKNOWN' and blocked.action_id==aid
    assert realizer.dispatch(m['intention_id'],aid,expected_revision=1)=='SUCCEEDED'
    assert len(realizer.kernel.capability._load()['effects'])==1
    assert [x['kind'] for x in r.store.all('attempts')]==['EXECUTE','VERIFY']
   if cut=='C6':
    raw=r.store.db.execute('SELECT r.* FROM subject_events e JOIN continuity_records r ON r.record_id=e.record_id WHERE e.source_key=?',('synthetic.affect-life.disclosure',)).fetchone()
    payload=r.subject.records.read(raw['record_id'])['payload']
    event=SubjectInput.model_validate_json(json.dumps(payload['input']))
    replay=r.subject.run(event)
    assert replay.replayed and replay.cycle_id==m['disclosure_cycle_id']
    assert len(r.store.all('subject_cycles'))==m['cycles']
   assert r.store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
   assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
   reports.append({'cut':cut,'result':'PASS','signal':'SIGKILL','identity_preserved':True,'judgment_preserved':True,
    'recovery':'VERIFY_ONLY_NO_RETRY' if cut=='C5' else 'FRESH_GATE_REQUIRED' if cut in ('C1','C3') else 'TERMINAL_BLOCKED' if cut in ('C2','C4') else 'REPLAY_NO_DUPLICATE_DISCLOSURE',
    'effects':len(realizer.kernel.capability._load()['effects']),'real_external_actions':0})
 return {'origin':'REAL_LOCAL_PROCESSES_SYNTHETIC_STORES','cuts':reports,'result':'PASS'}
