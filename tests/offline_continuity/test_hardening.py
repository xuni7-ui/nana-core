import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
import pytest
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError, Feedback, Observation
from nana_core.experience import ExperienceEngine
from nana_core.fake_world import FakeWorld
from nana_core.planning import FixtureModel
from nana_core.runtime import Runtime
from nana_core.storage import Store
from conftest import CARD, SOURCE, PARAGRAPHS, authorize, card_args
from test_runtime import reading


@pytest.mark.s1
def test_missing_identity_is_not_silently_recreated(tmp_path):
    path = tmp_path / "nana.db"
    with Store(path) as store:
        store.db.execute("DELETE FROM identities")
    with pytest.raises(CoreError, match="IDENTITY_MISSING"):
        Store(path)


@pytest.mark.s1
def test_backup_and_replay_refuse_overwrite(environment, tmp_path):
    store = environment[0]
    destination = tmp_path / "existing.db"
    destination.write_bytes(b"synthetic-existing-file")
    for operation in (store.backup, store.replay):
        with pytest.raises(CoreError, match="DESTINATION_EXISTS"):
            operation(destination)
    assert destination.read_bytes() == b"synthetic-existing-file"


@pytest.mark.s2
def test_world_refuses_core_database_alias(environment):
    store = environment[0]
    before = store.db.execute("SELECT name FROM sqlite_master").fetchall()
    with pytest.raises(CoreError, match="EXTERNAL_WORLD_MUST_BE_SEPARATE"):
        FakeWorld(store.path)
    assert store.db.execute("SELECT name FROM sqlite_master").fetchall() == before


