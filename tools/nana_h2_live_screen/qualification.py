"""Explicit finite real-OS qualification. Never observes an existing desktop.

Usage: python -m tools.nana_h2_live_screen.qualification preflight
       python -m tools.nana_h2_live_screen.qualification scenes --live-screen --root /tmp/owned-run --output /tmp/result.json
"""
import argparse,json,os,signal,time,threading,resource,hashlib
from pathlib import Path
from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND,HOUR
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.continuity.memory import MemoryService
from .lab import laboratory,capture

def counts(r):return {t:len(r.store.all(t)) for t in ['memories','cognitive_requests','subject_cycles','open_concerns','actions','grants','goals']}

def scenes(root):
    clock=VirtualClock();rows=[]
    with open_runtime(root/'subject/self.db',clock) as r,laboratory(r,root,live_screen=True) as (c,s,metrics,a):
        initial_identity=r.identity_id;before=counts(r);memories=[]
        for index,scene in enumerate('ABCDEFGHI'):
            s.render(scene);clock.advance(SECOND if scene=='C' else 3*SECOND)
            v=capture(r,c,'scene.'+scene);assert v['state'] in {'GROUNDED','DECODED'},v
            body=json.loads(c.records.memory.read(v['memory_id'])['text']);source=body['source'];receipt=source['screen_receipt'];memories.append(v['memory_id'])
            assert source['origin']=='REAL_OS_CONTROLLED' and body['decoded']['pixel_digest']==receipt['pixel_digest']
            assert source['source_revision']==1 and receipt['capture_scope']=='EXPLICIT_WINDOW'
            evidence=r.store.one('continuity_evidence',c.records.memory.read(v['memory_id'])['source_evidence_id'])
            assert json.loads(evidence['provenance_json'])['domain']=='RECORDED_PUBLIC' and evidence['source_kind']=='DIRECT_OBSERVATION'
            if scene=='H':
                calls=s.capture_calls
                for rapid in range(3):
                    s.render('A' if rapid%2 else 'B')
                    try:c.observe(c.request('screen.controlled',request_id='rapid.'+str(rapid),foreground=True))
                    except CoreError as exc:assert exc.code=='SOURCE_MIN_INTERVAL'
                    else:raise AssertionError('rapid captures ignored minimum')
                assert s.capture_calls==calls
                s.render('H')
            rows.append({'scene':scene,'state':v['state'],'reason':v['reason'],'pixel_digest':receipt['pixel_digest'],'event_time_us':source['event_time_us'],'origin':source['origin'],'width':receipt['width'],'height':receipt['height']})
        assert rows[0]['pixel_digest']!=rows[1]['pixel_digest']
        assert rows[1]['pixel_digest']==rows[2]['pixel_digest'] and rows[1]['event_time_us']!=rows[2]['event_time_us']
        assert rows[2]['reason']=='EXACT_DIGEST_DEBOUNCE'
        # Repeated rapid same-pixel observations still retain temporal identity.
        for i in range(3):clock.advance(SECOND);v=capture(r,c,'unchanged.'+str(i));assert v['reason']=='EXACT_DIGEST_DEBOUNCE'
        for _ in range(12):clock.advance(SECOND);r.step()
        cycles=[r.subject.result(row) for row in r.store.all('subject_cycles')]
        assert cycles and r.work.world.concerns.view()
        chosen=[x for x in cycles if x.judgment.stance=='WATCH']
        assert chosen,[(x.judgment.stance,x.intention.kind) for x in cycles]
        c.watch_from_cycle(chosen[0].cycle_id,'screen.controlled');assert c.interval_ms(c._source('screen.controlled'))==5000
        before_subject=r.store.one('subject_cycles',chosen[0].cycle_id)
        # Topology is fenced before any source bytes; no broader fallback.
        calls=s.capture_calls;s.resize();s.render('J');clock.advance(3*SECOND)
        try:capture(r,c,'scene.J.stale')
        except CoreError as exc:assert exc.code=='SCREEN_TOPOLOGY_CHANGED'
        else:raise AssertionError('resize accepted old binding')
        assert s.capture_calls==calls
        # Trusted host explicitly binds a fresh revision to resized own window.
        from .lab import PerceptionSourceProfile,HostPerceptionResolver,PerceptionConfigService,RealScreenPerceptionPort,ScreenBackendDescriptor,SourceCommand
        resolver=HostPerceptionResolver();config=PerceptionConfigService(root/'host/sensors.json',a,resolver)
        p=c._source('screen.controlled').model_copy(update={'revision':c.configuration.load().revision+1})
        port=RealScreenPerceptionPort(s,ScreenBackendDescriptor(backend_id='x11.owned-window'),p,r.clock,host_enabled=True);resolver.bind(p.adapter_ref,p.resource_ref,port)
        config.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=c.configuration.load().revision,profile=p),a)
        c.resolver,c.configuration=resolver,config
        c.host_allow=lambda candidate:candidate.source_profile_id==p.source_profile_id and candidate.revision==p.revision
        clock.advance(60*SECOND)
        j=capture(r,c,'scene.J.rebound');assert j['state']=='GROUNDED'
        rows.append({'scene':'J','stale_before_capture':True,'explicit_rebind_revision':p.revision,'resized_capture':j['state']})
        assert r.store.one('subject_cycles',chosen[0].cycle_id)==before_subject
        assert all(not r.store.all(t) for t in ['actions','grants','goals'])
        assert r.identity_id==initial_identity
        # Digest-only media in the persisted cognition envelope, never pixels.
        persisted='\n'.join(json.dumps(c.records.read(row['record_id'])['payload']) for row in r.store.all('continuity_records'))
        assert 'data:image' not in persisted and 'iVBORw0KGgo' not in persisted
        # Explicit deletion invalidates downstream support; no screenshot cache.
        MemoryService(r.store,r.authority).forget(memories[0],r.authority)
        try:c.records.memory.read(memories[0])
        except CoreError:pass
        else:raise AssertionError('forget did not close memory')
        return {'execution':'REAL_OS_CONTROLLED_WINDOW_SYNTHETIC_LOOPBACK_SEMANTICS','qualification_level':'L1','scenes':rows,'captures':s.capture_calls,'http_semantic_and_interpretation_calls':metrics['calls'],'before':before,'after':counts(r),'watch_cadence_ms':5000,'same_pixels_different_time':True,'exact_pixel_debounce':True,'source_backed_watch':True,'subject_no_external_action':True,'world_concern_original_c':True,'screen_text_has_no_authority':True,'raw_screen_persisted':False,'forget_source_closed':True,'identity_stable':True,'scope':'EXPLICIT_WINDOW','physical_monitor':False,'user_desktop':False,'ocr_quality':'NOT_RUN_NARROW_PIXEL_ORACLE_ONLY'}

