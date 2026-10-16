"""Offline, single-lineage transfer using the existing backup/quarantine protocol.

Not a live clone/fork or distributed anti-copy authority. Source retirement is
irreversible through this API; a failed export can be retried for the SAME target.
The trusted operator must carry the one package to its configured destination.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Literal
from uuid import UUID
import zipfile
from pydantic import Field
from ..contracts import CoreError, DTO
from ..storage import canonical, digest, uid
from ..storage.development_schema import LATEST, install
from .privacy import _atomic, _json_object
from .store import ContinuityStore

MAX_PACKAGE=64*1024*1024
_FILES={'subject.sqlite','privacy.json','manifest.json'}
_META={'recovery_quarantine','cloud.shadow_runtime','self.subject_revision','governance.registry','governance.clock',
       'auth_high_water_us','portable.retired','portable.received','runtime.epoch_floor'}
_TRANSIENT={'runtime.managed','runtime.health'}

class PortableTransferAuthority:
    """Trusted offline application construction, not Subject/ModelPort authority."""
    def __init__(self, *, destination_id=None, destination_root=None):
        if (destination_id is None) != (destination_root is None):
            raise CoreError('PORTABLE_DESTINATION_BINDING_REQUIRED')
        self.destination_id=destination_id
        self.destination_root=Path(destination_root).absolute() if destination_root is not None else None

    def assert_destination(self, destination_id, root):
        if self.destination_id!=destination_id or self.destination_root!=Path(root).absolute():
            raise CoreError('PORTABLE_DESTINATION_BINDING_REQUIRED')

class SubjectPackageManifest(DTO):
    format: Literal['SUBJECT_PACKAGE_V1'] = 'SUBJECT_PACKAGE_V1'
    operation: Literal['OFFLINE_TRANSFER_NOT_FORK'] = 'OFFLINE_TRANSFER_NOT_FORK'
    domain: Literal['SYNTHETIC_ONLY'] = 'SYNTHETIC_ONLY'
    transfer_id: str
    destination_id: str
    identity_id: str
    identity_revision: int = Field(ge=1)
    source_commit: str = Field(pattern=r'^[0-9a-f]{40}$')
    source_schema: int = Field(ge=7,le=12)
    export_event_cutoff: int = Field(ge=1)
    exported_at_us: int = Field(ge=0)
    epoch_floor: int = Field(ge=0)
    schema_digest: str
    files: dict[str,str]
    excluded: tuple[str,...] = ('credentials','provider_instances','embedding_cache','runtime_lease','runtime_health','machine_paths','external_execution_authority')


class SubjectForkProposal(DTO):
    """Reserved semantic distinction; no implementation can activate a fork."""
    operation: Literal['FORK_REQUIRES_NEW_IDENTITY'] = 'FORK_REQUIRES_NEW_IDENTITY'
    source_identity_id: str
    parent_lineage_digest: str = Field(pattern=r'^[0-9a-f]{64}$')
    state: Literal['NOT_IMPLEMENTED_NOT_AUTHORITY'] = 'NOT_IMPLEMENTED_NOT_AUTHORITY'


def _schema_digest(db):
    return digest([tuple(r) for r in db.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")])


def _expected_schema(version):
    from ..storage import sqlite_store
    db=sqlite3.connect(':memory:',isolation_level=None)
    try:
        db.executescript(Path(sqlite_store.__file__).with_name('schema_v1.sql').read_text())
        install(db,1,version)
        return _schema_digest(db)
    finally:db.close()


def _manifest(raw):
    try:
        obj=json.loads(raw,object_pairs_hook=_json_object)
        m=SubjectPackageManifest.model_validate_json(canonical(obj))
        if str(UUID(m.transfer_id))!=m.transfer_id or str(UUID(m.destination_id))!=m.destination_id or str(UUID(m.identity_id))!=m.identity_id:
            raise ValueError()
        if set(m.files)!={'subject.sqlite','privacy.json'} or any(not re.fullmatch('[0-9a-f]{64}',v) for v in m.files.values()):raise ValueError()
        return m
    except (ValueError,TypeError,KeyError):raise CoreError('SUBJECT_PACKAGE_MANIFEST_INVALID') from None


def verify_package(path,*,expected_sha256):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_PACKAGE:
        raise CoreError('SUBJECT_PACKAGE_PATH_INVALID')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise CoreError('SUBJECT_PACKAGE_INTEGRITY')
    try:
        import io
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            infos=z.infolist()
            if len(infos)!=3 or {i.filename for i in infos}!=_FILES or any(i.file_size>MAX_PACKAGE or i.external_attr>>16&0o170000==0o120000 for i in infos) or sum(i.file_size for i in infos)>MAX_PACKAGE:
                raise ValueError()
            files={i.filename:z.read(i) for i in infos}
        m=_manifest(files['manifest.json'])
        if any(digest(files[name])!=sha for name,sha in m.files.items()):raise ValueError()
        if m.schema_digest!=_expected_schema(m.source_schema):raise ValueError()
        return m,files
    except (ValueError,OSError,zipfile.BadZipFile,RuntimeError):raise CoreError('SUBJECT_PACKAGE_INTEGRITY') from None


class SubjectPackageService:
    def __init__(self,store,authority:PortableTransferAuthority):
        if type(authority) is not PortableTransferAuthority:raise CoreError('PORTABLE_CONTROLLER_REQUIRED')
        self._store,self._authority=store,authority
    def _auth(self,authority):
        if authority is not self._authority:raise CoreError('PORTABLE_CONTROLLER_REQUIRED')
    def _offline(self):
        s=self._store
        if getattr(s,'_runtime_guard',None):raise CoreError('PORTABLE_STOP_RUNTIME_FIRST')
        if s.schema_target>=8:
            lease=s.one('runtime_lease',s.identity['identity_id'])
            if lease and lease['state']=='ACTIVE':raise CoreError('PORTABLE_STOP_RUNTIME_FIRST')
            if s.db.execute("SELECT 1 FROM runtime_queue WHERE state='PROCESSING'").fetchone() or s.db.execute("SELECT 1 FROM runtime_cognition_calls WHERE state='RESERVED'").fetchone():raise CoreError('PORTABLE_UNRESOLVED_COGNITION')
        if s.db.execute("SELECT 1 FROM actions WHERE state IN ('READY','DISPATCHING','PENDING_VERIFY','UNKNOWN')").fetchone() or s.db.execute("SELECT 1 FROM budgets WHERE held>0").fetchone():
            raise CoreError('PORTABLE_UNRESOLVED_EFFECT')
        unknown={r['key'] for r in s.all('core_meta')}-_META-_TRANSIENT
        if unknown:raise CoreError('PORTABLE_UNSUPPORTED_MACHINE_METADATA')
        # Journal entries are never rewritten to strip an accidental credential.
        # Reject unsupported metadata instead of exporting it from an older event.
        for row in s.db.execute('SELECT data_json FROM events'):
            for c in json.loads(row[0])['changes']:
                if c['table']=='core_meta' and c['row']['key'] not in _META|_TRANSIENT:
                    raise CoreError('PORTABLE_UNSUPPORTED_MACHINE_METADATA')
                if c['table']=='runtime_lease' or (c['table']=='core_meta' and c['row']['key'] in _TRANSIENT):
                    raise CoreError('PORTABLE_HOST_METADATA_IN_HISTORY')
    def export(self,path,*,destination_id,source_commit,authority):
        self._auth(authority);s=self._store;path=Path(path)
        try:
            if str(UUID(destination_id))!=destination_id or not re.fullmatch('[0-9a-f]{40}',source_commit):raise ValueError()
        except (ValueError,TypeError):raise CoreError('PORTABLE_TRANSFER_SPEC_INVALID') from None
        if path.exists() or path.is_symlink():raise CoreError('DESTINATION_EXISTS')
        self._offline();s.ensure_privacy_current()
        old=s.one('core_meta','portable.retired')
        if old:
            transfer=json.loads(old['value_json'])
            if (transfer['destination_id'],transfer['source_commit'])!=(destination_id,source_commit):raise CoreError('PORTABLE_SOURCE_ALREADY_RETIRED')
        else:
            lease=s.one('runtime_lease',s.identity['identity_id']) if s.schema_target>=8 else None
            floor=s.one('core_meta','runtime.epoch_floor')
            transfer={'transfer_id':uid(),'destination_id':destination_id,'source_commit':source_commit,
                'epoch_floor':max(lease['epoch'] if lease else 0,json.loads(floor['value_json']) if floor else 0),
                'exported_at_us':s.clock.utc_now_us()}
            # Existing stopped-runtime fence is satisfied by a trusted maintenance
            # guard while exclusive Store flock remains held. No second runtime.
            prior=getattr(s,'_runtime_guard',None)
            s._runtime_guard=lambda: None
            try:
                with s.transaction('portable.source_retired',transfer) as tx:
                    tx.put('core_meta',{'key':'portable.retired','value_json':canonical(transfer)})
            finally:s._runtime_guard=prior
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.subject-package-',dir=path.parent) as name:
            root=Path(name);dbpath=root/'subject.sqlite'
            s.backup(dbpath)  # official managed, deletion-aware, quarantined backup
            db=sqlite3.connect(dbpath,isolation_level=None)
            try:
                if s.schema_target>=8:db.execute('DELETE FROM runtime_lease')
                if s.schema_target>=11:db.execute('UPDATE jobs SET owner_epoch=NULL')
                db.execute("DELETE FROM core_meta WHERE key IN ('runtime.managed','runtime.health')")
                db.execute("INSERT OR REPLACE INTO core_meta VALUES('runtime.epoch_floor',?)",(canonical(transfer['epoch_floor']),))
                schema_sha=_schema_digest(db)
                if schema_sha!=_expected_schema(s.schema_target):raise CoreError('PORTABLE_SCHEMA_DRIFT')
                db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.execute('VACUUM')
            finally:db.close()
            privacy=s.privacy.read()
            portable_privacy={'schema_version':1,'identity_id':privacy['identity_id'],'intents':privacy['intents']}
            files={'subject.sqlite':dbpath.read_bytes(),'privacy.json':canonical(portable_privacy).encode()}
            cutoff=s.db.execute('SELECT max(seq) FROM events').fetchone()[0]
            m=SubjectPackageManifest(**transfer,identity_id=s.identity['identity_id'],identity_revision=s.identity['revision'],source_schema=s.schema_target,
                export_event_cutoff=cutoff,schema_digest=schema_sha,files={k:digest(v) for k,v in files.items()})
            files['manifest.json']=m.model_dump_json().encode()
            output=root/'package.zip'
            with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for key in sorted(files):
                    info=zipfile.ZipInfo(key,date_time=(1980,1,1,0,0,0));info.external_attr=0o100600<<16;info.compress_type=zipfile.ZIP_DEFLATED
                    z.writestr(info,files[key])
            sha=digest(output.read_bytes());verify_package(output,expected_sha256=sha)
            # Atomic, no overwrite; publish only a fully verified archive.
            os.link(output,path);path.chmod(0o600)
            fd=os.open(path.parent,os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
        return {'path':str(path),'sha256':sha,'bytes':path.stat().st_size,'manifest':m}

    @staticmethod
    def import_quarantined(path,destination,*,expected_sha256,destination_id,authority):
        if type(authority) is not PortableTransferAuthority:raise CoreError('PORTABLE_CONTROLLER_REQUIRED')
        m,files=verify_package(path,expected_sha256=expected_sha256)
        if destination_id!=m.destination_id:raise CoreError('PORTABLE_DESTINATION_MISMATCH')
        authority.assert_destination(destination_id,destination)
        root=Path(destination)
        if root.exists() or root.is_symlink():raise CoreError('PORTABLE_CLEAN_DESTINATION_REQUIRED')
        root.mkdir(mode=0o700,parents=False)
        dbpath=root/'self.db'
        # No arbitrary archive extraction, filenames or symlink traversal.
        dbpath.write_bytes(files['subject.sqlite']);dbpath.chmod(0o600)
        privacy=json.loads(files['privacy.json'],object_pairs_hook=_json_object)
        if set(privacy)!={'schema_version','identity_id','intents'} or privacy['identity_id']!=m.identity_id:
            raise CoreError('PORTABLE_PRIVACY_INVALID')
        _atomic(Path(str(dbpath)+'.privacy.json'),{**privacy,'backups':[str(dbpath.resolve())]})
        db=sqlite3.connect(dbpath,isolation_level=None)
        try:
            db.execute('PRAGMA trusted_schema=OFF')
            if db.execute('PRAGMA user_version').fetchone()[0]!=m.source_schema or _schema_digest(db)!=m.schema_digest or db.execute('PRAGMA quick_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():
                raise CoreError('PORTABLE_DATABASE_INVALID')
            identity=db.execute('SELECT identity_id,revision FROM identities').fetchone()
            if identity!=(m.identity_id,m.identity_revision):raise CoreError('PORTABLE_IDENTITY_MISMATCH')
            retired=db.execute("SELECT value_json FROM core_meta WHERE key='portable.retired'").fetchone()
            if (not retired or json.loads(retired[0])['transfer_id']!=m.transfer_id
                    or json.loads(retired[0])['destination_id']!=m.destination_id
                    or db.execute('SELECT max(seq) FROM events').fetchone()[0]!=m.export_event_cutoff):
                raise CoreError('PORTABLE_LINEAGE_INVALID')
            db.execute('BEGIN IMMEDIATE')
            db.execute("DELETE FROM core_meta WHERE key='portable.retired'")
            db.execute("INSERT OR REPLACE INTO core_meta VALUES('portable.received',?)",(canonical({'state':'QUARANTINED','transfer_id':m.transfer_id,'destination_id':m.destination_id,'package_sha256':expected_sha256}),))
            db.execute('COMMIT')
        finally:db.close()
        # Opening applies opaque deletion intents and verifies sidecar semantics.
        with ContinuityStore(dbpath,schema_target=m.source_schema) as store:
            store.ensure_privacy_current()
        return dbpath

    def activate(self,*,transfer_id,destination_id,authority):
        self._auth(authority);s=self._store;self._offline()
        row=s.one('core_meta','portable.received')
        received=json.loads(row['value_json']) if row else None
        if not received or (received['transfer_id'],received['destination_id'])!=(transfer_id,destination_id):raise CoreError('PORTABLE_ACTIVATION_MISMATCH')
        authority.assert_destination(destination_id,s.path.parent)
        if received['state']=='ACTIVE':raise CoreError('PORTABLE_ALREADY_ACTIVATED')
        def guard():
            current=json.loads(s.one('core_meta','portable.received')['value_json'])
            if current!=received:raise CoreError('PORTABLE_ACTIVATION_STALE')
        s._portable_activation_guard=guard
        try:
            from .memory import MemoryService
            MemoryService(s).rebuild_index()
            with s.transaction('portable.destination_activated',{'transfer_id':transfer_id,'destination_id':destination_id}) as tx:
                for grant in s.all('grants'):tx.update('grants',grant['grant_id'],revoked=1)
                for budget in s.all('budgets'):tx.update('budgets',budget['dimension'],limit_value=budget['spent'],held=0)
                tx.put('core_meta',{'key':'recovery_quarantine','value_json':'false'})
                tx.put('core_meta',{'key':'portable.received','value_json':canonical({**received,'state':'ACTIVE'})})
        finally:del s._portable_activation_guard
        return s.identity['identity_id']
