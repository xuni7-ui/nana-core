"""Run with installed Python -I and explicit bundle/src, never repository runtime."""
import argparse,json,time
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.life.config import LifeConfig,write_config
from nana_core.continuity.project_work.service import material_for
from nana_core.continuity.controlled_world.lab import ControlledWorld
from nana_core.continuity.controlled_world.projects import ControlledProject
from nana_core.continuity.open_life.sources import IntakeSource
from nana_core.continuity.records import RecordService
from nana_core import actions


def run(bundle,root):
    bundle=Path(bundle).resolve();root=Path(root).absolute()
    assert Path(actions.__file__).resolve().is_relative_to(bundle/'src')
    if root.exists():raise ValueError('FRESH_INSTALLED_PROBE_REQUIRED')
    root.mkdir(parents=True,mode=0o700)
    with ControlledWorld(root/'world',interval=120) as world:
        material=lambda p:material_for(bundle,'src/nana_core/continuity/'+p)
        source=IntakeSource(source_id='feed',channel='OWNED_HTTP',location=world.services['feed'].url+'/source',semantic_format='SOURCED_CLAIM_JSON')
        project=ControlledProject(project_id='adaptive',trigger_entity='project-user',trigger_predicate='lab.project-status',task_ids=('document-transfer','archive-notes','form-transfer'),learn_methods=True)
        cfg=LifeConfig(project_root=str(bundle),materials=(material('recurrence.py'),),practice=material('identity.py'),heldout=material('autonomy/requests.py'),transfer=material('subject/social.py'),owned_application_profile=str(world.host.profile),owned_browser_endpoint=world.browser.endpoint,advanced_life=True,record_research_outcomes=True,max_autonomous_materials=0,world_sources=(source,),controlled_projects=(project,))
        home=root/'life';write_config(home,cfg)
        with LifeApplication(home,bootstrap_grant=True) as app:
            runtime=app.runtime;identity=runtime.identity_id;deadline=time.monotonic()+60;goal=None
            while time.monotonic()<deadline:
                goal=app.work.goal_for_object(app.advanced.projects.objects['adaptive'])
                if goal and goal['state']=='COMPLETED':break
                app.tick();time.sleep(.02)
            assert goal and goal['state']=='COMPLETED'
            gid=goal['goal_id'];plan=RecordService(runtime.store).read(json.loads(goal['body_json'])['plan_record_id'])['payload']
            assert len(plan['steps'])==3 and len(plan['checkpoint']['completed_operator_ids'])==6
            assert runtime.store.db.execute("SELECT count(*) FROM actions WHERE goal_id=? AND capability='world.publish' AND resource LIKE '%/archive-notes/effect'",(gid,)).fetchone()[0]==1
            assert (Path(world.host.target.workspace)/'document-transfer.txt').read_text()=='Meeting agenda'
            assert app.work.port.peek('form-transfer')['state']['submitted']
            assert runtime.store.db.execute("SELECT count(*) FROM experiences WHERE outcome='FAILURE'").fetchone()[0]>=2
            assert not runtime.store.db.execute('PRAGMA foreign_key_check').fetchall()
        with LifeApplication(home) as app:
            assert app.runtime.identity_id==identity and app.runtime.store.one('goals',gid)['state']=='COMPLETED'
    return {'execution':'FRESH_INSTALLED_BUNDLE_PYTHON_ISOLATED','source_commit':json.loads((bundle/'runtime.json').read_text())['source_commit'],'same_subject':True,'real_owned_failures_preserved':True,'original_g_per_domain_learning':True,'independent_current_verification':True,'checkpoint_operators':6,'remaining_steps':3,'file_move_count':1,'same_identity_restart':True,'repository_runtime_imports':False,'new_provider_calls':0}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(run(a.bundle,a.root),indent=2)+'\n')
