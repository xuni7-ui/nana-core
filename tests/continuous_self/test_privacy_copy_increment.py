"""Original journal authority and backup erasure, with bounded repeated SQL work."""
import fcntl
import sqlite3
from pathlib import Path

import pytest

from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.privacy import _atomic


@pytest.fixture
def copies(tmp_path):
    authority=OperatorAuthority()
    with ContinuityStore(tmp_path/'source.db',schema_target=13) as store:
        memory=MemoryService(store,authority);memory.entity('synthetic-peer','PERSON');ids=[]
        for index in range(16):
            text='SYNTHETIC_PRIVATE_ERASURE_'+str(index)
            eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.copy-erasure',
                source_reference='item-'+str(index),source_kind='USER_STATEMENT'),text=text,privacy_class='PERSONAL',observed_time_us=store.clock.utc_now_us()))
            ids.append(memory.add(MemoryCandidate(entity_id='synthetic-peer',scope='synthetic-home',memory_type=MemoryType.EPISODIC,
                epistemic_kind='STATEMENT',source_evidence_id=eid,text=text)))
        paths=[tmp_path/('copy-'+str(i)+'.db') for i in range(3)]
        for path in paths:store.backup(path)
        yield store,memory,authority,ids,paths


def erased(path,mid):
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT m.lifecycle,a.payload FROM memories m JOIN artifacts a ON a.artifact_id=m.payload_artifact_id WHERE m.memory_id=?',(mid,)).fetchone()
        assert row==('DELETED',None)


def test_new_withdrawal_does_not_rescan_old_intents_in_unchanged_copies(copies,monkeypatch):
    store,memory,authority,ids,paths=copies
    for mid in ids[:12]:assert memory.forget(mid,authority)['state']=='COMPLETE'
    scans=[];original=sqlite3.connect;names={str(p) for p in paths}
    def observed(database,*args,**kwargs):
        db=original(database,*args,**kwargs)
        if str(database) in names:
            db.set_trace_callback(lambda sql:scans.append(str(database)) if sql=='SELECT * FROM memories' else None)
        return db
    monkeypatch.setattr(sqlite3,'connect',observed)
    assert memory.forget(ids[12],authority)['state']=='COMPLETE'
    assert len(scans)==len(paths)
    for path in paths:
        erased(path,ids[0]);erased(path,ids[12])
    # Busy original writer lock keeps the new deletion pending, never COMPLETE.
    with open(str(paths[0])+'.lock','a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert memory.forget(ids[13],authority)['state']=='PENDING_BACKUP_PURGE'
        fcntl.flock(lock,fcntl.LOCK_UN)
    assert not store.privacy.sanitize_backups()
    for path in paths:erased(path,ids[13])


def test_stale_in_place_backup_replacement_reapplies_the_original_journal(copies):
    store,memory,authority,ids,paths=copies
    stale=paths[0].read_bytes();inode=paths[0].stat().st_ino
    for mid in ids[:3]:assert memory.forget(mid,authority)['state']=='COMPLETE'
    paths[0].write_bytes(stale)  # explicitly owned inactive quarantine, not source DB
    assert paths[0].stat().st_ino==inode
    assert not store.privacy.sanitize_backups()
    for path in paths:
        for mid in ids[:3]:erased(path,mid)


def test_changed_intent_body_cannot_reuse_a_same_length_backup_cursor(copies):
    store,memory,authority,ids,paths=copies
    assert memory.forget(ids[0],authority)['state']=='COMPLETE'
    body=store.privacy.read();target=store.one('memories',ids[1]);entry=body['intents'][0]
    entry['memory_ids'].append(ids[1]);entry['evidence_ids'].append(target['source_evidence_id'])
    # Simulate a valid atomic external anchor change with the same intent count.
    # The original journal is authority; a lookup cache cannot bless its old body.
    _atomic(store.privacy.path,body);store.ensure_privacy_current()
    assert not store.privacy.sanitize_backups()
    for path in paths:
        erased(path,ids[0]);erased(path,ids[1])


def test_wal_only_backup_write_invalidates_progress_without_main_file_change(copies):
    from nana_core.storage import digest
    store,memory,authority,ids,paths=copies
    path=paths[0]
    with sqlite3.connect(path,isolation_level=None) as setup:setup.execute('PRAGMA journal_mode=WAL')
    assert memory.forget(ids[0],authority)['state']=='COMPLETE'
    before=path.stat();artifact=store.one('memories',ids[0])['payload_artifact_id']
    external=sqlite3.connect(path,isolation_level=None)
    try:
        external.execute('PRAGMA wal_autocheckpoint=0')
        external.execute("UPDATE memories SET lifecycle='ACTIVE',assessment='CURRENT' WHERE memory_id=?",(ids[0],))
        text=b'SYNTHETIC_PRIVATE_ERASURE_0'
        external.execute("UPDATE artifacts SET payload=?,sha256=?,completeness='COMPLETE' WHERE artifact_id=?",(text,digest(text),artifact))
        after=path.stat()
        assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
        assert Path(str(path)+'-wal').stat().st_size>0
        assert not store.privacy.sanitize_backups()
        erased(path,ids[0])
    finally:external.close()


def test_real_pinned_wal_reader_keeps_purge_pending_until_checkpoint(copies):
    store,memory,authority,ids,paths=copies
    reader=sqlite3.connect(paths[0],isolation_level=None)
    try:
        reader.execute('PRAGMA journal_mode=WAL');reader.execute('BEGIN')
        assert reader.execute('SELECT payload FROM artifacts WHERE artifact_id=?',
            (store.one('memories',ids[0])['payload_artifact_id'],)).fetchone()[0] is not None
        result=memory.forget(ids[0],authority)
        assert result['state']=='PENDING_BACKUP_PURGE' and result['pending_backup_count']==1
    finally:reader.close()
    assert not store.privacy.sanitize_backups()
    for path in paths:erased(path,ids[0])
