import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.open_agency.contracts import PlannerInput,PlanCandidate
from nana_core.continuity.open_agency.planning import BoundedPlanner,validate_plan
from nana_core.continuity.open_agency.world import LocalWorldRegistry
from .helpers import *

def test_multigoal_interleaves_independent_domains_and_preserves_restart(tmp_path):
    path=tmp_path/'s'/'self.db';clock=VirtualClock()
    a=objective();b=objective('fixture.words','UNICODE_WORDS',['alpha','beta'],task_domain='language',motivation_source='CREATIVE_INTEREST')
    with fresh(path,clock) as r:
        port=configure(r,tmp_path/'w'/'world.fixture.json',(a,b))
        port.seed_observation(a.operators[0].resource,[1.2,2.3]);port.seed_observation(b.operators[0].resource,'alpha\tbeta')
        ma,mb=cue(r,a),cue(r,b)
        send(r,'first',(ma,));r.step();send(r,'second',(mb,));r.drain(4)
        assert len(r.store.all('goals'))==2
        advance(r,2);identity=r.identity_id;config=r.config;epoch=r.lease.epoch
    with NanaRuntime(path,config,clock=clock) as r:
        assert r.identity_id==identity and r.lease.epoch>epoch and r.work.agency is None
        configure(r,tmp_path/'w'/'world.fixture.json',(a,b),grant=False)
        advance(r,12)
        assert {g['state'] for g in r.store.all('goals')}=={'COMPLETED'}
        actions=r.store.all('actions');assert len(actions)==6
        assert len({x['goal_id'] for x in actions[:2]})==2
        assert not r.subject.pending('lab')

def test_plan_proposals_do_not_invent_capability_or_satisfy_missing_conditions():
    obj=objective();request=PlannerInput(objective=obj,source_record_id='root',world_revision='version')
    planner=BoundedPlanner();plan=planner.plan(request)
    assert plan.operator_ids==('inspect','compute','publish')
    bad=PlanCandidate(operator_ids=('publish',),source_record_id='root',world_revision='version')
    with pytest.raises(CoreError,match='PRECONDITION'):validate_plan(request,bad,LocalWorldRegistry())
    with pytest.raises(CoreError,match='SOURCE_STALE'):validate_plan(request,plan.model_copy(update={'world_revision':'old'}),LocalWorldRegistry())
    changed=obj.model_copy(update={'operators':tuple(op.model_copy(update={'args':{**op.args,'input_from':'not-in-plan'}}) if op.operator_id=='compute' else op for op in obj.operators)})
    bad_request=request.model_copy(update={'objective':changed})
    with pytest.raises(CoreError,match='DATAFLOW'):validate_plan(bad_request,plan,LocalWorldRegistry())

def test_missing_grant_blocks_without_attempt_or_authority_from_adoption(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        o=objective();p=configure(r,tmp_path/'w'/'world.fixture.json',(o,),grant=False);p.seed_observation(o.operators[0].resource,[1,2])
        mid=cue(r,o);send(r,'adopt',(mid,));r.step();advance(r,2)
        assert r.store.all('goals')[0]['state']=='BLOCKED'
        assert not r.store.all('attempts') and not r.store.all('grants')

def test_subgoal_dependency_suspend_resume_and_completed_cause_dedup(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        parent=objective();port=configure(r,tmp_path/'w'/'world.fixture.json',(parent,))
        port.seed_observation(parent.operators[0].resource,[1.2,2.3]);mid=cue(r,parent)
        send(r,'parent',(mid,));r.step();g=r.store.all('goals')[0]
        cause=capture(r,'pause-review','A sourced synthetic pause and later continuation opportunity.')
        r.work.agency.transition(g['goal_id'],'SUSPENDED',expected_version=g['version'],authority=r.authority,cause_memory_id=cause)
        child=objective('fixture.child',parent_id=g['goal_id'],depends_on=(g['goal_id'],))
        r.work.agency.policy.objectives[child.objective_id]=child
        now=r.clock.utc_now_us();kernel=r.work.agency.realization.kernel
        kernel.grant(GrantSpec(capabilities=tuple(kernel.capabilities)+(kernel.verify_capability,),resources=tuple(op.resource for op in child.operators),not_before_us=now,expires_at_us=now+HOUR),r.authority)
        port.seed_observation(child.operators[0].resource,[1.2,2.3]);cmid=cue(r,child);send(r,'child',(cmid,));r.drain(8)
        assert len(r.store.all('goals'))==2 and not r.store.all('actions')
        suspended=r.store.one('goals',g['goal_id'])
        r.work.agency.transition(g['goal_id'],'ACTIVE',expected_version=suspended['version'],authority=r.authority,cause_memory_id=cause)
        advance(r,12);assert all(g['state']=='COMPLETED' for g in r.store.all('goals'))
        actions=r.store.all('actions');assert all(a['goal_id']==g['goal_id'] for a in actions[:3])
        send(r,'same-cause-after-complete',(mid,));r.drain(8)
        assert len(r.store.all('goals'))==2

def test_world_change_replans_same_goal_with_fresh_observations_not_old_outputs(tmp_path):
    from nana_core.continuity.agency_contracts import GoalReviewRef
    with fresh(tmp_path/'s'/'self.db') as r:
        obj=objective();port=configure(r,tmp_path/'w'/'world.fixture.json',(obj,));port.seed_observation(obj.operators[0].resource,[1,2])
        mid=cue(r,obj);send(r,'old-world',(mid,));r.step();advance(r,4)
        goal=r.store.all('goals')[0];assert goal['state']=='FAILED'
        oldplan=json.loads(goal['body_json'])['plan_record_id']
        port.seed_observation(obj.operators[0].resource,[1.2,2.3]);r.clock.source.advance(1)
        cause=capture(r,'world-changed','A new direct synthetic observation reports changed source values.')
        send(r,'new-world',(cause,),goal_review=GoalReviewRef(goal_id=goal['goal_id'],version=goal['version'],cause_memory_id=cause))
        r.step();advance(r,6)
        after=r.store.one('goals',goal['goal_id'])
        assert after['state']=='COMPLETED' and json.loads(after['body_json'])['plan_record_id']!=oldplan
        outputs=r.work.agency._outputs(goal['goal_id'])
        reads=[o for o in outputs if o['operator_id']=='inspect']
        assert json.loads(MemoryService(r.store).read(reads[-1]['memory_id'])['text'])['data']==[1.2,2.3]
        assert len(r.store.all('goals'))==1
