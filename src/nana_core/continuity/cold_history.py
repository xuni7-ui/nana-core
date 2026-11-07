"""Read-only cold views of original managed backups; the live Store stays truth.

No history is removed and no backup is activated. A sealed copy is compacted
only by dropping known rebuildable indexes. Source correction/deletion and the
original privacy journal always outrank an old snapshot. Changed snapshots must
be recreated, never silently resealed or read as current facts.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat

from ..actions import OperatorAuthority
from ..contracts import CoreError
from ..storage import digest
from .privacy import _atomic, _json_object
from .store import REBUILDABLE_LOOKUP_INDEXES


def _signature(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode&0o077:
        raise CoreError('COLD_HISTORY_PRIVATE_FILE_REQUIRED')
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def _file_digest(path):
    result=hashlib.sha256()
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        for part in iter(lambda:stream.read(1<<20),b''):result.update(part)
    return result.hexdigest()


def _check_dependencies(db):
    """SQLite FK checks do not cover polymorphic source IDs."""
    for table,kind,parent,key in (
        ('memory_dependencies','MEMORY','memories','memory_id'),
        ('memory_dependencies','EVIDENCE','continuity_evidence','evidence_id'),
        ('record_dependencies','MEMORY','memories','memory_id'),
        ('record_dependencies','RECORD','continuity_records','record_id'),
    ):
        sql=('SELECT 1 FROM '+table+' d LEFT JOIN '+parent+' p ON p.'+key+'=d.parent_id '
             'WHERE d.parent_kind=? AND p.'+key+' IS NULL LIMIT 1')
        if db.execute(sql,(kind,)).fetchone():raise CoreError('COLD_HISTORY_DEPENDENCY_INTEGRITY')


class ColdHistoryService:
    """Host maintenance adapter, not a second MemoryService or runtime owner."""
    def __init__(self,store,authority):
        if not isinstance(authority,OperatorAuthority):raise CoreError('OPERATOR_AUTHORITY_REQUIRED')
        self.store,self.authority=store,authority

    def _owner(self):
        self.store.ensure_privacy_current()
        if self.store.db.in_transaction:raise CoreError('COLD_HISTORY_SAFE_POINT_REQUIRED')
        guard=getattr(self.store,'_runtime_guard',None)
        if guard:
            guard()
            control=self.store.one('core_meta','runtime.life_control')
            if not control or not json.loads(control['value_json']).get('paused'):
                raise CoreError('COLD_HISTORY_PAUSE_FIRST')
        return guard

    def create(self,destination,*,authority):
        if authority is not self.authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        guard=self._owner()
        path=self.store._private_path(Path(destination).absolute())
        seal_path=Path(str(path)+'.cold.json')
        if path.exists() or seal_path.exists() or seal_path.is_symlink():raise CoreError('DESTINATION_EXISTS')
        self.store.backup(path)  # same original quarantine and deletion registry
        initial=path.stat().st_size
        db=sqlite3.connect(path,isolation_level=None)
        removed=[]
        try:
            for name,expected in REBUILDABLE_LOOKUP_INDEXES.items():
                row=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?",(name,)).fetchone()
                if row:
                    if row[0]!=expected:raise CoreError('COLD_HISTORY_INDEX_DRIFT')
                    db.execute('DROP INDEX '+name);removed.append(name)
            if db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]:raise CoreError('COLD_HISTORY_CHECKPOINT_BUSY')
            db.execute('VACUUM')
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():
                raise CoreError('COLD_HISTORY_INTEGRITY')
            _check_dependencies(db)
            cutoff=db.execute('SELECT max(seq) FROM events').fetchone()[0]
            last=db.execute('SELECT event_id,data_json FROM events WHERE seq=?',(cutoff,)).fetchone()
            identity=db.execute('SELECT identity_id FROM identities').fetchone()[0]
            if identity!=self.store.identity['identity_id']:raise CoreError('COLD_HISTORY_IDENTITY_MISMATCH')
        finally:db.close()
        if guard:guard()
        seal={'format':'MANAGED_COLD_HISTORY_V1','identity_id':identity,'schema':self.store.schema_target,
            'cutoff':cutoff,'last_event_id':last[0],'last_event_data_digest':digest(last[1]),
            'sha256':_file_digest(path),'file_bytes':path.stat().st_size,
            'allocated_bytes':path.stat().st_blocks*512,'initial_file_bytes':initial,
            'removed_rebuildable_indexes':removed,'main_history_evicted':False,
            'authority':'LIVE_STORE_AND_ORIGINAL_PRIVACY_JOURNAL','activation':'QUARANTINED_NOT_A_RUNTIME'}
        _atomic(seal_path,seal)
        return {'path':str(path),**seal}

    def open(self,path,*,scopes,privacy_classes,entity_ids):
        self.store.ensure_privacy_current()
        path=self.store._private_path(Path(path).absolute())
        seal_path=Path(str(path)+'.cold.json');_signature(seal_path)
        with open(seal_path,encoding='utf-8') as stream:raw=stream.read(16385)
        if len(raw)>16384:raise CoreError('COLD_HISTORY_SEAL_INVALID')
        try:seal=json.loads(raw,object_pairs_hook=_json_object)
        except ValueError:raise CoreError('COLD_HISTORY_SEAL_INVALID') from None
        if (seal.get('format')!='MANAGED_COLD_HISTORY_V1' or seal.get('identity_id')!=self.store.identity['identity_id']
                or seal.get('schema')!=self.store.schema_target or seal.get('main_history_evicted') is not False):
            raise CoreError('COLD_HISTORY_SEAL_INVALID')
        if str(path.resolve()) not in self.store.privacy.read()['backups']:raise CoreError('COLD_HISTORY_NOT_MANAGED')
        before=_signature(path)
        if _file_digest(path)!=seal.get('sha256') or _signature(path)!=before:
            raise CoreError('COLD_HISTORY_CHANGED_RECREATE_REQUIRED')
        if any(Path(str(path)+suffix).exists() and Path(str(path)+suffix).stat().st_size for suffix in ('-wal','-journal')):
            raise CoreError('COLD_HISTORY_UNCHECKPOINTED')
        db=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)
        try:
            identity=db.execute('SELECT identity_id FROM identities').fetchone()
            last=db.execute('SELECT seq,event_id,data_json FROM events ORDER BY seq DESC LIMIT 1').fetchone()
            live=self.store.event(last[1]) if last else None
            quarantine=db.execute("SELECT value_json FROM core_meta WHERE key='recovery_quarantine'").fetchone()
            if (not identity or identity[0]!=seal['identity_id'] or not last or not live
                    or last[0]!=seal.get('cutoff') or last[1]!=seal.get('last_event_id')
                    or digest(last[2])!=seal.get('last_event_data_digest') or last[0]!=live['seq']
                    or digest(last[2])!=digest(live['data_json']) or not quarantine or quarantine[0]!='true'):
                raise CoreError('COLD_HISTORY_EVENT_BINDING')
        finally:db.close()
        if _signature(path)!=before:raise CoreError('COLD_HISTORY_CHANGED_RECREATE_REQUIRED')
        return ColdHistoryView(self.store,path,seal,before,tuple(scopes),tuple(privacy_classes),tuple(entity_ids))


class ColdHistoryView:
    def __init__(self,store,path,seal,signature,scopes,privacy,entities):
        self.store,self.path,self.seal,self.signature=store,path,seal,signature
        self.scopes,self.privacy,self.entities=scopes,privacy,entities

    def _current(self,memory_id):
        self.store.ensure_privacy_current()
        memory=self.store.one('memories',memory_id)
        if (not memory or memory['lifecycle']!='ACTIVE' or memory['assessment'] not in {'CURRENT','UNASSESSED'}
                or memory['scope'] not in self.scopes or memory['privacy_class'] not in self.privacy
                or memory['entity_id'] not in self.entities):raise CoreError('COLD_HISTORY_SOURCE_UNAVAILABLE')
        return memory

    def memory(self,memory_id):
        live=self._current(memory_id)  # deny erased/private/stale BEFORE any cold text
        if _signature(self.path)!=self.signature:raise CoreError('COLD_HISTORY_CHANGED_RECREATE_REQUIRED')
        lock_fd=os.open(str(self.path)+'.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        db=None
        try:
            fcntl.flock(lock_fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            db=sqlite3.connect(self.path.as_uri()+'?mode=ro&immutable=1',uri=True)
            db.row_factory=sqlite3.Row
            quarantine=db.execute("SELECT value_json FROM core_meta WHERE key='recovery_quarantine'").fetchone()
            if not quarantine or quarantine[0]!='true':raise CoreError('COLD_HISTORY_NOT_QUARANTINED')
            row=db.execute('SELECT * FROM memories WHERE memory_id=?',(memory_id,)).fetchone()
            if not row or dict(row)!=live:raise CoreError('COLD_HISTORY_SOURCE_CHANGED')
            artifact=db.execute('SELECT * FROM artifacts WHERE artifact_id=?',(live['payload_artifact_id'],)).fetchone()
            expected=self.store.db.execute('SELECT sha256,completeness FROM artifacts WHERE artifact_id=?',(live['payload_artifact_id'],)).fetchone()
            if (not artifact or not expected or artifact['completeness']!='COMPLETE' or expected['completeness']!='COMPLETE'
                    or digest(artifact['payload'])!=artifact['sha256'] or artifact['sha256']!=expected['sha256']):
                raise CoreError('COLD_HISTORY_INTEGRITY')
            event=db.execute('SELECT seq,event_id,data_json FROM events WHERE event_id=?',(live['event_id'],)).fetchone()
            original=self.store.event(live['event_id'])
            if (not event or event['seq']>self.seal['cutoff'] or event['seq']!=original['seq']
                    or digest(event['data_json'])!=digest(original['data_json'])):raise CoreError('COLD_HISTORY_EVENT_BINDING')
            self._current(memory_id)
            if _signature(self.path)!=self.signature:raise CoreError('COLD_HISTORY_CHANGED_RECREATE_REQUIRED')
            return {**live,'text':artifact['payload'].decode(),'read_from':'MANAGED_COLD_HISTORY_V1',
                'event_cutoff':self.seal['cutoff'],'current_authority':'LIVE_STORE','execution_authority':False}
        except BlockingIOError:raise CoreError('COLD_HISTORY_BUSY') from None
        finally:
            if db:db.close()
            os.close(lock_fd)
