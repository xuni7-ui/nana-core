"""Finite causal search and independent proposal validation; no execution will."""
import heapq
from ...contracts import CoreError
from ...storage import canonical
from .contracts import PlannerInput, PlanCandidate
from .task_graph import predecessors


class BoundedPlanner:
    """Replaceable satisficing resource, not a Subject or cost-optimal oracle.

    Relaxed additive distance orders a finite frontier. Actual transitions retain
    delete effects, exact producer history and hierarchical prerequisites.
    Exhaustion is unavailable/unknown feasibility, never proof of impossibility.
    """
    def plan(self, request):
        request = PlannerInput.model_validate_json(request.model_dump_json())
        obj = request.objective
        before = predecessors(obj)
        table = {op.operator_id: op for op in obj.operators}
        relevant, needed = set(), set(obj.desired)
        while True:
            chosen = {op.operator_id for op in obj.operators if set(op.produces) & needed}
            chosen.update(p for oid in relevant for p in before[oid])
            for oid in tuple(chosen):
                source = table[oid].args.get('input_from')
                if source:
                    if source not in table:
                        raise CoreError('PLAN_DATAFLOW_UNSATISFIED')
                    chosen.add(source)
            old = (len(relevant), len(needed))
            relevant.update(chosen)
            needed.update(f for oid in relevant for f in table[oid].requires)
            if old == (len(relevant), len(needed)):
                break
        ops = tuple(op for op in obj.operators if op.operator_id in relevant)
        # Separate token namespaces prevent facts spoofing operator completion.
        def fact(key): return ('fact', key)
        def executed(key): return ('executed', key)
        requirements = {op.operator_id: tuple(fact(f) for f in op.requires) + tuple(executed(p) for p in before[op.operator_id]) + ((executed(op.args['input_from']),) if op.args.get('input_from') else ()) for op in ops}
        effects = {op.operator_id: (*tuple(fact(f) for f in op.produces), executed(op.operator_id)) for op in ops}
        infinity = 10**12

        def estimate(facts, used):
            costs = {fact(f): 0 for f in facts}
            costs.update((executed(oid), 0) for oid in used)
            for _ in range(len(ops) + 1):
                changed = False
                for op in ops:
                    if op.operator_id in used:
                        continue
                    cost = op.cost + sum(costs.get(key, infinity) for key in requirements[op.operator_id])
                    if cost >= infinity:
                        continue
                    for key in effects[op.operator_id]:
                        if cost < costs.get(key, infinity):
                            costs[key] = cost
                            changed = True
                if not changed:
                    break
            return sum(costs.get(fact(f), infinity) for f in obj.desired)

        start = frozenset((*obj.initial,*request.checkpoint_facts))
        empty = frozenset(request.completed_operator_ids)
        if not empty<=table.keys():raise CoreError('PLAN_UNKNOWN_CHECKPOINT_OPERATOR')
        queue = [(estimate(start, empty), 0, 0, start, empty, ())]
        seen = {(start, empty): 0}
        serial = expanded = 0
        self.last_search = {'expanded': 0, 'generated': 1, 'relevant_operators': len(ops), 'frontier_bound': 8192, 'expansion_bound': 1024, 'optimality': 'NOT_CLAIMED'}
        while queue and expanded < 1024:
            _, cost, _, facts, used, path = heapq.heappop(queue)
            if seen.get((facts, used)) != cost:
                continue
            expanded += 1
            self.last_search['expanded'] = expanded
            if set(obj.desired) <= facts:
                return PlanCandidate(operator_ids=path, source_record_id=request.source_record_id, world_revision=request.world_revision)
            if len(path) >= obj.max_steps:
                continue
            for op in ops:
                oid = op.operator_id
                if oid in used or not set(op.requires) <= facts or not before[oid] <= used:
                    continue
                binding = op.args.get('input_from')
                if binding and binding not in used:
                    continue
                new = frozenset((facts - set(op.consumes)) | set(op.produces))
                new_used = used | {oid}
                new_cost = cost + op.cost
                key = (new, new_used)
                if new_cost >= seen.get(key, infinity):
                    continue
                score = estimate(new, new_used)
                if score >= infinity:
                    continue
                if len(seen) >= 8192 or len(queue) >= 8192:
                    raise CoreError('NO_BOUNDED_PLAN')
                seen[key] = new_cost
                serial += 1
                heapq.heappush(queue, (score, new_cost, serial, new, new_used, (*path, oid)))
                self.last_search['generated'] += 1
        raise CoreError('NO_BOUNDED_PLAN')


def validate_plan(request, candidate, registry):
    if type(candidate) is not PlanCandidate:
        raise CoreError('PLAN_CONTRACT_INVALID')
    request = PlannerInput.model_validate_json(request.model_dump_json())
    candidate = PlanCandidate.model_validate_json(candidate.model_dump_json())
    if (candidate.source_record_id, candidate.world_revision) != (request.source_record_id, request.world_revision):
        raise CoreError('PLAN_SOURCE_STALE')
    obj = request.objective
    if len(candidate.operator_ids) > obj.max_steps:
        raise CoreError('PLAN_STEP_LIMIT')
    facts, produced = set((*obj.initial,*request.checkpoint_facts)), set(request.completed_operator_ids)
    if len(produced)!=len(request.completed_operator_ids) or not produced<={op.operator_id for op in obj.operators}:raise CoreError('PLAN_INVALID_CHECKPOINT')
    operators = {op.operator_id: op for op in obj.operators}
    before = predecessors(obj)
    steps = []
    for oid in candidate.operator_ids:
        if oid not in operators:
            raise CoreError('PLAN_UNKNOWN_OPERATOR')
        op = operators[oid]
        if oid in produced:
            raise CoreError('PLAN_AMBIGUOUS_REPEAT')
        if not set(op.requires) <= facts:
            raise CoreError('PLAN_PRECONDITION_UNSATISFIED')
        if op.args.get('input_from') and op.args['input_from'] not in produced:
            raise CoreError('PLAN_DATAFLOW_UNSATISFIED')
        if not before[oid] <= produced:
            raise CoreError('PLAN_TASK_DEPENDENCY_UNSATISFIED')
        registry.validate(op.capability, op.resource, op.args)
        facts.difference_update(op.consumes)
        facts.update(op.produces)
        steps.append(op)
        produced.add(oid)
    if not set(obj.desired) <= facts:
        raise CoreError('PLAN_GOAL_NOT_REACHED')
    if len(canonical([s.model_dump(mode='json') for s in steps]).encode()) > 131072:
        raise CoreError('PLAN_SIZE_LIMIT')
    return tuple(steps)
