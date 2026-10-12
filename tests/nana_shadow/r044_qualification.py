"""Exact approved package offline recovery qualification, FIXXTURE ONLY.

No production seal, host binding, plugin install or model call. The sealed test
candidate is immutable metadata for FixtureTrustStore, never sealed_trust.py.
"""
import ast
import asyncio
from datetime import datetime,timezone,timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from uuid import uuid4

CORE='ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513'
CHILD=r'''
import asyncio,os,sys,time
from pathlib import Path
root,data,ipc,rid,pid,marker=sys.argv[1:]
sys.path.insert(0,str(Path(root)/'package/support'))
from tools.nana_astrbot_shadow.package import verify_package
verify_package(root)
from nana_host_shadow.bootstrap_entry import runtime
runtime(Path(root));sys.path.insert(0,str(Path(root)/'package/src'))
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore
old=ShortLivedWorker._finish_on_writer
def stop_before_cleanup(self):
 Path(marker).write_text('CORE_COMPLETE_BEFORE_CLEANUP')
 while True:time.sleep(.005)
ShortLivedWorker._finish_on_writer=stop_before_cleanup
asyncio.run(ShortLivedWorker(data,ipc,rid,client_pid=int(pid),seconds=10,trust=FixtureTrustStore()).serve())
'''


def archive_inventory(archive):
    """Test/pre-install inspection BEFORE extraction; no new production authority."""
    from pathlib import PurePosixPath
    with tarfile.open(archive) as tar:
        members=tar.getmembers();names=[m.name for m in members]
        if not 0<len(members)<=4096 or len(names)!=len(set(names)):raise ValueError('ARCHIVE_DUPLICATE_OR_LIMIT')
        if sum(m.size for m in members)>64*1024*1024:raise ValueError('ARCHIVE_SIZE')
        roots=set()
        for m in members:
            path=PurePosixPath(m.name)
            if (not m.isfile() or path.is_absolute() or '..' in path.parts or len(path.parts)<2
                or path.as_posix()!=m.name or any(c in m.name for c in ('\x00','\n','\r'))
                or m.mode & 0o022):raise ValueError('ARCHIVE_ENTRY_POLICY')
            roots.add(path.parts[0])
        if len(roots)!=1:raise ValueError('ARCHIVE_ROOT')
        return members


