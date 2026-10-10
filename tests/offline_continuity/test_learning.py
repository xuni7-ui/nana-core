import json
import pytest
from pydantic import ValidationError
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.contracts import Feedback, CoreError, StrategyRule
from nana_core.experience import ExperienceEngine
from nana_core.planning import FixtureModel, PlanCompiler
from nana_core.runtime import Runtime
from nana_core.storage import Store
from test_runtime import reading
from conftest import CARD, SOURCE, authorize

pytestmark = pytest.mark.s4


def learn_once(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock, resources=(SOURCE, CARD, "notebook://synthetic/card-2"))
    runtime = Runtime(store, kernel, FixtureModel())
    goal = runtime.process(reading())
    engine = ExperienceEngine(store, kernel)
    feedback, strategies = engine.learn(Feedback(goal_id=goal,
        text="Synthetic feedback: useful card, but please include where to find the original passage.",
        requested_fields=("locator",)), authority)
    assert len(strategies) == 1
    return runtime, engine, feedback, strategies[0]


def test_E13_E14_experience_changes_plan_and_actual_reads(environment):
    store, world, kernel, _, _ = environment
    runtime, _, _, strategy = learn_once(environment)
    grant_before = store.all("grants")
    second = runtime.process(reading("synthetic-reading-2", "notebook://synthetic/card-2"))
    plan = json.loads(next(p for p in store.all("plans") if p["goal_id"] == second)["body_json"])
    assert [s["capability"] for s in plan["steps"]] == ["reading.source.read", "reading.source.locate", "reading.card.create"]
    assert plan["applied_strategies"][0]["strategy_id"] == strategy
    assert world.counts()["locate_calls"] == 1
    card = json.loads(world.db.execute("SELECT content_json FROM cards WHERE resource=?", ("notebook://synthetic/card-2",)).fetchone()[0])
    assert card["locator"] == json.loads(world.db.execute("SELECT pages_json FROM sources WHERE source_id=?", (SOURCE,)).fetchone()[0])[0]["locator"]
    active = store.one("strategies", strategy)
    with_experience = PlanCompiler().apply(plan["before"], [active])
    without_experience = PlanCompiler().apply(plan["before"], [])
    assert len(with_experience["steps"]) == len(without_experience["steps"]) + 1
    assert store.all("grants") == grant_before


def test_E11_restart_preserves_identity_time_strategy_and_decision(environment, tmp_path):
    store, world, kernel, authority, clock = environment
    runtime, _, _, strategy = learn_once(environment)
    identity = store.identity
    original = store.all("events")
    # Reopen a SQLite Backup API copy to exercise persistence without closing fixture ownership.
    path = tmp_path / "restart-copy.db"
    import sqlite3
    target = sqlite3.connect(path)
    store.db.backup(target)
    target.close()
    with Store(path, clock) as restarted:
        auth = OperatorAuthority()
        new_runtime = Runtime(restarted, ActionKernel(restarted, world, auth), FixtureModel())
        assert restarted.identity == identity
        assert restarted.all("events") == original
        goal = new_runtime.process(reading("synthetic-reading-2", "notebook://synthetic/card-2"))
        decision = json.loads(next(d for d in restarted.all("decisions") if d["goal_id"] == goal)["body_json"])
        assert decision["request"]["identity_id"] == identity["identity_id"]
        assert decision["request"]["strategy_refs"] == [strategy + "@1"]
        assert world.counts()["locate_calls"] == 1


def test_E15_learning_does_not_grant_added_read_permission(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock, resources=(SOURCE, CARD, "notebook://synthetic/card-2"),
        capabilities={"reading.source.read", "reading.card.create", "reading.action.verify"})
    runtime = Runtime(store, kernel, FixtureModel())
    first = runtime.process(reading())
    ExperienceEngine(store, kernel).learn(Feedback(goal_id=first, text="Synthetic request for a locator.", requested_fields=("locator",)), authority)
    grants_before, limits_before = store.all("grants"), [b["limit_value"] for b in store.all("budgets")]
    second = runtime.process(reading("synthetic-reading-2", "notebook://synthetic/card-2"))
    assert store.one("goals", second)["state"] == "BLOCKED"
    assert json.loads(store.one("goals", second)["body_json"])["blocked_reason"] == "AUTH_REQUIRED"
    assert world.counts()["locate_calls"] == 0
    assert world.counts()["effects"] == 1
    assert store.all("grants") == grants_before
    assert [b["limit_value"] for b in store.all("budgets")] == limits_before


def test_E16_scope_negative_and_E17_feedback_retraction(environment):
    store, world, kernel, authority, _ = environment
    runtime, engine, feedback, strategy = learn_once(environment)
    plan = json.loads(store.all("plans")[0]["body_json"])
    outside = PlanCompiler().apply(plan["before"], [store.one("strategies", strategy)], template="unrelated")
    assert outside["steps"] == plan["before"]
    assert not outside["applied_strategies"]
    engine.retract_feedback(feedback, authority)
    assert store.one("strategies", strategy)["status"] == "SUSPENDED"
    second = runtime.process(reading("synthetic-reading-2", "notebook://synthetic/card-2"))
    compiled = json.loads(next(p for p in store.all("plans") if p["goal_id"] == second)["body_json"])
    assert not compiled["applied_strategies"]
    assert world.counts()["locate_calls"] == 0


def test_candidate_needs_testing_and_support(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    goal = Runtime(store, kernel, FixtureModel()).process(reading())
    engine = ExperienceEngine(store, kernel)
    feedback = engine.feedback(Feedback(goal_id=goal, text="Synthetic locator feedback.", requested_fields=("locator",)), authority)
    strategy = engine.propose(feedback)[0]
    with pytest.raises(CoreError, match="UNTESTED_STRATEGY"):
        engine.activate(strategy)
    assert all(engine.test(strategy).values())
    engine.retract_feedback(feedback, authority)
    with pytest.raises(CoreError, match="UNTESTED_STRATEGY|FEEDBACK_RETRACTED"):
        engine.activate(strategy)


@pytest.mark.parametrize("extra", [{"grant_permission": "public.send"}, {"increase_budget": 100}, {"disable_verification": True}])
def test_E15_invalid_strategy_operations_are_rejected(extra):
    with pytest.raises(ValidationError):
        StrategyRule.model_validate({"kind": "ADD_READ_STEP", **extra})


def test_feedback_without_missing_field_does_not_manufacture_learning(environment):
    store, world, kernel, _, _ = environment
    runtime, engine, _, _ = learn_once(environment)
    second = runtime.process(reading("synthetic-reading-2", "notebook://synthetic/card-2"))
    _, candidates = engine.learn(Feedback(goal_id=second, text="Synthetic: locator still requested.", requested_fields=("locator",)), environment[3])
    assert not candidates


def test_E19_full_projection_replay_after_learning(environment, tmp_path):
    store, world, kernel, _, _ = environment
    runtime, _, _, _ = learn_once(environment)
    runtime.process(reading("synthetic-reading-2", "notebook://synthetic/card-2"))
    counts_before = world.counts()
    path = tmp_path / "replay.db"
    store.replay(path)
    with Store(path, environment[4]) as replay:
        assert replay.snapshot() == store.snapshot()
    assert world.counts() == counts_before
