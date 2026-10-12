"""AstrBot side: stdlib metadata/HMAC/AF_UNIX only. No Core/SQLite/Pydantic imports."""
import asyncio
from datetime import datetime,timezone
import os
from pathlib import Path
import socket
import struct
from .bridge_wire import load_config,project_raw,envelope,frame,read_frame,validate_socket,process_fingerprint,stamp,DirectoryFence
from .message_hook_adapter import extract_scalar_metadata

class OneShotBridgeClient:
    def __init__(self,config_path,*,timeout=.15,logger=None):
        if not 0<timeout<=.5:raise ValueError('BRIDGE_CLIENT_DEADLINE')
        self._directory=DirectoryFence(Path(config_path).parent)
        try:
            self.__config=load_config(config_path,directory=self._directory)
            # Local IPC authentication NEVER conveys receipt authority.
            if self.__config['trust_domain']!='PRODUCTION':raise ValueError('FIXTURE_CLIENT_BIND_BLOCKED')
        except BaseException:
            self._directory.close();raise
        self.timeout,self._logger=timeout,logger
        self._attempted=False;self.active=True;self.last_status='IDLE'

    def _note(self,code):
        self.last_status=code
        try:
            if self._logger is not None:self._logger(code)
        except BaseException:pass

    async def on_decorating_result(self,event):
        writer=None
        try:
            c=self.__config
            if not self.active or self._attempted:self._note('DROP_SESSION_ATTEMPTED');return None
            if os.getpid()!=c['client_pid'] or process_fingerprint(os.getpid())!=c['client_fingerprint']:
                self._note('DROP_CLIENT_IDENTITY');return None
            if datetime.now(timezone.utc)>=stamp(c['expires_at']):self._note('DROP_SESSION_EXPIRED');return None
            raw=extract_scalar_metadata(event)
            m=project_raw(raw,c)
            if (m['platform']!=c['platform_scope'] or m['type']!=c['event_type_scope']
                or m['conversation_hash']!=c['conversation_hash'] or m['sender_hash']!=c['sender_hash']):
                self._note('DROP_SCOPE');return None
            # Set BEFORE connect/write: no implicit retries after ambiguous transport.
            self._attempted=True
            self._directory.check()
            validate_socket(c,directory=self._directory)
            async def exchange():
                nonlocal writer
                reader,writer=await asyncio.open_unix_connection(c['socket_path'])
                s=writer.get_extra_info('socket')
                pid,uid,gid=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                if pid!=c['server_pid'] or uid!=c['uid']:raise ValueError('BRIDGE_SERVER_PEER')
                validate_socket(c,directory=self._directory)
                writer.write(frame(envelope(m,c)));await writer.drain()
                response=await read_frame(reader,self.timeout)
                if (type(response) is not dict or set(response)!={'schema_version','session_id','status'}
                    or type(response['schema_version']) is not int or response['schema_version']!=1 or response['session_id']!=c['session_id']):raise ValueError('BRIDGE_REPLY')
                allowed={'SHADOW_BLOCKED','DROP_SESSION_USED','DROP_POLICY','UNKNOWN'}
                if response['status'] not in allowed:raise ValueError('BRIDGE_REPLY')
                return response['status']
            self._note(await asyncio.wait_for(exchange(),self.timeout))
        except asyncio.CancelledError:self._note('DROP_CANCELLED_UNKNOWN')
        except TimeoutError:self._note('UNKNOWN_IPC_COMPLETION')
        except BaseException:self._note('DROP_IPC_UNKNOWN')
        finally:
            if writer is not None:
                writer.close()
                try:await asyncio.wait_for(writer.wait_closed(),self.timeout)
                except BaseException:pass
        return None

    async def close(self):
        self.active=False;self._directory.close();return None
