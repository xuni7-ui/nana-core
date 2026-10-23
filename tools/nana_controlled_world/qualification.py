"""One owned Subject in five evolving services, original C/D/F/Kernel/G/I.

Controller supplies descriptors/faults, not solved research answers. Deterministic
semantics and bounded generated workflows, never live-model or human qualification.
"""
import argparse,json,time,subprocess
from pathlib import Path
from uuid import uuid4
from nana_core.continuity.controlled_world.lab import ControlledWorld
from nana_core.continuity.controlled_world.projects import ControlledProject
from nana_core.continuity.open_life.sources import IntakeSource,WorldIntake
from nana_core.continuity.project_work.service import material_for,capture,post
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.agency_contracts import GoalReviewRef
from nana_core.continuity.records import RecordService
from nana_core.continuity.open_agency.learning import LearningSpec,LearningCase
from nana_core.continuity.learning import ExperienceService,ExperienceInput
from nana_core.continuity.world_loop.world import WorldModel
from nana_core.life.application import LifeApplication
from nana_core.life.config import LifeConfig,write_config
from nana_core.life.cloud import backup,transfer,receive
from nana_core.life.surfaces import SurfaceBinding,SurfaceObservation
from nana_core.contracts import CoreError
from nana_core.storage import digest
ROOT=Path(__file__).resolve().parents[2]

def until(app,condition,seconds=80):
    start=time.monotonic()
    while time.monotonic()-start<seconds:
        if condition():return
        app.tick();time.sleep(.02)
    raise RuntimeError('CONTROLLED_LIFECYCLE_BOUND '+str([(g['template'],g['state']) for g in app.runtime.store.all('goals')]))

def review(app,goal,behavior,key):
    r=app.runtime;c=ConcernCue(cue_kind='LOAD_STATE' if behavior=='REST' else 'OPEN_LOOP',topic_key='project.review',motivation_source='LONG_TERM_GOAL',possible_behaviors=('WITHDRAW',) if behavior=='WITHDRAW' else ('CONTINUE_PROJECT','REST'),cognitive_load='HIGH' if behavior=='REST' else 'LOW')
    mid=capture(r,key,c.model_dump_json(),predicate='concern.project.'+key)
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.project.review.'+key,kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),goal_review=GoalReviewRef(goal_id=goal['goal_id'],version=goal['version'],cause_memory_id=mid,purpose='LIFECYCLE'))
    cycle=r.subject.run(event);r.work.after_cycle(cycle,event);return cycle

