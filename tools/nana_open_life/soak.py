"""Finite advanced attention virtual-time soak, not old Foundation 24h replay."""
import argparse,json,time
from pathlib import Path
from nana_core.continuity.world_loop.reference import open_runtime,capture
from nana_core.continuity.open_life.opportunities import OpportunityQueue,LifeOpportunity
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import HOUR,DAY,SECOND

def run(root,days=60):
    if not 1<=days<=90:raise ValueError('bounded virtual duration required')
    root=Path(root);root.mkdir(mode=0o700,parents=True,exist_ok=False);clock=VirtualClock();started=time.monotonic()
    with open_runtime(root/'s.db',clock) as r:
        q=OpportunityQueue(r);rootm=capture(r,'finite-question',{'source':'same unchanged owned project observation'})
        candidates=[]
        for i,behavior in enumerate(('EXPLORE','WATCH','REST','SOCIALIZE')):
            topic='finite.topic-'+str(i)
            c=LifeOpportunity(kind='CURIOSITY' if i==0 else 'REST' if i==2 else 'RELATIONSHIP' if i==3 else 'MAINTENANCE',topic=topic,source_memory_ids=(rootm,),cue=ConcernCue(cue_kind='DISCOVERY',topic_key=topic,motivation_source='CURIOSITY' if i==0 else 'REST' if i==2 else 'SOCIAL_CONNECTION' if i==3 else 'MAINTENANCE',possible_behaviors=(behavior,),availability='BUSY' if i==3 else 'UNKNOWN',resource_class='ORDINARY'),expires_at_us=clock.utc_now_us()+DAY)
            candidates.append(c);q.offer(c)
        peaks={'pending':0,'runtime_queue':0,'opportunity_waiting':0};daily=[]
        for day in range(days):
            for hour in range(24):
                # Re-presenting unchanged facts cannot regenerate cycles/goals.
                for c in candidates:q.offer(c)
                for _ in range(4):
                    q.opportunity();clock.advance(SECOND);r.step()
                clock.advance(HOUR-4*SECOND);r.step()
                for key,sql in [('pending',"SELECT count(*) FROM subject_intentions WHERE state='PENDING'"),('opportunity_waiting',"SELECT count(*) FROM jobs WHERE work_kind='LIFE_OPPORTUNITY' AND state='WAITING'")]:peaks[key]=max(peaks[key],r.store.db.execute(sql).fetchone()[0])
                peaks['runtime_queue']=max(peaks['runtime_queue'],r.queue.depth())
            daily.append({'virtual_day':day+1,'cycles':len(r.store.all('subject_cycles')),'events':r.store.db.execute('SELECT count(*) FROM events').fetchone()[0],'jobs':len(r.store.all('jobs')),'db_bytes':(root/'s.db').stat().st_size})
        assert peaks['pending']<=8 and peaks['runtime_queue']<=64
        assert len(r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_OPPORTUNITY'").fetchall())==4
        assert not r.store.all('actions') and not r.store.all('cognitive_requests')
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
        decisions=[]
        from nana_core.continuity.records import RecordService
        for c in r.store.all('subject_cycles'):
            b=RecordService(r.store).read(c['record_id'])['payload'];decisions.append(b['intention'].get('behavior'))
        return {'scope':'VIRTUAL_TIME_SYNTHETIC_FINITE_ATTENTION_NOT_REAL_60_DAY_RESIDENCY','days':days,'wall_seconds':time.monotonic()-started,'peaks':peaks,'daily_samples':daily,'opportunity_jobs':4,'new_paid_provider_calls':0,'actions':0,'decisions':decisions,'unchanged_fact_regeneration':0,'history_growth':'RECORDED_LINEAR_RUNTIME_AUDIT','one_subject':True}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--runtime-sources',action='store_true');a=p.parse_args();r=run_runtime_sources(a.root) if a.runtime_sources else run(a.root);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'days':r['days'],'wall_seconds':r['wall_seconds'],'peaks':r['peaks'] if 'peaks' in r else {'research_jobs':r['research_jobs'],'max_pending':r['max_pending']}}))


def run_runtime_sources(root,days=60):
    """Same original LifeApplication with automatic intake/research in virtual time."""
    if not 31<=days<=90:raise ValueError('virtual source qualification requires31–90days')
    from nana_core.life import application
    from nana_core.life.config import LifeConfig,write_config
    from nana_core.continuity.project_work.service import material_for
    from nana_core.continuity.open_life.sources import IntakeSource
    from nana_core.continuity.world_loop.world import WorldModel
    root=Path(root);root.mkdir(mode=0o700,parents=True,exist_ok=False)
    assets=root/'sources';assets.mkdir();clock=VirtualClock();start=time.monotonic()
    for i,n in enumerate(('practice','heldout','transfer')):(assets/(n+'.py')).write_text('def '+n+'():\n    return '+str(i)+'\n')
    def feed(value,until=None):
        claim={'entity_id':'project-user','predicate':'virtual.source','kind':'INTERPRETED','value':value,'valid_from_us':clock.utc_now_us(),'valid_until_us':until}
        (assets/'feed.json').write_text(json.dumps({'world_claim':claim}))
    feed('initial',clock.utc_now_us()+10*DAY)
    m=lambda n:material_for(assets,n+'.py');home=root/'life'
    write_config(home,LifeConfig(project_root=str(assets),materials=(m('practice'),),practice=m('practice'),heldout=m('heldout'),transfer=m('transfer'),max_autonomous_materials=0,idle_review_seconds=3600,advanced_life=True,world_source_interval_seconds=3600,world_sources=(IntakeSource(source_id='feed',channel='STRUCTURED_FEED',location='feed.json',semantic_format='SOURCED_CLAIM_JSON'),)))
    # Test-host clock policy only: hourly virtual jumps need the already-supported
    # long development lease. No production/runtime defaults are modified.
    original=application.runtime_config
    def virtual_config(c):
        cfg=original(c)
        return cfg.model_copy(update={'lease_us':2*HOUR,'heartbeat_us':15*60*SECOND,'idle_recall_us':HOUR,'living':cfg.living.model_copy(update={'maintenance_interval_us':HOUR})})
    application.runtime_config=virtual_config
    try:
        with application.LifeApplication(home,clock=clock) as app:
            r=app.runtime;max_pending=0;daily=[]
            for day in range(days):
                if day==30:feed('new independently observed revision')
                for hour in range(24):
                    for _ in range(4):clock.advance(SECOND);app.tick()
                    clock.advance(HOUR-4*SECOND);app.tick()
                    max_pending=max(max_pending,r.store.db.execute("SELECT count(*) FROM subject_intentions WHERE state='PENDING'").fetchone()[0])
                world=WorldModel(r.store,scopes=('project-work',),privacy_classes=('PROJECT',)).view('project-user','virtual.source')
                daily.append({'day':day+1,'world':world.state,'research_jobs':r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_RESEARCH'").fetchone()[0],'opportunity_jobs':r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_OPPORTUNITY'").fetchone()[0],'pending':max_pending})
            jobs=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_RESEARCH'").fetchall()
            assert len(jobs)==2 and all(j['state']=='DONE' for j in jobs)
            assert any(x['world']=='UNKNOWN' for x in daily[10:30])
            assert max_pending<=8 and not r.store.all('actions') and not r.store.all('cognitive_requests')
            assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
            return {'scope':'VIRTUAL_TIME_ORIGINAL_RUNTIME_AUTOMATIC_OWNED_SOURCE_RESEARCH','days':days,'wall_seconds':time.monotonic()-start,'research_jobs':len(jobs),'max_pending':max_pending,'source_expiry_to_unknown':True,'unchanged_source_no_repeat':True,'actual_source_revision_new_research':True,'paid_provider_calls':0,'daily':daily}
    finally:application.runtime_config=original

if __name__=='__main__':main()
