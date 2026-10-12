"""Actual SIGKILL, fresh independent read-only process per kill point."""
import asyncio
from datetime import datetime,timezone,timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
import pytest
from r044_helpers import fixture
from tools.nana_astrbot_shadow.one_shot import review_document
from tools.nana_host_shadow.safety import canonical,digest,private_file
from tools.nana_astrbot_shadow.bridge_wire import load_config,project_raw,envelope,frame,read_frame

POINTS=[('before_store_init','init'),('r04.store_bound:after','init'),('r04.hash_domain_initialized:inside','init'),
 ('r04.receipt_created:inside','receipt'),('r04.receipt_created:after','receipt'),
 ('r04.receipt_reviewed:before','receipt'),('r04.receipt_reviewed:after','receipt'),
 ('r04.receipt_armed:inside','receipt'),('r04.receipt_armed:after','receipt'),
 ('r041.session_claimed:before','worker'),('r041.session_claimed:inside','worker'),('r041.session_claimed:after','worker'),
 ('socket_bind:before','worker'),('socket_bind:after','worker'),
 ('session.json:before','worker'),('session.json:after','worker'),('client.json:before','worker'),('client.json:after','worker'),
 ('first_frame:before','worker'),('before_consume','worker'),('before_consume_commit','worker'),
 ('after_consume_commit','worker'),('before_evidence','worker'),('after_evidence','worker'),
 ('core_complete:before','worker'),('core_complete:after','worker'),('cleanup:before','worker'),
 ('socket_unlink:before','worker'),('socket_unlink:after','worker'),('verify:before','worker'),
 ('r041.session_closed:inside','worker'),('r041.session_closed:after','worker')]

CODE=r'''
import asyncio,json,os,signal,sys,time
from pathlib import Path
from contextlib import contextmanager
from nana_core.storage import Store
from tools.nana_astrbot_shadow.one_shot import ReceiptLedger,FixtureTrustStore,parse_receipt,review_document
from tools.nana_astrbot_shadow.one_shot_cli import initialize
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.bridge_wire import DirectoryFence
import tools.nana_astrbot_shadow.bridge_worker as mod
root,ipc,rid,client,point,marker,group,receipt=sys.argv[1:]
def block(p):
 if p==point:
  Path(marker).write_text(p)
  while True:time.sleep(.005)
original_tx=Store.transaction
@contextmanager
def transaction(self,kind,*a,**kw):
 block(kind+':before')
 with original_tx(self,kind,*a,**kw) as tx:
  yield tx
  block(kind+':inside')
 block(kind+':after')
Store.transaction=transaction
original_complete=ReceiptLedger.complete
def complete(self,*a,**kw):
 block('core_complete:before');r=original_complete(self,*a,**kw);block('core_complete:after');return r
ReceiptLedger.complete=complete
original_write=ShortLivedWorker._write_sidecar
def write(self,name,*a,**kw):
 block(name+':before');result=original_write(self,name,*a,**kw);block(name+':after');return result
ShortLivedWorker._write_sidecar=write
original_bind=asyncio.start_unix_server
async def bind(*a,**kw):
 block('socket_bind:before');r=await original_bind(*a,**kw);block('socket_bind:after');return r
asyncio.start_unix_server=bind
original_handle=ShortLivedWorker._handle
async def handle(self,*a):block('first_frame:before');return await original_handle(self,*a)
ShortLivedWorker._handle=handle
original_finish=ShortLivedWorker._finish_on_writer
def finish(self):block('cleanup:before');return original_finish(self)
ShortLivedWorker._finish_on_writer=finish
original_unlink=DirectoryFence.unlink_owned
def unlink(self,name,*a,**kw):
 if name=='bridge.sock':block('socket_unlink:before')
 result=original_unlink(self,name,*a,**kw)
 if name=='bridge.sock':block('socket_unlink:after')
 return result
DirectoryFence.unlink_owned=unlink
original_verify=mod.verify_first_real_message_shadow
def verify(*a,**kw):block('verify:before');return original_verify(*a,**kw)
mod.verify_first_real_message_shadow=verify
if group=='init':block('before_store_init');initialize(root)
elif group=='receipt':
 with Store(Path(root)/'observer-shadow.db') as store:
  l=ReceiptLedger(store,FixtureTrustStore());r=parse_receipt(Path(receipt).read_text())
  l.create(r);l.review(rid,review_document(r));l.arm(rid)
else:
 async def run():
  w=ShortLivedWorker(root,ipc,rid,client_pid=int(client),seconds=10,trust=FixtureTrustStore(),checkpoint=block)
  asyncio.get_running_loop().add_signal_handler(signal.SIGTERM,w.stop_event.set)
  await w.serve()
 asyncio.run(run())
'''

