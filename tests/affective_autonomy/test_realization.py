import pytest
from nana_core.contracts import CoreError,GrantSpec
from nana_core.actions import ActionKernel
from nana_core.continuity.autonomy.fixture_effects import OfflineEffectPort
from nana_core.continuity.autonomy.realization import GovernedRealization
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.continuity.autonomy.disclosure import action_phase
from .test_governance import proposed,constraint,TARGET


def equipped(r,*,grant=True):
 port=OfflineEffectPort(r.store.identity['identity_id'],r.store.path.parent/'world.fixture.json')
 ctrl=GovernanceController(r.store,r.authority);ctrl.initialize(r.authority)
 service=GovernedRealization(r.store,port,r.authority)
 service.kernel.set_budgets({'write_attempts':8,'external_requests':16,'cost_micro_units':32},r.authority)
 if grant:
  service.kernel.grant(GrantSpec(capabilities=('reading.source.read','reading.action.verify'),resources=(TARGET.resource,),
   not_before_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+1_000_000_000),r.authority)
 return service,ctrl


def test_pass_is_not_grant_and_direct_kernel_cannot_bypass_governance(subject):
 r=subject;service,ctrl=equipped(r,grant=False);c=proposed(r)
 out,aid=service.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
 assert out.result=='PASS' and aid
 with pytest.raises(CoreError,match='AUTH_REQUIRED'):
  service.dispatch(c.intention_id,aid,expected_revision=1)
 assert r.store.one('actions',aid)['state']=='BLOCKED'
 assert action_phase(r.store,aid)[0]=='ACTION_BLOCKED'
 with pytest.raises(CoreError,match='GOVERNANCE_FENCE_REQUIRED'):
  service.kernel.propose('reading.source.read',TARGET.resource,{'source_id':TARGET.resource})
 with pytest.raises(CoreError,match='SHADOW_BLOCKED'):
  ActionKernel(r.store,object(),r.authority).propose('reading.source.read',TARGET.resource,{'source_id':TARGET.resource})


def test_synthetic_verify_and_late_veto_preserve_actual_history(subject):
 r=subject;service,ctrl=equipped(r);c=proposed(r)
 out,aid=service.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
 ctrl.install(constraint(r),r.authority)
 assert service.dispatch(c.intention_id,aid,expected_revision=1)=='INTENTION_BLOCKED_MANAGER'
 assert r.store.one('actions',aid)['state']=='CANCELLED'
 ctrl.revoke('constraint-a',expected_revision=1,authority=r.authority)
 fresh=proposed(r,'later');out,aid=service.propose(fresh.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
 def late(stage):
  if stage=='after_effect':
   ctrl.install(constraint(r,constraint_id='late'),r.authority)
   raise OSError('fixture lost acknowledgment')
 assert service.dispatch(fresh.intention_id,aid,expected_revision=1,fault=late)=='SUCCEEDED'
 assert action_phase(r.store,aid)[0]=='VERIFIED_EFFECT'
 assert len(service.kernel.capability._load()['effects'])==1
