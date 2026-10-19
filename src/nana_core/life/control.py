"""Bounded private local IPC handled at the original Runtime's safe point.

No worker/second decision loop, TCP listener, credentials, arbitrary command or
Grant installation API. A local trusted application is the controller, never a
model. QQ/Bili submissions remain explicitly development shadow observations.
"""
import json
import os
import re
import socket
import stat
import struct
import time
import shutil
from pathlib import Path
from ..contracts import CoreError
from ..continuity.privacy import _json_object
from .surfaces import SurfaceObservation

LIMIT=16384

def dispatch(app,request):
    if type(request) is not dict:raise CoreError('CLOUD_TYPED_REQUEST_REQUIRED')
    op=request.get('operation')
    mutating=op in {'surface','backup'} or (op=='control' and request.get('command')=='resume')
    if mutating and shutil.disk_usage(app.home).free<app.config.min_free_disk_mb*1024*1024:raise CoreError('CLOUD_DISK_GUARD')
    if op=='surface' and set(request)=={'operation','observation'}:
        return app.surfaces.receive(SurfaceObservation.model_validate_json(json.dumps(request['observation'])))
    if op=='view' and set(request)=={'operation','view'}:
        if request['view']=='life':return app.board()
        if request['view']=='status':return app.status()
    if op=='continuity' and set(request)=={'operation','binding_id','tier'}:
        return app.surfaces.view(request['binding_id'],tier=request['tier']).model_dump(mode='json')
    if op=='control' and set(request)=={'operation','command'}:
        name=request['command']
        if name in {'pause','resume'}:return app.pause(name=='pause')
        if name in {'busy','available'}:return app.presence(name.upper())
        if name=='revoke':return app.revoke()
        if name=='stop':app.runtime.request_stop();return {'state':'STOP_REQUESTED'}
    if op=='forget' and set(request)=={'operation','memory_id'}:
        return app.forget(request['memory_id'])
    if op=='surface-enabled' and set(request)=={'operation','binding_id','enabled','expected_revision'}:
        from .config import update_config
        from .surfaces import SurfaceSession
        if type(request['enabled']) is not bool or type(request['expected_revision']) is not int:raise CoreError('CLOUD_SETTING_TYPE_INVALID')
        if request['binding_id'] not in {b.binding_id for b in app.config.surface_bindings}:raise CoreError('SURFACE_DISABLED_OR_UNBOUND')
        bindings=tuple(b.model_copy(update={'enabled':request['enabled']}) if b.binding_id==request['binding_id'] else b for b in app.config.surface_bindings)
        app.config=update_config(app.home,app.config.model_copy(update={'surface_bindings':bindings,'revision':request['expected_revision']+1}),expected_revision=request['expected_revision'])
        app.surfaces=SurfaceSession(app,app.config.surface_bindings)
        return {'host_config_revision':app.config.revision,'subject_state_changed':False}
    if op=='backup' and set(request)=={'operation','name'}:
        if type(request['name']) is not str or not re.fullmatch('[a-z][a-z0-9_-]{0,63}',request['name']):raise CoreError('CLOUD_BACKUP_NAME_INVALID')
        from .cloud import backup
        return backup(app.runtime.store,app.home/'backups'/(request['name']+'.db'))
    if op=='review-share' and set(request)=={'operation','cycle_id','binding_id'}:
        return app.shared.review(request['cycle_id'],request['binding_id'])
    raise CoreError('CLOUD_OPERATION_DENIED')


class ControlServer:
    def __init__(self,app):
        self.app=app;self.path=app.home/'control.sock'
        if self.path.exists() or self.path.is_symlink():
            s=self.path.lstat()
            if not stat.S_ISSOCK(s.st_mode) or s.st_uid!=os.getuid():raise CoreError('CLOUD_CONTROL_PATH_DENIED')
            # Runtime lease and exclusive Store lock have already been acquired;
            # only now is an old owned socket known to belong to a stopped owner.
            self.path.unlink()
        self.socket=socket.socket(socket.AF_UNIX)
        self.socket.bind(str(self.path));self.path.chmod(0o600);self.socket.listen(4);self.socket.setblocking(False)
        self.inode=self.path.lstat().st_ino
    def poll(self):
        try:conn,_=self.socket.accept()
        except BlockingIOError:return False
        with conn:
            conn.settimeout(.2)
            try:
                _,uid,_=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                if uid!=os.getuid():raise CoreError('CLOUD_CONTROL_OWNER_REQUIRED')
                raw=b'';deadline=time.monotonic()+.5
                while b'\n' not in raw and len(raw)<=LIMIT:
                    if time.monotonic()>=deadline:raise CoreError('CLOUD_REQUEST_TIMEOUT')
                    part=conn.recv(4096)
                    if not part:break
                    raw+=part
                if len(raw)>LIMIT or not raw.endswith(b'\n'):raise CoreError('CLOUD_REQUEST_BOUND')
                req=json.loads(raw,object_pairs_hook=_json_object)
                result=dispatch(self.app,req)
                response={'ok':True,'result':result}
            except (CoreError,ValueError,OSError,TypeError,KeyError) as exc:
                response={'ok':False,'code':exc.code if isinstance(exc,CoreError) else 'CLOUD_REQUEST_REJECTED'}
            try:conn.sendall((json.dumps(response,ensure_ascii=False)+'\n').encode())
            except OSError:pass # lost response never authorizes replay
        return True
    def close(self):
        self.socket.close()
        try:
            if self.path.lstat().st_ino==self.inode:self.path.unlink()
        except FileNotFoundError:pass
    def __enter__(self):return self
    def __exit__(self,*unused):self.close()


def request(home,data,timeout=None):
    path=Path(home).absolute()/'control.sock';root=path.parent
    if root!=root.resolve() or root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o077:raise CoreError('CLOUD_PRIVATE_HOME_REQUIRED')
    row=path.lstat()
    if not stat.S_ISSOCK(row.st_mode) or row.st_uid!=os.getuid() or row.st_mode&0o077:raise CoreError('CLOUD_CONTROL_PATH_DENIED')
    raw=(json.dumps(data)+'\n').encode()
    if len(raw)>LIMIT:raise CoreError('CLOUD_REQUEST_BOUND')
    if timeout is None:
        from .config import load_config
        timeout=max(5,2*load_config(root).provider_timeout_ms/1000+2)
    from ..presence.cli import status
    current=status(root/'subject/self.db')
    if not current.get('runtime_active'):raise CoreError('CLOUD_RUNTIME_NOT_CURRENT')
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(timeout)
        try:sock.connect(str(path))
        except OSError:raise CoreError('CLOUD_CONTROL_PRE_DISPATCH_UNAVAILABLE') from None
        pid,uid,_=struct.unpack('3i',sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if uid!=os.getuid() or pid!=current['lease']['pid'] or path.lstat().st_ino!=row.st_ino:raise CoreError('CLOUD_CONTROL_OWNER_REQUIRED')
        try:
            sock.sendall(raw);reply=b''
            while b'\n' not in reply and len(reply)<=262144:
                part=sock.recv(4096)
                if not part:break
                reply+=part
        except OSError:raise CoreError('CLOUD_COMPLETION_UNKNOWN_NO_RETRY') from None
    if len(reply)>262144:raise CoreError('CLOUD_RESPONSE_BOUND')
    try:return json.loads(reply,object_pairs_hook=_json_object)
    except ValueError:raise CoreError('CLOUD_RESPONSE_UNKNOWN_NO_RETRY') from None