READER=r'''
import json,sys
from pathlib import Path
from tools.nana_astrbot_shadow.one_shot_cli import ReadOnlyStoreView
from tools.nana_astrbot_shadow.one_shot import ReceiptLedger,FixtureTrustStore
root,rid=sys.argv[1:];path=Path(root)/'observer-shadow.db'
r={'classification':'SAFE_RETRY','uses':0,'observations':0,'identity_id':None,'session_reserved':False,'state':None,'writes':0}
if path.exists():
 s=ReadOnlyStoreView(path)
 try:
  ids=s.all('identities');r['identity_id']=ids[0]['identity_id'] if ids else None
  r['observations']=len([e for e in s.all('events') if e['kind']=='observation.received'])
  r['zero_counts']={t:len(s.all(t)) for t in ('actions','attempts','grants','budgets','strategies')}
  for e in s.all('events'):json.loads(e['data_json'])
  if not s.one('core_meta','r04.hash_key'):r['classification']='UNKNOWN_NEEDS_REVIEW'
  else:
   l=ReceiptLedger(s,FixtureTrustStore());f=s.one('core_meta','r041.receipt_session:'+rid)
   r['session_reserved']=f is not None
   row=s.one('core_meta','r04.receipt:'+rid)
   if row:
    st=l.status(rid);r.update(uses=st['uses'],state=st['state'],completion=st['completion'])
    if st['uses']:r['classification']='TERMINAL_CONSUMED' if st['core_recorded'] else 'UNKNOWN_NEEDS_REVIEW'
    elif f:r['classification']='UNKNOWN_NEEDS_REVIEW'
   elif f:r['classification']='BLOCKED'
 except BaseException:r['classification']='BLOCKED'
 finally:s.close()
print(json.dumps(r,sort_keys=True))
'''


def wait(p,path,seconds=6):
    end=time.monotonic()+seconds
    while not path.exists() and p.poll() is None and time.monotonic()<end:time.sleep(.005)
    assert path.exists(),'CHECKPOINT_NOT_REACHED'

@pytest.mark.parametrize('point,group',POINTS)
def test_sigkill_matrix_reopened_state_never_revives_permission(tmp_path,point,group):
    if group=='init':
        root=tmp_path/'data';root.mkdir(mode=0o700);ipc=tmp_path/'ipc';ipc.mkdir(mode=0o700)
        rid='r04-'+uuid4().hex;raw=None;receipt=tmp_path/'unused';identity=None
    else:
        root,ipc,r,raw=fixture(tmp_path/'case',armed=(group=='worker'))
        # r044 helper owns the nested private directory, unlike old fixture helper.
        rid=r.receipt_id;receipt=tmp_path/'receipt.json'
        if group=='receipt':
            r=r.model_copy(update={'receipt_id':'r04-'+uuid4().hex})
            r=r.model_copy(update={'review_receipt_digest':digest(review_document(r))});rid=r.receipt_id
        receipt.write_text(r.canonical());receipt.chmod(0o600)
        pstate=json.loads(subprocess.check_output([sys.executable,'-c',READER,str(root),rid],text=True));identity=pstate['identity_id']
    marker=tmp_path/'checkpoint'
    p=subprocess.Popen([sys.executable,'-c',CODE,str(root),str(ipc),rid,str(os.getpid()),point,str(marker),group,str(receipt)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    start=time.monotonic()
    try:
        # Wait for either an early checkpoint or published client capability.
        end=time.monotonic()+6
        while not marker.exists() and not (ipc/'client.json').exists() and p.poll() is None and time.monotonic()<end:time.sleep(.005)
        if not marker.exists():
            assert (ipc/'client.json').exists() and group=='worker'
            c=load_config(ipc/'client.json')
            async def deliver():
                reader,writer=await asyncio.open_unix_connection(c['socket_path'])
                writer.write(frame(envelope(project_raw(raw,c),c)));await writer.drain()
                for _ in range(1200):
                    if marker.exists():break
                    if p.poll() is not None:break
                    await asyncio.sleep(.005)
                assert marker.exists(),'CHECKPOINT_NOT_REACHED'
                p.kill();assert await asyncio.to_thread(p.wait,5)==-9
                writer.close()
                try:await writer.wait_closed()
                except ConnectionError:pass
            asyncio.run(deliver())
        else:p.kill();assert p.wait(5)==-9
        out,err=p.communicate(timeout=5);assert out==err==b''
        result=json.loads(subprocess.check_output([sys.executable,'-c',READER,str(root),rid],text=True))
        assert result['classification'] in ('SAFE_RETRY','TERMINAL_CONSUMED','UNKNOWN_NEEDS_REVIEW','BLOCKED')
        assert result['uses'] in (0,1) and result['observations']<=1
        assert all(x==0 for x in result.get('zero_counts',{}).values()) and result['writes']==0
        if identity:assert result['identity_id']==identity
        if point in ('after_consume_commit','before_evidence','after_evidence','core_complete:before'):
            assert result['uses']==1 and result['classification']=='UNKNOWN_NEEDS_REVIEW'
        if point in ('core_complete:after','cleanup:before','verify:before','socket_unlink:before','socket_unlink:after','r041.session_closed:inside','r041.session_closed:after'):
            assert result['uses']==1 and result['classification']=='TERMINAL_CONSUMED'
        # Persist classification only, no cap/nonce/raw IDs. No automatic rearm/retry.
        report={'point':point,'group':group,'SIGKILL':True,'fresh_reader_process':True,'seconds':round(time.monotonic()-start,4),**result}
        folder=Path('.nana-experiment/r044/crash-matrix');folder.mkdir(parents=True,exist_ok=True)
        (folder/(point.replace(':','-')+'.json')).write_text(json.dumps(report,sort_keys=True))
    finally:
        if p.poll() is None:p.kill();p.wait(5)
        p.communicate(timeout=5)
