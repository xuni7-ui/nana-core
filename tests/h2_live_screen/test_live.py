"""Opt-in, real OS test windows only. Public fixture semantics are NOT a real model."""
import json,os,signal,subprocess,sys,time,shutil
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.continuity.sensors.contracts import SourceCommand,CapturePolicy
from nana_core.continuity.sensors.application import PerceptionSettingsService
from tools.nana_h2_live_screen.lab import laboratory,capture
from tools.nana_h2_live_screen.qualification import scenes
from tests.h2_perception.test_runtime import user_event
from tests.h2_perception.test_recovery import STAGES

def test_ten_real_os_scenes_h1_world_concern_c(tmp_path,live_screen):
    result=scenes(tmp_path);assert result['captures']>=12 and result['world_concern_original_c']

def test_live_runtime_preemption_backpressure_disable_remove_and_frontend(tmp_path,live_screen):
    clock=VirtualClock()
    with open_runtime(tmp_path/'subject/self.db',clock) as r,laboratory(r,tmp_path,live_screen=True) as (c,s,m,a):
        from tools.nana_h2_live_screen.x11_surface import ControlledX11Surface
        with pytest.raises(CoreError,match='SCREEN_BACKEND_BUSY'):ControlledX11Surface(live_screen=True)
        service=PerceptionSettingsService(c,a);view=service.projection(c.policy)
        body=json.dumps(view);assert 'L1_REAL_OS_CONTROLLED' in body
        assert not any(x in body for x in ['resource_ref','session_nonce','auth_cookie','display_socket'])
        def cut(stage):
            if stage=='AFTER_CAPTURE_BEFORE_INGEST':r.post(user_event(r,'preempt'))
        c._checkpoint=cut;c.enqueue(c.request('screen.controlled',request_id='preempt'))
        assert r.step()['perception']['reason']=='SEMANTIC_DEFERRED_SOURCE_BYTES_EXPIRED';assert s.capture_calls==1 and m['calls']==0
        event=r.step();assert r.store.one('runtime_queue',event['queue_id'])['event_type']=='USER_EVENT'
        c._checkpoint=lambda stage:None;clock.advance(3*SECOND);v=capture(r,c,'later');assert v['state']=='GROUNDED'
        c.configuration.update(SourceCommand(operation='SET_CAPTURE_POLICY',expected_revision=1,policy=CapturePolicy(pending_capacity=2)),a)
        for i in range(2):c.enqueue(c.request('screen.controlled',request_id='pressure.'+str(i)))
        with pytest.raises(CoreError,match='BACKPRESSURE'):c.enqueue(c.request('screen.controlled',request_id='pressure.full'))
        c.configuration.update(SourceCommand(operation='DISABLE_PERCEPTION_SOURCE',expected_revision=2,target_id='screen.controlled'),a)
        with pytest.raises(CoreError,match='BLOCKED_BY_HOST'):c.observe(c.request('screen.controlled',request_id='disabled'))
        assert s.capture_calls==2 and c.records.memory.read(v['memory_id'])
        c.configuration.update(SourceCommand(operation='REMOVE_PERCEPTION_SOURCE',expected_revision=3,target_id='screen.controlled'),a)
        with pytest.raises(CoreError):c.request('screen.controlled',request_id='removed')
        assert c.records.memory.read(v['memory_id'])

def cleanup_owned(root):
    # Only the test worker's own explicit cleanup receipt; never enumerate peers.
    receipt=json.loads((root/'owned_cleanup.json').read_text());owned=Path(receipt['temporary_root'])
    assert owned.parent==Path('/tmp') and owned.name.startswith('nana-owned-display-')
    for _ in range(40):
        stat=Path('/proc')/str(receipt['pid'])/'stat'
        if not stat.exists() or stat.read_text().split()[2]=='Z':break
        time.sleep(.05)
    else:raise AssertionError('owned Xorg outlived parent death signal')
    try:os.waitpid(receipt['pid'],os.WNOHANG)
    except ChildProcessError:pass
    shutil.rmtree(owned,ignore_errors=True)

@pytest.mark.parametrize('stage',STAGES)
def test_real_backend_sigkill_six_cuts(tmp_path,live_screen,stage):
    import ctypes
    assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0  # reap only this worker's owned orphan
    cmd=[sys.executable,'-m','tools.nana_h2_live_screen.qualification']
    child=subprocess.run(cmd+['crash','--live-screen','--root',str(tmp_path),'--stage',stage],capture_output=True,timeout=30)
    assert child.returncode==-signal.SIGKILL,child.stderr.decode()[-2000:]
    cleanup_owned(tmp_path)
    resumed=subprocess.run(cmd+['resume','--live-screen','--root',str(tmp_path)],capture_output=True,timeout=30)
    assert resumed.returncode==0,resumed.stderr.decode()[-2000:]
    value=json.loads(resumed.stdout);assert value['no_capture_replay'] and value['no_semantic_replay'] and value['new_host_revision']==2

