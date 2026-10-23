import json
from nana_core.continuity.controlled_world.lab import ControlledWorld
from nana_core.continuity.controlled_world.projects import ControlledProject
from nana_core.continuity.open_life.sources import IntakeSource
from nana_core.continuity.agency_contracts import GoalReviewRef
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.project_work.service import capture
from nana_core.life.config import update_config
from nana_core.life.application import LifeApplication
from controlled_hands.conftest import initialize,until


def review(app,goal,kind,key):
    r=app.runtime
    c=ConcernCue(cue_kind='LOAD_STATE' if kind=='REST' else 'OPEN_LOOP',topic_key='project.review',motivation_source='LONG_TERM_GOAL',possible_behaviors=('WITHDRAW',) if kind=='WITHDRAW' else ('CONTINUE_PROJECT','REST'),cognitive_load='HIGH' if kind=='REST' else 'LOW')
    mid=capture(r,key,c.model_dump_json(),predicate='concern.project.'+key)
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.project.lifecycle.'+key,kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),goal_review=GoalReviewRef(goal_id=goal['goal_id'],version=goal['version'],cause_memory_id=mid,purpose='LIFECYCLE'))
    cycle=r.subject.run(event);r.work.after_cycle(cycle,event);return cycle


def test_automatic_multihand_project_c_pause_restart_resume(owned_root,monkeypatch):
    with ControlledWorld(owned_root/'world',interval=120) as world:
        home=owned_root/'life';cfg=initialize(home,world.host.profile,skills=False)
        project=ControlledProject(project_id='maintenance',trigger_entity='project-user',trigger_predicate='lab.project-status',task_ids=('document-transfer','archive-notes','form-transfer'),review_seconds=30)
        src=IntakeSource(source_id='feed',channel='OWNED_HTTP',location=world.services['feed'].url+'/source',semantic_format='SOURCED_CLAIM_JSON')
        update_config(home,cfg.model_copy(update={'revision':2,'advanced_life':True,'record_research_outcomes':True,'owned_browser_endpoint':world.browser.endpoint,'world_sources':(src,),'controlled_projects':(project,)}),expected_revision=1)
        with LifeApplication(home,bootstrap_grant=True) as app:
            until(app,lambda:bool(app.runtime.store.db.execute("SELECT 1 FROM goals WHERE template='owned-maintenance'").fetchone()))
            r=app.runtime;goal=r.store.db.execute("SELECT * FROM goals WHERE template='owned-maintenance'").fetchone();gid=goal['goal_id'];identity=r.identity_id
            plan=json.loads(goal['body_json'])['plan_record_id']
            actual_now=r.clock.utc_now_us
            with monkeypatch.context() as simulation:
                simulation.setattr(r.clock,'utc_now_us',lambda:actual_now()+60_000_000)
                assert app.advanced.projects.view()[0]['age_state']=='STALE' # projection-only virtual age, no effect or authority change
            cycle=review(app,goal,'REST','pause');assert cycle.intention.behavior=='REST'
            assert r.store.one('goals',gid)['state']=='SUSPENDED'
            assert app.advanced.projects.view()[0]['age_state']=='DORMANT'
            # Original autonomous share formation must not hold global load forever.
        with LifeApplication(home) as app:
            r=app.runtime;assert r.identity_id==identity
            g=r.store.one('goals',gid);assert g['state']=='SUSPENDED'
            review(app,g,'CONTINUE','resume')
            until(app,lambda:r.store.one('goals',gid)['state']=='COMPLETED')
            actions=r.store.db.execute('SELECT * FROM actions WHERE goal_id=?',(gid,)).fetchall()
            assert len(actions)==9 and all(a['state']=='SUCCEEDED' for a in actions)
            assert json.loads(r.store.one('goals',gid)['body_json'])['plan_record_id']==plan
            result=json.loads((__import__('pathlib').Path(world.host.target.workspace)/'application-state.json').read_text())
            assert result['state']['archive-notes']['values']=={'reviewed':'public project notes:draft','reference':'public project notes:raw'}
            assert result['state']['form-transfer']['values']['query']=='wind'
            until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE task_class='research.comparison'").fetchone()))
            assert not r.store.all('cognitive_requests')
            assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()


