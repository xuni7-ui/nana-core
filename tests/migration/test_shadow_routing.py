import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import pytest
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.contracts import CAPABILITIES, CoreError, Feedback, Invocation, Observation, PlanProposal, StepProposal
from nana_core.experience import ExperienceEngine
from nana_core.fake_world import FakeWorld
from nana_core.migration.routing import CapabilityRouter
from nana_core.migration.shadow import ShadowObserver
from nana_core.planning import FixtureModel
from nana_core.runtime import Runtime
from nana_core.storage import Store, digest
from .conftest import CARD, NEXT, SOURCE

pytestmark = pytest.mark.s6


def observation(object_id="synthetic-reading", card=CARD):
    return Observation(source_namespace="synthetic.migration", object_id=object_id,
        raw_text="A fictional reader needs a private note to resume reading.",
        occurred_at="2026-09-12T09:30:00+08:00", source_id=SOURCE, card_resource=card)


def plan(locate=False, card=CARD):
    steps = [StepProposal(capability="reading.source.read", resource=SOURCE)]
    if locate: steps.append(StepProposal(capability="reading.source.locate", resource=SOURCE))
    steps.append(StepProposal(capability="reading.card.create", resource=card))
    return PlanProposal(purpose="Synthetic reading continuity.", steps=tuple(steps))


def args(world):
    text = world.db.execute("SELECT text FROM sources WHERE source_id=?", (SOURCE,)).fetchone()[0]
    return {"source_id": SOURCE, "source_digest": digest(text.encode()), "content": text, "locator": None}


def test_shadow_compares_without_actions_permissions_or_budget_changes(routed):
    store, world, router, kernel, authority, clock = routed
    protected = {t: store.all(t) for t in ("identities", "goals", "actions", "attempts", "grants", "budgets", "strategies")}
    observer = ShadowObserver(store)
    comparison = observer.observe(observation(), plan(), plan(locate=True))
    assert comparison["differences"] == ["PLAN_STEPS_DIFFER"]
    assert not comparison["execution_requested"] and not comparison["goal_created"]
    assert comparison["execution_owner_at_observation"]["actor"] == "legacy_simulator"
    assert protected == {t: store.all(t) for t in protected}
    assert world.counts() == {"effects": 0, "execute_calls": 0, "locate_calls": 0, "verify_calls": 0}
    again = observer.observe(observation(), plan(), plan(locate=True))
    assert again == comparison
    with pytest.raises(CoreError, match="SHADOW_COMPARISON_COLLISION"):
        observer.observe(observation(), plan(), plan())
    assert len([e for e in store.all("events") if e["kind"] == "migration.shadow_compared"]) == 1


def test_shadow_then_owner_executes_duplicate_event_once(routed):
    store, world, router, kernel, authority, clock = routed
    observer = ShadowObserver(store)
    comparison = observer.observe(observation(), plan(), plan())
    runtime = Runtime(store, kernel, FixtureModel())
    identity = store.identity
    first = runtime.process(observation())
    for _ in range(20): assert runtime.process(observation()) == first
    assert store.identity == identity
    assert store.one("goals", first)["event_id"] == comparison["observation_event_id"]
    assert world.counts()["effects"] == 1 and world.counts()["execute_calls"] == 2


def test_shadow_does_not_suspend_invalid_strategy(routed):
    store, world, router, kernel, authority, clock = routed
    goal = Runtime(store, kernel, FixtureModel()).process(observation())
    engine = ExperienceEngine(store, kernel)
    feedback, strategies = engine.learn(Feedback(goal_id=goal, text="Synthetic: next reading card needs a locator.",
        requested_fields=("locator",)), authority)
    with store.transaction("synthetic.support_invalidated_without_projection_update") as tx:
        tx.put("core_meta", {"key": "invalidated_evidence:" + feedback, "value_json": "true"})
    before = store.all("strategies")
    compared = ShadowObserver(store).observe(observation("synthetic-next", NEXT), plan(card=NEXT), plan(card=NEXT))
    assert before == store.all("strategies")
    assert compared["core_draft"]["applied_strategies"] == []
    assert world.counts()["effects"] == 1


@pytest.mark.parametrize("actor,code", [("shadow", "SHADOW_HAS_NO_EXECUTION_RIGHT"),
    ("core_simulator", "EXECUTION_OWNER_MISMATCH")])
