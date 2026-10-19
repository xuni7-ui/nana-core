from nana_core.life.application import LifeApplication
from tests.independent_life.test_dialogue import relay
from .conftest import initialize

def test_hourly_reservations_intersect_original_global_budget(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,provider_calls_per_hour=2,provider_cost_ceiling_micro=100)
 with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
  app.pause();a=app.chat('SYNTHETIC_PUBLIC_PROJECT first',privacy='PROJECT',message_id='a')
  assert len(calls)==2 and a['render_state']=='UNVERIFIED_MODEL_WORDING'
  b=app.chat('SYNTHETIC_PUBLIC_PROJECT second',privacy='PROJECT',message_id='b')
  assert b['provider_state']=='PROVIDER_HOURLY_BUDGET' and len(calls)==2
  assert len(app.runtime.store.all('cognitive_requests'))==2

def test_per_provider_budget_does_not_add_global_capacity(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,per_provider_calls_per_day=1,provider_cost_ceiling_micro=100)
 with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
  app.pause();a=app.chat('SYNTHETIC_PUBLIC_PROJECT',privacy='PROJECT',message_id='a')
  assert len(calls)==1 and a['render_state']=='PROVIDER_PROFILE_DAILY_BUDGET'
  assert not app.runtime.store.all('grants')
