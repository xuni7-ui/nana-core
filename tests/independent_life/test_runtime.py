from nana_core.life.application import LifeApplication
from nana_core.continuity.memory import MemoryService
from .conftest import advance


def test_no_input_real_work_learning_and_later_reuse_happen_in_single_runtime(app):
    rows=advance(app,100)
    assert len(list((app.home/'reports').glob('*.md')))==2
    assert all(g['state']=='COMPLETED' for g in app.runtime.store.all('goals'))
    assert app.runtime.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE'").fetchone()
    assert app.runtime.store.db.execute("SELECT state FROM lessons").fetchone()[0]=='ACTIVE'
    assert app.runtime.store.db.execute("SELECT verdict FROM strategy_assessments").fetchone()[0]=='SUCCESS'
    assert app.runtime.store.db.execute("SELECT count(*) FROM cognitive_requests").fetchone()[0]==0
    assert any(x and x.get('cycle') and x['cycle'].intention.self_generated for x in rows)
    assert app.status()['view']['resources']['calls']==0


def test_pause_reactive_preemption_restart_and_no_regrant(app):
    advance(app,2);before=app.runtime.store.all('jobs');app.pause()
    advance(app,10);assert before==app.runtime.store.all('jobs')
    response=app.chat('今天只是吐槽一下。',message_id='one')
    assert response['mode']=='VENT' and response['intention']=='SOCIAL_INTERACTION'
    assert before==app.runtime.store.all('jobs')
    ident=app.runtime.identity_id;count=len(app.runtime.store.all('grants'));home=app.home;clock=app.clock
    app.close()
    with LifeApplication(home,clock=clock) as reopened:
        assert reopened.runtime.identity_id==ident and reopened.runtime.work.paused
        assert len(reopened.runtime.store.all('grants'))==count
        assert reopened.chat('今天只是吐槽一下。',message_id='one')['state']=='ALREADY_REVIEWED_NO_REPLAY'
        reopened.pause(False);advance(reopened,100)
        assert len(list((home/'reports').glob('*.md')))==2


def test_source_deletion_and_revocation_fence_future_work(app):
    advance(app,100)
    root=app.runtime.store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_reference LIKE 'input:%' ORDER BY e.rowid LIMIT 1").fetchone()[0]
    assert app.work.assess_later_use() is None # already independently assessed once
    MemoryService(app.runtime.store,app.runtime.authority).forget(root,app.runtime.authority)
    from nana_core.continuity.subject.growth_life import opportunities
    assert not opportunities(app.runtime.store,scope='project-work',privacy_classes=('PROJECT',))
    app.revoke();before=len(app.runtime.store.all('actions'));advance(app,20)
    assert len(app.runtime.store.all('actions'))==before


def test_no_privacy_raw_body_capture_and_topic_refusal(app):
    app.pause();first=app.chat('这个话题不要研究 LOCAL_CANARY_UNSTORED',topic='closed')
    assert first['mode']=='RESPECT_BOUNDARY'
    follow=app.chat('请帮我看看这个',topic='closed');assert follow['mode']=='RESPECT_BOUNDARY'
    assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'LOCAL_CANARY_UNSTORED')>0").fetchone()
    MemoryService(app.runtime.store,app.runtime.authority).forget(first['message_memory_id'],app.runtime.authority)
    assert app.chat('请帮我看看这个',topic='closed')['mode']=='HELP'