def test_only_selected_owner_can_reach_backend(routed, actor, code):
    store, world, router, kernel, authority, clock = routed
    action = kernel.propose("reading.card.create", CARD, args(world))
    kernel.prepare(action)
    target = router.bind(actor, authority)
    def attempted_in_shadow(point):
        if point == "before_call":
            with pytest.raises(CoreError, match=code):
                target.execute(kernel._invocation(store.one("actions", action)))
    kernel.dispatch(action, fault=attempted_in_shadow)
    assert kernel.verify(action) == "SUCCEEDED"
    assert world.counts()["effects"] == world.counts()["execute_calls"] == 1


def test_duplicate_direct_dispatch_is_fenced_before_backend(routed):
    store, world, router, kernel, authority, clock = routed
    action = kernel.propose("reading.card.create", CARD, args(world))
    kernel.prepare(action)
    port = router.bind("legacy_simulator", authority)
    def intercepted(point):
        if point == "before_call":
            invocation = kernel._invocation(store.one("actions", action))
            port.execute(invocation)
            with pytest.raises(CoreError, match="ROUTE_ALREADY_DISPATCHED"):
                port.execute(invocation)
    # A deliberately competing trusted caller used the dispatch once. Kernel's
    # own call is rejected -> UNKNOWN -> query recovery; never a second effect.
    assert kernel.dispatch(action, fault=intercepted) == "UNKNOWN"
    assert kernel.verify(action) == "SUCCEEDED"
    assert world.counts()["execute_calls"] == world.counts()["effects"] == 1


def test_core_proposal_cannot_bypass_kernel_authorization(routed):
    store, world, router, kernel, authority, clock = routed
    action = kernel.propose("reading.card.create", CARD, args(world))
    port = router.bind("legacy_simulator", authority)
    row = store.one("actions", action)
    forged = Invocation(action_id=action, attempt_id="synthetic-unprepared-attempt", capability=row["capability"],
        resource=row["resource"], args=json.loads(row["args_json"]), args_hash=row["args_hash"], idempotency_key=row["idempotency_key"])
    with pytest.raises(CoreError, match="CORE_ACTION_REQUIRED"):
        port.execute(forged)
    assert world.counts()["effects"] == 0


def test_pending_handoff_denied_and_stale_ports_fenced(routed, tmp_path):
    store, world, router, kernel, authority, clock = routed
    old_port = router.bind("legacy_simulator", authority)
    inactive_port = router.bind("core_simulator", authority)
    action = kernel.propose("reading.card.create", CARD, args(world))
    kernel.prepare(action)
    with pytest.raises(CoreError, match="UNRESOLVED_WORK_PREVENTS_HANDOFF"):
        router.select_owner("core_simulator", authority)
    world.control("lose_receipt", 1)
    assert kernel.dispatch(action) == "UNKNOWN"
    with pytest.raises(CoreError, match="UNRESOLVED_WORK_PREVENTS_HANDOFF"):
        router.select_owner("core_simulator", authority)
    assert kernel.verify(action) == "SUCCEEDED"
    owner = router.select_owner("core_simulator", authority)
    assert owner["epoch"] == 2
    new_kernel = ActionKernel(store, router.bind("core_simulator", authority), authority)
    new_action = new_kernel.propose("reading.card.create", NEXT, args(world))
    new_kernel.prepare(new_action)
    def stale_clients(point):
        if point == "before_call":
            invocation = new_kernel._invocation(store.one("actions", new_action))
            for port in (old_port, inactive_port):
                with pytest.raises(CoreError, match="EXECUTION_OWNER_MISMATCH"):
                    port.execute(invocation)
    world.control("lose_receipt", 0)
    assert new_kernel.run(new_action, fault=stale_clients) == "SUCCEEDED"
    assert world.counts()["effects"] == world.counts()["execute_calls"] == 2
    assert router.owner == owner


def test_router_rechecks_expiry_after_kernel_dispatch_check(routed):
    store, world, router, kernel, authority, clock = routed
    action = kernel.propose("reading.card.create", CARD, args(world))
    kernel.prepare(action)
    def expires(point):
        if point == "before_call": clock.advance(101_000_000)
    assert kernel.dispatch(action, fault=expires) == "UNKNOWN"
    assert world.counts()["execute_calls"] == world.counts()["effects"] == 0
    assert kernel.recover()[action] == "AUTH_EXPIRED"
    with pytest.raises(CoreError, match="UNRESOLVED_WORK_PREVENTS_HANDOFF"):
        router.select_owner("core_simulator", authority)


