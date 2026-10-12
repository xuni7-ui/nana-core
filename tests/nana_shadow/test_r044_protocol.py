"""Frame mutation/fragmentation/EOF/slow-sender/peer-identity qualification."""
import asyncio
import copy
import json
import os
import struct
import time
import pytest
from test_r041_bridge import fixture,ready,send
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.bridge_wire import frame,envelope,project_raw,read_frame,MAX_FRAME,verify_envelope
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore
from r044_helpers import readback

@pytest.mark.parametrize('mutation',['zero','huge','invalid_utf8','duplicate_keys','newline','null','deep',
    'wrong_nonce','old_mac','right_mac_wrong_session','wrong_store','wrong_receipt','body','profile','attachment',
    'prompt','history','nul','unknown_method'])
def test_protocol_mutations_never_consume(tmp_path,mutation):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=1,trust=FixtureTrustStore())
        task,c=await ready(w);obj=envelope(project_raw(raw,c),c)
        if mutation=='zero':encoded=b'\0'*4
        elif mutation=='huge':encoded=struct.pack('!I',MAX_FRAME+1)
        elif mutation=='invalid_utf8':encoded=struct.pack('!I',2)+b'\xff\xfe'
        elif mutation=='duplicate_keys':
            data=b'{"schema_version":1,"schema_version":1}';encoded=struct.pack('!I',len(data))+data
        elif mutation=='newline':encoded=frame(obj)+b'\n' # see below: mutate INSIDE canonical frame
        elif mutation=='null':encoded=frame(None)
        elif mutation=='deep':
            data=b'['*1500+b'0'+b']'*1500;encoded=struct.pack('!I',len(data))+data
        else:
            if mutation=='wrong_nonce':obj['session_nonce']='0'*64
            elif mutation=='old_mac':obj['mac']='0'*64
            elif mutation=='right_mac_wrong_session':
                obj=envelope(project_raw(raw,c),{**c,'session_id':'0'*32})
            elif mutation=='wrong_store':obj['store_binding']='0'*64
            elif mutation=='wrong_receipt':obj['receipt_id']='r04-'+'0'*32
            elif mutation=='nul':obj['metadata']['platform']='dev\0'
            elif mutation=='unknown_method':obj['method']='generic.execute'
            else:obj['metadata'][mutation]='PRIVATE-SYNTHETIC-CANARY'
            encoded=frame(obj)
        if mutation=='newline':
            data=encoded[4:];encoded=struct.pack('!I',len(data))+data
        try:await send(c,encoded=encoded)
        except (asyncio.IncompleteReadError,ConnectionError):pass
        w.stop_event.set();await task
    asyncio.run(run())
    status,count,_=readback(root,r.receipt_id);assert status['uses']==count==0

@pytest.mark.parametrize('kind',['byte_fragments','early_eof','slowloris','duplicate_frames'])
def test_stream_boundaries_are_bounded_and_never_double_ingress(tmp_path,kind):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=1,trust=FixtureTrustStore())
        task,c=await ready(w);data=frame(envelope(project_raw(raw,c),c))
        reader,writer=await asyncio.open_unix_connection(c['socket_path'])
        start=time.monotonic()
        try:
            if kind=='byte_fragments':
                for byte in data:writer.write(bytes([byte]))
                await writer.drain();assert (await read_frame(reader,.8))['status']=='SHADOW_BLOCKED'
            elif kind=='duplicate_frames':
                writer.write(data+data);await writer.drain()
                assert (await read_frame(reader,.8))['status']=='SHADOW_BLOCKED'
                # One connection/one observation; second frame discarded at close.
            elif kind=='early_eof':
                writer.write(data[:12]);await writer.drain();writer.write_eof()
                with pytest.raises(asyncio.IncompleteReadError):await read_frame(reader,.8)
            else:
                writer.write(data[:4]);await writer.drain();await asyncio.sleep(.22)
                with pytest.raises(asyncio.IncompleteReadError):await read_frame(reader,.8)
            assert time.monotonic()-start<1
        finally:
            writer.close()
            try:await writer.wait_closed()
            except ConnectionError:pass
            w.stop_event.set();await task
    asyncio.run(run());status,count,_=readback(root,r.receipt_id)
    assert status['uses']==count==int(kind in ('byte_fragments','duplicate_frames'))
