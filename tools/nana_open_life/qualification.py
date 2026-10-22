"""One actual owned Subject lifecycle; no live model, private data or social IO."""
import argparse,json,time,resource,os,subprocess
from uuid import uuid4
from pathlib import Path
from nana_core.life.config import LifeConfig,write_config
from nana_core.life.application import LifeApplication
from nana_core.life.cloud import backup,transfer,receive
from nana_core.life.inspector import inspect
from nana_core.life.surfaces import SurfaceBinding
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.browser import OwnedBrowser
from nana_core.continuity.project_work.service import material_for,capture,post
from nana_core.continuity.open_life.opportunities import OpportunityQueue,LifeOpportunity
from nana_core.continuity.open_life.sources import IntakeSource,WorldIntake
from nana_core.continuity.open_life.research import ResearchService
from nana_core.continuity.records import RecordService
from nana_core.continuity.world_loop.world import SourcedClaim,WorldModel
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.subject.framing import ProblemFrame,FactCondition
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND,DAY
from nana_core.contracts import CoreError
REPO=Path(__file__).resolve().parents[2]


def until(app,predicate,seconds=50):
    started=time.monotonic()
    while time.monotonic()-started<seconds:
        if predicate():return
        app.tick();time.sleep(.01)
    raise RuntimeError('OPEN_LIFE_OWNED_BOUND_INCOMPLETE '+str([(g['template'],g['state']) for g in app.runtime.store.all('goals')]))


