"""Bounded foreground bridge operator. No daemon/spawn/auto install/production auth."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import signal
import re
from datetime import datetime,timezone,timedelta
import socket
import stat
from .bridge_wire import private_directory,process_fingerprint,sha,stamp,install_process_deadline,DirectoryFence,canonical
from .one_shot_cli import operator_ledger,_SafeParser
from .one_shot import PRODUCTION_REVIEW_PINS,ProductionTrustStore,utc
from . import sealed_trust
from .bridge_worker import ShortLivedWorker
from tools.nana_host_shadow.safety import read_json,private_file


def session_status(ipc):
    ipc=private_directory(ipc)
    with DirectoryFence(ipc) as fence:
        raw=fence.read('session.json',65536)
    row=json.loads(raw)
    if (canonical(row)+'\n').encode()!=raw:raise ValueError('BRIDGE_SESSION_CANONICAL')
    if type(row) is not dict or set(row)!={'schema_version','session_id','receipt_id','store_binding','pid','pid_fingerprint','uid',
        'socket_device','socket_inode','socket_path','expires_at','trust_domain','phase','host_binding','real_host_bridge','E12'}:
        raise ValueError('BRIDGE_SESSION_METADATA')
    if type(row['schema_version']) is not int or row['schema_version']!=1:raise ValueError('BRIDGE_SESSION_SCHEMA')
    for k in ('pid','uid','socket_device','socket_inode'):
        if type(row[k]) is not int or row[k]<0:raise ValueError('BRIDGE_SESSION_INTEGER')
    for k in ('pid_fingerprint','store_binding'):
        if type(row[k]) is not str or not re.fullmatch('[0-9a-f]{64}',row[k]):raise ValueError('BRIDGE_SESSION_HASH')
    if (type(row['session_id']) is not str or not re.fullmatch('[0-9a-f]{32}',row['session_id'])
        or type(row['receipt_id']) is not str or not re.fullmatch('r04-[0-9a-f]{32}',row['receipt_id'])
        or row['phase'] not in ('RUNNING','CLOSED') or row['trust_domain'] not in ('PRODUCTION','FIXTURE')
        or row['host_binding']!='UNVERIFIED' or row['real_host_bridge']!='NOT_RUN' or row['E12']!='NOT_RUN'):
        raise ValueError('BRIDGE_SESSION_LABEL')
    stamp(row['expires_at'])
    if Path(row['socket_path'])!=ipc/'bridge.sock' or row['uid']!=os.getuid():raise ValueError('BRIDGE_SESSION_PATH')
    live=False
    try:live=process_fingerprint(row['pid'])==row['pid_fingerprint']
    except (FileNotFoundError,ProcessLookupError):pass
    return {**row,'worker_alive':live,'effective_state':row['phase'] if live or row['phase']=='CLOSED' else 'UNKNOWN_WORKER_EXIT'}


def verified_session(directory,ipc,*,with_fence=False):
    row=session_status(ipc)
    with operator_ledger(directory) as l:
        r,v=l.record(row['receipt_id'])
        fence=l.store.one('core_meta','r041.receipt_session:'+row['receipt_id'])
        if not fence:raise ValueError('BRIDGE_SESSION_FENCE_MISSING')
        journal=None
        for e in l.store.db.execute("SELECT data_json FROM events WHERE kind LIKE 'r041.%' ORDER BY rowid DESC"):
            for change in json.loads(e['data_json'])['changes']:
                if change['table']=='core_meta' and change['row']['key']==fence['key']:
                    journal=change['row']['value_json'];break
            if journal is not None:break
        if journal!=fence['value_json']:raise ValueError('BRIDGE_SESSION_PROJECTION_CORRUPT')
        value=json.loads(fence['value_json'])
        # A forged sidecar cannot turn stop into an arbitrary PID signal.
        st=private_directory(ipc).stat()
        if (value.get('ipc_device'),value.get('ipc_inode'))!=(st.st_dev,st.st_ino):
            raise ValueError('BRIDGE_DIRECTORY_FENCE_DRIFT')
        if (value['session_id']!=row['session_id'] or value['store_binding']!=l.binding
            or value['pid']!=row['pid'] or value['pid_fingerprint']!=row['pid_fingerprint']
            or value['ipc_hash']!=sha(str(private_directory(ipc)))
            or value.get('socket_device')!=row['socket_device'] or value.get('socket_inode')!=row['socket_inode']):raise ValueError('BRIDGE_SESSION_FENCE_DRIFT')
    return (row,value) if with_fence else row

def stop(directory,ipc):
    row=verified_session(directory,ipc)
    if not row['worker_alive']:return {**row,'stop_result':'ALREADY_EXITED'}
    # pidfd fences PID reuse. Recheck fingerprint AFTER opening the descriptor.
    fd=os.pidfd_open(row['pid'])
    try:
        if process_fingerprint(row['pid'])!=row['pid_fingerprint']:raise ValueError('BRIDGE_PID_REUSED')
        signal.pidfd_send_signal(fd,signal.SIGTERM)
    finally:os.close(fd)
    return {'status':'STOP_REQUESTED','session_id':row['session_id'],'confirmation':'status/collect required'}


def stale_cleanup(directory,ipc):
    ipc=private_directory(ipc)
    with DirectoryFence(ipc) as fence:
        row,journal=verified_session(directory,ipc,with_fence=True)
        if row['worker_alive']:raise ValueError('BRIDGE_LIVE_CLEANUP_BLOCKED')
        expected=journal.get('client_config_digest')
        if type(expected) is not str or not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('BRIDGE_CLIENT_FENCE_MISSING')
        owned=[];unresolved=0
        # Fixed known names plus our atomic-detach tombstones. No arbitrary paths.
        names=['bridge.sock','client.json']+[n for n in os.listdir(fence.fd) if re.fullmatch(r'\.fence-[0-9a-f]{32}',n)]
        for name in names:
            try:st=fence.entry(name)
            except FileNotFoundError:continue
            if stat.S_ISSOCK(st.st_mode):
                if ((st.st_dev,st.st_ino)!=(row['socket_device'],row['socket_inode'])
                    or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o600):
                    if name=='bridge.sock':raise ValueError('BRIDGE_STALE_SOCKET_DRIFT')
                    unresolved+=1;continue
                owned.append((name,(st.st_dev,st.st_ino)))
            elif name=='client.json' or name.startswith('.fence-'):
                from .bridge_wire import decode_config
                try:c=decode_config(fence.read(name,8192))
                except (ValueError,OSError):
                    if name=='client.json':raise ValueError('BRIDGE_STALE_CLIENT_DRIFT') from None
                    unresolved+=1;continue
                if sha(c)!=expected:
                    if name=='client.json':raise ValueError('BRIDGE_STALE_CLIENT_DRIFT')
                    unresolved+=1;continue
                owned.append((name,(st.st_dev,st.st_ino)))
            else:raise ValueError('BRIDGE_STALE_SOCKET_DRIFT')
        # Validate ALL before first deletion; wrong client sidecar changes nothing.
        for name,identity in owned:fence.unlink_owned(name,identity)
    return {'status':'STALE_EPHEMERALS_REMOVED' if not unresolved else 'UNKNOWN_NEEDS_REVIEW',
            'unresolved_ephemerals':unresolved,'receipt_rearmed':False,'store_modified':False,'evidence_preserved':True}


def preflight(directory,rid,client_pid):
    result={'status':'BLOCKED','real_host_bridge':'NOT_RUN','host_binding':'UNVERIFIED','E12':'NOT_RUN',
        'linux_peercred':hasattr(socket,'SO_PEERCRED'),'pidfd':hasattr(os,'pidfd_open'),'production_review_pins':len(PRODUCTION_REVIEW_PINS)}
    private_directory(directory);process_fingerprint(client_pid)
    with operator_ledger(directory) as l:
        r,v=l.record(rid)
        now=datetime.now(timezone.utc)
        live=utc(r.issued_at)<=now+timedelta(seconds=2) and now<utc(r.expires_at)
        result.update(receipt_live=live,source_seal_executable=sealed_trust.SEAL_MODE=='ONE_SHOT',
            operator_domain_is_production=type(l.trust) is ProductionTrustStore,receipt_state=v['state'],receipt_expires_at=r.expires_at,exact_store_binding=r.store_binding==l.binding,
            receipt_trusted=l._review_valid(r,v['review']),session_fence_exists=l.store.one('core_meta','r041.receipt_session:'+rid) is not None)
        if (result['receipt_live'] and result['source_seal_executable'] and result['operator_domain_is_production']
            and result['receipt_trusted'] and v['state']=='ARMED' and not result['session_fence_exists']
            and result['linux_peercred'] and result['pidfd']):result['status']='READY'
    return result


def main(argv=None):
    parser=_SafeParser(description=__doc__)
    parser.add_argument('command',nargs='?',default='status',choices=('preflight','start','status','stop','collect','verify','cleanup'))
    parser.add_argument('--directory');parser.add_argument('--ipc-directory',required=True)
    parser.add_argument('--receipt-id');parser.add_argument('--client-pid',type=int)
    parser.add_argument('--seconds',type=float,default=60);parser.add_argument('--dry-run',action='store_true')
    try:
        a=parser.parse_args(argv)
        if a.dry_run:r={'status':'DRY_RUN','files_written':0,'host_binding':'UNVERIFIED'}
        elif a.command=='preflight':r=preflight(a.directory,a.receipt_id,a.client_pid)
        elif a.command=='start':
            check=preflight(a.directory,a.receipt_id,a.client_pid)
            if check['status']!='READY':raise ValueError('BRIDGE_NOT_READY')
            async def serve():
                worker=ShortLivedWorker(a.directory,a.ipc_directory,a.receipt_id,client_pid=a.client_pid,seconds=a.seconds)
                loop=asyncio.get_running_loop()
                loop.add_signal_handler(signal.SIGTERM,worker.stop_event.set)
                loop.add_signal_handler(signal.SIGINT,worker.stop_event.set)
                window=min(a.seconds,max(0,(stamp(check['receipt_expires_at'])-datetime.now(timezone.utc)).total_seconds()))
                previous=install_process_deadline(window+5)
                try:await worker.serve()
                finally:
                    signal.setitimer(signal.ITIMER_REAL,0)
                    signal.signal(signal.SIGALRM,previous)
            asyncio.run(serve());r=session_status(a.ipc_directory)
        elif a.command=='status':r=session_status(a.ipc_directory)
        elif a.command=='stop':r=stop(a.directory,a.ipc_directory)
        elif a.command=='cleanup':r=stale_cleanup(a.directory,a.ipc_directory)
        elif a.command in ('collect','verify'):
            with DirectoryFence(a.ipc_directory) as fence:raw=fence.read('result.json',65536)
            report=json.loads(raw)
            if (canonical(report)+'\n').encode()!=raw:raise ValueError('BRIDGE_RESULT_CANONICAL')
            from .one_shot_proof import verify_first_real_message_shadow
            with operator_ledger(a.directory) as l:
                verdict=verify_first_real_message_shadow(report.get('proof'),l)
                if a.command=='verify':r=verdict
                else:
                    # Never echo arbitrary/tampered sidecar fields or bodies.
                    row=verified_session(a.directory,a.ipc_directory)
                    r={'session_id':row['session_id'],'phase':row['effective_state'],
                       'verification':verdict,'receipt':l.status(row['receipt_id']),
                       'host_binding':'UNVERIFIED','real_host_bridge':'NOT_RUN'}
        else:raise ValueError('BRIDGE_OPERATOR_POLICY')
        print(json.dumps(r,sort_keys=True));return 0
    except BaseException:
        print(json.dumps({'status':'BLOCKED','reason':'BRIDGE_OPERATOR_POLICY_OR_STATE','host_binding':'UNVERIFIED'}));return 2
if __name__=='__main__':raise SystemExit(main())
