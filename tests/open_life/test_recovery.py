import json,os,signal,subprocess,sys
from pathlib import Path
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.continuity.open_life.opportunities import OpportunityQueue
from nana_core.presence.authority import VirtualClock

def test_actual_sigkill_after_c_commit_before_attention_ack(tmp_path):
    child=subprocess.run([sys.executable,'-m','tests.open_life.crash_worker',str(tmp_path)],env={'PATH':os.defpath,'PYTHONPATH':str(Path.cwd())+':'+str(Path('src').resolve())},capture_output=True,timeout=15)
    assert child.returncode==-signal.SIGKILL,child.stderr.decode()[:1000]
    cut=json.loads((tmp_path/'cut.json').read_text())
    with open_runtime(tmp_path/'s.db',VirtualClock()) as r:
        q=OpportunityQueue(r);result=q.opportunity()
        assert result['state']=='C_JUDGED'
        assert r.identity_id==cut['identity_id']
        assert len(r.store.all('subject_cycles'))==cut['cycles']
        for _ in range(30):q.opportunity()
        assert len(r.store.all('subject_cycles'))==cut['cycles']
        assert not r.store.all('actions') and not r.store.all('cognitive_requests')
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()

import pytest
@pytest.mark.parametrize('cut',['before-schedule','after-gather'])
def test_automatic_research_actual_sigkill_before_schedule_or_after_gather(tmp_path,cut):
    from nana_core.life.config import LifeConfig,write_config
    from nana_core.life.application import LifeApplication
    from nana_core.continuity.project_work.service import material_for
    from nana_core.continuity.open_life.sources import IntakeSource
    from nana_core.presence.contracts import SECOND
    root=tmp_path/'owned';root.mkdir();clock=VirtualClock()
    for i,n in enumerate(('practice','heldout','transfer')):(root/(n+'.py')).write_text('def '+n+'():\n    return '+str(i)+'\n')
    (root/'feed.json').write_text(json.dumps({'world_claim':{'entity_id':'project-user','predicate':'source.status','value':'open','kind':'INTERPRETED','valid_from_us':clock.utc_now_us()}}))
    m=lambda n:material_for(root,n+'.py');home=tmp_path/'home'
    write_config(home,LifeConfig(project_root=str(root),materials=(m('practice'),),practice=m('practice'),heldout=m('heldout'),transfer=m('transfer'),max_autonomous_materials=0,advanced_life=True,world_sources=(IntakeSource(source_id='feed',channel='STRUCTURED_FEED',location='feed.json',semantic_format='SOURCED_CLAIM_JSON'),)))
    child=subprocess.run([sys.executable,'-m','tests.open_life.research_crash_worker',str(home),cut],env={'PATH':os.defpath,'PYTHONPATH':str(Path.cwd())+':'+str(Path('src').resolve())},capture_output=True,timeout=15)
    assert child.returncode==-signal.SIGKILL,child.stderr.decode()[:1000]
    mark=json.loads((home/'cut.json').read_text())
    with LifeApplication(home,clock=clock) as app:
        r=app.runtime
        for _ in range(30):clock.advance(SECOND);app.tick()
        jobs=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_RESEARCH'").fetchall()
        assert len(jobs)==1 and jobs[0]['state']=='DONE'
        assert r.identity_id==mark['identity_id']
        assert r.store.db.execute("SELECT count(*) FROM subject_events WHERE source_key LIKE 'development.life.%'").fetchone()[0]==1
        assert not r.store.all('actions') and not r.store.all('cognitive_requests')
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
