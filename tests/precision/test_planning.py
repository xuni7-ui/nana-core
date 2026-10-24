import json
import pytest
from pydantic import ValidationError
from nana_core.contracts import CoreError
from nana_core.storage import digest
from nana_core.continuity.open_agency.contracts import Objective, Operator, TaskGroup, PlannerInput, PlanCandidate, InputStateGuard
from nana_core.continuity.open_agency.planning import BoundedPlanner, validate_plan
from nana_core.continuity.open_agency.world import LocalWorldRegistry
from nana_core.continuity.agency_contracts import GoalReviewRef
from tests.open_autonomy.helpers import fresh, configure, cue, send, advance, capture, objective


def request(obj):
    return PlannerInput(objective=obj,source_record_id='source',world_revision=digest(obj.model_dump(mode='json')))


def test_dataflow_producer_and_irrelevant_permutations_are_not_fact_equivalent():
    obj=objective()
    op=Operator(operator_id='cheap',capability='world.observe',resource='synthetic://decoy',produces=('observed',),args={},cost=1)
    obj=obj.model_copy(update={'operators':(op,*tuple(x.model_copy(update={'cost':3}) if x.operator_id=='inspect' else x for x in obj.operators))})
    proposal=BoundedPlanner().plan(request(obj))
    assert proposal.operator_ids==('inspect','compute','publish')
    assert validate_plan(request(obj),proposal,LocalWorldRegistry())


def test_hierarchical_37_steps_original_c_kernel_and_same_owner_restart(tmp_path):
    ops=[];groups=[];ends=[]
    for i in range(12):
        key='b'+str(i)+'.';prior=objective('precision.branch'+str(i),expected=2*i+.75)
        for op in prior.operators:
            args=dict(op.args)
            if args.get('input_from'):args['input_from']=key+args['input_from']
            ops.append(op.model_copy(update={'operator_id':key+op.operator_id,'requires':tuple(key+x for x in op.requires),'produces':tuple(key+x for x in op.produces),'args':args}))
        groups.append(TaskGroup(group_id='group.b'+str(i),members=tuple(key+x for x in ('inspect','compute','publish'))))
        ends.append(key+'published')
    ops.append(Operator(operator_id='finish',capability='world.compute',resource='synthetic://finish',requires=tuple(ends),produces=('done',),args={'method':'IDENTITY','data':'complete'},expected_digest=digest('complete')))
    groups.append(TaskGroup(group_id='group.root',members=tuple(g.group_id for g in groups)))
    obj=Objective(objective_id='precision.long',scope='lab',motivation_source='PROJECT_COMPLETION',task_domain='numbers',operators=tuple(ops),task_groups=tuple(groups),desired=('done',),max_steps=37,horizon='ONGOING')
    path=tmp_path/'state'/'self.db';world=tmp_path/'world'/'long.fixture.json'
    with fresh(path) as r:
        port=configure(r,world,(obj,))
        for i in range(12):port.seed_observation('synthetic://input/precision.branch'+str(i),[i+.25,i+.5])
        mid=cue(r,obj);send(r,'long',(mid,));r.step();advance(r,17)
        identity=r.identity_id;config=r.config;clock=r.clock.source
        goal=r.store.all('goals')[0];gid=goal['goal_id'];assert goal['state']=='ACTIVE'
        old_count=len(r.store.all('actions'));assert 0<old_count<37
    from nana_core.presence import NanaRuntime
    with NanaRuntime(path,config,clock=clock) as r:
        configure(r,world,(obj,),grant=False)
        advance(r,45)
        assert r.identity_id==identity and r.store.one('goals',gid)['state']=='COMPLETED'
        assert len(r.store.all('actions'))==37
        assert len({a['effect_slot'] for a in r.store.all('actions')})==37
        for i in range(12):
            actual=port._load()['resources']['synthetic://output/precision.branch'+str(i)]['data']
            assert actual==2*i+.75
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()


def test_group_barriers_cycle_and_duplicated_members_fail_closed():
    obj=objective()
    group=TaskGroup(group_id='group.all',members=('inspect','compute','publish'))
    with pytest.raises(ValidationError):
        Objective.model_validate_json(obj.model_copy(update={'task_groups':(group,TaskGroup(group_id='group.loop',members=('group.all',),depends_on=('group.all',)) ,TaskGroup(group_id='group.other',members=('inspect',)))}).model_dump_json())
    cyc=(TaskGroup(group_id='group.a',members=('inspect',),depends_on=('group.b',)),TaskGroup(group_id='group.b',members=('compute','publish'),depends_on=('group.a',)))
    with pytest.raises(ValidationError):Objective.model_validate_json(obj.model_copy(update={'task_groups':cyc}).model_dump_json())
    # Dependencies also apply to operators which do not require the same facts.
    lone=Operator(operator_id='audit',capability='world.observe',resource='synthetic://audit',produces=('audited',),args={})
    obj=obj.model_copy(update={'operators':(*obj.operators,lone),'task_groups':(group,TaskGroup(group_id='group.audit',members=('audit',),depends_on=('group.all',))),'desired':('audited',)})
    proposal=BoundedPlanner().plan(request(obj))
    assert proposal.operator_ids[-1]=='audit' and len(proposal.operator_ids)==4
    with pytest.raises(CoreError,match='TASK_DEPENDENCY'):
        validate_plan(request(obj),PlanCandidate(operator_ids=('audit',),source_record_id='source',world_revision=request(obj).world_revision),LocalWorldRegistry())


