"""Query-aware control using existing WorldModel.view calls, with no graph SQL.

The caller supplies the same known seed AND the question's ordered predicates.
This control only answers fixed two-hop patterns; it is not a general planner.
"""
import time

from .association_probe import AssociationPath, AssociationResult


def direct_two_hop(world, seed, *, patterns, max_views=32, timeout_ms=100,
                   valid_at_us=None, known_at_us=None):
    if len(world.scopes) != 1 or not 1 <= len(patterns) <= 8 or any(len(p) != 2 for p in patterns):
        raise ValueError('bounded two-hop query patterns required')
    if not 1 <= max_views <= 32 or not 0 < timeout_ms <= 1000:
        raise ValueError('bounded research budget required')
    store = world.store
    store.ensure_privacy_current()
    changes, deadline = store.db.total_changes, time.perf_counter()+timeout_ms/1000
    if not store.one('entities', seed):
        raise ValueError('canonical seed entity required')
    now = store.clock.utc_now_us()
    valid = now if valid_at_us is None else valid_at_us
    known = now if known_at_us is None else known_at_us
    views, paths, exhausted = {}, [], False

    def read(entity, predicate):
        nonlocal exhausted
        key = entity, predicate
        if time.perf_counter() >= deadline or store.db.total_changes != changes:
            return ()
        if key not in views:
            if len(views) == max_views:
                exhausted = True
                return ()
            views[key] = world.view(entity, predicate, valid_at_us=valid, known_at_us=known)
        if store.db.total_changes != changes:
            return ()
        view = views[key]
        if view.state != 'SUPPORTED_BELIEF':
            return ()
        targets = []
        for alternative in view.alternatives:
            value = alternative['value']
            if type(value) is dict and set(value) == {'entity_id'} and type(value['entity_id']) is str:
                target = value['entity_id']
                if store.one('entities', target):
                    targets.append((target, view.support_records))
        return targets

    for first, second in patterns:
        for topic, first_support in read(seed, first):
            if topic == seed:
                continue
            for target, second_support in read(topic, second):
                if target not in {seed, topic}:
                    found = AssociationPath((seed, topic, target), (first, second),
                        tuple(dict.fromkeys((*first_support, *second_support))))
                    if found not in paths:
                        paths.append(found)
    store.ensure_privacy_current()
    changed, late = store.db.total_changes != changes, time.perf_counter() >= deadline
    return AssociationResult(() if changed or late else tuple(paths), len(views), exhausted, late, changed)
