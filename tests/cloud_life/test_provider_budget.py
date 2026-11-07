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
  assert '过去24小时' in a['text'] and 'PROVIDER_' not in a['text'] and '尚未配置' not in a['text']
  assert not app.runtime.store.all('grants')


def test_total_call_budget_survives_restart_and_next_day(tmp_path):
 from nana_core.presence.authority import VirtualClock
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,provider_calls_per_day=20,provider_calls_per_hour=20,provider_cost_ceiling_micro=100,provider_total_calls_limit=2)
 clock=VirtualClock()
 with relay(home,'CHAT') as (router,calls):
  with LifeApplication(home,clock=clock,router=router) as app:
   app.pause();a=app.chat('SYNTHETIC_PROJECT first',privacy='PROJECT',message_id='a')
   assert len(calls)==2 and a['render_state']=='UNVERIFIED_MODEL_WORDING'
  clock.advance(25*3600*1000000)
  with LifeApplication(home,clock=clock,router=router) as app:
   b=app.chat('SYNTHETIC_PROJECT new day',privacy='PROJECT',message_id='b')
   assert b['provider_state']=='PROVIDER_TOTAL_CALL_BUDGET' and len(calls)==2
   assert len(app.runtime.store.all('cognitive_requests'))==2


def test_total_cost_is_reserved_not_invented_actual_billing(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,provider_cost_ceiling_micro=100,provider_total_reserved_cost_micro=100)
 with relay(home,'CHAT') as (router,calls),LifeApplication(home,router=router) as app:
  app.pause();a=app.chat('SYNTHETIC_PROJECT',privacy='PROJECT',message_id='a')
  assert len(calls)==1 and a['render_state']=='PROVIDER_TOTAL_RESERVED_COST_BUDGET'
  row=app.runtime.store.all('cognitive_requests')[0]
  assert row['reserved_cost_micro']==100 and row['actual_cost_micro']==0 # registered loopback only
