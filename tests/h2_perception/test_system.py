import json
from pathlib import Path
from uuid import uuid4
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore
from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority,verify_package
from nana_core.continuity.world_loop.reference import configure,open_runtime
from nana_core.continuity.world_loop.semantic_harness import semantic_harness
from nana_core.continuity.memory import MemoryService
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND,HOUR
from .helpers import *
from .test_runtime import periodic,user_event
from .test_boundaries import watch


def test_real_h2_h1_world_concern_original_c_and_delete(tmp_path):
    from nana_core.continuity.world_loop.semantic_harness import semantic_proposer
    def interpretation(req):
        proposal=semantic_proposer(req)
        if req.cognitive_role=='GOALS':proposal=proposal.model_copy(update={'interests':tuple(i.model_copy(update={'expected_value':'HIGH','possible_behaviors':('WATCH',)}) for i in proposal.interests)})
        return proposal
    with open_runtime(tmp_path/'subject/self.db',VirtualClock()) as r,semantic_harness(proposer=interpretation) as (transport,metrics):
        configure(r,tmp_path,transport,('synthetic://public',),grant=False,planner=False)
        c,adapter,m,a=setup(r,tmp_path);c.attach()
        c.concern_callback=lambda result,cid:[r.work.world.observe(mid) for mid in result['semantic_memory_ids']]
        value=c.observe(c.request('screen.a',request_id='screen'));assert value['state']=='GROUNDED'
        for i in range(8):r.clock.source.advance(SECOND);r.step()
        concerns=r.work.world.concerns.view();assert concerns and r.store.all('subject_cycles')
        cycles=[r.subject.result(x) for x in r.store.all('subject_cycles')]
        assert any(x.judgment.stance=='WATCH' or x.intention.kind in {'NO_ACTION','WAIT'} for x in cycles)
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')
        MemoryService(r.store,r.authority).forget(value['memory_id'],r.authority)
        assert not r.work.world.concerns.view()
        assert not [v for v in r.work.world.world.snapshot() if v.state=='SUPPORTED_BELIEF']
        for i in range(3):r.clock.source.advance(SECOND);r.step()
        assert not r.work.world.concerns.view()


def test_b8_host_sources_not_portable_same_subject_new_device(tmp_path):
    db=tmp_path/'a/self.db';clock=VirtualClock()
    with open_runtime(db,clock) as r:
        c,adapter,m,a=setup(r,tmp_path/'a');v=c.observe(c.request('screen.a',request_id='one'));identity=r.identity_id
        # Secret-looking paths and opaque host references belong only to local configuration.
        assert 'resource_ref' not in c.records.memory.read(v['memory_id'])['text']
    controller=PortableTransferAuthority();destination=str(uuid4())
    with ContinuityStore(db,clock,schema_target=13) as store:
        package=SubjectPackageService(store,controller).export(tmp_path/'transfer.zip',destination_id=destination,source_commit='a4abd5ce230848ae6667e5e5362964636e3ead08',authority=controller)
        manifest,files=verify_package(package['path'],expected_sha256=package['sha256'])
        assert set(files)=={'manifest.json','privacy.json','subject.sqlite'}
        for needle in [b'"adapter_ref"',b'"resource_ref"',str(c.configuration._path).encode()]:assert all(needle not in data for data in files.values())
    (tmp_path/'b').mkdir(mode=0o700)
    auth=PortableTransferAuthority(destination_id=destination,destination_root=tmp_path/'b/subject')
    imported=SubjectPackageService.import_quarantined(package['path'],tmp_path/'b/subject',expected_sha256=package['sha256'],destination_id=destination,authority=auth)
    with ContinuityStore(imported,clock,schema_target=13) as store:SubjectPackageService(store,auth).activate(transfer_id=manifest.transfer_id,destination_id=destination,authority=auth)
    with open_runtime(imported,clock) as r:
        assert r.identity_id==identity and r.perception is None and MemoryService(r.store).read(v['memory_id'])
        c2,adapter2,m2,a2=setup(r,tmp_path/'b');new=c2.observe(c2.request('screen.a',request_id='new-device'));assert new['state']=='GROUNDED' and r.identity_id==identity


