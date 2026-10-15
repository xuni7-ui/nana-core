"""Foreground synthetic runtime CLI. No production install/daemon/network mode."""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
from ..actions import OperatorAuthority
from ..clock import Clock
from ..contracts import CoreError
from ..continuity import ContinuityStore,IdentityService
from ..continuity.memory import MemoryService
from .contracts import RuntimeConfig
from .authority import process_identity
from .runtime import NanaRuntime


def status(path):
    if not Path(path).is_file():return {'status':'UNKNOWN','reason':'RUNTIME_NOT_INITIALIZED'}
    with sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_lease'").fetchone():
            return {'status':'UNKNOWN','reason':'NOT_A_RUNTIME_STORE'}
        lease=db.execute('SELECT * FROM runtime_lease').fetchone()
        if not lease:return {'status':'UNKNOWN','reason':'NO_RUNTIME_LEASE'}
        lease=dict(lease)
        alive=False
        try:alive=(process_identity(lease['pid'])==(lease['process_start'],lease['boot_id']))
        except (OSError,ValueError):pass
        rows=dict(db.execute("SELECT key,value_json FROM core_meta WHERE key='runtime.health'"))
        now=Clock().utc_now_us()
        freshness='UNKNOWN' if now<lease['heartbeat_at_us'] else 'FRESH' if now<lease['expires_at_us'] else 'STALE'
        state=lease['state'] if lease['state']!='ACTIVE' or freshness=='FRESH' else 'STALE_OR_TIME_UNCERTAIN'
        return {'status':state if alive else 'STOPPED_OR_CRASHED','process_alive':alive,'heartbeat_freshness':freshness,
            'runtime_active':bool(alive and lease['state']=='ACTIVE' and freshness=='FRESH'),'lease':lease,
            'operational':json.loads(rows['runtime.health']) if rows else {},
            'queue':dict(db.execute('SELECT state,count(*) FROM runtime_queue GROUP BY state'))}


def request_stop(path):
    report=status(path)
    if not report.get('process_alive') or report.get('lease',{}).get('state')!='ACTIVE':
        return {'status':'ALREADY_STOPPED'}
    lease=report['lease'];pid=lease['pid']
    if pid==os.getpid() or not hasattr(os,'pidfd_open'):raise CoreError('RUNTIME_STOP_IDENTITY_UNAVAILABLE')
    fd=os.pidfd_open(pid)
    try:
        if process_identity(pid)!=(lease['process_start'],lease['boot_id']):raise CoreError('RUNTIME_STOP_IDENTITY_CHANGED')
        cmd=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
        if b'nana_core.presence.cli' not in cmd:raise CoreError('RUNTIME_STOP_NOT_CLI_OWNER')
        signal.pidfd_send_signal(fd,signal.SIGTERM)
    finally:os.close(fd)
    return {'status':'STOP_REQUESTED','instance_id':lease['instance_id'],'epoch':lease['epoch']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('init-synthetic','run','status','stop'))
    parser.add_argument('--db',required=True)
    parser.add_argument('--config')
    parser.add_argument('--max-seconds',type=float,default=30)
    args=parser.parse_args()
    try:
        if args.command=='status':print(json.dumps(status(args.db)));return
        if args.command=='stop':print(json.dumps(request_stop(args.db)));return
        config=RuntimeConfig.model_validate_json(Path(args.config).read_text()) if args.config else RuntimeConfig(scopes=('synthetic-life',),entity_id='synthetic-person')
        if args.command=='init-synthetic':
            if Path(args.db).exists():raise CoreError('RUNTIME_DESTINATION_EXISTS')
            with ContinuityStore(args.db,schema_target=config.schema_target) as store:
                IdentityService(store,OperatorAuthority())
                MemoryService(store).entity(config.entity_id,'PERSON')
                print(json.dumps({'status':'SYNTHETIC_STORE_CREATED','identity_id':store.identity['identity_id']}))
            return
        if not 0<=args.max_seconds<=86400:raise CoreError('RUNTIME_DURATION_INVALID')
        with NanaRuntime(args.db,config) as runtime:
            def stop(*unused):runtime.stop_requested=True
            signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
            # run() owns final close; read health before closing only via status.
            runtime.run(args.max_seconds)
        print(json.dumps({'status':'STOPPED','real_external_actions':0}))
    except (CoreError,OSError,ValueError):
        print(json.dumps({'status':'BLOCKED','reason':'RUNTIME_INPUT_OR_STATE_INVALID'}))
        raise SystemExit(2) from None

if __name__=='__main__':main()