def test_shared_internal_candidate_completes_without_claiming_send(owned_root):
    with ControlledWorld(owned_root/'world',interval=120) as world:
        home=owned_root/'life';cfg=initialize(home,world.host.profile,skills=False)
        update_config(home,cfg.model_copy(update={'revision':2,'advanced_life':True,'shared_presence':True}),expected_revision=1)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime
            until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM events WHERE kind='life.share_candidate_formed'").fetchone()))
            from nana_core.continuity.records import RecordService
            record=r.store.db.execute("SELECT record_id FROM continuity_records WHERE target_id LIKE 'shared-candidate:%' LIMIT 1").fetchone()[0]
            body=RecordService(r.store).read(record)['payload']
            assert body['delivery']=='NONE' and not body['external_action'] and not body['authority_granted']
            assert r.store.one('subject_intentions',body['intention_id'])['state']=='COMPLETED'
            cycle=r.subject.result(r.store.one('subject_cycles',body['cycle_id']))
            assert cycle.intention.kind=='SOCIAL_INTERACTION' and cycle.evaluation.normative=='ENDORSED'
            assert app.shared.reconcile() is None


def test_supersession_only_links_original_c_withdrawal_and_adoption(owned_root):
    import pytest
    from nana_core.continuity.hands.host import OwnedApplication
    from nana_core.continuity.hands.contracts import ApplicationTask
    from nana_core.contracts import CoreError
    from nana_core.continuity.subject import SubjectInput
    tasks=tuple(ApplicationTask(task_id=n,kind='FORM',wanted={'label':'reviewed'},fields=('label',)) for n in ('first','replacement'))
    with OwnedApplication(owned_root/'app',tasks=tasks) as host:
        home=owned_root/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home) as app:
            r=app.runtime;agency=r.work.agency
            def adopt(key):
                obj=app.work.objects[key];cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key=obj.objective_id,program_id=obj.objective_id,motivation_source=obj.motivation_source)
                mid=capture(r,'supersede-'+key,cue.model_dump(mode='json'),predicate='concern.'+obj.objective_id)
                event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.supersede.'+key,kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope='project-work',privacy_class='PROJECT',source_memory_ids=(mid,),observed_at_us=r.clock.utc_now_us())
                cycle=r.subject.run(event);r.work.after_cycle(cycle,event)
                return app.work.goal_for(key),cycle
            old,first=adopt('first');new,second=adopt('replacement')
            cause=capture(r,'source-changed',{'observed_project_need':'replacement now applies'})
            with pytest.raises(CoreError):agency.link_supersession(old['goal_id'],new['goal_id'],first.cycle_id,cause_memory_id=cause,authority=r.authority)
            withdrawal=review(app,old,'WITHDRAW','supersede-old')
            from nana_core.continuity.records import RecordService
            cause=RecordService(r.store).read(r.store.one('subject_events',withdrawal.event_id)['record_id'])['payload']['input']['goal_review']['cause_memory_id']
            link=agency.link_supersession(old['goal_id'],new['goal_id'],withdrawal.cycle_id,cause_memory_id=cause,authority=r.authority)
            assert agency.link_supersession(old['goal_id'],new['goal_id'],withdrawal.cycle_id,cause_memory_id=cause,authority=r.authority)==link
            from nana_core.continuity.records import RecordService
            assert RecordService(r.store).read(link)['payload']['derived_display']=='SUPERSEDED'
            assert r.store.one('goals',old['goal_id'])['state']=='ABANDONED' and r.store.one('goals',new['goal_id'])['state']=='ACTIVE'
            assert not r.store.all('grants') and not r.store.all('actions')
