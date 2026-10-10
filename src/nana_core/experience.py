"""Feedback-driven, scoped procedural memory. No arbitrary code or permission mutation."""
import json
from .contracts import CoreError, Feedback, StrategyRule
from .planning import PlanCompiler
from .storage import canonical, digest, uid

# Capability output schema registry: induction selects a producer for a missing
# requested field. It does not use test event IDs, paragraph text, or expected counts.
OUTPUT_PRODUCERS = {"locator": "reading.source.locate"}


class ExperienceEngine:
    def __init__(self, store, kernel):
        self.store, self.kernel = store, kernel
        self.compiler = PlanCompiler()

    def feedback(self, feedback: Feedback, authority):
        self.kernel._operator(authority)
        goal = self.store.one("goals", feedback.goal_id)
        if not goal or goal["state"] != "COMPLETED":
            raise CoreError("VERIFIED_GOAL_REQUIRED")
        with self.store.transaction("feedback.received", {"feedback": feedback.model_dump(),
                "issuer": authority.principal, "goal_id": goal["goal_id"]}) as tx:
            tx.payload_id = tx.artifact(feedback.model_dump_json().encode())
            tx.put("memory_items", {"memory_id": tx.event_id, "kind": "CLAIM", "status": "ACTIVE",
                "body_json": canonical({"epistemic_kind": "USER_STATEMENT", "assessment": "SUPPORTED",
                    "content": feedback.text, "requested_fields": feedback.requested_fields,
                    "goal_id": goal["goal_id"], "source_refs": [{"event_id": tx.event_id,
                        "artifact_id": tx.payload_id, "coverage": "FULL"}]}), "created_event_id": tx.event_id})
        return tx.event_id

    def propose(self, feedback_event_id):
        event = self.store.event(feedback_event_id)
        support = self.store.one("memory_items", feedback_event_id)
        if event["kind"] != "feedback.received" or not support or support["status"] != "ACTIVE":
            raise CoreError("INVALID_FEEDBACK_SOURCE")
        feedback = Feedback.model_validate_json(canonical(json.loads(event["data_json"])["data"]["feedback"]))
        goal = self.store.one("goals", feedback.goal_id)
        if goal["state"] != "COMPLETED":
            raise CoreError("VERIFIED_GOAL_REQUIRED")
        actions = [a for a in self.store.all("actions") if a["goal_id"] == goal["goal_id"]
                   and a["capability"] == "reading.card.create" and a["state"] == "SUCCEEDED"]
        if len(actions) != 1:
            raise CoreError("VERIFIED_CARD_REQUIRED")
        result = json.loads(actions[0]["result_json"])
        missing = [f for f in feedback.requested_fields if not result.get(f)]
        candidates = []
        for field in dict.fromkeys(missing):
            producer = OUTPUT_PRODUCERS.get(field)
            if producer is None:
                raise CoreError("UNSUPPORTED_LEARNING_FIELD")
            rule = StrategyRule(capability=producer, required_output=field)
            strategy_id = uid()
            episode = next(m for m in self.store.all("memory_items") if m["kind"] == "EPISODE"
                           and json.loads(m["body_json"])["goal_id"] == goal["goal_id"])
            body = {"rule_json": rule.model_dump_json(), "scope": goal["template"],
                "support_refs": [feedback_event_id, episode["created_event_id"],
                    json.loads(actions[0]["body_json"])["verification_event_id"]],
                "hypothesis": f"Acquire {field} before writing this class of reading card.",
                "rule_hash": digest(rule.model_dump()), "evaluation": None,
                "promotion_scope": "narrow_trial_not_general_law"}
            with self.store.transaction("experience.proposed", {"strategy_id": strategy_id}) as tx:
                tx.put("strategies", {"strategy_id": strategy_id, "revision": 1, "status": "CANDIDATE",
                    "feedback_event_id": feedback_event_id, "body_json": canonical(body)})
            candidates.append(strategy_id)
        return candidates

    def test(self, strategy_id):
        strategy = self.store.one("strategies", strategy_id)
        if not strategy or strategy["status"] != "CANDIDATE":
            raise CoreError("ILLEGAL_STRATEGY_TRANSITION")
        body = json.loads(strategy["body_json"])
        rule = StrategyRule.model_validate_json(body["rule_json"])
        base = [{"capability": "reading.source.read", "resource": "source://synthetic/evaluation"},
                {"capability": "reading.card.create", "resource": "notebook://synthetic/evaluation"}]
        preview = {**strategy, "status": "ACTIVE"}
        positive = self.compiler.apply(base, [preview])
        already_present = self.compiler.apply(positive["steps"], [preview])
        unrelated = self.compiler.apply(base, [preview], template="unrelated")
        checks = {
            "adds_missing_read": sum(s["capability"] == rule.capability for s in positive["steps"]) == 1,
            "does_not_duplicate_read": already_present["steps"] == positive["steps"],
            "scope_is_respected": unrelated["steps"] == base and not unrelated["applied_strategies"],
            "write_target_unchanged": positive["steps"][-1] == base[-1],
            "only_allowlisted_read_added": len(positive["steps"]) == len(base) + 1
                and positive["steps"][-2]["resource"] == base[0]["resource"],
        }
        body["evaluation"] = {"compiler_version": self.compiler.version, "cases": checks,
                              "rule_hash": digest(rule.model_dump()), "tested": all(checks.values())}
        with self.store.transaction("experience.tested", {"strategy_id": strategy_id, "checks": checks}) as tx:
            tx.update("strategies", strategy_id, status="TESTED" if all(checks.values()) else "REJECTED",
                      body_json=canonical(body))
        return checks

    def activate(self, strategy_id):
        strategy = self.store.one("strategies", strategy_id)
        if not strategy or strategy["status"] != "TESTED":
            raise CoreError("UNTESTED_STRATEGY")
        body = json.loads(strategy["body_json"])
        rule = StrategyRule.model_validate_json(body["rule_json"])
        support = self.store.one("memory_items", strategy["feedback_event_id"])
        if not support or support["status"] != "ACTIVE":
            raise CoreError("FEEDBACK_RETRACTED")
        if body["evaluation"]["rule_hash"] != digest(rule.model_dump()) or not body["evaluation"]["tested"]:
            raise CoreError("STALE_STRATEGY_EVALUATION")
        for event_id in body["support_refs"]:
            event = self.store.event(event_id)
            if event["artifact_id"]:
                self.store.artifact(event["artifact_id"])
        with self.store.transaction("experience.activated", {"strategy_id": strategy_id}) as tx:
            tx.update("strategies", strategy_id, status="ACTIVE")

    def learn(self, feedback: Feedback, authority):
        feedback_id = self.feedback(feedback, authority)
        strategies = self.propose(feedback_id)
        for strategy_id in strategies:
            self.test(strategy_id)
            self.activate(strategy_id)
        return feedback_id, strategies

    def retire(self, strategy_id, authority):
        self.kernel._operator(authority)
        if self.store.one("strategies", strategy_id)["status"] != "ACTIVE":
            raise CoreError("ILLEGAL_STRATEGY_TRANSITION")
        with self.store.transaction("experience.retired", {"strategy_id": strategy_id}) as tx:
            tx.update("strategies", strategy_id, status="RETIRED")

    def retract_feedback(self, feedback_event_id, authority):
        self.kernel._operator(authority)
        with self.store.transaction("feedback.retracted", {"feedback_event_id": feedback_event_id}) as tx:
            tx.update("memory_items", feedback_event_id, status="RETRACTED")
            for strategy in self.store.all("strategies"):
                if strategy["feedback_event_id"] == feedback_event_id and strategy["status"] in {"ACTIVE", "TESTED", "CANDIDATE"}:
                    tx.update("strategies", strategy["strategy_id"], status="SUSPENDED")