def virtual_life(root):
    clock=VirtualClock();captures=0;max_queue=0;boosted=False;preempted=False
    with open_runtime(root/'subject/self.db',clock) as r:
        c,adapter,m,a=setup(r,root);c.attach();periodic(c,a,ms=600000)
        # Three independently injected synthetic sensors share the same Runtime owner.
        for sid,kind,mod,data,ops in [('camera.b','CAMERA','IMAGE',png('blue'),('VISION',)),('mic.c','MICROPHONE','AUDIO',__import__('nana_core.continuity.world_loop.samples',fromlist=['media_samples']).media_samples()['AUDIO'],('AUDIO_UNDERSTAND',))]:
            port=SyntheticSourceAdapter(r.clock,data,kind=kind,modality=mod);c.resolver.bind('fixture',sid,port)
            p=profile(source_profile_id=sid,source_kind=kind,modality=mod,resource_ref=sid,privacy_class='PERSONAL' if mod=='AUDIO' else 'PUBLIC',semantic_operations=ops,max_capture_bytes=131072,min_interval_ms=100,capture_mode='PERIODIC',base_interval_ms=600000)
            c.configuration.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=c.configuration.load().revision,profile=p),a)
        identity=r.identity_id;initial=clock.utc_now_us();r.step()
        for slot in range(48):
            clock.advance(1800*SECOND)
            if slot==3:
                last=c.state['sources']['screen.a'].get('last_memory_id')
                if last:
                    cycle=watch(r,c,last);c.watch_from_cycle(cycle.cycle_id,'screen.a',duration_us=1800*SECOND);boosted=c.interval_ms(c._source('screen.a'))==5000
            if slot in {9,11}:
                op='DISABLE_PERCEPTION_SOURCE' if slot==9 else 'ENABLE_PERCEPTION_SOURCE'
                c.configuration.update(SourceCommand(operation=op,expected_revision=c.configuration.load().revision,target_id='camera.b'),a)
            if slot==15:
                ps=c.router.config;pa=ps._ProviderConfigService__authority;update(ps,pa,'DISABLE_PROVIDER',target_id='fixture.semantic')
            if slot==18:
                ps=c.router.config;pa=ps._ProviderConfigService__authority;update(ps,pa,'ENABLE_PROVIDER',target_id='fixture.semantic')
            if slot==6:
                def cut(stage):
                    if stage=='AFTER_CAPTURE_BEFORE_INGEST':r.post(user_event(r,'soak'))
                c._checkpoint=cut
            for i in range(5):
                value=r.step();max_queue=max(max_queue,r.queue.depth())
                if value and value.get('perception',{}).get('reason')=='SEMANTIC_DEFERRED_SOURCE_BYTES_EXPIRED':preempted=True
            c._checkpoint=lambda stage:None
            assert len(c.state['requests'])<=64 and len(c.state['sources'])<=32 and len(c.state.get('pending',{}))<=16
            assert r.identity_id==identity
        assert boosted and preempted and c.state['coalesced']>0 and m.calls<=64 and max_queue<=8
        return {'virtual_hours':(clock.utc_now_us()-initial)/HOUR,'screen_captures':adapter.captures,'semantic_calls':m.calls,'queue_max':max_queue,'request_hot_count':len(c.state['requests']),'source_hot_count':len(c.state['sources']),'coalesced':c.state['coalesced'],'watch_boost':boosted,'user_preemption':preempted,'identity_stable':True,'records':len(r.store.all('continuity_records'))}

def test_24h_virtual_mixed_sensor_soak(tmp_path):
    result=virtual_life(tmp_path);assert result['virtual_hours']>=24
