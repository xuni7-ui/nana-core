"""Pinned actual wall-clock owned residency. Never upgrades a running snapshot."""
import argparse,json,time,os,hashlib,subprocess,resource,signal
from pathlib import Path
from nana_core.continuity.controlled_world.lab import ControlledWorld,_atomic
from nana_core.continuity.open_life.sources import IntakeSource
from nana_core.continuity.controlled_world.projects import ControlledProject
from nana_core.continuity.project_work.service import material_for
from nana_core.life.config import LifeConfig,write_config
from nana_core.life.application import LifeApplication
from nana_core.storage import canonical
ROOT=Path(__file__).resolve().parents[2]

def fingerprints():
    names=subprocess.check_output(['git','ls-files','src','tools/nana_controlled_world'],cwd=ROOT,text=True).splitlines()
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names if (ROOT/n).is_file()}

def config(root,world):
    material=lambda p:material_for(ROOT,'src/nana_core/continuity/'+p)
    return LifeConfig(project_root=str(ROOT),materials=(material('recurrence.py'),),practice=material('identity.py'),heldout=material('autonomy/requests.py'),transfer=material('subject/social.py'),owned_application_profile=str(world.host.profile),owned_browser_endpoint=world.browser.endpoint,allow_local_skills=True,max_autonomous_materials=0,advanced_life=True,record_research_outcomes=True,controlled_projects=(ControlledProject(project_id='maintenance',trigger_entity='project-user',trigger_predicate='lab.project-status',trigger_value='review-needed',require_research=True,task_ids=('document-transfer','archive-notes','form-transfer')),ControlledProject(project_id='followup',trigger_entity='project-user',trigger_predicate='lab.project-status',trigger_value='inconsistent',task_ids=('reading-list','index-topics'))),world_source_root=str(world.services['documents'].root),world_sources=(IntakeSource(source_id='feed',channel='OWNED_HTTP',location=world.services['feed'].url+'/source',semantic_format='SOURCED_CLAIM_JSON'),IntakeSource(source_id='api',channel='OWNED_HTTP',location=world.services['api'].url+'/source',semantic_format='SOURCED_CLAIM_JSON'),IntakeSource(source_id='document',channel='LOCAL_FILE',location='status.json',semantic_format='SOURCED_CLAIM_JSON')),world_source_interval_seconds=300,shared_presence=True,quiet_start_local_hour=0,quiet_end_local_hour=0)

def run(root,seconds):
    root=Path(root).absolute()
    if root.exists():raise ValueError('FRESH_PINNED_ROOT_REQUIRED')
    root.mkdir(mode=0o700,parents=True);pin=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','diff','HEAD','--','src','tools'],cwd=ROOT):raise ValueError('PINNED_CLEAN_SOURCE_REQUIRED')
    hashes=fingerprints();_atomic(root/'source-manifest.json',{'source_head':pin,'files':hashes,'root':str(ROOT),'requested_seconds':seconds})
    start=time.monotonic();cpu=time.process_time();exit_code=1;samples=[];failure=None;identity=None;checks={};last_sample=-60;running=True
    def stop(*args):
        nonlocal running
        running=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        with ControlledWorld(root/'world',interval=300) as world:
            home=root/'life';write_config(home,config(root,world))
            with LifeApplication(home,bootstrap_grant=True) as app:
                r=app.runtime;s=r.store;identity=r.identity_id
                idle_ticks=0;active_ticks=0
                while running and time.monotonic()-start<seconds:
                    stamp=r.cadence.stamp();activity=app.tick()
                    if activity:active_ticks+=1
                    else:idle_ticks+=1
                    elapsed=time.monotonic()-start
                    if elapsed-last_sample>=30:
                        last_sample=elapsed
                        sample={'elapsed_seconds':elapsed,'cpu_seconds':time.process_time()-cpu,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'fds':len(os.listdir('/proc/self/fd')),'threads':len(os.listdir('/proc/self/task')),'queue':r.queue.depth(),'db_family_bytes':sum(p.stat().st_size for p in (home/'subject').glob('self.db*') if p.is_file())}
                        for t in ('goals','actions','experiences','lessons','subject_cycles','jobs'):sample[t]=s.db.execute('SELECT count(*) FROM '+t).fetchone()[0]
                        sample['unknown_actions']=s.db.execute("SELECT count(*) FROM actions WHERE state='UNKNOWN'").fetchone()[0]
                        sample['pending_opportunities']=s.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_OPPORTUNITY' AND state='WAITING'").fetchone()[0]
                        sample['pending_intentions']=s.db.execute("SELECT count(*) FROM subject_intentions WHERE state='PENDING'").fetchone()[0]
                        sample['research_jobs']=s.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_RESEARCH'").fetchone()[0]
                        sample['provider_calls']=s.db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]
                        sample['idle_ticks']=idle_ticks;sample['active_ticks']=active_ticks
                        sample['share_candidate_records']=s.db.execute("SELECT count(*) FROM continuity_records WHERE target_id LIKE 'shared-candidate:%'").fetchone()[0]
                        sample['services_alive']=all(x.proc.poll() is None for x in world.services.values()) and world.browser.proc.poll() is None and world.host.proc.poll() is None
                        samples.append(sample)
                        _atomic(root/'progress.json',{'status':'RUNNING_NOT_QUALIFIED','source_head':pin,'identity_id':identity,'requested_seconds':seconds,'sample':sample})
                    r.cadence.wait(min(1.,r.next_wait_seconds()),stamp)
                checks={'foreign_keys_clean':not s.db.execute('PRAGMA foreign_key_check').fetchall(),'quick_check':s.db.execute('PRAGMA quick_check').fetchone()[0]=='ok','one_identity':s.db.execute('SELECT count(*) FROM identities').fetchone()[0]==1,'zero_provider':s.db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]==0}
                before=s.db.execute('SELECT count(*) FROM actions').fetchone()[0]
            with LifeApplication(home) as reopened:
                checks['same_identity_restart']=reopened.runtime.identity_id==identity
                checks['no_action_replay']=reopened.runtime.store.db.execute('SELECT count(*) FROM actions').fetchone()[0]==before
            checks['source_bytes_unchanged']=fingerprints()==hashes
            checks['source_head_unchanged']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==pin
            checks['duration']=time.monotonic()-start>=seconds
            exit_code=0 if all(checks.values()) else 1
    except BaseException as exc:
        failure=type(exc).__name__+':'+str(exc)[:256]
    result={'status':'PASS_PINNED_OWNED_RESIDENCY' if exit_code==0 else 'FAILED_OR_INTERRUPTED_NOT_QUALIFIED','exit_code':exit_code,'duration_seconds':time.monotonic()-start,'requested_seconds':seconds,'source_head_start':pin,'source_head_end':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'identity_id':identity,'checks':checks,'samples':samples,'failure':failure,'scope':'OWNED_LOCAL_SERVICES_NO_PAID_MODELS_NO_SOCIAL_NO_PRIVATE_DATA'}
    _atomic(root/'result.json',result)
    return exit_code

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--seconds',type=int,default=18000);a=p.parse_args()
    if not 60<=a.seconds<=43200:p.error('60..43200 bounded real seconds')
    raise SystemExit(run(a.root,a.seconds))
if __name__=='__main__':main()
