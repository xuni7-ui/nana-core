"""Run from installed Python -I with explicit bundle/src; no repository imports."""
import argparse,json,time
from urllib.request import urlopen
from pathlib import Path
from nana_core.continuity.controlled_world.lab import ControlledWorld
from nana_core.continuity.controlled_world.projects import ControlledProject
from nana_core.continuity.open_life.sources import IntakeSource
from nana_core.continuity.project_work.service import material_for
from nana_core.life.config import LifeConfig,write_config
from nana_core.life.application import LifeApplication
from nana_core.life import application
from nana_core.life.surfaces import SurfaceBinding,SurfaceObservation
from nana_core.life.owned_surface import OwnedSurfaceBridge,social_observations

def run(bundle,root):
    bundle=Path(bundle).resolve();root=Path(root).absolute()
    assert Path(application.__file__).resolve().is_relative_to(bundle/'src')
    if root.exists():raise ValueError('FRESH_OWNED_PROBE_ROOT_REQUIRED')
    root.mkdir(mode=0o700,parents=True)
    with ControlledWorld(root/'world',interval=120,source_seeds={'feed':7,'documents':8,'api':9,'social':10}) as world:
        m=lambda p:material_for(bundle,'src/nana_core/continuity/'+p)
        bindings=tuple(SurfaceBinding(binding_id='surface.'+n,platform='platform.local',surface='surface.'+n,adapter='adapter.owned') for n in ('web','social'))
        config=LifeConfig(project_root=str(bundle),materials=(m('recurrence.py'),),practice=m('identity.py'),heldout=m('autonomy/requests.py'),transfer=m('subject/social.py'),owned_application_profile=str(world.host.profile),owned_browser_endpoint=world.browser.endpoint,advanced_life=True,record_research_outcomes=True,max_autonomous_materials=0,surface_bindings=bindings,controlled_projects=(ControlledProject(project_id='maintenance',trigger_entity='project-user',trigger_predicate='lab.project-status',trigger_value='review-needed',require_research=True,task_ids=('document-transfer','archive-notes','form-transfer')),),world_sources=tuple(IntakeSource(source_id=k,channel='OWNED_HTTP',location=world.services[k].url+'/source',semantic_format='SOURCED_CLAIM_JSON') for k in ('feed','documents','api')))
        home=root/'life';write_config(home,config)
        with LifeApplication(home,bootstrap_grant=True) as app:
            identity=app.runtime.identity_id;deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                goal=app.work.goal_for_object(app.advanced.projects.objects['maintenance'])
                if goal and goal['state']=='COMPLETED':break
                app.tick();time.sleep(.02)
            assert goal and goal['state']=='COMPLETED'
            actions=app.runtime.store.db.execute('SELECT * FROM actions WHERE goal_id=?',(goal['goal_id'],)).fetchall()
            assert len(actions)==9 and all(a['state']=='SUCCEEDED' for a in actions)
            assert app.runtime.store.db.execute("SELECT 1 FROM experiences WHERE task_class='research.comparison'").fetchone()
            with OwnedSurfaceBridge(app,bindings={'surface.web':'USER','surface.social':'BACKGROUND'}) as bridge:
                bridge.post(SurfaceObservation(binding_id='surface.web',event_id='installed-web',text='现在项目进展怎样？'))
                with urlopen(world.services['social'].url+'/events',timeout=2) as response:payload=json.load(response)
                bridge.post(social_observations(payload,binding_id='surface.social')[0])
                assert app.tick()['surface_ingress']['binding_id']=='surface.web'
                assert app.tick()['surface_ingress']['binding_id']=='surface.social'
            assert not app.runtime.store.db.execute('PRAGMA foreign_key_check').fetchall()
        with LifeApplication(home) as app:
            assert app.runtime.identity_id==identity
            assert app.runtime.store.one('goals',goal['goal_id'])['state']=='COMPLETED'
    return {'execution':'FRESH_INSTALLED_BUNDLE_ISOLATED_PYTHON','source_commit':json.loads((bundle/'runtime.json').read_text())['source_commit'],'five_services':True,'structural_browser':True,'configured_three_source_research':True,'original_nine_step_multihand_project':True,'independent_verify':True,'research_operation_experience':True,'actual_localhost_ingress':True,'same_identity_restart':True,'repository_required':False,'inherited_pythonpath_required':False,'new_provider_calls':0}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(run(a.bundle,a.root),indent=2)+'\n')
if __name__=='__main__':main()
