"""Explicit project source inventory. No source execution or external API calls."""
import argparse,json
from pathlib import Path
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.project_work.service import open_project_runtime,material_for,ProjectWork,learning_spec
from nana_core.continuity.project_work.port import read_material


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True);p.add_argument('--state',type=Path,required=True)
    p.add_argument('--source',action='append',required=True,help='explicit approved tracked nonprivate Python path, <=6144 bytes')
    p.add_argument('--practice',required=True);p.add_argument('--heldout',required=True);p.add_argument('--transfer',required=True)
    p.add_argument('--allow-local-artifacts',action='store_true',required=True)
    args=p.parse_args()
    materials=[material_for(args.repo,x) for x in args.source]
    training=[read_material(args.repo,material_for(args.repo,x)) for x in (args.practice,args.heldout,args.transfer)]
    spec=learning_spec(*training);clock=VirtualClock()
    with open_project_runtime(args.state/'subject/self.db',clock) as r:
        work=ProjectWork(r,args.repo,materials,args.state/'artifacts',spec,grant=True)
        rows=[]
        for material in materials:
            root=work.request(material.material_id)
            prior_goals=len(r.store.all('goals'))
            work.run_until(lambda:len(r.store.all('goals'))>prior_goals)
            goal=r.store.all('goals')[-1]
            work.run_until(lambda:r.store.one('goals',goal['goal_id'])['state'] in {'FAILED','COMPLETED'})
            failure=r.store.db.execute("SELECT * FROM experiences WHERE task_class='python-api' AND outcome='FAILURE' ORDER BY rowid DESC LIMIT 1").fetchone()
            if not r.work.open_learning.strategy('python-api','project-work') and failure:
                work.reflect_failure(failure['experience_id']);work.run_until(lambda:bool(r.work.open_learning.strategy('python-api','project-work')))
            work.run_until(lambda:r.store.one('goals',goal['goal_id'])['state']=='COMPLETED')
            rows.append({'source':material.relative_path,'source_digest':material.sha256,'source_memory_id':root})
        print(json.dumps({'identity_id':r.identity_id,'inputs':rows,'artifacts':work.artifacts(),'execution':'REAL_LOCAL_PROJECT_FILES_NO_CODE_EXECUTION','learning':'BOUNDED_EXISTING_METHOD_SELECTION','provider_calls':0},indent=2))
if __name__=='__main__':main()
