import json
from pathlib import Path
import pytest
from nana_core.contracts import CoreError, Invocation
from nana_core.storage import digest
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.project_work.service import ProjectWork,open_project_runtime,material_for,learning_spec
from nana_core.continuity.project_work.port import ProjectMaterialPort,read_material
from nana_core.continuity.project_work.analysis import inventory
from nana_core.continuity.project_work.oracle import expected_inventory
from nana_core.continuity.records import RecordService

REPO=Path(__file__).resolve().parents[2]
PATHS=('src/nana_core/continuity/recurrence.py','src/nana_core/continuity/extensions.py')
TRAINING=('src/nana_core/continuity/identity.py','src/nana_core/continuity/autonomy/requests.py','src/nana_core/continuity/subject/social.py')

def setup(r,tmp_path):
    materials=tuple(material_for(REPO,p) for p in PATHS)
    spec=learning_spec(*(read_material(REPO,material_for(REPO,p)) for p in TRAINING))
    return ProjectWork(r,REPO,materials,tmp_path/'reports',spec,grant=True),materials


def test_real_two_source_use_original_learning_kernel_and_reopen(tmp_path):
    clock=VirtualClock()
    with open_project_runtime(tmp_path/'subject/state.db',clock) as r:
        work,materials=setup(r,tmp_path);identity=r.identity_id
        root=work.request(materials[0].material_id)
        work.run_until(lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE'").fetchone()))
        failure=r.store.db.execute("SELECT * FROM experiences WHERE outcome='FAILURE'").fetchone()
        work.reflect_failure(failure['experience_id'])
        work.run_until(lambda:bool(r.work.open_learning.strategy('python-api','project-work')))
        work.run_until(lambda:len(list(work.port.output.glob('*.md')))==1)
        work.request(materials[1].material_id)
        work.run_until(lambda:len(list(work.port.output.glob('*.md')))==2)
        results=[json.loads(p.read_text()) for p in work.port.output.glob('*.json')]
        assert {x['source_path'] for x in results}==set(PATHS)
        for row in results:
            material=next(m for m in materials if m.relative_path==row['source_path'])
            assert row['data']==expected_inventory(read_material(REPO,material))
        assert r.store.one('experiences',failure['experience_id'])['outcome']=='FAILURE'
        body=RecordService(r.store).read(r.store.db.execute("SELECT record_id FROM jobs WHERE work_kind='LEARNING'").fetchone()[0])['payload']
        assert body['results']['BASELINE']['passed']<body['results']['EVALUATE']['passed']
        assert body['results']['TRANSFER']['all_passed']
        before=len(r.store.all('actions'));assert all(a['state']=='SUCCEEDED' for a in r.store.all('actions'))
        assert r.store.db.execute('PRAGMA foreign_key_check').fetchall()==[]
    with open_project_runtime(tmp_path/'subject/state.db',clock) as r:
        ProjectWork(r,REPO,materials,tmp_path/'reports',grant=False)
        assert r.identity_id==identity and len(r.store.all('actions'))==before
        assert not r.store.db.execute("SELECT 1 FROM runtime_queue WHERE state='PROCESSING'").fetchone()


def test_manifest_blocks_traversal_symlinks_and_changed_source(tmp_path):
    (tmp_path/'safe.py').write_text('def work():\n    pass\n')
    material=material_for(tmp_path,'safe.py')
    (tmp_path/'safe.py').write_text('def changed():\n    pass\n')
    with pytest.raises(CoreError,match='PROJECT_SOURCE_CHANGED'):read_material(tmp_path,material)
    (tmp_path/'alias.py').symlink_to(tmp_path/'safe.py')
    with pytest.raises(CoreError):material_for(tmp_path,'alias.py')
    with pytest.raises(CoreError):material_for(tmp_path,'../outside.py')
    with pytest.raises(CoreError):material_for(tmp_path,'/etc/passwd')


def test_candidate_oracle_disagree_on_real_missing_class_methods():
    data=read_material(REPO,material_for(REPO,PATHS[0]))
    assert inventory('PYTHON_TOP_DEFS',data)!=expected_inventory(data)
    assert inventory('PYTHON_AST_API',data)==expected_inventory(data)


def test_no_grant_and_unsupported_port_do_not_gain_authority(tmp_path):
    from nana_core.continuity.autonomy.realization import GovernedRealization
    with open_project_runtime(tmp_path/'subject/state.db',VirtualClock()) as r:
        materials=(material_for(REPO,PATHS[0]),)
        work=ProjectWork(r,REPO,materials,tmp_path/'reports',grant=False)
        work.request(materials[0].material_id)
        work.run_until(lambda:bool(r.store.all('actions')))
        work.run_until(lambda:r.store.all('actions')[0]['state']=='BLOCKED')
        assert not work.artifacts()
        class Pretend:identity_id=r.identity_id
        with pytest.raises(CoreError,match='OFFLINE_REALIZATION_ONLY'):GovernedRealization(r.store,Pretend(),r.authority)


def test_verified_navigation_needs_learned_inventory_and_current_source(tmp_path):
    from nana_core.continuity.memory import MemoryService
    with open_project_runtime(tmp_path/'subject/state.db',VirtualClock()) as r:
        work,materials=setup(r,tmp_path)
        root=work.request(materials[0].material_id)
        work.run_until(lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE'").fetchone()))
        with pytest.raises(CoreError,match='PROJECT_SYMBOL_NOT'):work.lookup(materials[0].material_id,'RecurrenceSpec.next_after')
        exp=r.store.db.execute("SELECT experience_id FROM experiences WHERE outcome='FAILURE'").fetchone()[0]
        work.reflect_failure(exp);work.run_until(lambda:len(list(work.port.output.glob('*.md')))==1)
        result=work.lookup(materials[0].material_id,'RecurrenceSpec.next_after')
        assert result['line']==43 and 'def next_after' in result['excerpt']
        MemoryService(r.store,r.authority).forget(root,r.authority)
        with pytest.raises(CoreError,match='PROJECT_SYMBOL_NOT'):work.lookup(materials[0].material_id,'RecurrenceSpec.next_after')


def test_actual_work_life_causality_and_independent_withdrawal_arm(tmp_path):
    from tools.nana_real_life.qualification import run
    normal=run(tmp_path/'retirement',REPO)
    erased=run(tmp_path/'withdrawal',REPO,withdraw=True)
    assert normal['quality']==erased['quality']
    assert normal['future_share']=='REPORT_DISCOVERY' and normal['busy']=='NO_ACTION' and normal['no_interest']=='NO_ACTION'
    assert normal['strategy_retirement'] and not normal['source_withdrawal']
    assert erased['source_withdrawal'] and not erased['strategy_retirement']
    assert normal['restart_identity_stable'] and erased['no_resurrection_after_restart']


def test_actual_failure_offered_as_concern_can_choose_rest_instead_of_learning(tmp_path):
    from nana_core.continuity.project_work.service import capture,post
    from nana_core.continuity.subject.opportunities import ConcernCue
    with open_project_runtime(tmp_path/'subject/state.db',VirtualClock()) as r:
        work,materials=setup(r,tmp_path);work.request(materials[0].material_id)
        work.run_until(lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE'").fetchone()))
        failure=r.store.db.execute("SELECT * FROM experiences WHERE outcome='FAILURE'").fetchone()
        # High-load context is an explicit hypothetical control, not claimed to
        # be actual fatigue or a user relationship observation.
        cue=ConcernCue(cue_kind='LOAD_STATE',topic_key='project-load',motivation_source='CAPABILITY_GAP',program_id='learn.python-api',possible_behaviors=('LEARN','REST'),cognitive_load='HIGH')
        mid=capture(r,'hypothetical-load-control',cue.model_dump(mode='json'),kind='MODEL_DERIVATION',parents=(failure['result_memory_id'],),predicate='concern.project-load')
        post(r,'rest-control',(mid,));result=r.step()['cycle']
        assert result.intention.behavior=='REST' and not result.goal_candidate_id
        assert not r.store.db.execute("SELECT 1 FROM jobs WHERE work_kind='LEARNING'").fetchone()