def test_input_guard_stales_before_write_and_fresh_c_replan_reobserves(tmp_path):
    obj=objective()
    obj=obj.model_copy(update={'operators':tuple(op.model_copy(update={'input_guard':InputStateGuard(observation_operator_id='inspect',max_age_us=4_000_000)}) if op.operator_id=='publish' else op for op in obj.operators)})
    with fresh(tmp_path/'s'/'self.db') as r:
        port=configure(r,tmp_path/'w'/'state.fixture.json',(obj,));port.seed_observation(obj.operators[0].resource,[1.2,2.3])
        send(r,'guarded',(cue(r,obj),));r.step();advance(r,2)
        assert len(r.store.all('actions'))==2
        r.clock.source.advance(4_000_000);r.step()
        goal=r.store.all('goals')[0];assert goal['state']=='BLOCKED'
        assert len(r.store.all('actions'))==2 and not port._load().get('resources',{}).get(obj.operators[-1].resource)
        last=json.loads(r.store.db.execute("SELECT data_json FROM events WHERE kind='living.goal_parked' ORDER BY seq DESC LIMIT 1").fetchone()[0])['data']
        assert last['reason']=='STATE_DEPENDENCY_STALE'
        old_pending=r.store.db.execute("SELECT * FROM subject_intentions WHERE state='PENDING' AND kind='ACTION_PROPOSAL'").fetchone()
        old_cycle=r.store.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=?',(old_pending['subject_event_id'],)).fetchone()
        assert old_cycle['judgment']=='AGREE'
        cause=capture(r,'refresh','A fresh sourced observation warrants rechecking the finite project.')
        send(r,'new-state',(cause,),goal_review=GoalReviewRef(goal_id=goal['goal_id'],version=goal['version'],cause_memory_id=cause));r.step();advance(r,4)
        assert r.store.one('goals',goal['goal_id'])['state']=='COMPLETED'
        assert sum(a['capability']=='world.publish' for a in r.store.all('actions'))==1
        assert len(r.store.all('goals'))==1
        assert r.store.one('subject_intentions',old_pending['intention_id'])['state']=='DEFERRED'
        assert r.store.one('subject_cycles',old_cycle['cycle_id'])['judgment']=='AGREE'


def test_replan_cannot_duplicate_verified_effect_before_progress_commit(tmp_path,monkeypatch):
    with fresh(tmp_path/'s'/'self.db') as r:
        obj=objective();port=configure(r,tmp_path/'w'/'effect.fixture.json',(obj,));port.seed_observation(obj.operators[0].resource,[1.2,2.3])
        send(r,'before-cut',(cue(r,obj),));r.step();advance(r,2)
        memory=r.work.agency.records.memory
        def stop(_):raise RuntimeError('CONTROLLED_AFTER_VERIFY_BEFORE_PROGRESS')
        with monkeypatch.context() as patch:
            patch.setattr(memory,'capture',stop)
            with pytest.raises(RuntimeError,match='CONTROLLED_AFTER_VERIFY'):advance(r,1)
        goal=r.store.all('goals')[0]
        assert len(r.store.all('actions'))==3 and all(a['state']=='SUCCEEDED' for a in r.store.all('actions'))
        cause=capture(r,'fresh-but-no-retry','An independent fresh reconsideration source is available.')
        with pytest.raises(CoreError,match='RECONCILE_COMPLETED_EFFECT_FIRST'):
            r.work.agency.revise(goal['goal_id'],expected_version=goal['version'],cause_memory_id=cause,authority=r.authority)
        # Original committed C decision reconciles the same already-done effect.
        raw=r.store.all('subject_cycles')[-1];cycle=r.subject.result(raw)
        from nana_core.continuity.records import RecordService
        event=r.store.one('subject_events',cycle.event_id)
        ref=RecordService(r.store).read(event['record_id'])['payload']['input']['goal_step']
        from nana_core.continuity.agency_contracts import GoalStepRef
        r.work.agency.advance(GoalStepRef(**ref),cycle)
        assert r.store.one('goals',goal['goal_id'])['state']=='COMPLETED'
        assert len(r.store.all('actions'))==3 and len(port._load()['effects'])==3


def test_revision_guard_does_not_convert_wrong_observation_to_permission(tmp_path):
    obj=objective();guard=InputStateGuard(observation_operator_id='inspect',max_age_us=60_000_000,expected_revision=digest('different'))
    obj=obj.model_copy(update={'operators':tuple(op.model_copy(update={'input_guard':guard}) if op.operator_id=='publish' else op for op in obj.operators)})
    with fresh(tmp_path/'self.db') as r:
        port=configure(r,tmp_path/'w'/'revision.fixture.json',(obj,));port.seed_observation(obj.operators[0].resource,[1.2,2.3])
        send(r,'mismatch',(cue(r,obj),));r.step();advance(r,5)
        assert r.store.all('goals')[0]['state']=='BLOCKED'
        assert not any(a['capability']=='world.publish' for a in r.store.all('actions'))


def test_legacy_wire_and_bounds_no_group_injection():
    obj=objective();assert 'task_groups' not in obj.model_dump(mode='json')
    assert all('input_guard' not in op for op in obj.model_dump(mode='json')['operators'])
    from nana_core.continuity.agency_contracts import GoalStepRef
    assert GoalStepRef(work_id='job',revision=1,cursor=127).cursor==127
    with pytest.raises(ValidationError):GoalStepRef(work_id='job',revision=1,cursor=129)
