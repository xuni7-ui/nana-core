"""Rebuildable hierarchical dependencies over the existing typed plan operators."""


def predecessors(objective):
    operators = {op.operator_id for op in objective.operators}
    groups = {group.group_id: group for group in objective.task_groups}
    if len(groups) != len(objective.task_groups) or operators & groups.keys():
        raise ValueError('duplicate task graph identity')
    parents, leaves, heights = {}, {}, {}

    def descend(key, stack=()):
        if key in operators:
            return frozenset((key,))
        if key not in groups or key in stack or len(stack) >= 8:
            raise ValueError('task graph missing member, cycle or depth bound')
        if key in leaves:
            if len(stack)+heights[key]>8:
                raise ValueError('task graph depth bound')
            return leaves[key]
        group = groups[key]
        if len(set(group.members)) != len(group.members):
            raise ValueError('duplicate task member')
        result = set()
        for member in group.members:
            if member in parents and parents[member] != key:
                raise ValueError('task member has multiple parents')
            parents[member] = key
            result.update(descend(member, (*stack, key)))
        leaves[key] = frozenset(result)
        heights[key] = 1+max((heights[member] for member in group.members if member in groups),default=0)
        if len(stack)+heights[key]>8:
            raise ValueError('task graph depth bound')
        return leaves[key]

    for key in groups:
        descend(key)
    before = {oid: set() for oid in operators}
    for group in objective.task_groups:
        if len(set(group.depends_on)) != len(group.depends_on):
            raise ValueError('duplicate task dependency')
        for dependency in group.depends_on:
            if dependency not in groups:
                raise ValueError('unknown task dependency')
            for oid in leaves[group.group_id]:
                before[oid].update(leaves[dependency])
    for op in objective.operators:
        source = op.args.get('input_from')
        if source in operators:
            before[op.operator_id].add(source)
        if op.input_guard:
            source = op.input_guard.observation_operator_id
            table = {item.operator_id: item for item in objective.operators}
            if source not in table or table[source].capability != 'world.observe':
                raise ValueError('state guard requires declared observation')
            before[op.operator_id].add(source)
    visiting, done = set(), set()

    def visit(oid):
        if oid in visiting:
            raise ValueError('cyclic task scheduling dependency')
        if oid in done:
            return
        visiting.add(oid)
        for parent in before[oid]:
            visit(parent)
        visiting.remove(oid)
        done.add(oid)

    for oid in before:
        visit(oid)
    return {oid: frozenset(values) for oid, values in before.items()}
