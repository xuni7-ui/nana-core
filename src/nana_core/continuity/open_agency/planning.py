"""Bounded uniform-cost planning and independent proposal validation."""
import heapq
from ...contracts import CoreError
from ...storage import canonical,digest
from .contracts import Objective,PlannerInput,PlanCandidate

class BoundedPlanner:
    """A replaceable deterministic planner resource, never a SubjectLoop."""
    def plan(self,request):
        obj=request.objective;start=frozenset(obj.initial);serial=0
        queue=[(0,serial,start,())];seen={start:0};expanded=0
        while queue and expanded<1024:
            cost,_,facts,path=heapq.heappop(queue);expanded+=1
            if set(obj.desired)<=facts:
                return PlanCandidate(operator_ids=path,source_record_id=request.source_record_id,world_revision=request.world_revision)
            if len(path)>=obj.max_steps:continue
            for op in obj.operators:
                if set(op.requires)<=facts:
                    new=(facts-set(op.consumes))|set(op.produces);new=frozenset(new)
                    if cost+op.cost>=seen.get(new,10**9):continue
                    seen[new]=cost+op.cost;serial+=1
                    heapq.heappush(queue,(cost+op.cost,serial,new,(*path,op.operator_id)))
        raise CoreError('NO_BOUNDED_PLAN')

def validate_plan(request,candidate,registry):
    if type(candidate) is not PlanCandidate:raise CoreError('PLAN_CONTRACT_INVALID')
    candidate=PlanCandidate.model_validate_json(candidate.model_dump_json())
    if (candidate.source_record_id,candidate.world_revision)!=(request.source_record_id,request.world_revision):raise CoreError('PLAN_SOURCE_STALE')
    obj=request.objective
    if len(candidate.operator_ids)>obj.max_steps:raise CoreError('PLAN_STEP_LIMIT')
    facts=set(obj.initial);operators={x.operator_id:x for x in obj.operators};steps=[];produced=set()
    for oid in candidate.operator_ids:
        if oid not in operators:raise CoreError('PLAN_UNKNOWN_OPERATOR')
        op=operators[oid]
        if oid in produced:raise CoreError('PLAN_AMBIGUOUS_REPEAT')
        binding=op.args.get('input_from')
        if not set(op.requires)<=facts:raise CoreError('PLAN_PRECONDITION_UNSATISFIED')
        if binding and binding not in produced:raise CoreError('PLAN_DATAFLOW_UNSATISFIED')
        registry.validate(op.capability,op.resource,op.args)
        facts.difference_update(op.consumes);facts.update(op.produces);steps.append(op);produced.add(oid)
    if not set(obj.desired)<=facts:raise CoreError('PLAN_GOAL_NOT_REACHED')
    # Every external input/output edge must be explicit, no arbitrary placeholders.
    if len(canonical([s.model_dump(mode='json') for s in steps]).encode())>32768:raise CoreError('PLAN_SIZE_LIMIT')
    return tuple(steps)
