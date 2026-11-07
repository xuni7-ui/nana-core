"""Original managed backup readback and actual file compaction, DEV only."""
from pathlib import Path
import json,sqlite3
from contextlib import closing
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.continuity.cold_history import ColdHistoryService
from .test_dream_recall import source


def test_managed_cold_readback_compacts_only_copy_keeps_source_and_original_withdrawal(app,tmp_path):
    mid=source(app,'cold-source','SYNTHETIC source at an old event time, no private history')
    service=ColdHistoryService(app.runtime.store,app.runtime.authority)
    source_events=list(app.runtime.store.db.execute('SELECT event_id,data_json FROM events ORDER BY seq'))
    result=service.create(tmp_path/'cold'/'history.sqlite',authority=app.runtime.authority)
    assert result['file_bytes']<result['initial_file_bytes'] and result['removed_rebuildable_indexes']
    assert not result['main_history_evicted']
    view=service.open(result['path'],scopes=('project-work',),privacy_classes=('PROJECT',),entity_ids=('project-user',))
    recalled=view.memory(mid)
    assert recalled['text'].startswith('SYNTHETIC source') and recalled['current_authority']=='LIVE_STORE'
    assert recalled['event_time_us']==11 and recalled['event_cutoff']==result['cutoff']
    assert list(app.runtime.store.db.execute('SELECT event_id,data_json FROM events ORDER BY seq'))==source_events
    with closing(sqlite3.connect(result['path'],isolation_level=None)) as db:
        assert db.execute("SELECT value_json FROM core_meta WHERE key='recovery_quarantine'").fetchone()[0]=='true'
        assert not db.execute('PRAGMA foreign_key_check').fetchone()
    app.forget(mid)
    with pytest.raises(CoreError,match='SOURCE_UNAVAILABLE'):view.memory(mid)
    with closing(sqlite3.connect(result['path'],isolation_level=None)) as db:
        assert db.execute('SELECT lifecycle FROM memories WHERE memory_id=?',(mid,)).fetchone()[0]=='DELETED'
        assert not db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'SYNTHETIC source at an old event time')>0").fetchone()
    with pytest.raises(CoreError,match='CHANGED_RECREATE'):service.open(result['path'],scopes=('project-work',),privacy_classes=('PROJECT',),entity_ids=('project-user',))


def test_cold_view_checks_current_scope_correction_and_tamper(app,tmp_path):
    mid=source(app,'cold-first','SYNTHETIC old fact',predicate_key='cold.fact')
    service=ColdHistoryService(app.runtime.store,app.runtime.authority)
    result=service.create(tmp_path/'archive'/'self.sqlite',authority=app.runtime.authority)
    kwargs=dict(scopes=('project-work',),privacy_classes=('PROJECT',),entity_ids=('project-user',))
    view=service.open(result['path'],**kwargs)
    denied=service.open(result['path'],scopes=('other',),privacy_classes=('PROJECT',),entity_ids=('project-user',))
    with pytest.raises(CoreError,match='SOURCE_UNAVAILABLE'):denied.memory(mid)
    source(app,'cold-new','SYNTHETIC corrected fact',predicate_key='cold.fact',correction_of=mid)
    with pytest.raises(CoreError,match='SOURCE_UNAVAILABLE'):view.memory(mid)
    path=Path(result['path'])
    with closing(sqlite3.connect(path,isolation_level=None)) as db:db.execute("UPDATE artifacts SET payload=? WHERE artifact_id=?",(b'SYNTHETIC tamper',app.runtime.store.one('memories',mid)['payload_artifact_id']))
    with pytest.raises(CoreError,match='CHANGED_RECREATE'):service.open(path,**kwargs)


def test_cold_creation_reuses_existing_owner_pause_and_authority(app,tmp_path):
    service=ColdHistoryService(app.runtime.store,app.runtime.authority)
    with pytest.raises(CoreError,match='UNAUTHENTICATED_OPERATOR'):
        service.create(tmp_path/'untrusted'/'self.sqlite',authority=OperatorAuthority())
    app.pause(False)
    with pytest.raises(CoreError,match='PAUSE_FIRST'):
        service.create(tmp_path/'running'/'self.sqlite',authority=app.runtime.authority)
    assert not (tmp_path/'running'/'self.sqlite').exists()


def test_same_original_subject_reopens_cold_history_after_restart(app,tmp_path):
    from nana_core.life.application import LifeApplication
    from nana_core.continuity import ContinuityStore
    from nana_core.continuity.memory import MemoryService
    mid=source(app,'cold-restart','SYNTHETIC remembered across a restart')
    authority=app.runtime.authority
    sealed=ColdHistoryService(app.runtime.store,authority).create(tmp_path/'cold'/'restart.sqlite',authority=authority)
    home=app.home;clock=app.clock;identity=app.runtime.identity_id;app.close()
    with LifeApplication(home,clock=clock) as current:
        current.pause();reader=ColdHistoryService(current.runtime.store,current.runtime.authority)
        view=reader.open(sealed['path'],scopes=('project-work',),privacy_classes=('PROJECT',),entity_ids=('project-user',))
        assert view.memory(mid)['text']=='SYNTHETIC remembered across a restart'
        assert current.runtime.identity_id==identity
    # Inspect a stopped, quarantined restore copy through the existing Store.
    # It recreates only the known indexes and never activates another Runtime.
    with ContinuityStore(sealed['path'],clock,schema_target=13) as restored:
        assert restored.identity['identity_id']==identity
        assert restored.one('core_meta','recovery_quarantine')['value_json']=='true'
        assert MemoryService(restored).read(mid)['text']=='SYNTHETIC remembered across a restart'
        assert not restored.db.execute('PRAGMA foreign_key_check').fetchone()
