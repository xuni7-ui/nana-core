import pytest
from pydantic import ValidationError
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.continuity.autonomy.contracts import RealizationTarget
from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraint,ManagerConstraintGate,manager_views
from nana_core.continuity.subject.opportunities import ConcernCue
from .conftest import event,memory,concern

TARGET=RealizationTarget(capability='reading.source.read',operation='READ',resource='synthetic://ordinary/topic',resource_class='ORDINARY')
def proposed(r,key='candidate'):
 m=concern(r,key,ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CURIOSITY',topic_key=key,possible_behaviors=('EXPLORE',),resource_ref=TARGET.resource,resource_class='ORDINARY'))
 return r.subject.run(event(r,key,source_memory_ids=(m,),realization_target=TARGET))

def constraint(r,**updates):
 data=dict(constraint_id='constraint-a',revision=1,issuer=r.authority.principal,source_reference='fixture-reviewed',identity_id=r.store.identity['identity_id'],scope='lab',targets=(TARGET,),effective_from_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+100_000_000,reason_code='DO_NOT_READ_RESOURCE')
 data.update(updates);return ManagerConstraint(**data)

def test_post_judgment_block_transparency_revoke_and_no_auto_retry(subject):
 r=subject;ctrl=GovernanceController(r.store,r.authority);ctrl.initialize(r.authority)
 c=proposed(r);original=r.subject.result(dict(r.store.db.execute('SELECT * FROM subject_cycles WHERE cycle_id=?',(c.cycle_id,)).fetchone()))
 source=ctrl.install(constraint(r),r.authority);gate=ManagerConstraintGate(r.store)
 blocked=gate.gate(c.intention_id,expected_revision=1)
 assert blocked.result=='BLOCK' and blocked.constraint_refs==(source,)
 assert blocked.action_id is None and blocked.actual_effect=='NONE'
 assert gate.gate(c.intention_id,expected_revision=1)==blocked
 assert r.subject.result(dict(r.store.db.execute('SELECT * FROM subject_cycles WHERE cycle_id=?',(c.cycle_id,)).fetchone()))==original
 review=r.subject.run(event(r,'review',governance_review_id=blocked.record_id))
 assert review.judgment.stance=='DISAGREE' and review.social_proposal is None
 assert manager_views(r.store,scope='lab',privacy_classes=('PERSONAL',))[0]['result']=='BLOCK'
 with pytest.raises(CoreError,match='UNAUTHENTICATED'):
  ctrl.revoke('constraint-a',expected_revision=1,authority=OperatorAuthority('pretend-subject'))
 ctrl.revoke('constraint-a',expected_revision=1,authority=r.authority)
 assert gate.gate(c.intention_id,expected_revision=1)==blocked
 fresh=proposed(r,'fresh');passed=gate.gate(fresh.intention_id,expected_revision=1)
 assert passed.result=='PASS' and not r.store.all('grants') and not r.store.all('actions')
 with pytest.raises(CoreError,match='INTENTION_BLOCKED'):gate.require_current(blocked)
 gate.require_current(passed)
 ctrl.install(constraint(r,constraint_id='new-rule'),r.authority)
 with pytest.raises(CoreError,match='STALE_MANAGER_PASS'):gate.require_current(passed)


def test_negative_only_and_source_authentication(subject):
 r=subject;ctrl=GovernanceController(r.store,r.authority)
 with pytest.raises(ValidationError):constraint(r,restriction='MUST_CONTACT')
 with pytest.raises(ValidationError):constraint(r,positive_task='message every day')
 with pytest.raises(ValidationError):RealizationTarget(capability='*',operation='READ',resource='synthetic://*')
 with pytest.raises(CoreError,match='TYPED_NEGATIVE'):ctrl.install({'restriction':'DENY'},r.authority)
 c=proposed(r);unknown=ManagerConstraintGate(r.store).gate(c.intention_id,expected_revision=1)
 assert unknown.result=='UNKNOWN'
 ctrl.initialize(r.authority)
 assert ManagerConstraintGate(r.store).gate(c.intention_id,expected_revision=1)==unknown