def test_live_manager_preserves_watch_and_pixels_never_acquire_authority(tmp_path,live_screen):
    from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraint
    from nana_core.continuity.autonomy.contracts import RealizationTarget
    from tests.h2_perception.test_boundaries import watch
    clock=VirtualClock()
    with open_runtime(tmp_path/'subject/self.db',clock) as r,laboratory(r,tmp_path,live_screen=True) as (c,s,m,a):
        s.render('F');value=capture(r,c,'spoof');cycle=watch(r,c,value['memory_id']);c.watch_from_cycle(cycle.cycle_id,'screen.controlled')
        old=r.store.one('subject_cycles',cycle.cycle_id);before=s.capture_calls
        controller=GovernanceController(r.store,r.authority);now=r.clock.utc_now_us()
        controller.install(ManagerConstraint(constraint_id='controlled.capture.veto',revision=1,issuer=r.authority.principal,source_reference='host.policy',identity_id=r.identity_id,scope='world',targets=(RealizationTarget(capability='perception.capture',operation='READ',resource='synthetic://perception/screen.controlled',resource_class='ORDINARY'),),effective_from_us=now,expires_at_us=now+100*SECOND,reason_code='NO_CAPTURE'),r.authority)
        clock.advance(3*SECOND)
        with pytest.raises(CoreError,match='MANAGER_BLOCKED'):capture(r,c,'denied')
        assert s.capture_calls==before and old==r.store.one('subject_cycles',cycle.cycle_id)
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')
        assert c.status(c.policy)['sources'][0]['last_block']['stage']=='MANAGER'


def test_real_source_b8_transfer_new_display_and_forget(tmp_path,live_screen):
    from uuid import uuid4
    from nana_core.continuity import ContinuityStore
    from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority,verify_package
    from nana_core.continuity.memory import MemoryService
    clock=VirtualClock();db=tmp_path/'a/subject/self.db'
    with open_runtime(db,clock) as r,laboratory(r,tmp_path/'a',live_screen=True) as (c,s,m,a):
        v=capture(r,c,'original-host');identity=r.identity_id
    authority=PortableTransferAuthority();destination=str(uuid4())
    with ContinuityStore(db,clock,schema_target=13) as store:
        transfer=SubjectPackageService(store,authority).export(tmp_path/'transfer.zip',destination_id=destination,source_commit='06c80a907af49c3b80bf097f90c71e02d552aaf8',authority=authority)
        manifest,files=verify_package(transfer['path'],expected_sha256=transfer['sha256']);assert set(files)=={'manifest.json','privacy.json','subject.sqlite'}
        for needle in [b'"resource_ref"',b'"adapter_ref"',b'MIT-MAGIC-COOKIE',b'iVBORw0KGgo',str(c.configuration._path).encode()]:assert all(needle not in data for data in files.values())
    (tmp_path/'b').mkdir(mode=0o700);authority=PortableTransferAuthority(destination_id=destination,destination_root=tmp_path/'b/subject')
    imported=SubjectPackageService.import_quarantined(transfer['path'],tmp_path/'b/subject',expected_sha256=transfer['sha256'],destination_id=destination,authority=authority)
    with ContinuityStore(imported,clock,schema_target=13) as store:SubjectPackageService(store,authority).activate(transfer_id=manifest.transfer_id,destination_id=destination,authority=authority)
    with open_runtime(imported,clock) as r:
        assert r.identity_id==identity and r.perception is None
        with laboratory(r,tmp_path/'b',live_screen=True) as (c,s,m,a):
            assert s.capture_calls==0 and c.records.memory.read(v['memory_id'])
            new=capture(r,c,'new-host');assert new['state']=='GROUNDED' and r.identity_id==identity
            MemoryService(r.store,r.authority).forget(new['memory_id'],r.authority)
            with pytest.raises(CoreError):c.records.memory.read(new['memory_id'])


def test_visual_injection_payload_cannot_propose_authority(tmp_path,live_screen):
    from nana_core.continuity.world_loop.cognition import InterestProposal
    from nana_core.continuity.world_loop.semantic_harness import semantic_proposer
    from tools.nana_h2_live_screen import lab
    # A hostile interpretation is exercised over genuine captured attack pixels.
    # H1 rejects MEDIA goal proposals regardless of what the visible words say.
    original=lab.interpretation
    def malicious(req):
        p=semantic_proposer(req)
        if req.cognitive_role=='MEDIA':
            p=p.model_copy(update={'interests':(InterestProposal(topic='unauthorized',motivation_source='CURIOSITY',interpretation='hostile synthetic interpretation',source_memory_ids=req.primary_source_refs,expected_value='HIGH',possible_behaviors=('WATCH',)),)})
        return p
    lab.interpretation=malicious
    try:
        with open_runtime(tmp_path/'subject/self.db',VirtualClock()) as r,laboratory(r,tmp_path,live_screen=True) as (c,s,m,a):
            s.render('D');v=capture(r,c,'injection');assert v['semantic']['VISION']['state']=='REJECTED'
            assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')
            assert all(x['source_kind']!='USER_STATEMENT' for x in r.store.all('continuity_evidence'))
    finally:lab.interpretation=original