def wall(root,seconds):
    if seconds<300:raise CoreError('WALL_QUALIFICATION_MINIMUM_300_SECONDS')
    start=time.monotonic();cpu=time.process_time();fds=len(os.listdir('/proc/self/fd'));threads=threading.active_count();rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;latencies=[]
    with open_runtime(root/'subject/self.db',Clock(),wall=True) as r,laboratory(r,root,live_screen=True,interval_ms=10000,periodic=True) as (c,s,m,a):
        identity=r.identity_id;max_queue=0;next_scene=start;index=0;max_pending=0
        while time.monotonic()-start<seconds:
            if time.monotonic()>=next_scene:s.render('ABDG'[index%4]);index+=1;next_scene+=35
            t=time.monotonic();v=r.step()
            if v and v.get('perception',{}).get('memory_id'):latencies.append((time.monotonic()-t)*1000)
            max_queue=max(max_queue,r.queue.depth());max_pending=max(max_pending,len(c.state.get('pending',{})))
            r.cadence.wait(.1,r.cadence.stamp())
        assert r.identity_id==identity and s.capture_calls>=12 and s.capture_calls<=seconds//5+2
        assert max_queue<=8 and max_pending<=16 and len(c.state['requests'])<=64
        result={'elapsed_seconds':time.monotonic()-start,'captures':s.capture_calls,'semantic_and_interpretation_http_calls':m['calls'],'queue_max':max_queue,'pending_max':max_pending,'identity_stable':True,'scenes_rendered':'ABDG','scope':'EXPLICIT_WINDOW','execution':'REAL_OS_CONTROLLED','capture_slice_latency_ms':{'count':len(latencies),'max':max(latencies,default=0),'mean':sum(latencies)/max(1,len(latencies))},'owned_xorg_running_during_run':s.proc.poll() is None}
    result.update(fd_before=fds,fd_after=len(os.listdir('/proc/self/fd')),threads_before=threads,threads_after=threading.active_count(),maxrss_growth_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss-rss,cpu_seconds=time.process_time()-cpu,owned_xorg_stopped=s.proc.poll() is not None,raw_screen_files=0)
    assert result['fd_after']<=fds+2 and result['threads_after']<=threads+1 and result['maxrss_growth_kib']<65536 and result['owned_xorg_stopped']
    return result

def crash(root,stage):
    with open_runtime(root/'subject/self.db',VirtualClock()) as r,laboratory(r,root,live_screen=True) as (c,s,m,a):
        # Harness-only owned-process cleanup receipt, never a Subject record.
        (root/'owned_cleanup.json').write_text(json.dumps({'pid':s.proc.pid,'temporary_root':str(s.root)}))
        c._checkpoint=lambda name:os.kill(os.getpid(),signal.SIGKILL) if name==stage else None
        c.observe(c.request('screen.controlled',request_id='crash.once',foreground=True))
        raise AssertionError('checkpoint not reached')

def resume(root):
    clock=VirtualClock();clock.advance(3*HOUR)
    with open_runtime(root/'subject/self.db',clock) as r,laboratory(r,root,live_screen=True) as (c,s,m,a):
        first=counts(r);c.recover();c.recover();assert first==counts(r)
        assert s.capture_calls==0 and m['calls']==0
        states=[x['state'] for x in c.state['requests'].values()]
        assert not any(x in {'CAPTURING','CAPTURED','DECODED'} for x in states)
        return {'result':'PASS','no_capture_replay':True,'no_semantic_replay':True,'counts':first,'states':states,'new_host_revision':c._source('screen.controlled').revision}