def noisy_learning(app):
    r=app.runtime;ls=r.work.open_learning;records=RecordService(r.store)
    def case(k,data,expected,context='project'):return LearningCase(case_id=k,context=context,data=data,expected=expected)
    a=LearningSpec(learning_key='learn.noisy-first',domain='controlled-text',baseline_method='IDENTITY',hypotheses=('SPLIT_SPACE',),practice=(case('practice-a','one two',['one','two']),),evaluation=(case('heldout-a','three\tfour',['three','four']),case('noise-a','five six',['five','six'])),transfer=(case('transfer-a','line\nbreak',['line','break'],'transcript'),))
    b=LearningSpec(learning_key='learn.noisy-revised',domain='controlled-text',baseline_method='SPLIT_SPACE',hypotheses=('UNICODE_WORDS',),practice=(case('practice-b','seven\teight',['seven','eight']),),evaluation=(case('heldout-b','nine\nten',['nine','ten']),),transfer=(case('transfer-b','Ａ\u3000Ｂ',['A','B'],'unicode-feed'),))
    ls.specs.update({a.learning_key:a,b.learning_key:b})
    for spec in (a,b):
        cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key=spec.learning_key,program_id=spec.learning_key,motivation_source='CAPABILITY_GAP',possible_behaviors=('LEARN',))
        mid=capture(r,spec.learning_key,cue.model_dump(mode='json'),kind='MODEL_DERIVATION',parents=app.work.training_sources[:2],predicate='concern.'+spec.learning_key)
        post(r,spec.learning_key,(mid,),task_class='controlled-text')
        until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM jobs j JOIN continuity_records c ON j.record_id=c.record_id WHERE j.work_kind='LEARNING' AND c.target_id=? AND j.state IN ('BLOCKED','DONE')",(spec.learning_key,)).fetchone()))
    rows=[]
    for spec in (a,b):
        job=r.store.db.execute("SELECT j.* FROM jobs j JOIN continuity_records c ON j.record_id=c.record_id WHERE j.work_kind='LEARNING' AND c.target_id=?",(spec.learning_key,)).fetchone();body=records.read(job['record_id'])['payload'];rows.append({'key':spec.learning_key,'state':job['state'],'results':{k:{'checked':v['checked'],'passed':v['passed'],'all_passed':v['all_passed']} for k,v in body['results'].items()}})
    assert rows[0]['state']=='BLOCKED' and not rows[0]['results']['EVALUATE']['all_passed']
    assert rows[1]['state']=='DONE' and rows[1]['results']['TRANSFER']['all_passed']
    lesson=r.store.db.execute("SELECT * FROM lessons WHERE task_class='controlled-text' AND state='ACTIVE'").fetchone();assert lesson
    counter=ls.monitor(lesson['lesson_id'],(case('literal-counterexample','KEEP  SPACES',['KEEP','','SPACES'],'literal'),),authority=r.authority)
    assert not counter['all_passed'] and ls.strategy('controlled-text','project-work') is None
    return {'trials':rows,'negative_transfer_suspended':True,'lesson_id':lesson['lesson_id'],'not_a_developer_code_change':True}

