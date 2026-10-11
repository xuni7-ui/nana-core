"""Fixture proposal -> actual bounded dev patch/test/verify/commit; no real LLM."""
import argparse,json,os,signal,subprocess
from pathlib import Path
from pydantic import Field
from ..contracts import DTO,CoreError,GrantSpec,Observation
from ..actions import ActionKernel,OperatorAuthority
from ..storage import Store,canonical,digest,uid
from ..migration.routing import CapabilityRouter
from ..semantic.selection import ModelSelectionPolicy,TaskRequirements
from .engineering import EngineeringCapabilityPort,EngineeringRegistry

class EngineeringProposal(DTO):
    purpose:str=Field(min_length=1,max_length=512)
    path:str
    before_hash:str
    content:str
    test_id:str
    commit_message:str

class EngineeringFixture:
    descriptor='literal-contract-engineering-fixture'
    def propose(self,request):
        # Constraint-driven synthetic fixture, never a claim of code reasoning.
        return EngineeringProposal(purpose='Satisfy the operator literal contract',path=request['allowed_path'],
            before_hash=request['before_hash'],content='VALUE = '+repr(request['required_value'])+'\n',test_id='literal',commit_message='Apply synthetic literal contract')

def initialize(workspace):
    w=Path(workspace);w.mkdir(parents=True)
    (w/'.nana-engineering-fixture.json').write_text(canonical({'synthetic_only':True,'workspace_id':'synthetic-engineering'}))
    (w/'settings.py').write_text('VALUE = 1\n')
    for argv in (['git','init','-b','dev/synthetic-engineering',str(w)],
                 ['git','-C',str(w),'add','--','.nana-engineering-fixture.json','settings.py'],
                 ['git','-C',str(w),'-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','-c','user.name=Nana synthetic','-c','user.email=synthetic@example.invalid','commit','-m','Synthetic baseline']):
        subprocess.run(argv,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env={'PATH':os.defpath,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'})

def bind(store,directory,authorize=False):
    a=OperatorAuthority('synthetic-engineering-operator')
    port=EngineeringCapabilityPort(store,Path(directory)/'workspace',Path(directory)/'engineering_world.db',allow_paths=('settings.py',),
        branch='dev/synthetic-engineering',test_contracts={'literal':('settings.py',{'VALUE':2})})
    registry=EngineeringRegistry(port)
    router=CapabilityRouter(store,{c:port for c in registry.definitions},a,resource_scope='isolated_development',registry=registry)
    router.select_owner('core_simulator',a)
    kernel=ActionKernel(store,router.bind('core_simulator',a),a,registry=registry)
    if authorize and not store.all('grants'):
        now=store.clock.utc_now_us();kernel.set_budgets({'write_attempts':8,'external_requests':30,'cost_micro_units':30},a)
        kernel.grant(GrantSpec(capabilities=tuple(registry.definitions)+(registry.verify_capability,),resources=(port.resource,),not_before_us=now-1,expires_at_us=now+3600_000_000),a)
    return port,kernel

def run(directory,*,authorize=True,kill_after_patch=False):
    p=Path(directory).resolve()
    live=Path(__file__).resolve().parents[3]
    if p==live or live in p.parents:raise CoreError('LIVE_CORE_WORKSPACE_FORBIDDEN')
    p.mkdir(parents=True,exist_ok=True)
    if not (p/'workspace').exists():initialize(p/'workspace')
    with Store(p/'core.db') as s:
        port,kernel=bind(s,p,authorize)
        try:
            evidence=s.ingest(Observation(source_namespace='synthetic.engineering',object_id='literal-contract-2',kind='unrelated',raw_text='Synthetic operator task: VALUE should equal 2; literal data only'))
            existing=s.all('goals')
            if existing:goal=existing[0];proposal=EngineeringProposal.model_validate_json(json.loads(goal['body_json'])['proposal_json'])
            else:
                try:ModelSelectionPolicy().select(TaskRequirements(task_class='engineering',context_tokens=512),[],[])
                except CoreError:selection='BLOCKED_NO_AUTHORIZED_REAL_ENDPOINT'
                proposal=EngineeringFixture().propose({'identity':s.identity,'event_id':evidence,'allowed_path':'settings.py',
                    'before_hash':digest((p/'workspace/settings.py').read_bytes()),'required_value':2})
                # Operator Core, not model, accepts one constrained engineering plan.
                kernel._valid_args('file.patch',port.resource,{'path':proposal.path,'before_hash':proposal.before_hash,'content':proposal.content})
                gid,pid=uid(),uid()
                with s.transaction('engineering.goal_plan_accepted',{'event_id':evidence,'model_kind':'fixture'}) as tx:
                    tx.put('goals',{'goal_id':gid,'goal_key':digest([s.identity['identity_id'],evidence,'engineering']),'event_id':evidence,'template':'engineering_literal','state':'ACTIVE','version':1,
                        'body_json':canonical({'proposal_json':proposal.model_dump_json(),'purpose':proposal.purpose,'model':EngineeringFixture.descriptor,'model_selection':selection})})
                    tx.put('plans',{'plan_id':pid,'goal_id':gid,'body_json':canonical({'steps':['file.patch','tests.run','git.diff','git.commit'],'proposal':proposal.model_dump()})})
                goal=s.one('goals',gid)
            plan=next(x for x in s.all('plans') if x['goal_id']==goal['goal_id']);states={};ids={}
            steps=[('file.patch',{'path':proposal.path,'before_hash':proposal.before_hash,'content':proposal.content}),('tests.run',{'test_id':proposal.test_id}),('git.diff',{})]
            for index,(cap,args) in enumerate(steps):
                action=kernel.propose(cap,port.resource,args,goal_id=goal['goal_id'],plan_id=plan['plan_id'],effect_slot=digest([goal['goal_id'],index]))
                def fault(point):
                    if kill_after_patch and cap=='file.patch' and point=='after_effect':os.kill(os.getpid(),signal.SIGKILL)
                state=kernel.run(action,fault=fault);states[cap]=state;ids[cap]=action
                if state!='SUCCEEDED':return {'status':'BLOCKED','states':states,'real_model_calls':0,'E12':'NOT_RUN'}
            parent=port._git('rev-parse','HEAD')
            prior=[a for a in s.all('actions') if a['goal_id']==goal['goal_id'] and a['capability']=='git.commit']
            if prior:parent=json.loads(prior[0]['args_json'])['parent_sha']
            action=kernel.propose('git.commit',port.resource,{'message':proposal.commit_message,'test_action_id':ids['tests.run'],'parent_sha':parent},
                goal_id=goal['goal_id'],plan_id=plan['plan_id'],effect_slot=digest([goal['goal_id'],3]))
            states['git.commit']=kernel.run(action);ids['git.commit']=action
            if states['git.commit']!='SUCCEEDED':return {'status':'BLOCKED','states':states,'real_model_calls':0,'E12':'NOT_RUN'}
            current=s.one('goals',goal['goal_id'])
            if current['state']!='COMPLETED':
                with s.transaction('engineering.goal_completed',{'goal_id':goal['goal_id'],'action_ids':ids}) as tx:
                    tx.update('goals',goal['goal_id'],state='COMPLETED',version=current['version']+1)
                    tx.put('memory_items',{'memory_id':uid(),'kind':'EPISODE','status':'ACTIVE','created_event_id':tx.event_id,
                        'body_json':canonical({'type':'ENGINEERING_EXPERIENCE_CANDIDATE','what_happened':'Bounded literal patch satisfied independent operator tests before dev commit',
                            'action_ids':ids,'source_refs':[{'event_id':evidence,'coverage':'FULL'}],'assessment':'UNASSESSED','strategy_enabled':False,'permission_expansion':False})})
            report={'status':'PASS','identity':s.identity,'goal_id':goal['goal_id'],'states':states,'action_ids':ids,
                'attempts':len(s.all('attempts')),'commit_sha':port._git('rev-parse','HEAD'),'workspace_hash':port._hash(),
                'model_kind':'fixture','real_model_calls':0,'E12':'NOT_RUN','model_autonomous_development':'NOT_RUN',
                'production_calls':0,'external_messages':0,'experience':'verified episode + UNASSESSED candidate; no activated engineering Strategy'}
            return report
        finally:port.close()

def main():
    a=argparse.ArgumentParser();a.add_argument('directory');a.add_argument('--kill-after-patch',action='store_true');x=a.parse_args();print(canonical(run(x.directory,kill_after_patch=x.kill_after_patch)))
if __name__=='__main__':main()