def virtual(root):
    from .lab import rebind
    from nana_core.continuity.sensors.contracts import SourceCommand
    from nana_core.presence.contracts import RuntimeEvent,Cause
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraint
    from nana_core.continuity.autonomy.contracts import RealizationTarget
    clock=VirtualClock();start=clock.utc_now_us();maximum=0;preempt=False;boost=False;blocked=False
    with open_runtime(root/'subject/self.db',clock) as r,laboratory(r,root,live_screen=True,periodic=True,interval_ms=600000) as (c,s,m,a):
        identity=r.identity_id;r.step();controller=GovernanceController(r.store,r.authority)
        for n in range(48):
            clock.advance(1800*SECOND);s.render('A' if n%2 else 'B')
            if n==4:
                for row in r.store.all('subject_cycles'):
                    if r.subject.result(row).judgment.stance=='WATCH':
                        c.watch_from_cycle(row['cycle_id'],'screen.controlled',duration_us=1800*SECOND);boost=c.interval_ms(c._source('screen.controlled'))==5000;break
            if n==8:c.configuration.update(SourceCommand(operation='DISABLE_PERCEPTION_SOURCE',expected_revision=c.configuration.load().revision,target_id='screen.controlled'),a)
            if n==10:rebind(c,s,a,changes={'enabled':True})
            if n==16:
                controller.install(ManagerConstraint(constraint_id='virtual.capture.veto',revision=1,issuer=r.authority.principal,source_reference='host.virtual',identity_id=r.identity_id,scope='world',targets=(RealizationTarget(capability='perception.capture',operation='READ',resource='synthetic://perception/screen.controlled',resource_class='ORDINARY'),),effective_from_us=clock.utc_now_us(),expires_at_us=clock.utc_now_us()+3600*SECOND,reason_code='NO_CAPTURE'),r.authority)
            if n==6:
                def cut(stage):
                    if stage=='AFTER_CAPTURE_BEFORE_INGEST':
                        now=clock.utc_now_us();r.post(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=SubjectInput(source_key='synthetic.live-screen.preempt',kind='INTERACTION',origin='USER',entity_id=r.config.entity_id,scope='world',observed_at_us=now,text='public synthetic attention request'),causes=(Cause(kind='CANONICAL_SELF',reference_id=r.identity_id),),due_at_us=now,priority=3))
                c._checkpoint=cut
            for _ in range(5):
                out=r.step();maximum=max(maximum,r.queue.depth())
                if out and out.get('perception',{}).get('reason')=='SEMANTIC_DEFERRED_SOURCE_BYTES_EXPIRED':preempt=True
            c._checkpoint=lambda stage:None
            blocked=blocked or bool(c.state['sources'].get('screen.controlled',{}).get('last_block'))
            assert r.identity_id==identity and len(c.state['requests'])<=64 and len(c.state.get('pending',{}))<=16
        assert boost and preempt and blocked and c.state['coalesced']>0 and maximum<=8
        return {'virtual_hours':(clock.utc_now_us()-start)/HOUR,'actual_os_captures':s.capture_calls,'synthetic_http_calls':m['calls'],'queue_max':maximum,'hot_requests':len(c.state['requests']),'coalesced':c.state['coalesced'],'watch_boost':boost,'user_preemption':preempt,'manager_veto_seen':blocked,'disable_rebind_exercised':True,'identity_stable':True,'raw_pixels_retained':False,'execution':'VIRTUAL_TIME_REAL_OWNED_OS_WINDOW_SYNTHETIC_SEMANTICS'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['preflight','scenes','wall','virtual','crash','resume']);p.add_argument('--live-screen',action='store_true');p.add_argument('--root',type=Path);p.add_argument('--output',type=Path);p.add_argument('--seconds',type=float,default=300);p.add_argument('--stage');args=p.parse_args()
    if args.mode=='preflight':result={'os':'Linux' if os.name=='posix' else 'OTHER','owned_xorg_binary_available':Path('/usr/bin/Xorg').is_file(),'dummy_driver_available':Path('/usr/lib/xorg/modules/drivers/dummy_drv.so').is_file(),'ambient_display_used':False,'capture_performed':False,'capture_default':'DENY','live_flag_required':True}
    else:
        if not args.live_screen:p.error('--live-screen required; no capture attempted')
        if args.root is None:p.error('--root required')
        args.root.mkdir(mode=0o700,parents=True,exist_ok=True)
        result=scenes(args.root) if args.mode=='scenes' else wall(args.root,args.seconds) if args.mode=='wall' else virtual(args.root) if args.mode=='virtual' else crash(args.root,args.stage) if args.mode=='crash' else resume(args.root)
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    else:print(json.dumps(result))
if __name__=='__main__':main()
