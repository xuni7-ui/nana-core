import json
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.surfaces import SurfaceBinding
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from .conftest import initialize,until

def test_verified_experience_can_reach_original_c_and_shadow_delivery_gate(tmp_path):
 task=ApplicationTask(task_id='note',kind='DOCUMENT',wanted='finite')
 with OwnedApplication(tmp_path/'app',tasks=(task,)) as target:
  home=tmp_path/'life';initialize(home,owned_application_profile=str(target.profile),quiet_start_local_hour=0,quiet_end_local_hour=0,surface_bindings=(SurfaceBinding(binding_id='cloud.cli',platform='cloud.local',surface='chat.direct',adapter='shadow.local'),))
  with LifeApplication(home,bootstrap_grant=True) as app:
   assert not app.shared.candidates()
   until(app,lambda:bool(app.shared.candidates()));app.pause()
   candidate=app.shared.candidates()[0];app.presence('AVAILABLE',privacy_classes=('PUBLIC','PROJECT'))
   offered=app.shared.opportunity();assert offered
   app.pause(False);until(app,lambda:app.runtime.store.one('runtime_queue',offered['queue_id'])['state']=='DONE');app.pause()
   q=app.runtime.store.one('runtime_queue',offered['queue_id']);cycle=app.runtime.store.one('subject_cycles',q['cycle_id'])
   outcome=app.runtime.subject.result(cycle);assert outcome.intention.kind=='SOCIAL_INTERACTION'
   review=app.shared.review(outcome.cycle_id,'cloud.cli')
   assert not review['delivered'] and not review['execution_authority'] and review['decision']['result']=='ELIGIBLE'
   app.presence('BUSY',privacy_classes=('PUBLIC','PROJECT'))
   with pytest.raises(CoreError,match='RETIRED'):app.shared.review(outcome.cycle_id,'cloud.cli')
   app.forget(candidate['source_memory_ids'][0]);assert not app.shared.candidates()
   with pytest.raises(CoreError):app.shared.review(outcome.cycle_id,'cloud.cli')
   assert len(app.runtime.store.all('grants'))==1

def test_quiet_hours_use_iana_local_time_and_no_half_window():
 from nana_core.continuity.open_agency.delivery import DeliveryPolicy,DeliveryAdmission
 from nana_core.presence.authority import VirtualClock
 from datetime import datetime,timezone
 class Store:
  clock=VirtualClock(int(datetime(2026,10,19,21,30,tzinfo=timezone.utc).timestamp()*1e6))
 # 05:30 in Shanghai is quiet; UTC21:30 with same wall-hour range is not.
 local=DeliveryPolicy(recipients=(),quiet_timezone='Asia/Shanghai',quiet_start_local_hour=23,quiet_end_local_hour=7)
 gate=object.__new__(DeliveryAdmission);gate.store=Store();gate.policy=local;assert gate._quiet()
 gate.policy=DeliveryPolicy(recipients=());assert not gate._quiet()
 with pytest.raises(ValueError):DeliveryPolicy(recipients=(),quiet_start_local_hour=7)
 with pytest.raises(ValueError):DeliveryPolicy(recipients=(),quiet_timezone='not/a-timezone')
