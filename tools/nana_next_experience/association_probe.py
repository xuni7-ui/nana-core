"""Isolated R1 experiment: source-backed two-hop recall in the ORIGINAL Store.

Original implementation inspired by Graphiti's bounded graph expansion, not
copied code. No extraction, graph database, persistent index or Core hook.
Only explicit ``{'entity_id': ...}`` world-belief values form links. Results are
retrieval proposals, not facts, motives, permissions or a learned capability.
"""
from collections import deque
from dataclasses import dataclass
import time

from nana_core.contracts import CoreError


@dataclass(frozen=True)
class AssociationPath:
    entities: tuple[str, ...]
    predicates: tuple[str, ...]
    support_records: tuple[str, ...]


@dataclass(frozen=True)
class AssociationResult:
    paths: tuple[AssociationPath, ...]
    views_read: int
    budget_exhausted: bool
    deadline_exceeded: bool
    source_changed: bool


def linked_recall(world, seed, *, predicates, max_views=32, max_depth=2,
                  timeout_ms=100, valid_at_us=None, known_at_us=None):
    """Read at most max_views original temporal projections, within one scope.

    The deadline is checked between synchronous reads, not a SQLite interrupt or
    hard wall-time guarantee. A late result is withheld, never called timely.
    Empty/unsupported/conflicted/withdrawn links do not bridge to other entities.
    """
    if (len(world.scopes) != 1 or not 1 <= max_views <= 32 or not 1 <= max_depth <= 3
            or not 0 < timeout_ms <= 1000 or not 1 <= len(predicates) <= 8):
        raise ValueError('bounded single-scope research query required')
    store = world.store
    store.ensure_privacy_current()
    changes = store.db.total_changes
    if not store.one('entities', seed):
        raise ValueError('canonical seed entity required')
    now = store.clock.utc_now_us()
    valid = now if valid_at_us is None else valid_at_us
    known = now if known_at_us is None else known_at_us
    deadline = time.perf_counter() + timeout_ms/1000
    pending = deque([AssociationPath((seed,), (), ())])
    paths, reads, exhausted, late = [], 0, False, False
    # Cache is query-local only: current privacy/source/time is checked afresh on
    # every new query. Shared tails can produce different causal paths.
    views = {}
    while pending:
        path = pending.popleft()
        if len(path.predicates) >= max_depth:
            continue
        if time.perf_counter() >= deadline:
            late = True
            break
        store.ensure_privacy_current()
        placeholders = ','.join('?' for _ in world.privacy) or 'NULL'
        predicate_slots = ','.join('?' for _ in predicates)
        keys = store.db.execute(f'''SELECT b.predicate_key, max(b.known_at_us) AS t
            FROM world_beliefs b JOIN continuity_records r ON r.record_id=b.record_id
            WHERE b.scope=? AND b.entity_id=? AND b.known_at_us<=?
              AND b.predicate_key IN ({predicate_slots})
              AND r.lifecycle='ACTIVE' AND r.privacy_class IN ({placeholders})
            GROUP BY b.predicate_key ORDER BY t DESC,b.predicate_key LIMIT 33''',
            (world.scopes[0], path.entities[-1], known, *predicates, *world.privacy)).fetchall()
        for key in keys:
            predicate = key['predicate_key']
            if predicate not in predicates:
                continue
            if time.perf_counter() >= deadline:
                late = True
                break
            cache_key = (path.entities[-1], predicate)
            if cache_key not in views:
                if reads == max_views:
                    exhausted = True
                    break
                reads += 1
                try:
                    views[cache_key] = world.view(path.entities[-1], predicate,
                        valid_at_us=valid, known_at_us=known)
                except CoreError:
                    continue
            view = views.get(cache_key)
            if time.perf_counter() >= deadline:
                late = True
                break
            if view is None or view.state != 'SUPPORTED_BELIEF':
                continue
            for alternative in view.alternatives:
                value = alternative['value']
                if type(value) is not dict or set(value) != {'entity_id'}:
                    continue
                target = value['entity_id']
                if type(target) is not str or target in path.entities or not store.one('entities', target):
                    continue
                found = AssociationPath((*path.entities, target), (*path.predicates, predicate),
                    tuple(dict.fromkeys((*path.support_records, *view.support_records))))
                if found not in paths:
                    paths.append(found)
                    pending.append(found)
        if exhausted or late:
            break
    # Paths alone do not attest current sources after the caller changes the
    # Store. There is deliberately no integration API or durable certificate.
    store.ensure_privacy_current()
    changed = store.db.total_changes != changes
    late = late or time.perf_counter() >= deadline
    return AssociationResult(() if changed or late else tuple(paths), reads, exhausted, late, changed)
