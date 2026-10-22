import json
from pathlib import Path
from nana_core.life.config import LifeConfig,write_config
from nana_core.life.application import LifeApplication
from nana_core.continuity.project_work.service import material_for
from nana_core.continuity.open_life.sources import IntakeSource
from nana_core.continuity.world_loop.world import WorldModel
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND

def test_configured_source_runs_in_original_idle_runtime_and_withdraws(tmp_path):
    root=tmp_path/'owned';root.mkdir();clock=VirtualClock()
    for i,n in enumerate(('practice','heldout','transfer')):(root/(n+'.py')).write_text('def '+n+'():\n    return '+str(i)+'\n')
    feed=root/'feed.json'
    def value(v):return {'world_claim':{'entity_id':'project-user','predicate':'source.status','value':v,'kind':'INTERPRETED','valid_from_us':clock.utc_now_us(),'confidence':.6}}
    initial=value('open');feed.write_text(json.dumps(initial))
    m=lambda n:material_for(root,n+'.py')
    config=LifeConfig(project_root=str(root),materials=(m('practice'),),practice=m('practice'),heldout=m('heldout'),transfer=m('transfer'),max_autonomous_materials=0,advanced_life=True,world_source_interval_seconds=30,world_sources=(IntakeSource(source_id='feed',channel='STRUCTURED_FEED',location='feed.json',semantic_format='SOURCED_CLAIM_JSON'),))
    home=tmp_path/'home';write_config(home,config)
    with LifeApplication(home,clock=clock) as app:
        for _ in range(10):clock.advance(SECOND);app.tick()
        r=app.runtime;world=WorldModel(r.store,scopes=('project-work',),privacy_classes=('PROJECT',))
        assert world.view('project-user','source.status').state=='SUPPORTED_BELIEF'
        original=app.advanced.intake.read('feed')
        assert any(c['behavior']=='EXPLORE' for c in app.advanced.queue.view())
        jobs=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_RESEARCH'").fetchall()
        assert jobs and all(j['state']=='DONE' for j in jobs)
        from nana_core.continuity.records import RecordService
        assert RecordService(r.store).read(jobs[0]['record_id'])['payload']['state']=='INSUFFICIENT_EVIDENCE'
        assert not r.store.all('experiences') and not r.store.all('lessons')
        feed.write_text(json.dumps(value('closed')))
        for _ in range(8):clock.advance(10*SECOND);app.tick()
        assert world.view('project-user','source.status').state=='CONFLICT'
        app.forget(original)
        assert world.view('project-user','source.status').state=='UNKNOWN'
        assert not r.store.all('actions') and not r.store.all('cognitive_requests')
        assert app.board()['advanced_life']['world_source_health']
        count=r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_RESEARCH'").fetchone()[0]
    with LifeApplication(home,clock=clock) as reopened:
        for _ in range(5):clock.advance(SECOND);reopened.tick()
        assert reopened.runtime.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_RESEARCH'").fetchone()[0]==count
        assert not reopened.runtime.store.all('actions') and not reopened.runtime.store.all('cognitive_requests')
