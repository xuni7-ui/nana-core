import os,sys,signal,json
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
home=Path(sys.argv[1]);cut=sys.argv[2];clock=VirtualClock()
with LifeApplication(home,clock=clock) as app:
    r=app.runtime
    if cut=='before-schedule':app.advanced.research_work.slice=lambda:None
    for _ in range(80):
        clock.advance(SECOND);app.tick()
        q=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_OPPORTUNITY' AND state='DONE' LIMIT 1").fetchone()
        j=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_RESEARCH' LIMIT 1").fetchone()
        if (cut=='before-schedule' and q and not j) or (cut=='after-gather' and j and j['cursor']==1 and j['state']=='WAITING'):
            (home/'cut.json').write_text(json.dumps({'identity_id':r.identity_id,'opportunity_id':q['job_id'],'cut':cut}))
            os.kill(os.getpid(),signal.SIGKILL)
    raise RuntimeError('exact research cut not reached')
