import json
import pytest
from pydantic import ValidationError
from nana_core.contracts import Observation, CoreError
from nana_core.planning import FixtureModel
from nana_core.runtime import Runtime
from conftest import SOURCE, CARD, authorize

pytestmark = pytest.mark.s3


def reading(object_id="synthetic-reading-1", card=CARD, text="A fictional reader was interrupted while reading."):
    return Observation(source_namespace="synthetic", object_id=object_id, raw_text=text,
        occurred_at="2026-10-01T00:00:00Z", source_id=SOURCE, card_resource=card)


def test_E01_E02_event_to_verified_card_once(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    model = FixtureModel()
    runtime = Runtime(store, kernel, model)
    event = reading()
    goal = runtime.process(event)
    for _ in range(100):
        assert runtime.process(event.model_copy(update={"channel": "alternate"})) == goal
    assert store.one("goals", goal)["state"] == "COMPLETED"
    assert world.counts() == {"effects": 1, "execute_calls": 2, "locate_calls": 0, "verify_calls": 2}
    assert model.calls == 1
    assert len(store.all("goals")) == len(store.all("plans")) == 1
    assert len([m for m in store.all("memory_items") if m["kind"] == "EPISODE"]) == 1
    assert all(a["state"] == "SUCCEEDED" for a in store.all("actions"))


def test_goal_can_be_proposed_without_execution_authority(environment):
    store, world, kernel, _, _ = environment
    goal = Runtime(store, kernel, FixtureModel()).process(reading())
    assert store.one("goals", goal)["state"] == "BLOCKED"
    assert len(store.all("plans")) == 1
    assert world.counts()["execute_calls"] == 0


def test_E10_untrusted_model_success_and_target_are_rejected(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    class ForgingModel:
        descriptor = "untrusted-fixture"
        def propose(self, request):
            return {"purpose": "forge", "steps": [{"capability": "reading.source.read", "resource": SOURCE},
                {"capability": "reading.card.create", "resource": CARD}], "execution_succeeded": True}
    with pytest.raises(ValidationError):
        Runtime(store, kernel, ForgingModel()).process(reading())
    assert not store.all("actions")
    assert not world.counts()["effects"]


def test_long_context_is_an_excerpt_with_full_raw_evidence(environment):
    store, world, kernel, authority, clock = environment
    authorize(kernel, authority, clock)
    goal = Runtime(store, kernel, FixtureModel()).process(reading(text="synthetic " * 2000))
    decision = json.loads(store.all("decisions")[0]["body_json"])
    assert decision["request"]["event_text_coverage"] == "EXCERPT"
    assert len(decision["request"]["event_text"]) == 4000
    event = store.event(store.one("goals", goal)["event_id"])
    assert len(store.artifact(event["artifact_id"]).decode()) == 20000


def test_E20_wakes_are_deduplicated_and_not_autonomous_goals(environment):
    store, world, kernel, _, clock = environment
    model = FixtureModel()
    runtime = Runtime(store, kernel, model)
    first = runtime.schedule_wake("synthetic-check-in", clock.utc_now_us())
    assert runtime.schedule_wake("synthetic-check-in", clock.utc_now_us()) == first
    runtime.tick()
    runtime.tick()
    assert store.one("jobs", first)["state"] == "DONE"
    assert not store.all("goals")
    assert model.calls == 0
    assert not world.counts()["execute_calls"]


def test_E16_unrelated_event_has_no_goal(environment):
    store, world, kernel, _, _ = environment
    model = FixtureModel()
    assert Runtime(store, kernel, model).process(Observation(
        source_namespace="synthetic", object_id="unrelated", kind="unrelated", raw_text="Synthetic weather.")) is None
    assert not store.all("goals")
    assert not model.calls
