from .test_continuity import propose


def test_unfinished_topic_can_offer_original_c_once_without_delivery(app):
    propose(app,value='bounded project question',kind='UNFINISHED_TOPIC')
    app.presence('AVAILABLE')
    offered=app.shared.opportunity()
    assert offered and offered['not_delivery']
    for _ in range(4):app.tick()
    event=app.runtime.store.db.execute("SELECT * FROM subject_events WHERE source_key LIKE 'local.unfinished.%'").fetchone()
    assert event and event['origin']=='SELF_WAKE'
    app.clock.advance(6_000_000)
    assert app.shared.opportunity() is None
    assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_busy_and_declined_topic_prevent_spontaneous_candidate(app):
    propose(app,value='later question',kind='UNFINISHED_TOPIC')
    app.presence('BUSY')
    assert app.shared.opportunity() is None
    app.clock.advance(6_000_000);app.presence('AVAILABLE')
    app.chat('这个话题先不聊了',privacy='PROJECT',topic='daily')
    assert app.shared.opportunity() is None
