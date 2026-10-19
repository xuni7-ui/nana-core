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
