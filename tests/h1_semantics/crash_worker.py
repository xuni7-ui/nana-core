"""Actual process death at H1 commits. Child does not communicate with live systems."""
import os,signal,sys
from pathlib import Path
from nana_core.continuity.world_loop.reference import open_runtime,configure
from nana_core.continuity.world_loop.semantic_harness import semantic_harness,semantic_proposer
from nana_core.continuity.world_loop.cognition import CognitionSession,InterestProposal
from nana_core.continuity.world_loop.semantics import MediaSemanticService
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.continuity.world_loop.reference import codec_providers,context_policy
from nana_core.continuity.world_loop.samples import media_samples
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tests.world_loop.crash_worker import kill_after_commit

def proposer(req):
    out=semantic_proposer(req)
    if req.cognitive_role=='GOALS':
        return out.model_copy(update={'interests':tuple(i.model_copy(update={'expected_value':'HIGH','possible_behaviors':('WATCH',)}) for i in out.interests)})
    return out

def main():
    root=Path(sys.argv[1]);cut=sys.argv[2];clock=VirtualClock()
    with semantic_harness(proposer=proposer) as (t,_),open_runtime(root/'subject'/'self.db',clock) as r:
        configure(r,root,t,('synthetic://public',),grant=False,planner=False)
        mode={'decode':'IMAGE','calling':'AUDIO','proposed':'VIDEO','belief':'IMAGE','cycle':'IMAGE'}[cut]
        data=media_samples()[mode]
        if cut=='decode':kill_after_commit(r.store,'world.media_observed')
        now=clock.utc_now_us();mid,_=PerceptionService(r.store,codec_providers(),context_policy()).ingest(data,PublicMediaSource(source_id='recovery',modality=mode,origin='SYNTHETIC',event_time_us=now,observed_time_us=now),entity_id='observer',scope='world')
        s=MediaSemanticService(r.work.world.cognition);cid=s.prepare('recover',mid,data)
        if cut=='calling':
            def stop(req):os.kill(os.getpid(),signal.SIGKILL)
            t.exchange=stop
        if cut=='proposed':kill_after_commit(r.store,'world.cognition_proposed')
        s.execute(cid)
        if cut=='belief':kill_after_commit(r.store,'world.belief_revision')
        result=s.ground(cid,entity_id='device')
        r.work.world.observe(result['semantic_memory_ids'][0])
        if cut=='cycle':kill_after_commit(r.store,'subject.cycle_accepted')
        for _ in range(32):clock.advance(SECOND);r.step()
    raise RuntimeError('cut not reached')
if __name__=='__main__':main()
