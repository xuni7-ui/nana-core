"""Same-process shadow ingestion/comparison with no CapabilityPort or Runtime."""
import json
from ..contracts import CoreError, PlanProposal
from ..planning import ContextBuilder, PlanCompiler
from ..storage import canonical, digest


class ShadowObserver:
    def __init__(self, store):
        self.store = store
        self.compiler = PlanCompiler()

    def observe(self, observation, legacy_proposal: PlanProposal | None,
                core_proposal: PlanProposal | None, comparison_revision="1"):
        if not observation.source_namespace.startswith("synthetic."):
            raise CoreError("SYNTHETIC_OBSERVATION_REQUIRED")
        if observation.kind == "reading" and (not observation.source_id or not observation.card_resource
            or not observation.source_id.startswith("source://synthetic/")
            or not observation.card_resource.startswith("notebook://synthetic/")):
            raise CoreError("SYNTHETIC_RESOURCE_REQUIRED")
        if any(p is not None and not isinstance(p, PlanProposal) for p in (legacy_proposal, core_proposal)):
            raise CoreError("STRICT_SHADOW_PROPOSAL_REQUIRED")
        # Revalidate even frozen DTOs constructed through model_copy/model_construct.
        plans = [PlanProposal.model_validate(p.model_dump()) if p else None for p in (legacy_proposal, core_proposal)]
        event_id = self.store.ingest(observation)
        key = canonical([event_id, comparison_revision])
        inputs = {"legacy": plans[0].model_dump() if plans[0] else None,
                  "core": plans[1].model_dump() if plans[1] else None}
        previous = self.store.db.execute("SELECT * FROM events WHERE source_namespace=? AND source_key=?",
            ("migration.shadow_comparison", key)).fetchone()
        if previous:
            data = json.loads(previous["data_json"])["data"]
            if data["input_hash"] != digest(inputs):
                raise CoreError("SHADOW_COMPARISON_COLLISION")
            return {"comparison_event_id": previous["event_id"], **data}
        differences = []
        compiled = None
        legacy_valid = None
        if observation.kind == "reading":
            if plans[1] is None:
                raise CoreError("SHADOW_CORE_PROPOSAL_REQUIRED")
            request, strategies = ContextBuilder(self.store).build(event_id, suspend_invalid=False)
            compiled = self.compiler.compile(plans[1], request, strategies)
            try:
                if plans[0] is None:
                    raise CoreError("LEGACY_PLAN_UNAVAILABLE")
                self.compiler.validate(plans[0], request)
                legacy_valid = True
                if [s.model_dump() for s in plans[0].steps] != compiled["steps"]:
                    differences.append("PLAN_STEPS_DIFFER")
            except CoreError as exc:
                legacy_valid = False
                differences.append(exc.code)
        else:
            if any(p is not None for p in plans):
                differences.append("UNRELATED_EVENT_SHOULD_NOT_CREATE_GOAL")
        owner = self.store.one("core_meta", "migration.execution_owner")
        data = {"observation_event_id": event_id, "input_hash": digest(inputs), "inputs": inputs,
            "core_draft": compiled, "legacy_plan_valid": legacy_valid, "differences": differences,
            "execution_owner_at_observation": json.loads(owner["value_json"]) if owner else None,
            "execution_requested": False, "goal_created": False,
            "scope": "synthetic shadow comparison only; not legacy production parity"}
        # Return the same JSON representation on first observation and restart.
        data = json.loads(canonical(data))
        with self.store.transaction("migration.shadow_compared", data,
            "migration.shadow_comparison", key, self.store.event(event_id)["occurred_at_us"]) as tx:
            tx.payload_id = tx.artifact(canonical(data).encode())
        return {"comparison_event_id": tx.event_id, **data}
