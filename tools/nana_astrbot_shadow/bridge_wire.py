"""Shared stdlib-only UDS contract; copied byte-identically into the plugin ZIP.

There is one message kind: observe metadata. No RPC/command/pickle/TCP support.
All IDs on the wire are scoped HMACs. Session secrets are NEVER evidence output.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import struct
from datetime import datetime,timezone,timedelta

MAX_FRAME=4096
SOURCE='astrbot_on_decorating_result'
HEX=re.compile(r'[0-9a-f]{64}\Z')
RID=re.compile(r'r04-[0-9a-f]{32}\Z')
LABEL=re.compile(r'[a-zA-Z][a-zA-Z0-9_.-]{0,47}\Z')
BAD=re.compile(r'(?:sk-|gh[pousr]_|github_pat_|Bearer |eyJ|token|cookie|session)',re.I)
METADATA_KEYS={'platform','type','event_id','timestamp','conversation_hash','sender_hash','event_source','synthetic','probe_id'}
ENVELOPE_KEYS={'schema_version','session_id','session_nonce','store_binding','receipt_id','metadata','mac'}
CONFIG_KEYS={'schema_version','session_id','session_nonce','store_binding','receipt_id','socket_path','socket_device',
             'socket_inode','server_pid','server_fingerprint','client_pid','client_fingerprint','uid','hash_scope',
             'hash_key','wire_key','expires_at','trust_domain','platform_scope','event_type_scope','conversation_hash','sender_hash'}

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(value):return hashlib.sha256(value if type(value) is bytes else canonical(value).encode()).hexdigest()
def stamp(value):
    if type(value) is not str or len(value)>40:raise ValueError('WIRE_TIME')
    t=datetime.fromisoformat(value)
    if t.tzinfo is None or t.utcoffset()!=timedelta(0) or t.isoformat()!=value:raise ValueError('WIRE_UTC')
    return t

def validate_metadata(m,rid):
    if type(m) is not dict or set(m)!=METADATA_KEYS:raise ValueError('WIRE_FIELDS')
    for key in ('platform','type'):
        v=m[key]
        if type(v) is not str or not LABEL.fullmatch(v) or BAD.search(v):raise ValueError('WIRE_LABEL')
    for key in ('event_id','conversation_hash','sender_hash'):
        if type(m[key]) is not str or not HEX.fullmatch(m[key]):raise ValueError('WIRE_HASH')
    stamp(m['timestamp'])
    if m['event_source']!=SOURCE or m['synthetic'] is not False or m['probe_id']!='nana-probe-'+rid:raise ValueError('WIRE_SOURCE')
    return m

def scoped_hash(scope,key,kind,value):
    if type(value) is not str or not 1<=len(value)<=256:raise ValueError('WIRE_ID')
    msg=b''.join(len(p.encode()).to_bytes(4,'big')+p.encode() for p in (scope,kind,value))
    return hmac.new(key,msg,hashlib.sha256).hexdigest()

def project_raw(raw,config):
    if type(raw) is not dict or set(raw)!={'platform','type','event_id','timestamp','conversation_id','sender_id'}:raise ValueError('WIRE_RAW_FIELDS')
    key=bytes.fromhex(config['hash_key']);scope=config['hash_scope']
    m={'platform':raw['platform'],'type':raw['type'],'event_id':scoped_hash(scope,key,'event_id',raw['event_id']),
       'timestamp':raw['timestamp'],'conversation_hash':scoped_hash(scope,key,'conversation_id',raw['conversation_id']),
       'sender_hash':scoped_hash(scope,key,'sender_id',raw['sender_id']),
       'event_source':SOURCE,'synthetic':False,'probe_id':'nana-probe-'+config['receipt_id']}
    return validate_metadata(m,config['receipt_id'])

def envelope(metadata,config):
    validate_metadata(metadata,config['receipt_id'])
    obj={'schema_version':1,'session_id':config['session_id'],'session_nonce':config['session_nonce'],
         'store_binding':config['store_binding'],'receipt_id':config['receipt_id'],'metadata':metadata}
    obj['mac']=hmac.new(bytes.fromhex(config['wire_key']),canonical(obj).encode(),hashlib.sha256).hexdigest()
    return obj

def verify_envelope(obj,config):
    if type(obj) is not dict or set(obj)!=ENVELOPE_KEYS or type(obj['schema_version']) is not int or obj['schema_version']!=1:raise ValueError('WIRE_SCHEMA')
    for key in ('session_id','session_nonce','store_binding','receipt_id'):
        if type(obj[key]) is not str or obj[key]!=config[key]:raise ValueError('WIRE_SESSION_SCOPE')
    validate_metadata(obj['metadata'],config['receipt_id'])
    body={k:v for k,v in obj.items() if k!='mac'}
    mac=hmac.new(bytes.fromhex(config['wire_key']),canonical(body).encode(),hashlib.sha256).hexdigest()
    if type(obj['mac']) is not str or not hmac.compare_digest(obj['mac'],mac):raise ValueError('WIRE_MAC')
    return obj['metadata']

def frame(obj):
    data=canonical(obj).encode()
    if not 0<len(data)<=MAX_FRAME:raise ValueError('WIRE_SIZE')
    return struct.pack('!I',len(data))+data

def decode(data):
    if type(data) is not bytes or not 0<len(data)<=MAX_FRAME:raise ValueError('WIRE_SIZE')
    obj=json.loads(data.decode('utf-8'))
    if canonical(obj).encode()!=data:raise ValueError('WIRE_NONCANONICAL')
    return obj

async def read_frame(reader,timeout=.2):
    import asyncio
    async def receive():
        size=struct.unpack('!I',await reader.readexactly(4))[0]
        if not 0<size<=MAX_FRAME:raise ValueError('WIRE_SIZE')
        return decode(await reader.readexactly(size))
    return await asyncio.wait_for(receive(),timeout)

def private_directory(path):
    p=Path(os.path.abspath(path))
    if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('WIRE_SYMLINK')
    st=p.stat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o700:raise ValueError('WIRE_DIRECTORY')
    return p

def load_config(path,*,directory=None):
    p=Path(path)
    if directory is None:
        with DirectoryFence(p.parent) as fence:return decode_config(fence.read(p.name,8192))
    if directory.path!=Path(os.path.abspath(p.parent)):raise ValueError('WIRE_DIRECTORY_SCOPE')
    return decode_config(directory.read(p.name,8192))

def decode_config(data):
    c=json.loads(data)
    if type(c) is not dict or set(c)!=CONFIG_KEYS or canonical(c).encode()+b'\n'!=data:raise ValueError('WIRE_CONFIG_SCHEMA')
    if type(c['schema_version']) is not int or c['schema_version']!=1:raise ValueError('WIRE_CONFIG_SCHEMA')
    for key in ('session_nonce','store_binding','hash_key','wire_key','server_fingerprint','client_fingerprint','conversation_hash','sender_hash'):
        if type(c[key]) is not str or not HEX.fullmatch(c[key]):raise ValueError('WIRE_CONFIG_HASH')
    if type(c['receipt_id']) is not str or not RID.fullmatch(c['receipt_id']):raise ValueError('WIRE_RECEIPT')
    if type(c['session_id']) is not str or not re.fullmatch('[0-9a-f]{32}',c['session_id']):raise ValueError('WIRE_SESSION')
    for key in ('socket_device','socket_inode','server_pid','client_pid','uid'):
        if type(c[key]) is not int or c[key]<0:raise ValueError('WIRE_CONFIG_INTEGER')
    if not LABEL.fullmatch(c['hash_scope']) or c['trust_domain'] not in ('PRODUCTION','FIXTURE'):raise ValueError('WIRE_CONFIG_DOMAIN')
    for k in ('platform_scope','event_type_scope'):
        if type(c[k]) is not str or not LABEL.fullmatch(c[k]) or BAD.search(c[k]):raise ValueError('WIRE_CONFIG_LABEL')
    stamp(c['expires_at'])
    p=Path(c['socket_path'])
    if not p.is_absolute() or len(os.fsencode(p))>100 or p.name!='bridge.sock':raise ValueError('WIRE_SOCKET_PATH')
    return c

def process_fingerprint(pid):
    if type(pid) is not int or pid<=0:raise ValueError('WIRE_PID')
    # Process start time only, not cmdline/env/credentials.
    text=Path('/proc')/str(pid)/'stat'
    start=text.read_text().rsplit(')',1)[1].split()[19]
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    return sha([pid,start,boot])

def validate_socket(c,*,directory=None):
    p=Path(c['socket_path']);private_directory(p.parent)
    if directory is not None and directory.path!=p.parent:raise ValueError('WIRE_DIRECTORY_SCOPE')
    st=directory.entry(p.name) if directory is not None else p.lstat()
    if not stat.S_ISSOCK(st.st_mode) or st.st_uid!=c['uid'] or stat.S_IMODE(st.st_mode)!=0o600:raise ValueError('WIRE_SOCKET_MODE')
    if (st.st_dev,st.st_ino)!=(c['socket_device'],c['socket_inode']):raise ValueError('WIRE_SOCKET_FINGERPRINT')
    if process_fingerprint(c['server_pid'])!=c['server_fingerprint']:raise ValueError('WIRE_STALE_SERVER')


def install_process_deadline(seconds):
    """Only isolated foreground worker: fixed hard exit after shutdown grace.

    Never called by the client/plugin. No process-ID/command parameter.
    """
    import signal,sys
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):raise ValueError('BRIDGE_STARTUP_ISOLATION')
    if type(seconds) not in (int,float) or not 0<seconds<=605:raise ValueError('BRIDGE_HARD_DEADLINE')
    previous=signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM,lambda *_:os._exit(124))
    signal.setitimer(signal.ITIMER_REAL,seconds)
    return previous


class DirectoryFence:
    """Owned 0700 directory descriptor + inode, not a reusable path assertion.

    All sidecar operations are relative to this descriptor. A swapped path is
    rejected; cleanup never follows the replacement directory. Unlink first
    detaches a filename, then checks its inode, preventing deletion of a raced
    replacement. Conflicting foreign objects are preserved, never overwritten.
    This is not a defense against root/authorized PID memory modification.
    """
    def __init__(self,path):
        self.path=private_directory(path)
        self.fd=os.open(self.path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        st=os.fstat(self.fd);self.identity=(st.st_dev,st.st_ino);self.owned={};self._pins={}
        try:self.check()
        except BaseException:self.close();raise

    def check(self):
        if self.fd is None:raise ValueError('WIRE_DIRECTORY_CLOSED')
        p=private_directory(self.path);st=p.stat();opened=os.fstat(self.fd)
        if (st.st_dev,st.st_ino)!=self.identity or (opened.st_dev,opened.st_ino)!=self.identity:
            raise ValueError('WIRE_DIRECTORY_DRIFT')
        if opened.st_uid!=os.getuid() or stat.S_IMODE(opened.st_mode)!=0o700:raise ValueError('WIRE_DIRECTORY_DRIFT')
        return self

    def close(self):
        for pin in self._pins.values():os.close(pin)
        self._pins.clear()
        if self.fd is not None:os.close(self.fd);self.fd=None

    def __enter__(self):return self
    def __exit__(self,*exc):self.close()

    def _name(self,name):
        if type(name) is not str or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}',name) or name in ('.','..'):
            raise ValueError('WIRE_RELATIVE_FILE')
        return name

    def entry(self,name):
        self.check();return os.stat(self._name(name),dir_fd=self.fd,follow_symlinks=False)

    def read(self,name,maximum=8192):
        self.check();name=self._name(name)
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=self.fd)
        try:
            before=os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid()
                or stat.S_IMODE(before.st_mode)!=0o600 or before.st_nlink!=1 or before.st_size>maximum):
                raise ValueError('WIRE_CONFIG_FILE')
            with os.fdopen(fd,'rb',closefd=False) as stream:data=stream.read(maximum+1)
            after=os.fstat(fd);current=self.entry(name)
            if (len(data)>maximum or (before.st_dev,before.st_ino)!=(current.st_dev,current.st_ino)
                or (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns)):
                raise ValueError('WIRE_CONFIG_DRIFT')
            # Pin the validated inode through later identity-based operations.
            # Without a live descriptor unlink/recreate can reuse the same ino.
            identity=(after.st_dev,after.st_ino)
            if identity not in self._pins:self._pins[identity]=fd;fd=None
            return data
        finally:
            if fd is not None:os.close(fd)

    def _detach(self,name,expected,*,anchored=False):
        import secrets
        if anchored:
            st=os.fstat(self.fd)
            if (st.st_dev,st.st_ino)!=self.identity or st.st_uid!=os.getuid():raise ValueError('WIRE_DIRECTORY_DRIFT')
        else:self.check()
        name=self._name(name)
        quarantine='.fence-'+secrets.token_hex(16)
        # An unpredictable, reserved filename in our retained directory.
        fd=os.open(quarantine,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
        os.close(fd)
        try:os.rename(name,quarantine,src_dir_fd=self.fd,dst_dir_fd=self.fd)
        except BaseException:
            os.unlink(quarantine,dir_fd=self.fd);raise
        st=os.stat(quarantine,dir_fd=self.fd,follow_symlinks=False)
        if (st.st_dev,st.st_ino)!=expected:
            # link is NOREPLACE. Preserve a conflicting inode even under a race.
            try:
                os.link(quarantine,name,src_dir_fd=self.fd,dst_dir_fd=self.fd,follow_symlinks=False)
                os.unlink(quarantine,dir_fd=self.fd)
            except OSError:pass
            raise ValueError('WIRE_ENTRY_DRIFT')
        return quarantine

    def unlink_owned(self,name,expected=None,*,anchored=False):
        if not anchored:self.check()
        name=self._name(name)
        expected=expected or self.owned.get(name)
        if expected is None:raise ValueError('WIRE_ENTRY_NOT_OWNED')
        try:detached=self._detach(name,expected,anchored=anchored)
        except FileNotFoundError:return False
        os.unlink(detached,dir_fd=self.fd);os.fsync(self.fd)
        self.owned.pop(name,None)
        return True

    def _publish(self,temporary,name):
        # Linux-only fixed renameat2(NOREPLACE). A hardlink publish briefly has
        # nlink2 and can be observed/rejected as readiness by another process.
        import ctypes
        libc=ctypes.CDLL(None,use_errno=True)
        call=getattr(libc,'renameat2',None)
        if call is None:raise ValueError('WIRE_ATOMIC_PUBLISH_UNAVAILABLE')
        call.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint)
        call.restype=ctypes.c_int
        if call(self.fd,temporary.encode(),self.fd,name.encode(),1)!=0:
            raise OSError(ctypes.get_errno(),'WIRE_ATOMIC_PUBLISH')

    def write(self,name,value,*,replace=False):
        import secrets
        self.check();name=self._name(name)
        data=(canonical(value)+'\n').encode()
        if len(data)>65536:raise ValueError('WIRE_SIDECAR_SIZE')
        temporary='.write-'+secrets.token_hex(16)
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=self.fd)
        detached=None
        try:
            with os.fdopen(fd,'wb',closefd=False) as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            self.check()
            if replace:
                expected=self.owned.get(name)
                if expected is None:raise ValueError('WIRE_ENTRY_NOT_OWNED')
                detached=self._detach(name,expected)
            # Never overwrite an object which appeared during construction.
            self._publish(temporary,name)
            st=self.entry(name);opened=os.fstat(fd)
            if (st.st_dev,st.st_ino)!=(opened.st_dev,opened.st_ino):raise ValueError('WIRE_ENTRY_DRIFT')
            self.owned[name]=(opened.st_dev,opened.st_ino)
            self._pins[self.owned[name]]=fd;fd=None
            if detached:os.unlink(detached,dir_fd=self.fd)
            os.fsync(self.fd)
            return self.owned[name]
        finally:
            if fd is not None:os.close(fd)
            try:os.unlink(temporary,dir_fd=self.fd)
            except FileNotFoundError:pass