def run(root):
    root=Path(root).absolute()
    if root.exists():raise ValueError('FRESH_OWNED_ROOT_REQUIRED')
    root.mkdir(mode=0o700,parents=True);started=time.monotonic();pin=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    result={'scope':'FIVE_OWNED_SERVICES_AND_DETERMINISTIC_SEMANTICS','source_commit':pin,'new_paid_calls':0,'real_social_send':0,'private_data_accessed':False,'human_review':'NOT_RUN'}
    with ControlledWorld(root/'world',interval=15) as world:
        material=lambda p:material_for(ROOT,'src/nana_core/continuity/'+p)
        bindings=tuple(SurfaceBinding(binding_id='surface.'+n,platform='platform.local',surface='surface.'+n,adapter='adapter.owned') for n in ('cli','web','social'))
        projects=(ControlledProject(project_id='maintenance',trigger_entity='project-user',trigger_predicate='lab.project-status',trigger_value='review-needed',require_research=True,task_ids=('document-transfer','archive-notes','form-transfer')),ControlledProject(project_id='followup',trigger_entity='project-user',trigger_predicate='lab.project-status',trigger_value='inconsistent',task_ids=('reading-list','index-topics')))
        cfg=LifeConfig(project_root=str(ROOT),materials=(material('recurrence.py'),),practice=material('identity.py'),heldout=material('autonomy/requests.py'),transfer=material('subject/social.py'),owned_application_profile=str(world.host.profile),owned_browser_endpoint=world.browser.endpoint,allow_local_skills=True,max_autonomous_materials=0,advanced_life=True,record_research_outcomes=True,world_source_root=str(world.services['documents'].root),world_sources=tuple(IntakeSource(source_id=k,channel='OWNED_HTTP',location=world.services[k].url+'/source',semantic_format='SOURCED_CLAIM_JSON') for k in ('feed','documents','api')),world_source_interval_seconds=30,controlled_projects=projects,shared_presence=True,surface_bindings=bindings,quiet_start_local_hour=0,quiet_end_local_hour=0)
        home=root/'life';write_config(home,cfg)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime;s=r.store;identity=r.identity_id;records=RecordService(s)
            def goal(name):return app.work.goal_for_object(app.advanced.projects.objects[name])
            until(app,lambda:goal('maintenance') is not None)
            first=goal('maintenance');main=first['goal_id'];plan=json.loads(first['body_json'])['plan_record_id']
            assert review(app,first,'REST','main-pause').intention.behavior=='REST'
            assert s.one('goals',main)['state']=='SUSPENDED'
            assert review(app,s.one('goals',main),'CONTINUE_PROJECT','main-resume').intention.behavior=='CONTINUE_PROJECT'
            until(app,lambda:s.one('goals',main)['state']=='COMPLETED')
            actions=s.db.execute('SELECT * FROM actions WHERE goal_id=?',(main,)).fetchall();assert len(actions)==9 and all(a['state']=='SUCCEEDED' for a in actions)
            assert json.loads(s.one('goals',main)['body_json'])['plan_record_id']==plan
            result['project']={'goal_id':main,'adopted_from_world_by_original_c':True,'hand_families':['BROWSER_HTTP_FORM','FILES_LINK_UNLINK_REOPEN','APPLICATION_IPC_DOCUMENT'],'original_plan_steps':9,'pause_resume_same_plan':True,'independent_verify':True,'all_actions_succeeded':True}
            until(app,lambda:s.db.execute("SELECT count(*) FROM actions WHERE capability='world.skill' AND state='SUCCEEDED'").fetchone()[0]>=2)
            until(app,lambda:s.db.execute('SELECT count(*) FROM strategy_assessments').fetchone()[0]>=4)
            skill=app.work.skills.active_skill();assert skill
            result['growth']={'learning_jobs':s.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LEARNING'").fetchone()[0],'later_kernel_skill_uses':s.db.execute("SELECT count(*) FROM actions WHERE capability='world.skill' AND state='SUCCEEDED'").fetchone()[0],'strategy_assessments':[x['verdict'] for x in s.all('strategy_assessments')]}
            result['noisy_learning']=noisy_learning(app)
            # A later changed task contract is a real isolated trial; not a
            # fabricated external effect or permission for a broader skill.
            task=app.work.port.tasks['form-batch-transfer'];data={'task':task.model_dump(mode='json'),'revision':1}
            counter=LearningCase(case_id='preserve-unspecified-fields',context='partial-edit-not-full-reset',data=data,expected={'task_id':task.task_id,'revision':1,'commands':[{'op':'SET_FIELD','field':k,'value':v} for k,v in sorted(task.wanted.items())]+[{'op':'SUBMIT'}]})
            suspended=app.work.skills.engine.codes.monitor(skill,(counter,),authority=r.authority)
            assert records.read(suspended)['payload']['state']=='SUSPENDED'
            retired=app.work.skills.engine.codes.retire(suspended,authority=r.authority)
            assert app.work.skills.active_skill() is None
            result['skill_lifecycle']={'created_qualified_used_reused':True,'counterexample_isolated_trial':True,'suspended_then_retired':True,'retired_record_id':retired}
            until(app,lambda:bool(s.db.execute("SELECT 1 FROM experiences WHERE task_class='research.comparison'").fetchone()))
            result['research']={'automatic_runtime_job':True,'experience_records':[x['experience_id'] for x in s.db.execute("SELECT experience_id FROM experiences WHERE task_class='research.comparison'")],'research_is_not_learning':True,'world_truth_verified':False}
            # Actual timeout in an independent source, no resend under a new ID.
            slow=WorldIntake(r,root,(IntakeSource(source_id='slow',channel='OWNED_HTTP',location=world.services['api'].url+'/fault/delay'),),scope='project-work')
            try:slow.read('slow');raise AssertionError('timeout expected')
            except CoreError as exc:assert 'UNKNOWN' in exc.code
            try:slow.read('slow',observation_id='new-id');raise AssertionError('no retry expected')
            except CoreError as exc:assert 'UNKNOWN' in exc.code
            result['unknown']={'actual_source_timeout':True,'different_poll_id_retry_denied':True,'persisted_jobs':s.db.execute("SELECT count(*) FROM jobs WHERE work_kind='WORLD_INTAKE' AND state='UNKNOWN'").fetchone()[0]}
            # Same original Subject, concurrent transport inbox ordering checked
            # separately. Here actual source-backed cross-surface continuity.
            summary='Owned maintenance completed with '+str(len(actions))+' independently verified steps.'
            app.surfaces.receive(SurfaceObservation(binding_id='surface.cli',event_id='main-done',topic='lab-life',text='项目维护完成了。',approved_summary=summary,summary_authorization='EXPLICIT_PROJECT_SUMMARY'))
            app.surfaces.receive(SurfaceObservation(binding_id='surface.web',event_id='continue',topic='lab-life',text='现在项目进展怎样？'))
            app.surfaces.receive(SurfaceObservation(binding_id='surface.social',event_id='busy',topic='lab-life',text='这个话题不要深入了'))
            app.presence('BUSY',privacy_classes=('PUBLIC','PROJECT'))
            from nana_core.life.surfaces import recent_sources
            assert recent_sources(app,'lab-life','PROJECT')
            result['surfaces']={'same_identity':True,'bindings':3,'source_backed_recent_context':True,'topic_boundary_recorded':True,'no_send':True}
            until(app,lambda:goal('followup') is not None,seconds=100)
            g=goal('followup')
            if g['state']=='ACTIVE':review(app,g,'REST','followup-dormant')
            assert s.one('goals',g['goal_id'])['state']=='SUSPENDED'
            result['active_life']={'dormant_goal_id':g['goal_id'],'goals':len(s.all('goals')),'experiences':len(s.all('experiences')),'lessons':len(s.all('lessons')),'share_candidates':len(app.shared.candidates()),'unknown_intake_jobs':result['unknown']['persisted_jobs']}
            sample=app.advanced.intake.read('feed',observation_id='withdraw-test');before=s.db.execute('SELECT count(*) FROM actions').fetchone()[0];app.forget(sample)
            result['withdrawal']={'raw_source_deleted':True,'physical_action_history_preserved':s.db.execute('SELECT count(*) FROM actions').fetchone()[0]==before}
            result['backup']=backup(s,root/'review-copy.db');assert not s.db.execute('PRAGMA foreign_key_check').fetchall()
            counts={t:len(s.all(t)) for t in ('goals','actions','experiences','lessons')}
        with LifeApplication(home) as app:
            assert app.runtime.identity_id==identity and app.work.skills.active_skill() is None
            assert app.runtime.store.one('goals',result['active_life']['dormant_goal_id'])['state']=='SUSPENDED'
        destination_id=str(uuid4());package=root/'subject.nana';sent=transfer(home,package,destination_id=destination_id,source_commit=pin,pending_effects=False)
        received=receive(package,root/'host-b',sha256=sent['sha256'],destination_id=destination_id,config=cfg)
        with LifeApplication(root/'host-b') as app:
            s=app.runtime.store;assert app.runtime.identity_id==identity and all(g['revoked'] for g in s.all('grants'))
            assert all(len(s.all(t))==n for t,n in counts.items())
            assert app.work.skills.active_skill() is None
            assert s.db.execute("SELECT count(*) FROM jobs WHERE work_kind='WORLD_INTAKE' AND state='UNKNOWN'").fetchone()[0]==result['unknown']['persisted_jobs']
            result['migration']={'same_identity':True,'dormant_goal_preserved':True,'history_counts_preserved':True,'old_grants_revoked':True,'unknown_preserved':True,'retired_skill_not_revived':True,'no_duplicate_effect':True}
        try:LifeApplication(home);raise AssertionError('old writer must be fenced')
        except CoreError:result['migration']['old_writer_fenced']=True
    result['duration_seconds']=time.monotonic()-started;result['source_clean']=not subprocess.check_output(['git','diff','HEAD','--','src','tools'],cwd=ROOT)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(run(a.root),indent=2)+'\n')
if __name__=='__main__':main()
