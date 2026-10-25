"""Source-filtered task state from original Kernel verification, never truth cache."""

import json
from typing import Literal
from ...contracts import DTO, CoreError
from ...storage import digest


class TaskStateFact(DTO):
    operator_id: str
    resource: str
    action_id: str
    memory_id: str
    observed_at_us: int
    environment_revision: str | None
    freshness: Literal["CURRENT", "STALE", "REVISION_MISMATCH"]
    epistemic_kind: Literal["VERIFIED_OPERATION_RESULT"] = "VERIFIED_OPERATION_RESULT"
    verification_is_world_truth: Literal[False] = False
    authority_granted: Literal[False] = False


def observation_state(service, output, guard):
    """Must not be used to retry or erase an existing effect/UNKNOWN action."""
    action = service.store.one("actions", output["action_id"])
    if (
        not action
        or action["state"] != "SUCCEEDED"
        or action["capability"] != "world.observe"
        or not output.get("quality")
    ):
        raise CoreError("VERIFIED_STATE_REQUIRED")
    memory = service.records.memory.read(output["memory_id"])
    if memory["scope"] not in service.subject.scopes or memory["privacy_class"] not in service.subject.privacy_classes:
        raise CoreError("TASK_STATE_SCOPE_DENIED")
    payload = json.loads(memory["text"])
    expected = service.realization.kernel.payload(action, "result_json")
    if json.loads(expected) != payload:
        raise CoreError("TASK_STATE_RESULT_MISMATCH")
    now = service.store.clock.utc_now_us()
    age = now - memory["observed_time_us"]
    # The shared contract is the digest of independently observed data. Some
    # ports expose a native integer revision inside data, others an outer digest.
    # Never pretend a missing outer field is a current native resource CAS token.
    revision = digest(payload.get("data"))
    freshness = (
        "STALE"
        if age < 0 or age > guard.max_age_us
        else "REVISION_MISMATCH"
        if guard.expected_revision is not None and revision != guard.expected_revision
        else "CURRENT"
    )
    return TaskStateFact(
        operator_id=output["operator_id"],
        resource=action["resource"],
        action_id=action["action_id"],
        memory_id=memory["memory_id"],
        observed_at_us=memory["observed_time_us"],
        environment_revision=revision,
        freshness=freshness,
    )