def test_router_requires_consumed_budget_proof(routed, monkeypatch):
    store, world, router, kernel, authority, clock = routed
    action = kernel.propose("reading.card.create", CARD, args(world))
    kernel.prepare(action)
    port = router.bind("legacy_simulator", authority)
    def corrupt_proof(point):
        if point == "before_call":
            real_all = store.all
            monkeypatch.setattr(store, "all", lambda table: [] if table == "budget_holds" else real_all(table))
            with pytest.raises(CoreError, match="CONSUMED_ATTEMPT_BUDGET_REQUIRED"):
                port.execute(kernel._invocation(store.one("actions", action)))
            monkeypatch.setattr(store, "all", real_all)
    assert kernel.run(action, fault=corrupt_proof) == "SUCCEEDED"
    assert world.counts()["effects"] == world.counts()["execute_calls"] == 1


def test_shadow_cannot_select_owner_or_bind_without_operator(routed):
    store, world, router, kernel, authority, clock = routed
    with pytest.raises(CoreError, match="UNAUTHENTICATED_MIGRATION_OPERATOR"):
        router.select_owner("core_simulator", OperatorAuthority())
    with pytest.raises(CoreError, match="UNAUTHENTICATED_MIGRATION_OPERATOR"):
        router.bind("core_simulator", OperatorAuthority())
    with pytest.raises(CoreError, match="SYNTHETIC_EXECUTION_OWNER_REQUIRED"):
        router.select_owner("shadow", authority)
    assert router.owner["actor"] == "legacy_simulator"


def test_quarantined_replay_cannot_select_owner(routed, tmp_path):
    store, world, router, kernel, authority, clock = routed
    store.replay(tmp_path / "restored.db")
    with Store(tmp_path / "restored.db", clock) as restored:
        blocked = CapabilityRouter(restored, {c: world for c in CAPABILITIES}, authority)
        with pytest.raises(CoreError, match="RESTORE_QUARANTINE"):
            blocked.select_owner("core_simulator", authority)
    assert world.counts()["effects"] == 0


def test_routed_card_real_sigkill_recovers_one_effect_and_owner(tmp_path):
    core, external = tmp_path / "core.db", tmp_path / "world.db"
    authority = OperatorAuthority()
    from nana_core.clock import ManualClock
    from nana_core.contracts import GrantSpec, VERIFY_CAPABILITY
    clock = ManualClock()
    with Store(core, clock) as store:
        identity = store.identity
        world = FakeWorld(external)
        world.seed_source(SOURCE, [{"text": "Synthetic routed crash source.", "locator": "page 3"}])
        router = CapabilityRouter(store, {c: world for c in CAPABILITIES}, authority)
        router.select_owner("legacy_simulator", authority)
        kernel = ActionKernel(store, router.bind("legacy_simulator", authority), authority)
        kernel.set_budgets({"write_attempts": 3, "external_requests": 20, "cost_micro_units": 20}, authority)
        kernel.grant(GrantSpec(capabilities=tuple(sorted(CAPABILITIES | {VERIFY_CAPABILITY})), resources=(SOURCE, CARD),
            not_before_us=clock.utc_now_us(), expires_at_us=clock.utc_now_us() + 100_000_000), authority)
        action = kernel.propose("reading.card.create", CARD, args(world))
        kernel.prepare(action)
        world.close()
    script = """
import os,signal,sys
from nana_core.storage import Store
from nana_core.clock import ManualClock
from nana_core.actions import ActionKernel,OperatorAuthority
from nana_core.contracts import CAPABILITIES
from nana_core.fake_world import FakeWorld
from nana_core.migration.routing import CapabilityRouter
a=OperatorAuthority()
with Store(sys.argv[1],ManualClock()) as s:
 w=FakeWorld(sys.argv[2]);r=CapabilityRouter(s,{c:w for c in CAPABILITIES},a)
 k=ActionKernel(s,r.bind('legacy_simulator',a),a)
 def fault(point):
  if point=='after_effect':os.kill(os.getpid(),signal.SIGKILL)
 k.dispatch(sys.argv[3],fault=fault)
"""
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    child = subprocess.run([sys.executable, "-c", script, str(core), str(external), action], env=env, capture_output=True, timeout=10)
    assert child.returncode == -signal.SIGKILL
    with Store(core, clock) as store:
        world = FakeWorld(external)
        try:
            router = CapabilityRouter(store, {c: world for c in CAPABILITIES}, authority)
            assert router.owner == {"actor": "legacy_simulator", "epoch": 1, "scope": "synthetic_only"}
            assert store.identity == identity and store.one("actions", action)["state"] == "DISPATCHING"
            recovered = ActionKernel(store, router.bind("legacy_simulator", authority), authority).recover()
            assert recovered[action] == "SUCCEEDED"
            assert world.counts()["effects"] == world.counts()["execute_calls"] == 1
        finally:
            world.close()
