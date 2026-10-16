from nana_core.continuity.relational.contracts import DAY
from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService
from nana_core.continuity.relational.projections import social_appetite
from nana_core.presence.fixtures import concern
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.presence.contracts import HOUR
from .fixtures import fresh,bootstrap,signal,event
from .test_tradeoff import request


def test_bounded_self_restraint_due_review_and_no_permanent_rule(tmp_path):
 with fresh(tmp_path/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH')
  for i in range(2):signal(r,'social'+str(i))
  accepted=request(r,review_at_us=r.clock.utc_now_us()+DAY)
  service=VoluntaryAccommodationService(r.store,r.authority)
  cid=service.materialize(accepted.cycle_id,r.authority)
  assert service.materialize(accepted.cycle_id,r.authority)==cid
  assert len(r.store.all('commitments'))==1 and service.commitments.get(cid).state=='ACTIVE'
  mid=concern(r,'new-contact',ConcernCue(cue_kind='OPPORTUNITY',motivation_source='SOCIAL_CONNECTION',topic_key='new-contact',possible_behaviors=('SOCIALIZE',),behavior_domain='SOCIAL_NEW_CONTACTS',availability='AVAILABLE'))
  restrained=r.subject.run(event(r,'opportunity',kind='WAKE',origin='SELF_WAKE',text=None,source_memory_ids=(mid,)))
  assert restrained.evaluation.normative=='RESTRAINED'
  assert social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',)).state=='SEEKING'
  for _ in range(24):r.clock.source.advance(HOUR);r.lease.heartbeat(force=True)
  opportunities=r.subject.background_opportunities(entity_id='anchor-person',now_us=r.clock.utc_now_us(),quiet_since_us=0,quiet_window_us=HOUR)
  check=next(x for x in opportunities if x.source_id==cid)
  assert check.task_class=='relational.accommodation.review'
  review=r.subject.run(event(r,'review',kind='WAKE',origin='SELF_WAKE',text=None,task_class=check.task_class,commitment_check_id=cid))
  assert review.relational_decision.review_choice=='CONTINUE'
  assert review.relational_decision.response.temporal_boundary_us==accepted.relational_decision.response.temporal_boundary_us
  service.materialize(review.cycle_id,r.authority);version=service.commitments.get(cid).revision
  service.materialize(review.cycle_id,r.authority);assert service.commitments.get(cid).revision==version
  for _ in range(48):r.clock.source.advance(HOUR);r.lease.heartbeat(force=True)
  end=r.subject.run(event(r,'end',kind='WAKE',origin='SELF_WAKE',text=None,task_class=check.task_class,commitment_check_id=cid))
  assert end.relational_decision.review_choice=='END'
  assert end.relational_decision.response.temporal_boundary_us is None and end.relational_decision.response.decision=='DECLINE'
  service.materialize(end.cycle_id,r.authority);assert service.commitments.get(cid).state=='CANCELLED'
  again=r.subject.run(event(r,'resume-social',kind='WAKE',origin='SELF_WAKE',text=None,source_memory_ids=(mid,)))
  assert again.intention.kind=='SOCIAL_INTERACTION' and again.evaluation.normative=='ENDORSED'
  assert not r.store.all('actions') and not r.store.all('grants')