def run(archive,expected_sha):
    archive=Path(archive)
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected_sha
    start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='r44-q-') as td:
        temp=Path(td);temp.chmod(0o700)
        names=[m.name for m in archive_inventory(archive)]
        with tarfile.open(archive) as t:t.extractall(temp,filter='data')
        root=temp/Path(names[0]).parts[0];root.chmod(0o700)
        sys.path.insert(0,str(root/'package/support'))
        from tools.nana_astrbot_shadow.package import verify_package
        from tools.nana_host_shadow.safety import verify_bundle,digest,canonical,private_file
        m=verify_package(root);core=verify_bundle(root/'package');assert core['source_commit']==CORE and len(core['core_files'])==55
        from tools.nana_host_shadow.bootstrap_entry import runtime
        host,private=runtime(root);sys.path.insert(0,str(root/'package/src'))
        from tools.nana_astrbot_shadow.one_shot_cli import initialize,ReadOnlyStoreView
        from tools.nana_astrbot_shadow.onboarding import scope_metadata,prepare
        from tools.nana_astrbot_shadow.one_shot import ReceiptLedger,FixtureTrustStore,parse_receipt,review_document,Provenance
        from tools.nana_astrbot_shadow.bridge_wire import load_config,frame,envelope,project_raw
        from tools.nana_astrbot_shadow.one_shot_proof import collect,verify_first_real_message_shadow,mark_verified,ZERO_KEYS
        from tools.nana_astrbot_shadow import sealed_trust
        from nana_core.storage import Store
        import tools.nana_astrbot_shadow.bridge_cli as cli
        from contextlib import contextmanager
        data=temp/'data';data.mkdir(mode=0o700);initial=initialize(data)
        # All transient input IDs are explicitly synthetic; no body/discovery.
        raw={'platform':'development','type':'FakeEvent','event_id':'synthetic-q-event',
             'timestamp':datetime.now(timezone.utc).isoformat(),'sender_id':'synthetic-q-sender','conversation_id':'synthetic-q-conversation'}
        scope=temp/'scope.json';scope_metadata(data,{'platform_scope':raw['platform'],'event_type_scope':raw['type'],
            'sender_id':raw['sender_id'],'conversation_id':raw['conversation_id']},scope)
        request=temp/'request';prepare(data,json.loads(scope.read_text()),request)
        unsigned=parse_receipt((request/'receipt.json').read_text())
        # Test-domain review is rebuilt under FIXXTURE, never rename fixture as real.
        r=unsigned.model_copy(update={'review_provenance':Provenance.FIXTURE,'review_receipt_digest':'0'*64})
        r=r.model_copy(update={'review_receipt_digest':digest(review_document(r))});r=parse_receipt(r.canonical())
        with Store(data/'observer-shadow.db') as s:
            l=ReceiptLedger(s,FixtureTrustStore());l.create(r);l.review(r.receipt_id,review_document(r));l.arm(r.receipt_id)
            before=s.identity
        # Immutable test-candidate metadata: contains no executable production pin.
        candidate={'domain':'FIXTURE','receipt_digest':r.receipt_digest,'review_digest':r.review_receipt_digest,
                   'store_binding':r.store_binding,'Core_source_SHA':CORE,'support_source_SHA':m['support_source_SHA'],
                   'production_review_pins':0,'real_runtime_proof_pins':0}
        private_file(temp/'fixture-candidate.json',candidate);candidate_digest=digest(candidate)
        ipc=temp/'ipc';ipc.mkdir(mode=0o700);marker=temp/'checkpoint'
        p=subprocess.Popen([sys.executable,'-I','-B','-S','-c',CHILD,str(root),str(data),str(ipc),r.receipt_id,str(os.getpid()),str(marker)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            end=time.monotonic()+6
            while not (ipc/'client.json').exists() and p.poll() is None and time.monotonic()<end:time.sleep(.005)
            assert (ipc/'client.json').exists();c=load_config(ipc/'client.json')
            async def deliver():
                reader,writer=await asyncio.open_unix_connection(c['socket_path'])
                writer.write(frame(envelope(project_raw(raw,c),c)));await writer.drain()
                from tools.nana_astrbot_shadow.bridge_wire import read_frame
                response=await read_frame(reader,2);assert response['status']=='SHADOW_BLOCKED'
                writer.close()
                try:await writer.wait_closed()
                except ConnectionError:pass
            asyncio.run(deliver())
            end=time.monotonic()+4
            while not marker.exists() and p.poll() is None and time.monotonic()<end:time.sleep(.005)
            assert marker.exists();p.kill();assert p.wait(5)==-9
            out,err=p.communicate(timeout=5);assert out==err==b''
        finally:
            if p.poll() is None:p.kill();p.wait(5)
            p.communicate(timeout=5)
        @contextmanager
        def fixture_view(directory):
            s=ReadOnlyStoreView(Path(directory)/'observer-shadow.db')
            try:yield ReceiptLedger(s,FixtureTrustStore())
            finally:s.close()
        cli.operator_ledger=fixture_view # development-local readback; never in production CLI
        with Store(data/'observer-shadow.db') as s:
            l=ReceiptLedger(s,FixtureTrustStore());assert s.identity==before
            report=collect(l,r.receipt_id,observer_callback_received=True,sanitizer_accepted=True,noncore_zero={k:0 for k in ZERO_KEYS})
            assert verify_first_real_message_shadow(report,l)['status']=='SIMULATED_REAL_SHADOW_PROOF_PASS'
            assert mark_verified(report,l)['host_binding']=='UNVERIFIED'
            with_error=False
            try:l.arm(r.receipt_id)
            except ValueError:with_error=True
            assert with_error and l.status(r.receipt_id)['uses']==1
            assert len([e for e in s.all('events') if e['kind']=='observation.received'])==1
            assert all(not s.all(t) for t in ('actions','attempts','grants','budgets','strategies'))
            backup=temp/'backup.db';replay=temp/'replay.db';s.backup(backup);s.replay(replay)
        assert cli.stop(data,ipc)['stop_result']=='ALREADY_EXITED'
        cleanup=cli.stale_cleanup(data,ipc);assert cleanup['status']=='STALE_EPHEMERALS_REMOVED'
        assert not (ipc/'bridge.sock').exists() and not (ipc/'client.json').exists()
        for path in (backup,replay):
            with Store(path) as s:
                assert s.identity==before and s.one('core_meta','recovery_quarantine')['value_json']=='true'
                try:ReceiptLedger(s,FixtureTrustStore())
                except ValueError:pass
                else:raise AssertionError('RESTORED_STATE_MUST_BLOCK_INGRESS')
        assert not sealed_trust.PRODUCTION_REVIEW_PINS and not sealed_trust.REAL_RUNTIME_PROOF_PINS
        # Returned evidence has no hashes of secret keys, raw IDs, nonce or body.
        result={'status':'OFFLINE_RECOVERY_QUALIFIED','trust_domain':'FIXTURE','Core_source_SHA':CORE,
            'Core55_package_hashes':'PASS','support_source_SHA':m['support_source_SHA'],
            'fresh_archive_verified':True,'fixture_candidate_digest':candidate_digest,'production_pins':0,
            'real_runtime_pins':0,'one_ingress':True,'identity_continuous':True,'receipt_terminal':'VERIFIED_FIXTURE',
            'SIGKILL_after_core_complete':True,'verify':'SIMULATED_REAL_SHADOW_PROOF_PASS',
            'official_backup_quarantine':'PASS','official_replay_quarantine':'PASS','residual_live_workers':0,
            'residual_sockets':0,'residual_client_capabilities':0,'held_Store_leases':0,'external_actions':0,
            'real_model_calls':0,'host_binding':'UNVERIFIED','FIRST_REAL_ASTRBOT_SHADOW':'BLOCKED','E12':'NOT_RUN',
            'runtime':private,'seconds':round(time.monotonic()-start,3)}
        result['runtime'].pop('executable',None)
        return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();result=run(a.archive,a.sha256)
    Path(a.output).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'one_ingress':True,'production_pins':0}))
