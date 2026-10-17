import json
from nana_core.contracts import GrantSpec,CoreError
from nana_core.storage import canonical,digest
from nana_core.continuity.open_agency.service import OpenGoalPolicy
from nana_core.continuity.autonomy.fixture_effects import OfflineEffectPort
from nana_core.continuity.autonomy.governance import GovernanceController
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.extension import SelfExtensionWork
from nana_core.continuity.memory import MemoryService
from .helpers import *

def configure(r,tmp_path,transport,resources):
    p=OfflineEffectPort(r.identity_id,tmp_path/'world'/'state.fixture.json')
    GovernanceController(r.store,r.authority).initialize(r.authority)
    r.work.configure_open_agency(OpenGoalPolicy((),dynamic_resources=resources),p)
    r.work.configure_world(transport,policy(),resources=resources,skill_development=SelfExtensionWork(r))
    kernel=r.work.agency.realization.kernel;now=r.clock.utc_now_us()
    kernel.grant(GrantSpec(capabilities=tuple(kernel.capabilities)+(kernel.verify_capability,),resources=resources,not_before_us=now,expires_at_us=now+48*HOUR),r.authority)
    kernel.set_budgets({'write_attempts':100,'external_requests':500,'cost_micro_units':500},r.authority)
    p.code_skills=r.work.world.skills.codes
    return p

def test_dynamic_sourced_goals_and_two_self_detected_skill_kinds(tmp_path):
    resources=tuple('synthetic://'+name+suffix for name in ('numbers','words','arrange') for suffix in ('','/compute','/report'))
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness() as (transport,metrics):
        p=configure(r,tmp_path,transport,resources)
        from nana_core.continuity.world_loop.ports import CognitionPlannerPort
        r.work.agency.policy.planner=CognitionPlannerPort(r.work.world.cognition)
        for name,method,data,expected in [('numbers','NUMERIC_SUM',[1.5,2],3.5),('words','CASEFOLD','HELLO','hello'),('arrange','SORT',[3,1,2],[1,2,3])]:
            resource='synthetic://'+name;p.seed_observation(resource,data)
            mid=capture(r,name,{'opportunities':[{'topic':name,'resource':resource,'method':method,'expected':expected,'value':'HIGH','domain':name,'motive':'CREATIVE_INTEREST'}]})
            r.work.world.observe(mid)
        for _ in range(120):r.clock.source.advance(SECOND);r.step()
        assert len(r.store.all('goals'))==3
        assert all(g['state']=='COMPLETED' for g in r.store.all('goals'))
        assert r.work.agency.policy.objectives and metrics['calls']>=1
        for task in ('TEXT_CLEAN','TOKEN_ANALYSIS'):
            mid=capture(r,task,{'opportunities':[{'topic':task.lower().replace('_','-'),'value':'HIGH','skill_task':task}]});r.work.world.observe(mid)
        for _ in range(100):r.clock.source.advance(SECOND);r.step()
        active=dict(r.work.world.skills.active());assert set(active)=={'TEXT_CLEAN','TOKEN_ANALYSIS'}
        for task,rid in active.items():
            service=r.work.world.skills.codes;body=service.require_current(rid)
            assert body['spec']['revision']==2 and body['tests']['isolation']=='BWRAP_NAMESPACES_READONLY_NO_NETWORK'
        assert len([x for x in r.store.all('continuity_records') if x['record_kind']=='CODE_SKILL'])>=8
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()

def test_source_backed_world_revision_replans_without_reusing_old_observation(tmp_path):
    from nana_core.continuity.world_loop.world import SourcedClaim
    resources=('synthetic://numbers','synthetic://numbers/compute','synthetic://numbers/report')
    with fresh(tmp_path/'s'/'self.db') as r,provider_harness() as (transport,metrics):
        p=configure(r,tmp_path,transport,resources);p.seed_observation(resources[0],[1.5,2])
        mid=capture(r,'start',{'opportunities':[{'topic':'numbers','resource':resources[0],'method':'NUMERIC_SUM','expected':3.5,'value':'HIGH','domain':'numbers','motive':'CURIOSITY'}]});r.work.world.observe(mid)
        for _ in range(24):
            r.clock.source.advance(SECOND);r.step()
            job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='GOAL'").fetchone()
            if job and job['cursor']==1:break
        assert job and job['cursor']==1;oldplan=job['record_id'];goal=r.store.all('goals')[0]
        r.clock.source.advance(SECOND);p.seed_observation(resources[0],[1,2.5])
        fact=capture(r,'world-change',{'world_claim':SourcedClaim(entity_id='device',predicate='input.revision',value='new observed values',kind='RAW_OBSERVATION',valid_from_us=r.clock.utc_now_us(),related_resources=(resources[0],)).model_dump(mode='json')});r.work.world.observe(fact)
        for _ in range(50):r.clock.source.advance(SECOND);r.step()
        goal=r.store.one('goals',goal['goal_id']);assert goal['state']=='COMPLETED'
        current=json.loads(goal['body_json'])['plan_record_id'];assert current!=oldplan
        outputs=r.work.agency._outputs(goal['goal_id']);observations=[o for o in outputs if o.get('plan_record_id')==current and o['operator_id']=='inspect']
        assert observations and json.loads(MemoryService(r.store).read(observations[0]['memory_id'])['text'])['data']==[1,2.5]
