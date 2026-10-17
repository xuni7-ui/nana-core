"""Explicit offline process qualification entry; never auto-runs live devices."""
import argparse,json,os,signal,time,threading,resource
from pathlib import Path
from nana_core.clock import Clock
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND,HOUR
from nana_core.continuity.world_loop.reference import open_runtime
from .helpers import setup,setup_existing,png,SemanticFixture

def crash(root,stage):
    with open_runtime(root/'subject/self.db',VirtualClock()) as r:
        from nana_core.continuity.world_loop.reference import configure
        configure(r,root,SemanticFixture('fixture.interpret','fixture-cognition'),('synthetic://public',),grant=False,planner=False)
        c,adapter,m,a=setup(r,root,concern_callback=lambda result,cid:[r.work.world.observe(mid) for mid in result['semantic_memory_ids']])
        def cut(name):
            if name==stage:os.kill(os.getpid(),signal.SIGKILL)
        c._checkpoint=cut
        c.observe(c.request('screen.a',request_id='cut-once'))

def resume(root):
    with open_runtime(root/'subject/self.db',VirtualClock()) as r:
        c,adapter,m,a=setup_existing(r,root)
        before={t:len(r.store.all(t)) for t in ['memories','cognitive_requests','subject_cycles','open_concerns']}
        c.recover();c.recover()
        after={t:len(r.store.all(t)) for t in before}
        assert before==after and m.calls==0 and adapter.bytes_read==0
        return {'result':'PASS','no_provider_calls':True,'no_capture_replay':True,'counts':after,'states':[x['state'] for x in c.state['requests'].values()]}

def wall(root,seconds):
    started=time.monotonic();before_fd=len(os.listdir('/proc/self/fd'));before_threads=threading.active_count();before_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with open_runtime(root/'subject/self.db',Clock(),wall=True) as r:
        c,adapter,m,a=setup(r,root);c.attach();identity=r.identity_id
        from .test_runtime import periodic
        periodic(c,a,ms=10000)
        max_queue=0;max_pending=0
        while time.monotonic()-started<seconds:
            r.step();max_queue=max(max_queue,r.queue.depth());max_pending=max(max_pending,len(c.state.get('pending',{})))
            r.cadence.wait(.1,r.cadence.stamp())
        assert r.identity_id==identity and adapter.captures<=seconds//10+2 and m.calls<=adapter.captures
        assert len(c.state['requests'])<=64 and max_queue<=r.config.queue_capacity
        result={'elapsed_seconds':time.monotonic()-started,'captures':adapter.captures,'semantic_calls':m.calls,'queue_max':max_queue,'pending_max':max_pending,'identity_stable':True,'execution':'SYNTHETIC_SCREEN_ONLY_NO_LIVE_DEVICE'}
    result.update(fd_before=before_fd,fd_after=len(os.listdir('/proc/self/fd')),threads_before=before_threads,threads_after=threading.active_count(),maxrss_growth_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss-before_rss)
    assert result['fd_after']<=before_fd+2 and result['threads_after']<=before_threads+1 and result['maxrss_growth_kib']<65536
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['crash','resume','wall']);p.add_argument('root',type=Path);p.add_argument('--stage');p.add_argument('--seconds',type=float,default=180);p.add_argument('--output',type=Path);args=p.parse_args()
    result=crash(args.root,args.stage) if args.mode=='crash' else resume(args.root) if args.mode=='resume' else wall(args.root,args.seconds)
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    else:print(json.dumps(result))
