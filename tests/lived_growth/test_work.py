from pathlib import Path
from nana_core.life.config import LifeConfig,write_config
from nana_core.life.application import LifeApplication
from nana_core.continuity.project_work.service import material_for
from nana_core.continuity.project_work.documents import outline,expected_outline
from nana_core.continuity.records import RecordService
from nana_core.presence.authority import VirtualClock

REPO=Path(__file__).resolve().parents[2]
SOURCES=('src/nana_core/continuity/recurrence.py','src/nana_core/continuity/extensions.py','docs/nana_h2_perception_ingress_v1_frontend_contract.md','docs/nana_h2_live_real_screen_v1_frontend_contract.md')
TRAIN=('src/nana_core/continuity/identity.py','src/nana_core/continuity/autonomy/requests.py','src/nana_core/continuity/subject/social.py')
DOCS=('README.md','docs/nana_provider_capability_routing_v1_frontend_contract.md','docs/bridge_node_rebuild.md')

def initialize(home,*,skills=True):
    config=LifeConfig(project_root=str(REPO),materials=tuple(material_for(REPO,p) for p in SOURCES),practice=material_for(REPO,TRAIN[0]),heldout=material_for(REPO,TRAIN[1]),transfer=material_for(REPO,TRAIN[2]),document_learning=tuple(material_for(REPO,p) for p in DOCS),max_autonomous_materials=4,allow_local_skills=skills,activity_interval_seconds=.5)
    write_config(home,config);return config

def advance(app,n=1):
    rows=[]
    for _ in range(n):app.clock.advance(250_000);rows.append(app.tick())
    return rows

def test_two_real_task_domains_failure_learning_generated_skill_unseen_use(tmp_path):
    home=tmp_path/'life';initialize(home)
    with LifeApplication(home,clock=VirtualClock(),bootstrap_grant=True) as app:
        rows=advance(app,240)
        goals=app.runtime.store.all('goals')
        assert len(goals)==4 and all(g['state']=='COMPLETED' for g in goals),[(g['template'],g['state']) for g in goals]
        assert len(list((home/'reports').glob('*.md')))==4
        assert {g['template'] for g in goals}=={'python-api','markdown-outline'}
        assert len(app.runtime.store.db.execute("SELECT * FROM experiences WHERE outcome='FAILURE'").fetchall())==2
        assert len(app.runtime.store.db.execute("SELECT * FROM strategy_assessments WHERE verdict='SUCCESS'").fetchall())==2
        actions=app.runtime.store.db.execute("SELECT * FROM actions WHERE capability='world.skill'").fetchall()
        assert len(actions)==1 and actions[0]['state']=='SUCCEEDED'
        rid=app.work.port.skill_bindings['MD_OUTLINE_2'];skill=RecordService(app.runtime.store).read(rid)['payload']
        assert skill['state']=='ACTIVE' and skill['installed'] is False
        assert all(x['passed'] for x in skill['tests']['cases'])
        assert app.runtime.store.db.execute("SELECT count(*) FROM cognitive_requests").fetchone()[0]==0
        assert not app.runtime.store.db.execute("SELECT 1 FROM subject_intentions WHERE state='PENDING' AND slot_key='concern-document-tool-reuse'").fetchone()
        assert app.status()['view']['living_self']['presence']!='FOCUSED'
        ident=app.runtime.identity_id;clock=app.clock;action_count=len(app.runtime.store.all('actions'));app.close()
        with LifeApplication(home,clock=clock) as other:
            assert other.runtime.identity_id==ident
            assert other.work.port.skill_bindings['MD_OUTLINE_2']==rid
            advance(other,16)
            assert len(other.runtime.store.all('actions'))==action_count
            assert len(other.runtime.store.db.execute("SELECT * FROM actions WHERE capability='world.skill'").fetchall())==1


def test_document_recipe_and_oracle_boundary():
    data={'filename':'x.md','sha256':'0'*64,'source':'# One\n```\n## Fake\n```\n## Two\n### Three\n####### Not heading\nplain'}
    assert outline('MD_OUTLINE_1',data)!=expected_outline(data)
    assert outline('MD_OUTLINE_3',data)==expected_outline(data)