@pytest.mark.s2
def test_clock_rollback_cannot_resurrect_authority(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    first = kernel.propose("reading.source.read", SOURCE, {"source_id": SOURCE})
    assert kernel.run(first) == "SUCCEEDED"
    clock.advance(-3_000_000)
    second = kernel.propose("reading.card.create", CARD, card_args())
    with pytest.raises(CoreError, match="CLOCK_ROLLBACK"):
        kernel.run(second)
    assert world.counts()["effects"] == 0


@pytest.mark.s2
def test_unknown_cannot_be_cancelled_and_free_budget(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    world.control("lose_receipt", True)
    world.control("verify_unavailable", True)
    action = kernel.propose("reading.card.create", CARD, card_args())
    assert kernel.run(action) == "UNKNOWN"
    before = store.all("budgets")
    with pytest.raises(CoreError, match="ILLEGAL_ACTION_TRANSITION"):
        kernel.cancel(action)
    assert store.one("actions", action)["state"] == "UNKNOWN"
    assert store.all("budgets") == before


@pytest.mark.s2
def test_E07_competing_processes_cannot_overreserve(tmp_path):
    path, world_path = tmp_path / "nana.db", tmp_path / "fake_world.db"
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(path, clock) as store:
        world = FakeWorld(world_path)
        world.seed_source(SOURCE, PARAGRAPHS)
        kernel = ActionKernel(store, world, authority)
        kernel.set_budgets({"write_attempts": 1, "external_requests": 10, "cost_micro_units": 10}, authority)
        authorize(kernel, authority, clock, resources=(SOURCE, CARD, CARD + "-other"))
        actions = [kernel.propose("reading.card.create", r, card_args()) for r in (CARD, CARD + "-other")]
        world.close()
    script = '''
import sys, time
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError
from nana_core.fake_world import FakeWorld
from nana_core.storage import Store
try:
    with Store(sys.argv[1], ManualClock()) as store:
        world = FakeWorld(sys.argv[2])
        ActionKernel(store, world, OperatorAuthority()).prepare(sys.argv[3])
        print("RESERVED", flush=True)
        time.sleep(0.15)
        world.close()
except CoreError as error:
    print(error.code, flush=True)
'''
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path("src").resolve())}
    children = [subprocess.Popen([sys.executable, "-c", script, str(path), str(world_path), action],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for action in actions]
    output = [child.communicate(timeout=10)[0].strip() for child in children]
    assert all(child.returncode == 0 for child in children)
    assert output.count("RESERVED") == 1
    assert set(output) <= {"RESERVED", "RUNTIME_ALREADY_ACTIVE", "BUDGET_EXHAUSTED"}
    with Store(path, clock) as store:
        assert store.one("budgets", "write_attempts")["held"] == 1
        assert len(store.all("attempts")) == 1


@pytest.mark.s3
def test_model_cannot_change_authorized_plan_target(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    class RedirectingModel:
        descriptor = "adversarial-fixture"
        def propose(self, request):
            return {"purpose": "redirect", "steps": [{"capability": "reading.source.read", "resource": SOURCE},
                {"capability": "reading.card.create", "resource": "notebook://unapproved/target"}]}
    with pytest.raises(CoreError, match="RESOURCE_MISMATCH"):
        Runtime(store, kernel, RedirectingModel()).process(reading())
    assert not world.counts()["effects"]
    assert not store.all("actions")


@pytest.mark.s3
def test_entire_goal_recovers_after_real_card_commit_SIGKILL(tmp_path):
    path, world_path = tmp_path / "nana.db", tmp_path / "fake_world.db"
    clock, authority = ManualClock(), OperatorAuthority()
    with Store(path, clock) as store:
        world = FakeWorld(world_path)
        world.seed_source(SOURCE, PARAGRAPHS)
        kernel = ActionKernel(store, world, authority)
        kernel.set_budgets({"write_attempts": 1, "external_requests": 20, "cost_micro_units": 20}, authority)
        authorize(kernel, authority, clock)
        world.close()
    script = '''
import os, signal, sys
from nana_core.actions import ActionKernel, OperatorAuthority
from nana_core.clock import ManualClock
from nana_core.contracts import Observation
from nana_core.fake_world import FakeWorld
from nana_core.planning import FixtureModel
from nana_core.runtime import Runtime
from nana_core.storage import Store
with Store(sys.argv[1], ManualClock()) as store:
    world = FakeWorld(sys.argv[2])
    runtime = Runtime(store, ActionKernel(store, world, OperatorAuthority()), FixtureModel())
    def crash(point, capability):
        if point == "after_effect" and capability == "reading.card.create":
            os.kill(os.getpid(), signal.SIGKILL)
    runtime.process(Observation(source_namespace="synthetic", object_id="full-goal-crash",
        raw_text="Synthetic interrupted reading.", source_id=sys.argv[3], card_resource=sys.argv[4]), fault=crash)
'''
    result = subprocess.run([sys.executable, "-c", script, str(path), str(world_path), SOURCE, CARD],
        env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path("src").resolve())}, timeout=10)
    assert result.returncode == -signal.SIGKILL
    with Store(path, clock) as store:
        world = FakeWorld(world_path)
        model = FixtureModel()
        runtime = Runtime(store, ActionKernel(store, world, OperatorAuthority()), model)
        assert store.all("goals")[0]["state"] == "ACTIVE"
        runtime.resume()
        assert store.all("goals")[0]["state"] == "COMPLETED"
        assert world.counts()["effects"] == 1
        assert world.counts()["execute_calls"] == 2  # source + card; neither was repeated
        assert model.calls == 0  # recovery uses recorded plan, not a new model answer
        world.close()


@pytest.mark.s4
def test_candidate_induction_is_idempotent_for_same_feedback(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    goal = Runtime(store, kernel, FixtureModel()).process(reading())
    engine = ExperienceEngine(store, kernel)
    feedback = engine.feedback(Feedback(goal_id=goal, text="Synthetic location request.", requested_fields=("locator",)), authority)
    first = engine.propose(feedback)
    assert engine.propose(feedback) == first
    assert len(store.all("strategies")) == 1
