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

def load_config(path):
    p=Path(path);private_directory(p.parent)
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o600 or st.st_nlink!=1 or st.st_size>8192:raise ValueError('WIRE_CONFIG_FILE')
        with os.fdopen(fd,'rb',closefd=False) as f:data=f.read(8193)
        c=decode_config(data)
    finally:os.close(fd)
    return c

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
    return sha([pid,start])

def validate_socket(c):
    p=Path(c['socket_path']);private_directory(p.parent)
    st=p.lstat()
    if not stat.S_ISSOCK(st.st_mode) or st.st_uid!=c['uid'] or stat.S_IMODE(st.st_mode)!=0o600:raise ValueError('WIRE_SOCKET_MODE')
    if (st.st_dev,st.st_ino)!=(c['socket_device'],c['socket_inode']):raise ValueError('WIRE_SOCKET_FINGERPRINT')
    if process_fingerprint(c['server_pid'])!=c['server_fingerprint']:raise ValueError('WIRE_STALE_SERVER')
