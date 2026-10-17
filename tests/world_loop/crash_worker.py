"""Real process cut points; no live provider or production world."""
import os,signal,sys
from pathlib import Path
from nana_core.continuity.world_loop.reference import open_runtime,configure,capture
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.world import SourcedClaim
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND

def main():
    root=Path(sys.argv[1]);mode=sys.argv[2];clock=VirtualClock()
    with provider_harness() as (transport,_),open_runtime(root/'subject'/'self.db',clock) as r:
        port=configure(r,root,transport,('synthetic://recover',),planner=False);port.seed_observation('synthetic://recover',{'data':'public recoverable observation'})
        mid=capture(r,'recover-world',{'world_claim':SourcedClaim(entity_id='device',predicate='available',value=True,kind='RAW_OBSERVATION',valid_from_us=r.clock.utc_now_us()).model_dump(mode='json'),'opportunities':[{'topic':'recover','resource':'synthetic://recover','value':'HIGH','motive':'CURIOSITY'}]})
        r.work.world.world.ingest(mid);r.work.world.observe(mid)
        if mode=='calling':
            def cut(request):os.kill(os.getpid(),signal.SIGKILL)
            transport.exchange=cut
        elif mode=='goal':
            def cut(*args,**kwargs):os.kill(os.getpid(),signal.SIGKILL)
            r.work.world.after_cycle=cut # after Agency adoption, before concern ACK
        else:raise ValueError('unknown cut')
        for _ in range(32):clock.advance(SECOND);r.step()
    raise RuntimeError('cut not reached')
if __name__=='__main__':main()
