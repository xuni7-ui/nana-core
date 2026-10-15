from datetime import datetime,timezone
import pytest
from nana_core.contracts import CoreError
from nana_core.clock import parse_utc
from nana_core.continuity.autonomy.contracts import PositiveRequest
from nana_core.continuity.autonomy.requests import RequestCommitmentService
from nana_core.continuity.recurrence import RecurrenceSpec
from nana_core.continuity.commitments import CommitmentService
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.contracts import HOUR,DAY
from .conftest import event


def test_positive_request_propose_not_adopt_and_negotiate(subject):
 r=subject
 recurrence=RecurrenceSpec(timezone='UTC',hour=23,minute=0)
 c=r.subject.run(event(r,'request',positive_request=PositiveRequest(task_class='REMINDER',description='A fictional daily reminder',recurrence=recurrence)))
 assert c.request_decision.decision=='ACCEPT' and not r.store.all('commitments')
 app=RequestCommitmentService(r.store,r.authority)
 cid=app.materialize(c.cycle_id)
 assert app.materialize(c.cycle_id)==cid
 assert len(r.store.all('commitments'))==1 and app.commitments.get(cid).state=='PROPOSED'
 assert not r.store.all('runtime_schedules') and not r.store.all('grants')
 n=r.subject.run(event(r,'negotiate',positive_request=PositiveRequest(task_class='CONTACT',description='A fictional contact request')))
 assert n.request_decision.decision=='NEGOTIATE' and n.social_proposal
 assert app.materialize(n.cycle_id) is None


def test_daily_calendar_dst_gap_fold_and_coalescing(subject):
 gap=RecurrenceSpec(timezone='America/New_York',hour=2,minute=30)
 assert gap.next_after(parse_utc('2026-03-08T00:00:00Z'))==parse_utc('2026-03-08T07:00:00Z')
 early=RecurrenceSpec(timezone='America/New_York',hour=1,minute=30)
 late=early.model_copy(update={'fold':'LATEST'})
 assert early.next_after(parse_utc('2026-11-01T00:00:00Z'))==parse_utc('2026-11-01T05:30:00Z')
 assert late.next_after(parse_utc('2026-11-01T00:00:00Z'))==parse_utc('2026-11-01T06:30:00Z')
 assert early.next_after(parse_utc('2026-11-01T05:30:00Z'))==parse_utc('2026-11-02T06:30:00Z')
 r=subject;rec=RecurrenceSpec(timezone='UTC',hour=1,minute=0)
 c=r.subject.run(event(r,'daily',positive_request=PositiveRequest(task_class='REMINDER',description='Fictional check',recurrence=rec)))
 app=RequestCommitmentService(r.store,r.authority);cid=app.materialize(c.cycle_id)
 app.commitments.transition(cid,'ADOPTED',expected_revision=1,authority=r.authority)
 path=r.store.path;clock=r.clock;r.store.close()
 cfg=RuntimeConfig(schema_target=9,scopes=('lab',),entity_id='person-a',lease_us=3*HOUR,heartbeat_us=HOUR)
 try:
  with NanaRuntime(path,cfg,clock=clock) as rt:
   rt.drain()
   sid=next(x['schedule_id'] for x in rt.store.all('runtime_schedules') if x['schedule_kind']=='CALENDAR')
   # A 10-day absence coalesces to one occurrence in today's valid window.
   for _ in range(10*24+1):clock.advance(HOUR);rt.lease.heartbeat(force=True)
   rt.drain()
   calendar=rt.store.one('runtime_schedules',sid)
   assert calendar['occurrence']==1
   assert rt.store.one('runtime_queue',calendar['last_queue_id'])['state']=='DONE'
   assert not rt.store.all('actions') and not rt.store.all('grants')
   count=len(rt.store.all('subject_cycles'));rt.drain();assert len(rt.store.all('subject_cycles'))==count
  with NanaRuntime(path,cfg,clock=clock) as reopened:
   reopened.drain();assert reopened.store.one('runtime_schedules',sid)['occurrence']==1
 finally:
  # Fixture context owns its Store close; reopening this same object is not used.
  r.store.close=lambda:None
