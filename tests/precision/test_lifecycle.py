"""Original C/D/F/G and actual owned effects, not symbolic score alone."""
import json
from pathlib import Path
from nana_core.continuity.controlled_world.lab import ControlledWorld
from nana_core.continuity.controlled_world.projects import ControlledProject
from nana_core.continuity.open_life.sources import IntakeSource
from nana_core.life.application import LifeApplication
from nana_core.life.config import update_config
from tests.controlled_hands.conftest import initialize,until


def test_multihand_hierarchy_learns_per_task_domain_and_replans_same_goal(tmp_path):
    with ControlledWorld(tmp_path/'world',interval=120) as world:
        home=tmp_path/'life';cfg=initialize(home,world.host.profile,skills=False)
        project=ControlledProject(project_id='adaptive',trigger_entity='project-user',trigger_predicate='lab.project-status',task_ids=('document-transfer','archive-notes','form-transfer'),learn_methods=True)
        src=IntakeSource(source_id='feed',channel='OWNED_HTTP',location=world.services['feed'].url+'/source',semantic_format='SOURCED_CLAIM_JSON')
        update_config(home,cfg.model_copy(update={'revision':2,'advanced_life':True,'record_research_outcomes':True,'owned_browser_endpoint':world.browser.endpoint,'world_sources':(src,),'controlled_projects':(project,)}),expected_revision=1)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime
            until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM goals WHERE template='owned-maintenance'").fetchone()))
            goal=r.store.db.execute("SELECT * FROM goals WHERE template='owned-maintenance'").fetchone();gid=goal['goal_id']
            from nana_core.continuity.records import RecordService
            plan=RecordService(r.store).read(json.loads(goal['body_json'])['plan_record_id'])['payload']
            assert len(plan['objective']['task_groups'])==4
            # No preselected correct method: original primitive really fails,
            # original G learns, then a revised plan uses per-operator domains.
            until(app,lambda:r.store.one('goals',gid)['state']=='FAILED')
            failures=[e for e in r.store.all('experiences') if e['outcome']=='FAILURE']
            assert any(e['task_class']=='owned-document' for e in failures)
            until(app,lambda:r.store.one('goals',gid)['state']=='COMPLETED',seconds=60)
            assert len(r.store.db.execute("SELECT * FROM goals WHERE template='owned-maintenance'").fetchall())==1
            assert r.store.db.execute("SELECT 1 FROM events WHERE kind='open.goal_replanned'").fetchone()
            outputs=r.work.agency._outputs(gid)
            assert any(not o['quality'] for o in outputs) and any(o['quality'] for o in outputs)
            assert (Path(world.host.target.workspace)/'document-transfer.txt').read_text()=='Meeting agenda'
            assert app.work.port.peek('form-transfer')['state']['submitted']
            assert r.store.db.execute("SELECT count(*) FROM actions WHERE goal_id=? AND capability='world.publish' AND resource LIKE '%/archive-notes/effect'",(gid,)).fetchone()[0]==1
            assert r.store.db.execute("SELECT count(*) FROM events WHERE kind='action.reobserved'").fetchone()[0]>=2
            latest=RecordService(r.store).read(json.loads(r.store.one('goals',gid)['body_json'])['plan_record_id'])['payload']
            assert latest['checkpoint']['completed_operator_ids'] and len(latest['steps'])==3
            # Current observed source can still time out. It is not a goal failure
            # or permission to resend a different poll occurrence.
            from nana_core.continuity.open_life.sources import WorldIntake
            from nana_core.contracts import CoreError
            import pytest
            slow=IntakeSource(source_id='slow',channel='OWNED_HTTP',location=world.services['api'].url+'/fault/delay')
            intake=WorldIntake(r,tmp_path,(slow,),scope='project-work')
            with pytest.raises(CoreError,match='UNKNOWN'):intake.read('slow')
            with pytest.raises(CoreError,match='UNKNOWN_NO_RETRY'):intake.read('slow',observation_id='different-poll')
            assert r.store.one('goals',gid)['state']=='COMPLETED'
            assert all(r.store.one('experiences',e['experience_id'])['outcome']=='FAILURE' for e in failures)
            assert not r.store.all('cognitive_requests') and not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
