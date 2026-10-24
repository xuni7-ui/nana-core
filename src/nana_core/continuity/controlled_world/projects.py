"""Host-described finite multi-Hand projects offered to original C/F, not will."""
import json
from pydantic import Field
from ...contracts import DTO,CoreError
from ...storage import digest
from ..open_agency.contracts import Objective,TaskGroup
from ..open_life.opportunities import LifeOpportunity,ActivityCost
from ..subject.opportunities import ConcernCue
from ..world_loop.world import WorldModel

class ControlledProject(DTO):
    project_id:str=Field(pattern=r'^[a-z][a-z0-9_-]{0,23}$')
    trigger_entity:str=Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    trigger_predicate:str=Field(pattern=r'^[a-z][a-z0-9._:-]{0,95}$')
    trigger_value:str|None=Field(default=None,max_length=128)
    require_research:bool=False
    task_ids:tuple[str,...]=Field(min_length=2,max_length=24)
    review_seconds:int=Field(default=3600,ge=30,le=86400)
    max_cost:int=Field(default=32,ge=1,le=100)
    learn_methods:bool=False

class ProjectPortfolio:
    def __init__(self,app,specs):
        self.app=app;self.specs=tuple(specs);self.objects={}
        if not app.config.owned_application_profile or len(specs)>4:raise CoreError('OWNED_PROJECT_BINDING_REQUIRED')
        work=app.work
        for spec in specs:
            if len(set(spec.task_ids))!=len(spec.task_ids) or any(k not in work.port.tasks for k in spec.task_ids):raise CoreError('PROJECT_TASK_NOT_DECLARED')
            ops=[];last=None;groups=[]
            for i,key in enumerate(spec.task_ids):
                obj=work.objects[key];prefix='p'+str(i)+'.'
                for op in obj.operators:
                    args={**op.args}
                    if args.get('input_from'):args['input_from']=prefix+args['input_from']
                    # Reviewed existing correct primitive, not a generated final
                    # answer: named forms and replace docs instead of bad demos.
                    if op.capability=='world.compute' and not spec.learn_methods:
                        if args.get('method')=='HANDS_APPEND':args['method']='HANDS_REPLACE'
                        if args.get('method')=='HANDS_POSITIONAL':args['method']='HANDS_NAMED'
                    requires=tuple(prefix+x for x in op.requires)+((last,) if not op.requires and last else ())
                    ops.append(op.model_copy(update={'operator_id':prefix+op.operator_id,'requires':requires,'produces':tuple(prefix+x for x in op.produces),'consumes':tuple(prefix+x for x in op.consumes),'args':args,'strategy_selectable':op.strategy_selectable if spec.learn_methods else False,'task_domain':obj.task_domain if spec.learn_methods else None}))
                last=prefix+'applied'
                groups.append(TaskGroup(group_id='group.task'+str(i),members=tuple(op.operator_id for op in ops if op.operator_id.startswith(prefix))))
            groups.append(TaskGroup(group_id='group.project',members=tuple(group.group_id for group in groups)))
            obj=Objective(objective_id='project.'+spec.project_id,scope='project-work',motivation_source='PROJECT_COMPLETION',task_domain='owned-maintenance',desired=(last,),operators=tuple(ops),task_groups=tuple(groups),horizon='ONGOING',max_steps=len(ops))
            if sum(o.cost for o in obj.operators)>spec.max_cost:raise CoreError('PROJECT_COST_CEILING')
            work.policy.offer(obj);self.objects[spec.project_id]=obj
        work.reserved_task_ids=frozenset(k for x in specs for k in x.task_ids)

    def offer(self,queue):
        r=self.app.runtime;records=queue.records
        world=WorldModel(r.store,scopes=r.config.scopes,privacy_classes=('PUBLIC','PROJECT'))
        for spec in self.specs:
            obj=self.objects[spec.project_id]
            if self.app.work.goal_for_object(obj):continue
            view=world.view(spec.trigger_entity,spec.trigger_predicate)
            if view.state not in {'SUPPORTED_BELIEF','CONFLICT'}:continue
            if spec.trigger_value is not None and not any(a['value']==spec.trigger_value for a in view.alternatives):continue
            research=[]
            if spec.require_research:
                for job in r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LIFE_RESEARCH' AND state='DONE' ORDER BY updated_at_us DESC LIMIT 16"):
                    h=r.store.one('continuity_records',job['record_id'])
                    if not h or h['scope'] not in r.config.scopes or h['privacy_class'] not in r.config.privacy_classes or not records.current_support(h['record_id']):continue
                    b=records.read(job['record_id'])['payload']
                    if b.get('query')=={'entity_id':spec.trigger_entity,'predicate':spec.trigger_predicate} and b['state'] in {'ENOUGH_FOR_BOUNDED_BELIEF','CONTRADICTION'}:research.append(h['record_id']);break
                if not research:continue
            mids=tuple(dict.fromkeys(m for rid in (*view.support_records,*research) for m in records.support(rid)))[:16]
            if not mids:continue
            # Finite reviewed local operators, no provider/network money. This
            # estimate influences appraisal; actual Kernel budgets stay separate.
            estimate=ActivityCost(compute='HEAVY' if sum(o.cost for o in obj.operators)>24 else 'LIGHT')
            return queue.offer(LifeOpportunity(kind='GOAL',topic='project.'+spec.project_id,source_memory_ids=mids,resource_estimate=estimate,cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='project.'+spec.project_id,program_id=obj.objective_id,motivation_source='PROJECT_COMPLETION',possible_behaviors=('CONTINUE_PROJECT','WATCH','REST'),resource_class='ORDINARY'),expires_at_us=r.clock.utc_now_us()+86400_000_000))
        return None

    def view(self):
        r=self.app.runtime;now=r.clock.utc_now_us();out=[]
        for spec in self.specs:
            obj=self.objects[spec.project_id];g=self.app.work.goal_for_object(obj)
            if not g:continue
            state=g['state'];meta=json.loads(g['body_json']);work=r.store.one('jobs',meta['work_id'])
            stale=now-work['updated_at_us']>spec.review_seconds*1000000
            out.append({'project_id':spec.project_id,'goal_id':g['goal_id'],'state':state,'age_state':'DORMANT' if state=='SUSPENDED' else 'STALE' if stale and state in {'ACTIVE','BLOCKED'} else state,'cursor':work['cursor'],'tasks':spec.task_ids,'plan_steps':len(obj.operators),'review_due':stale,'derived':True,'not_new_goal_authority':True})
        return out
