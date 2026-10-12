"""Short-lived AF_UNIX server. One session/receipt; original single Store writer.

No generic methods, shell, external action, model or TCP listener. Production
trust pins unchanged/EMPTY. Fixture class is test-only, not an operator option.
"""
import asyncio
from datetime import datetime,timezone,timedelta
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import stat
import struct
from .bridge_wire import private_directory,process_fingerprint,verify_envelope,read_frame,frame,sha,decode_config
from .one_shot import ProductionTrustStore,FixtureTrustStore,utc
from .one_shot_ingress import OneShotSanitizer,OneShotCoreSink,OneShotObserver
from .one_shot_proof import collect,verify_first_real_message_shadow,ZERO_KEYS
from tools.nana_host_shadow.safety import private_file,canonical

class ShortLivedWorker:
    def __init__(self,directory,ipc_directory,receipt_id,*,client_pid,seconds=60,trust=None,checkpoint=None):
        if type(seconds) not in (int,float) or not 0<seconds<=600:raise ValueError('BRIDGE_WINDOW')
        self.directory=private_directory(directory);self.ipc=private_directory(ipc_directory)
        self.rid=receipt_id;self.client_pid=client_pid;self.seconds=seconds
        self.trust=trust if trust is not None else ProductionTrustStore()
        if type(self.trust) not in (ProductionTrustStore,FixtureTrustStore):raise ValueError('BRIDGE_TRUST_TYPE')
        self.checkpoint=checkpoint;self.observer=None;self.server=None;self.config=None
        self.stop_event=asyncio.Event();self.used=False;self.attempts=0;self.connections=set()
        self.limit=asyncio.Semaphore(100);self.lock=asyncio.Lock();self.core_recorded=False
        self._socket_identity=None;self._prepared=False

    def _prepare_on_writer(self):
        # R04 hash key/scope are the only domain; do not create another identity/store.
        from .one_shot_cli import operator_ledger
        if type(self.trust) is ProductionTrustStore:
            with operator_ledger(self.directory) as l:
                r,v=l.record(self.rid)
                if l.store.one('core_meta','r041.receipt_session:'+self.rid):raise ValueError('BRIDGE_SESSION_REPLAY')
                if v['state']!='ARMED' or not l._review_valid(r,v['review']):raise ValueError('BRIDGE_RECEIPT_NOT_ARMED_TRUSTED')
                key=json.loads(l.store.one('core_meta','r04.hash_key')['value_json'])
                scope=json.loads(l.store.one('core_meta','r04.hash_scope')['value_json'])
        else:
            # Fixture API needs the same persisted generated hash-domain rows.
            from nana_core.storage import Store
            with Store(self.directory/'observer-shadow.db') as store:
                from .one_shot import ReceiptLedger
                l=ReceiptLedger(store,self.trust);r,v=l.record(self.rid)
                if store.one('core_meta','r041.receipt_session:'+self.rid):raise ValueError('BRIDGE_SESSION_REPLAY')
                key=json.loads(store.one('core_meta','r04.hash_key')['value_json'])
                scope=json.loads(store.one('core_meta','r04.hash_scope')['value_json'])
        if scope!=r.hash_scope or v['state']!='ARMED' or not l._review_valid(r,v['review']):raise ValueError('BRIDGE_RECEIPT_SCOPE')
        now=datetime.now(timezone.utc)
        if now>=utc(r.expires_at) or utc(r.issued_at)>now+timedelta(seconds=2):raise ValueError('BRIDGE_RECEIPT_TIME')
        expires=min(utc(r.expires_at),now+timedelta(seconds=self.seconds))
        # Directory only has files owned by this new explicit session.
        if any(self.ipc.iterdir()):raise ValueError('BRIDGE_NEW_IPC_DIRECTORY_REQUIRED')
        s=OneShotSanitizer(scope=scope,hash_key=bytes.fromhex(key),receipt_id=self.rid)
        sink=OneShotCoreSink(self.directory,s,self.rid,trust=self.trust,checkpoint=self.checkpoint)
        self._sink=sink;ledger=sink.ledger()
        fence='r041.receipt_session:'+self.rid
        if ledger.store.one('core_meta',fence):raise ValueError('BRIDGE_SESSION_REPLAY')
        session_id=secrets.token_hex(16)
        self.config={'schema_version':1,'session_id':session_id,'session_nonce':secrets.token_hex(32),
           'store_binding':ledger.binding,'receipt_id':self.rid,'socket_path':str(self.ipc/'bridge.sock'),
           'socket_device':0,'socket_inode':0,'server_pid':os.getpid(),'server_fingerprint':process_fingerprint(os.getpid()),
           'client_pid':self.client_pid,'client_fingerprint':process_fingerprint(self.client_pid),'uid':os.getuid(),
           'hash_scope':scope,'hash_key':key,'wire_key':secrets.token_hex(32),'expires_at':expires.isoformat(),
           'trust_domain':ledger.trust.domain,'platform_scope':r.platform_scope,'event_type_scope':r.event_type_scope,
           'conversation_hash':r.conversation_hash,'sender_hash':r.sender_hash}
        with ledger.store.transaction('r041.session_claimed',{'receipt_id':self.rid,'session_id':session_id}) as tx:
            tx.put('core_meta',{'key':fence,'value_json':canonical({'session_id':session_id,'store_binding':ledger.binding,
                  'phase':'CLAIMED','expires_at':expires.isoformat(),
                  'pid':os.getpid(),'pid_fingerprint':self.config['server_fingerprint'],'ipc_hash':sha(str(self.ipc))})})
        return sink

    def _summary(self,phase):
        c=self.config
        return {'schema_version':1,'session_id':c['session_id'],'receipt_id':self.rid,'store_binding':c['store_binding'],
            'pid':c['server_pid'],'pid_fingerprint':c['server_fingerprint'],'uid':c['uid'],
            'socket_device':c['socket_device'],'socket_inode':c['socket_inode'],
            'socket_path':c['socket_path'],'expires_at':c['expires_at'],'trust_domain':c['trust_domain'],
            'phase':phase,'host_binding':'UNVERIFIED','real_host_bridge':'NOT_RUN','E12':'NOT_RUN'}

    async def serve(self):
        # One owned executor = R04 original FIFO Store worker. Preparation runs
        # on that same thread; no extra SQLite connection/writer lives alongside.
        from concurrent.futures import ThreadPoolExecutor
        executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='nana-short-shadow')
        loop=asyncio.get_running_loop()
        try:
            sink=await loop.run_in_executor(executor,self._prepare_on_writer)
            self._prepared=True
            # Reuse Observer, replace its still-empty thread before any work.
            self.observer=OneShotObserver(sink.sanitizer,sink,timeout=2)
            self.observer._worker.shutdown(wait=False);self.observer._worker=executor
            path=self.config['socket_path']
            if len(os.fsencode(path))>100:raise ValueError('BRIDGE_SOCKET_PATH_LENGTH')
            self.server=await asyncio.start_unix_server(self._handle,path=path,backlog=128,limit=8192)
            os.chmod(path,0o600)
            st=Path(path).lstat();self._socket_identity=(st.st_dev,st.st_ino)
            self.config.update(socket_device=st.st_dev,socket_inode=st.st_ino)
            decode_config((canonical(self.config)+'\n').encode())
            await loop.run_in_executor(executor,self._publish_on_writer)
            private_file(self.ipc/'client.json',self.config)
            private_file(self.ipc/'session.json',self._summary('RUNNING'))
            remaining=max(0,(utc(self.config['expires_at'])-datetime.now(timezone.utc)).total_seconds())
            try:await asyncio.wait_for(self.stop_event.wait(),remaining)
            except TimeoutError:pass
        finally:
            if self.server is not None:self.server.close();await self.server.wait_closed()
            tasks=list(self.connections)
            if tasks:
                done,pending=await asyncio.wait(tasks,timeout=2.5)
                for t in pending:t.cancel()
                if pending:await asyncio.gather(*pending,return_exceptions=True)
            # Evidence I/O may fail; each cleanup boundary must remain independent.
            # No exception in report writing is allowed to skip Store/thread/socket close.
            try:
                if self.observer is not None:
                    try:
                        summary=await loop.run_in_executor(executor,self._finish_on_writer)
                        private_file(self.ipc/'result.json',summary)
                    except BaseException:
                        try:private_file(self.ipc/'result.json',{'status':'UNKNOWN','host_binding':'UNVERIFIED'})
                        except BaseException:pass
            finally:
                try:
                    if self.observer is not None:await self.observer.close()
                    elif hasattr(self,'_sink'):await loop.run_in_executor(executor,self._sink.close)
                finally:
                    executor.shutdown(wait=False,cancel_futures=False)
                    if self._socket_identity is not None:
                        p=Path(self.config['socket_path'])
                        try:
                            st=p.lstat()
                            if stat.S_ISSOCK(st.st_mode) and (st.st_dev,st.st_ino)==self._socket_identity:p.unlink()
                        except OSError:pass
                    if self.config and self._prepared:
                        try:private_file(self.ipc/'session.json',self._summary('CLOSED'),replace=True)
                        except BaseException:pass
                        p=self.ipc/'client.json'
                        try:
                            if p.exists() and not p.is_symlink():p.unlink()
                        except OSError:pass

    async def _handle(self,reader,writer):
        task=asyncio.current_task();self.connections.add(task)
        status='DROP_POLICY'
        try:
            self.attempts+=1
            if self.attempts>128:self.stop_event.set();return
            async with self.limit:
                s=writer.get_extra_info('socket')
                pid,uid,gid=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                if uid!=self.config['uid'] or pid!=self.client_pid or process_fingerprint(pid)!=self.config['client_fingerprint']:
                    raise ValueError('BRIDGE_CLIENT_PEER')
                obj=await read_frame(reader,.2)
                m=verify_envelope(obj,self.config)
                # Do not consume a session attempt for mismatched R04 scope.
                c=self.config
                if (m['platform']!=c['platform_scope'] or m['type']!=c['event_type_scope']
                    or m['sender_hash']!=c['sender_hash'] or m['conversation_hash']!=c['conversation_hash']):raise ValueError('BRIDGE_METADATA_SCOPE')
                async with self.lock:
                    if self.used:status='DROP_SESSION_USED'
                    elif self.stop_event.is_set() or datetime.now(timezone.utc)>=utc(self.config['expires_at']):status='DROP_POLICY'
                    else:
                        self.used=True
                        await self.observer.callback_public(m)
                        last=self.observer.last_result
                        if last['status']=='RECORDED':status='SHADOW_BLOCKED';self.core_recorded=True
                        else:status='UNKNOWN'
                        # End bounded session after one eligible event; no reconnect
                        # can create another Core ingress. Retain already accepted peers.
                        self.stop_event.set()
            writer.write(frame({'schema_version':1,'session_id':self.config['session_id'],'status':status}))
            await asyncio.wait_for(writer.drain(),.2)
        except asyncio.CancelledError:pass
        except BaseException:pass  # never input/exception repr/traceback
        finally:
            writer.close()
            try:await asyncio.wait_for(writer.wait_closed(),.2)
            except BaseException:pass
            self.connections.discard(task)

    def _publish_on_writer(self):
        l=self._sink.ledger();key='r041.receipt_session:'+self.rid
        value=json.loads(l.store.one('core_meta',key)['value_json'])
        value.update(phase='BOUND',socket_device=self.config['socket_device'],socket_inode=self.config['socket_inode'])
        with l.store.transaction('r041.session_bound',{'session_id':self.config['session_id']}) as tx:
            tx.put('core_meta',{'key':key,'value_json':canonical(value)})

    def _finish_on_writer(self):
        l=self._sink.ledger()
        report=collect(l,self.rid,observer_callback_received=self.used,sanitizer_accepted=self.core_recorded,
                       noncore_zero={k:0 for k in ZERO_KEYS} if type(self.trust) is FixtureTrustStore else None)
        verdict=verify_first_real_message_shadow(report,l)
        fence='r041.receipt_session:'+self.rid
        with l.store.transaction('r041.session_closed',{'session_id':self.config['session_id']}) as tx:
            tx.put('core_meta',{'key':fence,'value_json':canonical({'session_id':self.config['session_id'],
                'store_binding':l.binding,'phase':'CLOSED','expires_at':self.config['expires_at'],
                'pid':self.config['server_pid'],'pid_fingerprint':self.config['server_fingerprint'],'ipc_hash':sha(str(self.ipc)),
                'socket_device':self.config['socket_device'],'socket_inode':self.config['socket_inode']})})
        return {'status':verdict['status'],'proof':report,'verification':verdict,'receipt':l.status(self.rid),
                'session_id':self.config['session_id'],'frames_seen':self.attempts,
                'external_execute':False,'host_binding':'UNVERIFIED','real_host_bridge':'NOT_RUN','E12':'NOT_RUN'}