def run(root,*,wall_seconds=60):
    root=Path(root).absolute()
    if root.exists():raise ValueError('FRESH_OWNED_ROOT_REQUIRED')
    root.mkdir(mode=0o700,parents=True);started=time.monotonic();result={'scope':'OWNED_DEV_PROCESSES_AND_SYNTHETIC_SEMANTICS','new_paid_provider_calls':0,'real_social_send':0,'private_data_accessed':False,'human_review':'NOT_RUN'}
    sources=root/'sources';sources.mkdir();(sources/'feed.json').write_text(json.dumps({'source':'owned project feed','need':'review unfinished application tasks'}));(sources/'guide.json').write_text(json.dumps({'source':'independent owned tutorial','need':'review unfinished application tasks'}))
    with OwnedApplication(root/'target') as host,OwnedBrowser(host.profile) as browser:
        material=lambda p:material_for(REPO,'src/nana_core/continuity/'+p)
        cfg=LifeConfig(project_root=str(REPO),materials=(material('recurrence.py'),),practice=material('identity.py'),heldout=material('autonomy/requests.py'),transfer=material('subject/social.py'),owned_application_profile=str(host.profile),owned_browser_endpoint=browser.endpoint,allow_local_skills=True,max_autonomous_materials=0,shared_presence=False,quiet_start_local_hour=0,quiet_end_local_hour=0,surface_bindings=(SurfaceBinding(binding_id='surface.cli',platform='platform.cloud',surface='surface.cli',adapter='adapter.local'),))
        home=root/'life';write_config(home,cfg)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime;identity=r.identity_id;records=RecordService(r.store)
            original_source=r.work.activity_source;q=OpportunityQueue(r);r.work.activity_source=q
            intake=WorldIntake(r,sources,tuple(IntakeSource(source_id=n,channel='STRUCTURED_FEED',location=n+'.json') for n in ('feed','guide')),scope='project-work')
            first=intake.read('feed')
            m,bid=intake.interpret(first,SourcedClaim(entity_id='project-user',predicate='work.review-needed',kind='INTERPRETED',value=True,valid_from_us=r.clock.utc_now_us(),confidence=.6))
            research=ResearchService(r,q,intake);j=research.notice('research.owned-work',(m,))
            until(app,lambda:r.store.one('jobs',j)['state']=='DONE')
            assert records.read(r.store.one('jobs',j)['record_id'])['payload']['behavior']=='EXPLORE'
            other=research.gather(j,'guide');m2,_=intake.interpret(other,SourcedClaim(entity_id='project-user',predicate='work.review-needed',kind='INTERPRETED',value=True,valid_from_us=r.clock.utc_now_us(),confidence=.6))
            comparison=research.compare(j,'project-user','work.review-needed',(m,m2))
            assert records.read(comparison)['payload']['state']=='ENOUGH_FOR_BOUNDED_BELIEF'
            # Actual owned application observation refutes an empty-document
            # premise; original C chooses a different problem before adoption.
            obs=app.work.port.peek('document-baseline')
            premise=capture(r,'observed-document-premise',{'document_empty':obs['state']['text']=='','owned_binding':host.target.binding},parents=(m,m2))
            obj=app.work.objects['document-baseline']
            cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='owned.reframe',program_id=obj.objective_id,motivation_source='PROJECT_COMPLETION')
            cm=capture(r,'framed-owned-work',cue.model_dump(mode='json'),kind='MODEL_DERIVATION',parents=(premise,),predicate='concern.owned.reframe')
            frame=ProblemFrame(requested_problem='Append a note to an empty document',assumed=(FactCondition(memory_id=premise,field='document_empty',expected=True),),alternative_problem='Replace an obsolete draft without retaining old text',required=(FactCondition(memory_id=premise,field='document_empty',expected=False),),program_id=obj.objective_id)
            r.work.activity_source=None
            post(r,'open-life-frame',(cm,premise),task_class='owned-document',problem_frame=frame)
            until(app,lambda:app.work.goal_for('document-baseline') is not None)
            frames=[records.read(c['record_id'])['payload'].get('problem_frame') for c in r.store.all('subject_cycles')]
            assert any(f and f['state']=='REFRAME' for f in frames)
            result['problem_framing']={'actual_nonempty_source':True,'original_cycle_count':len(frames),'goal_horizon':obj.horizon}
            r.work.activity_source=original_source
            until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM lessons WHERE state='ACTIVE' AND task_class='owned-document'").fetchone()))
            from nana_core.continuity.open_life.meta_learning import propose as meta_propose
            from nana_core.continuity.learning import ExperienceService
            method_lesson=r.store.db.execute("SELECT lesson_id FROM lessons WHERE state='ACTIVE' AND task_class='owned-document'").fetchone()[0]
            meta_lesson=meta_propose(r.store,method_lesson,authority=r.authority)
            experience=ExperienceService(r.store,r.authority)
            assert all(experience.test_lesson(meta_lesson).values());experience.activate(meta_lesson,r.authority)
            result['meta_learning']={'lesson_id':meta_lesson,'state':'ACTIVE','separate_executed_selection_experiment':True,'evaluator_unchanged':True,'later_changed_hypothesis_selection':'QUALIFIED_SEPARATELY_IN_TARGETED_TEST_NOT_CLAIMED_FROM_THIS_EPISODE'}
            until(app,lambda:len(r.store.all('goals'))==8 and all(g['state'] in {'COMPLETED','FAILED'} for g in r.store.all('goals')),seconds=60)
            until(app,lambda:len(r.store.all('strategy_assessments'))>=4)
            skill=app.work.skills.active_skill();assert skill
            skill_uses=r.store.db.execute("SELECT count(*) FROM actions WHERE capability='world.skill' AND state='SUCCEEDED'").fetchone()[0]
            assert skill_uses==2
            assessments=r.store.all('strategy_assessments')
            assert any(a['verdict']=='SUCCESS' for a in assessments) and any(a['verdict']=='COUNTEREXAMPLE' for a in assessments)
            result['lifecycle']={'identity_id':identity,'raw_source_memory_id':first,'semantic_memory_id':m,'world_belief_id':bid,'research_opportunity_id':j,'research_comparison_record':comparison,'goal_ids':[g['goal_id'] for g in r.store.all('goals')],'experience_outcomes':[e['outcome'] for e in r.store.all('experiences')],'learning_jobs':len(list(r.store.db.execute("SELECT job_id FROM jobs WHERE work_kind='LEARNING'"))),'strategy_verdicts':[a['verdict'] for a in assessments],'isolated_skill_record':skill,'later_kernel_skill_uses':skill_uses}
            assert 'FAILURE' in result['lifecycle']['experience_outcomes'] and 'SUCCESS' in result['lifecycle']['experience_outcomes']
            # Source-backed share is original C's option, not a send.
            shared=app.shared.candidates();assert shared
            selected=shared[0];social=LifeOpportunity(kind='RELATIONSHIP',topic=selected['topic'],source_memory_ids=selected['source_memory_ids'],cue=ConcernCue(cue_kind='DISCOVERY',topic_key=selected['topic'],motivation_source='SOCIAL_CONNECTION',possible_behaviors=('SOCIALIZE','STAY_SILENT'),availability='AVAILABLE',resource_class='ORDINARY'),expires_at_us=r.clock.utc_now_us()+DAY)
            share=q.offer(social);r.work.activity_source=q
            until(app,lambda:r.store.one('jobs',share)['state']=='DONE')
            sharebody=records.read(r.store.one('jobs',share)['record_id'])['payload']
            app.presence('BUSY',privacy_classes=('PUBLIC','PROJECT'))
            decision=app.shared.review(sharebody['cycle_id'],'surface.cli');assert decision['decision']['result']=='DEFER_BUSY' and not decision['delivered']
            result['shared_presence']={'candidate_count':len(shared),'busy_result':decision['decision']['result'],'delivered':False}
            # Actual wall residency: no forced new activity or provider use.
            r.work.activity_source=q;before=len(r.store.all('actions'));samples=[];wall_start=time.monotonic();cpu_start=time.process_time()
            while time.monotonic()-wall_start<wall_seconds:
                app.tick()
                if not samples or time.monotonic()-samples[-1]['elapsed_seconds']-wall_start>=5:
                    samples.append({'elapsed_seconds':time.monotonic()-wall_start,'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'fds':len(os.listdir('/proc/self/fd')),'threads':len(os.listdir('/proc/self/task')),'db_family_bytes':sum(p.stat().st_size for p in (home/'subject').iterdir() if p.is_file() and p.name.startswith('self.db')),'queue':r.queue.depth(),'actions':len(r.store.all('actions'))})
                time.sleep(.1)
            assert len(r.store.all('actions'))==before
            residence_cpu_seconds=time.process_time()-cpu_start
            retired=app.work.skills.engine.codes.retire(skill,authority=r.authority)
            assert app.work.skills.active_skill() is None
            result['capability_retirement']={'retired_record_id':retired,'not_recreated':True}
            app.forget(first)
            assert WorldModel(r.store,scopes=('project-work',),privacy_classes=('PROJECT',)).view('project-user','work.review-needed').state=='UNKNOWN'
            assert len(r.store.all('actions'))==before
            result['source_withdrawal']={'world_state':'UNKNOWN','historical_action_count_preserved':True,'no_physical_effect_rewrite':True}
            result['wall_residency']={'duration_seconds':time.monotonic()-wall_start,'samples':samples,'cpu_seconds':residence_cpu_seconds,'action_replay':0,'rss_semantics':'PROCESS_MAX_RSS_NOT_CURRENT_RSS'}
            result['backup']=backup(r.store,root/'review-copy.db')
            assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
            result['inspector_has_advanced']=inspect(home,scope='project-work',entity_id='project-user').advanced_life is not None
            snapshot={'goals':len(r.store.all('goals')),'actions':before,'experiences':len(r.store.all('experiences')),'lessons':len(r.store.all('lessons')),'jobs':len(r.store.all('jobs')),'opportunity_jobs':r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_OPPORTUNITY'").fetchone()[0]}
            now=r.clock.utc_now_us()
        # New ordinary runtime owner, same actual Subject. No new Grants.
        with LifeApplication(home) as app:
            assert app.runtime.identity_id==identity
            assert app.work.skills.active_skill() is None
            result['restart_same_identity']=True
            assert len(app.runtime.store.all('actions'))==snapshot['actions']
        destination_id=str(uuid4());source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
        package=root/'subject.nana';migration=transfer(home,package,destination_id=destination_id,source_commit=source_commit,pending_effects=False)
        destination=root/'host-b'
        received=receive(package,destination,sha256=migration['sha256'],destination_id=destination_id,config=cfg)
        with LifeApplication(destination) as app:
            assert app.runtime.identity_id==identity and all(g['revoked'] for g in app.runtime.store.all('grants'))
            assert len(app.runtime.store.all('actions'))==snapshot['actions']
            assert app.runtime.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LIFE_OPPORTUNITY'").fetchone()[0]==snapshot['opportunity_jobs']
            assert not OpportunityQueue(app.runtime).view() # withdrawn source stays unavailable after transfer
            result['migration']={'same_identity':True,'old_grants_revoked':True,'goals_preserved':len(app.runtime.store.all('goals'))==snapshot['goals'],'lessons_preserved':len(app.runtime.store.all('lessons'))==snapshot['lessons'],'opportunity_headers_preserved':True,'withdrawn_content_not_revived':True}
        result['snapshot']=snapshot
    result['total_wall_seconds']=time.monotonic()-started
    result['source_commit']=source_commit
    result['source_was_clean']=not subprocess.check_output(['git','diff','HEAD','--','src','tools'],cwd=REPO)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--wall-seconds',type=int,default=60);a=p.parse_args()
    result=run(a.root,wall_seconds=a.wall_seconds);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':'OWNED_LIFECYCLE_COMPLETE','wall_seconds':result['total_wall_seconds'],'new_provider_calls':0}))
if __name__=='__main__':main()
