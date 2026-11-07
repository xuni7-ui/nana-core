"""Host-local storage guard and bounded diagnostic projection; never Subject truth.

History, outcomes, UNKNOWN and privacy tombstones are retained. PASSIVE checkpoint
permits WAL reuse without forcing readers out. A hard/rate limit stops the writer,
not the Subject's original desires. No automatic history deletion or vacuum.
"""
import json,os,stat,tempfile
from pathlib import Path
from ..contracts import CoreError,DTO
from pydantic import Field,model_validator
from typing import Literal
from ..continuity.privacy import _json_object

MB=1024*1024
HOUR=3_600_000_000

class StorageWindow(DTO):
    version:int=Field(default=1,ge=1,le=1)
    started_us:int=Field(ge=0)
    window_us:int=Field(ge=0)
    logical_bytes:int=Field(ge=0)
    status:Literal['OBSERVING','STATE_SIZE_LIMIT_STOP','STATE_GROWTH_LIMIT_STOP']='OBSERVING'

    @model_validator(mode='after')
    def valid_window(self):
        if self.window_us<self.started_us:raise ValueError('invalid storage window')
        return self


def _atomic(path,data):
    if path.is_symlink():raise CoreError('STORAGE_MONITOR_INVALID')
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.storage-')
    try:
        with os.fdopen(fd,'w') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path);directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def size_view(store):
    page=store.db.execute('PRAGMA page_size').fetchone()[0]
    count=store.db.execute('PRAGMA page_count').fetchone()[0]
    free=store.db.execute('PRAGMA freelist_count').fetchone()[0]
    files={};allocations={};allocated_inodes={}
    for suffix in ('','-wal','-shm','.privacy.json'):
        p=Path(str(store.path)+suffix)
        if p.is_symlink():raise CoreError('CONTINUITY_SYMLINK_FORBIDDEN')
        if p.exists():
            details=p.stat();name=suffix or 'database'
            files[name]=details.st_size;allocations[name]=details.st_blocks*512
            allocated_inodes[(details.st_dev,details.st_ino)]=details.st_blocks*512
    # A registered copy may point to the same trusted deletion anchor elsewhere.
    anchor_details=store.privacy.path.stat();anchor=anchor_details.st_size
    allocated_inodes[(anchor_details.st_dev,anchor_details.st_ino)]=anchor_details.st_blocks*512
    return {'logical_database_bytes':page*count,'reusable_page_bytes':page*free,
        'privacy_anchor_bytes':anchor,'physical_file_bytes':files,
        'file_length_measurement':'STAT_ST_SIZE_NOT_ALLOCATED_BLOCKS','allocated_file_bytes':allocations,
        'allocated_family_bytes':sum(allocated_inodes.values()),'allocation_measurement':'DEDUPLICATED_STAT_ST_BLOCKS_TIMES_512',
        'family_bytes':sum(files.values())+max(0,anchor-files.get('.privacy.json',0)),'history_deleted':False}


def profile(store):
    sizes=size_view(store)
    tables=[{'name':r[0],'allocated_bytes':r[1],'payload_bytes':r[2]} for r in store.db.execute('SELECT name,sum(pgsize),sum(payload) FROM dbstat GROUP BY name ORDER BY sum(pgsize) DESC LIMIT 64')]
    events=[{'kind':r[0],'recent_count':r[1],'json_bytes':r[2]} for r in store.db.execute('SELECT kind,count(*),sum(length(CAST(data_json AS BLOB))) FROM (SELECT kind,data_json FROM events ORDER BY seq DESC LIMIT 4096) GROUP BY kind ORDER BY sum(length(CAST(data_json AS BLOB))) DESC LIMIT 32')]
    return {'derived':True,**sizes,'tables_and_indexes':tables,'event_coverage':'LATEST_4096_NOT_FULL_HISTORY','event_kinds':events,
        'retention':{'permanent':['provenance','lineage','events','outcome_action_history','UNKNOWN','privacy_deletion_journal'],
        'rebuildable':['memory_terms','derived_context','life_journal_projection'],
        'checkpoint_reusable':['WAL_pages_without_pinned_readers','freelist_pages'],
        'rotate':['sanitized_runtime_logs'],
        'archive':'FUTURE_EXPLICIT_VERIFIED_ARCHIVE_NOT_AUTOMATIC_PRUNING'},'authority':False}


def read_window(path):
    if not path.exists() and not path.is_symlink():return None
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd) as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise ValueError()
            raw=f.read(4097)
        if len(raw)>4096:raise ValueError()
        return StorageWindow.model_validate_json(json.dumps(json.loads(raw,object_pairs_hook=_json_object)))
    except (OSError,ValueError):raise CoreError('STORAGE_MONITOR_INVALID') from None


class StorageGuard:
    def __init__(self,app):
        self.app=app;self.path=app.home/'storage-monitor.json';self.next_us=0;self.last=None
        self.state=read_window(self.path)
    def observe(self,*,force=False):
        app=self.app;r=app.runtime;now=r.clock.utc_now_us()
        if not force and now<self.next_us:return self.last
        r.lease.assert_current();self.next_us=now+app.config.storage_review_seconds*1_000_000
        sizes=size_view(r.store);logical=sizes['logical_database_bytes']+sizes['privacy_anchor_bytes'];cfg=app.config
        state=self.state or StorageWindow(started_us=now,window_us=now,logical_bytes=logical)
        if now<state.window_us:raise CoreError('STORAGE_MONITOR_CLOCK_CONFLICT')
        status=state.status;elapsed=now-state.window_us;growth=max(0,logical-state.logical_bytes)
        if status.endswith('_STOP'):pass # latched across restart until trusted offline review
        elif sizes['family_bytes']>cfg.max_state_mb*MB:status='STATE_SIZE_LIMIT_STOP'
        elif state.window_us-state.started_us>=cfg.storage_growth_grace_seconds*1_000_000 and elapsed>=cfg.storage_growth_window_seconds*1_000_000:
            if growth*HOUR>cfg.max_state_growth_mb_per_hour*MB*elapsed:status='STATE_GROWTH_LIMIT_STOP'
        if elapsed>=cfg.storage_growth_window_seconds*1_000_000 and status=='OBSERVING':
            state=state.model_copy(update={'window_us':now,'logical_bytes':logical})
        state=state.model_copy(update={'status':status});self.state=state
        r.lease.assert_current()
        checkpoint=r.store.db.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
        self.last={**sizes,'status':status,'growth_bytes_observed_window':growth,'window_elapsed_us':elapsed,
            'checkpoint':{'busy':checkpoint[0],'wal_pages':checkpoint[1],'checkpointed_pages':checkpoint[2]},'automatic_pruning':False}
        _atomic(self.path,state.model_dump_json());r.lease.assert_current()
        if status.endswith('_STOP'):r.request_stop()
        return self.last
