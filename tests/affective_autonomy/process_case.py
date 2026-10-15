"""Tracked local child only. No host access or external effect transport."""
import json,signal,sys
from pathlib import Path
from life import fresh,equip,propose,rule,cycle,TARGET
from nana_core.continuity.autonomy.contracts import DisclosureRequest

path,marker,cut=sys.argv[1:]
with fresh(Path(path),real_clock=True) as r:
 realizer,ctrl=equip(r)
 c=propose(r)
 report={'identity_id':r.store.identity['identity_id'],'cycle_id':c.cycle_id,'intention_id':c.intention_id,
  'epoch':r.lease.epoch,'config':r.config.model_dump(mode='json')}
 def pause():
  Path(marker).write_text(json.dumps(report))
  while True:signal.pause()
 if cut=='C1':pause()
 if cut=='C2':
  ctrl.install(rule(r),r.authority)
  report['outcome_id']=realizer.gate.gate(c.intention_id,expected_revision=1).record_id;pause()
 if cut=='C3':
  report['outcome_id']=realizer.gate.gate(c.intention_id,expected_revision=1).record_id;pause()
 out,aid=realizer.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
 report['action_id']=aid
 if cut=='C4':
  ctrl.install(rule(r),r.authority);pause()
 if cut=='C5':
  def fault(stage):
   if stage=='after_effect':pause()
  realizer.dispatch(c.intention_id,aid,expected_revision=1,fault=fault)
 if cut=='C6':
  d=cycle(r,'disclosure',disclosure_request=DisclosureRequest(topic='work',action_id=aid))
  report['disclosure_cycle_id']=d.cycle_id
  report['cycles']=len(r.store.all('subject_cycles'))
  pause()
 raise AssertionError('unreached checkpoint')
