import hashlib,json,os,sqlite3
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.inspector import inspect
from tests.cloud_life.conftest import initialize


def files(home):
    # SQLite RO readers update transient SHM read marks; these are not Subject
    # events, DB/WAL pages or authority. Empty newly opened WAL is also transient.
    return {str(p.relative_to(home)):hashlib.sha256(p.read_bytes()).hexdigest() for p in home.rglob('*') if p.is_file() and not p.name.endswith('-shm') and not (p.name.endswith('-wal') and p.stat().st_size==0)}


def test_read_only_live_and_stopped_inspection_and_delete(tmp_path):
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        app.pause();reply=app.chat('PROJECT controlled message',topic='project',privacy='PROJECT')
        events=app.runtime.store.db.execute('SELECT count(*) FROM events').fetchone()[0]
        before=files(home)
        view=inspect(home,scope='project-work',entity_id='project-user')
        assert files(home)==before
        assert app.runtime.store.db.execute('SELECT count(*) FROM events').fetchone()[0]==events
        assert view.identity_id==app.runtime.identity_id and view.execution_authority is False
        assert view.sections['runtime'][0].state=='ACTIVE'
        assert 'PROJECT controlled message' not in view.model_dump_json()
        app.forget(reply['message_memory_id'])
        second=inspect(home,scope='project-work',entity_id='project-user')
        for items in second.sections.values():
            assert all(reply['message_memory_id'] not in x.source_memory_ids for x in items)
    before=files(home);inspect(home,scope='project-work',entity_id='project-user');assert before==files(home)


def test_inspector_fail_closed_policy_corruption_missing(tmp_path):
    missing=tmp_path/'missing'
    with pytest.raises((CoreError,OSError)):inspect(missing,scope='project-work',entity_id='project-user')
    assert not missing.exists()
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home):pass
    with pytest.raises(CoreError,match='INSPECTOR_POLICY_DENIED'):inspect(home,scope='project-work',entity_id='project-user',privacy=('SECRET',))
    anchor=home/'subject/self.db.privacy.json';anchor.write_text('{broken')
    with pytest.raises(CoreError):inspect(home,scope='project-work',entity_id='project-user')


def test_pending_privacy_journal_is_not_silently_repaired(tmp_path):
    from uuid import uuid4
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        message=app.chat('PROJECT synthetic',topic='project',privacy='PROJECT')['message_memory_id']
        anchor=app.runtime.store.privacy.path;body=json.loads(anchor.read_text())
        body['intents'].append({'intent_id':str(uuid4()),'memory_ids':[message],'evidence_ids':[],'created_at_us':app.clock.utc_now_us()})
        anchor.write_text(json.dumps(body))
        before=files(home)
        with pytest.raises(CoreError,match='INSPECTOR_PRIVACY_RECONCILIATION_REQUIRED'):inspect(home,scope='project-work',entity_id='project-user')
        assert before==files(home)


def test_surprise_text_and_secret_record_are_never_rendered(tmp_path):
    from nana_core.continuity.project_work.service import capture
    from nana_core.continuity.records import RecordService
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        r=app.runtime;mid=capture(r,'hardening.private-presence',{'note':'TEST_ONLY_NOT_SECRET'})
        with r.store.transaction('synthetic.inspector.privacy') as tx:
            rid=RecordService(r.store).create(tx,kind='INTENTION',scope='project-work',payload={'state':'PENDING','purpose':'UNFINISHED_SURPRISE_CONTENT_TEST_ONLY'},memories=(mid,))
            secret=RecordService(r.store).create(tx,kind='INTENTION',scope='project-work',payload={'state':'PENDING','purpose':'SECRET_RECORD_TEST_ONLY'},memories=(mid,),privacy_floor='SECRET')
        view=inspect(home,scope='project-work',entity_id='project-user');raw=view.model_dump_json()
        assert rid in raw and secret not in raw
        assert 'UNFINISHED_SURPRISE_CONTENT_TEST_ONLY' not in raw and 'SECRET_RECORD_TEST_ONLY' not in raw
        assert view.private_activity=='UNKNOWN_CONTENT_NOT_EXPOSED'
        app.forget(mid)
        after=inspect(home,scope='project-work',entity_id='project-user').model_dump_json()
        assert rid not in after and secret not in after
