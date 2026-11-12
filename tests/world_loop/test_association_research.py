"""Isolated original-Store experiment; no Core integration or upstream runtime."""
import time

from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.world import WorldModel
from nana_core.presence.authority import VirtualClock
from tools.nana_next_experience.association_compare import add_link, corpus, PREDICATES
from tools.nana_next_experience.association_probe import linked_recall


def opened(path, clock):
    return ContinuityStore(path, clock, schema_target=13)


def world(store):
    return WorldModel(store, scopes=('world',), privacy_classes=('PUBLIC',))


def test_original_store_same_view_budget_recovers_older_two_hop_support(tmp_path):
    with opened(tmp_path/'s.db', VirtualClock()) as store:
        IdentityService(store, OperatorAuthority())
        goals = corpus(store)
        w = world(store)
        original = w.snapshot(limit=32)
        supports = {rid for view in original for rid in view.support_records}
        baseline = sum(goal['supports'] <= supports for rows in goals.values() for goal in rows)
        changes = store.db.total_changes
        all_paths = []
        for seed in goals:
            found = linked_recall(w, seed, predicates=PREDICATES)
            assert found.views_read <= 32 and not found.source_changed and not found.deadline_exceeded
            all_paths.extend(p for p in found.paths if len(p.predicates) == 2)
        assert baseline == 12 and len(all_paths) == 24
        assert {p.entities for p in all_paths} == {goal['entities'] for rows in goals.values() for goal in rows}
        assert store.db.total_changes == changes


def test_conflict_private_expired_and_cycles_cannot_bridge(tmp_path):
    clock = VirtualClock()
    with opened(tmp_path/'s.db', clock) as store:
        IdentityService(store, OperatorAuthority())
        add_link(store, 'root', 'seed', 'topic', 'interest.a')
        add_link(store, 'tail', 'topic', 'resource', 'needs')
        w = world(store)
        assert any(len(p.predicates) == 2 for p in linked_recall(w, 'seed', predicates=PREDICATES).paths)
        add_link(store, 'conflict', 'topic', 'different', 'needs')
        assert not any(len(p.predicates) == 2 for p in linked_recall(w, 'seed', predicates=PREDICATES).paths)
        add_link(store, 'private-root', 'other', 'private-topic', 'interest.a')
        add_link(store, 'private-tail', 'private-topic', 'private-resource', 'needs', privacy='PERSONAL')
        assert not any(len(p.predicates) == 2 for p in linked_recall(w, 'other', predicates=PREDICATES).paths)
        add_link(store, 'expired-root', 'expired', 'expired-topic', 'interest.a', valid_until_us=clock.utc_now_us()+1)
        add_link(store, 'expired-tail', 'expired-topic', 'expired-resource', 'needs')
        assert not linked_recall(w, 'expired', predicates=PREDICATES).paths
        add_link(store, 'cycle-root', 'cycle', 'cycle-topic', 'interest.a')
        add_link(store, 'cycle-tail', 'cycle-topic', 'cycle', 'needs')
        assert all(len(p.predicates) == 1 for p in linked_recall(w, 'cycle', predicates=PREDICATES).paths)


def test_withdrawal_and_same_identity_restart_remove_path(tmp_path):
    path = tmp_path/'s.db'
    clock = VirtualClock()
    with opened(path, clock) as store:
        authority = OperatorAuthority()
        IdentityService(store, authority)
        identity = store.identity['identity_id']
        mid, _ = add_link(store, 'root', 'seed', 'topic', 'interest.a')
        add_link(store, 'tail', 'topic', 'resource', 'needs')
        assert len(linked_recall(world(store), 'seed', predicates=PREDICATES).paths) == 2
        MemoryService(store, authority).forget(mid, authority)
        assert not linked_recall(world(store), 'seed', predicates=PREDICATES).paths
    with opened(path, clock) as store:
        assert store.identity['identity_id'] == identity
        assert not linked_recall(world(store), 'seed', predicates=PREDICATES).paths


def test_budgets_and_mid_read_source_change_withhold_incomplete_or_stale_answers(tmp_path, monkeypatch):
    with opened(tmp_path/'s.db', VirtualClock()) as store:
        authority = OperatorAuthority()
        IdentityService(store, authority)
        mid, _ = add_link(store, 'root', 'seed', 'topic', 'interest.a')
        add_link(store, 'tail', 'topic', 'resource', 'needs')
        w = world(store)
        limited = linked_recall(w, 'seed', predicates=PREDICATES, max_views=1)
        assert limited.views_read == 1 and limited.budget_exhausted
        assert not any(len(p.predicates) == 2 for p in limited.paths)
        original = w.view
        def slow(*args, **kwargs):
            result = original(*args, **kwargs)
            time.sleep(.005)
            return result
        monkeypatch.setattr(w, 'view', slow)
        late = linked_recall(w, 'seed', predicates=PREDICATES, timeout_ms=1)
        assert late.deadline_exceeded and not late.paths
        def withdraw(*args, **kwargs):
            result = original(*args, **kwargs)
            MemoryService(store, authority).forget(mid, authority)
            return result
        monkeypatch.setattr(w, 'view', withdraw)
        result = linked_recall(w, 'seed', predicates=PREDICATES)
        assert result.source_changed and not result.paths


def test_known_time_and_separate_instances_do_not_share_a_retrieval_cache(tmp_path):
    for instance, target in [('first', 'one'), ('second', 'two')]:
        clock = VirtualClock()
        with opened(tmp_path/f'{instance}.db', clock) as store:
            IdentityService(store, OperatorAuthority())
            add_link(store, 'root', 'seed', 'topic', 'interest.a')
            past = clock.utc_now_us()-1
            add_link(store, 'tail', 'topic', target, 'needs')
            assert not any(len(p.predicates) == 2 for p in linked_recall(world(store), 'seed',
                predicates=PREDICATES, known_at_us=past).paths)
            found = linked_recall(world(store), 'seed', predicates=PREDICATES)
            assert {p.entities[-1] for p in found.paths if len(p.predicates) == 2} == {target}
