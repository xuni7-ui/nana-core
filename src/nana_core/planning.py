"""One bounded goal template, a deterministic engineering ModelPort, and a constrained compiler."""
import json
from .contracts import CoreError, ModelRequest, PlanProposal, StepProposal, StrategyRule


class ContextBuilder:
    def __init__(self, store):
        self.store = store

    def build(self, event_id, *, suspend_invalid=True):
        event = self.store.event(event_id)
        observation = json.loads(event["data_json"])["data"]["observation"]
        if observation["kind"] != "reading" or not observation["source_id"] or not observation["card_resource"]:
            raise CoreError("NOT_A_READING_GOAL")
        strategies = []
        for strategy in self.store.all("strategies"):
            if strategy["status"] == "ACTIVE":
                feedback = self.store.one("memory_items", strategy["feedback_event_id"])
                support_valid = True
                for ref in json.loads(strategy["body_json"])["support_refs"]:
                    try:
                        if self.store.one("core_meta", "invalidated_evidence:" + ref):
                            raise CoreError("EVIDENCE_INVALIDATED")
                        evidence = self.store.event(ref)
                        if evidence["artifact_id"]:
                            self.store.artifact(evidence["artifact_id"])
                    except CoreError:
                        support_valid = False
                if feedback and feedback["status"] == "ACTIVE" and support_valid:
                    strategies.append(strategy)
                elif suspend_invalid:
                    with self.store.transaction("experience.support_unavailable", {"strategy_id": strategy["strategy_id"]}) as tx:
                        tx.update("strategies", strategy["strategy_id"], status="SUSPENDED")
        raw = self.store.artifact(event["artifact_id"]).decode()
        request = ModelRequest(identity_id=self.store.identity["identity_id"],
            identity_revision=self.store.identity["revision"],
            identity_snapshot=json.loads(self.store.identity["body_json"]), event_id=event_id,
            event_text=raw[:4000], event_text_coverage="FULL" if len(raw) <= 4000 else "EXCERPT",
            source_id=observation["source_id"], card_resource=observation["card_resource"],
            strategy_refs=tuple(f"{s['strategy_id']}@{s['revision']}" for s in strategies))
        return request, strategies


class FixtureModel:
    """Rule-based offline planner, NOT a real LLM or semantic migration proof.

    It receives no test IDs or expected outputs and does not inspect experience.
    Learning changes plans in PlanCompiler, enabling a controlled causal comparison.
    """
    descriptor = "engineering-fixture-v1"

    def __init__(self):
        self.calls = 0

    def propose(self, request: ModelRequest):
        self.calls += 1
        return PlanProposal(purpose="Prepare a private reading card to help resume shared reading.",
            steps=(StepProposal(capability="reading.source.read", resource=request.source_id),
                   StepProposal(capability="reading.card.create", resource=request.card_resource)))


class PlanCompiler:
    version = "1"

    def validate(self, proposal, request):
        if not isinstance(proposal, PlanProposal):
            # JSON is the external boundary; JSON arrays can represent strict tuples.
            proposal = PlanProposal.model_validate_json(json.dumps(proposal))
        steps = proposal.steps
        if steps[0].capability != "reading.source.read" or steps[-1].capability != "reading.card.create":
            raise CoreError("INVALID_PLAN_ORDER")
        if sum(s.capability == "reading.card.create" for s in steps) != 1:
            raise CoreError("INVALID_WRITE_COUNT")
        if sum(s.capability == "reading.source.read" for s in steps) != 1:
            raise CoreError("INVALID_READ_COUNT")
        if sum(s.capability == "reading.source.locate" for s in steps) > 1:
            raise CoreError("DUPLICATE_LOCATOR_STEP")
        for step in steps:
            expected = request.card_resource if step.capability == "reading.card.create" else request.source_id
            if step.resource != expected:
                raise CoreError("RESOURCE_MISMATCH")
        return proposal

    def apply(self, steps, strategies, template="reading_card"):
        before = [dict(s) for s in steps]
        result = [dict(s) for s in steps]
        applied = []
        for strategy in strategies:
            if strategy["status"] != "ACTIVE":
                continue
            rule = StrategyRule.model_validate_json(json.loads(strategy["body_json"])["rule_json"])
            if rule.scope != template:
                continue
            reads = [s for s in result if s["capability"] == "reading.source.read"]
            if len(reads) != 1:
                raise CoreError("STRATEGY_PRECONDITION_FAILED")
            if not any(s["capability"] == rule.capability for s in result):
                result.insert(len(result) - 1, {"capability": rule.capability, "resource": reads[0]["resource"]})
            applied.append({"strategy_id": strategy["strategy_id"], "revision": strategy["revision"],
                "matched_condition": "reading_card requires locator", "required_output": rule.required_output})
        if len(result) > 5:
            raise CoreError("PLAN_LIMIT_EXCEEDED")
        return {"before": before, "steps": result, "applied_strategies": applied, "compiler_version": self.version}

    def compile(self, proposal, request, strategies):
        proposal = self.validate(proposal, request)
        compiled = self.apply([s.model_dump() for s in proposal.steps], strategies)
        compiled.update({"purpose": proposal.purpose, "template": proposal.goal_template,
                         "request": request.model_dump()})
        return compiled
