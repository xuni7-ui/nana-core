import json
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.records import RecordService
from nana_core.continuity.open_agency.projections import project_open
from nana_core.continuity.open_agency.contracts import Objective,Operator
from nana_core.continuity.open_agency.code_skills import CodeSkillService
from .helpers import *
from .test_code_skills import skill_need

def test_secret_content_never_enters_core_even_with_fixture_grant_and_high_interest(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        o=Objective(objective_id='explore.secret',scope='lab',motivation_source='CURIOSITY',task_domain='media',desired=('seen',),operators=(Operator(operator_id='observe',capability='world.observe',resource='synthetic://private/fixture',produces=('seen',),args={}),))
        p=configure(r,tmp_path/'w'/'world.fixture.json',(o,));canary='SYNTHETIC_SECRET_CONTENT_MUST_NOT_ESCAPE'
        p.seed_observation(o.operators[0].resource,{'privacy_class':'SECRET','data':canary})
        mid=cue(r,o);send(r,'hard-privacy',(mid,));r.drain(8)
        assert not any(a['payload'] and canary.encode() in a['payload'] for a in r.store.all('artifacts'))
        assert not r.store.all('runtime_cognition_calls')
        assert all(a['state']!='SUCCEEDED' for a in r.store.all('actions'))
        assert not json.loads(p.path.read_text())['effects']

def test_deleted_support_removes_goal_from_all_tier_and_frontend_views(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        o=objective();p=configure(r,tmp_path/'w'/'world.fixture.json',(o,));p.seed_observation(o.operators[0].resource,[1.2,2.3])
        mid=cue(r,o);send(r,'visible',(mid,));r.step()
        policy=ContextPolicy(policy_id='test',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        assert len(project_open(r.store,policy,scopes=('lab',)).goals)==1
        MemoryService(r.store,r.authority).forget(mid,r.authority)
        assert not project_open(r.store,policy,scopes=('lab',)).goals
        from nana_core.continuity.surfaces import ContinuityViews
        for tier in ('L0_LIVE','L1_RECENT','L2_DURABLE'):
            assert not ContinuityViews(r.store,policy).project(tier,entity_id='synthetic-person',scopes=('lab',)).adopted_goal_ids

def test_observation_classification_propagates_into_kernel_payload_and_derived_results(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        o=objective();p=configure(r,tmp_path/'w'/'world.fixture.json',(o,))
        p.seed_observation(o.operators[0].resource,[1.2,2.3],privacy_class='PERSONAL')
        c=ConcernCue(cue_kind='OPEN_LOOP',motivation_source=o.motivation_source,topic_key='public-request',program_id=o.objective_id)
        mid=capture(r,'public-request',c.model_dump_json(),predicate='concern.public-request',privacy='PUBLIC')
        send(r,'taint',(mid,),privacy_class='PUBLIC');r.step();advance(r,5)
        assert r.store.all('goals')[0]['state']=='COMPLETED'
        records=RecordService(r.store)
        actions=r.store.all('actions');observe=actions[0]
        result_rid=json.loads(observe['result_json'])['action_payload_record']
        assert records.read(result_rid)['privacy_class']=='PERSONAL'
        second_args=json.loads(actions[1]['args_json'])['action_payload_record']
        assert records.read(second_args)['privacy_class']=='PERSONAL'
        outputs=r.work.agency._outputs(r.store.all('goals')[0]['goal_id'])
        observed=outputs[0]['memory_id'];assert MemoryService(r.store).read(observed)['privacy_class']=='PERSONAL'
        MemoryService(r.store,r.authority).forget(observed,r.authority)
        import pytest
        from nana_core.contracts import CoreError
        with pytest.raises(CoreError):records.read(second_args)
