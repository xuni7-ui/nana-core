import os,signal,sys,json
from pathlib import Path
from nana_core.continuity.world_loop.reference import open_runtime,capture
from nana_core.continuity.open_life.opportunities import OpportunityQueue,LifeOpportunity
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND,DAY
root=Path(sys.argv[1]);root.mkdir(exist_ok=True)
with open_runtime(root/'s.db',VirtualClock()) as r:
    m=capture(r,'cut',{'question':'project world change'})
    q=OpportunityQueue(r)
    j=q.offer(LifeOpportunity(kind='WORLD_CHANGE',topic='cut.world',source_memory_ids=(m,),cue=ConcernCue(cue_kind='DISCOVERY',topic_key='cut.world',motivation_source='CURIOSITY',possible_behaviors=('EXPLORE','WATCH'),resource_class='ORDINARY'),expires_at_us=r.clock.utc_now_us()+DAY))
    q.opportunity()
    for _ in range(8):r.clock.source.advance(SECOND);r.step()
    (root/'cut.json').write_text(json.dumps({'job_id':j,'identity_id':r.identity_id,'cycles':len(r.store.all('subject_cycles'))}))
    os.kill(os.getpid(),signal.SIGKILL)
