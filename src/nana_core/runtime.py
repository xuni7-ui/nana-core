"""Small synchronous offline driver. One active goal, no host or network services."""
import json
from pydantic import ValidationError
from .contracts import CoreError
from .planning import ContextBuilder, PlanCompiler
from .storage import canonical, digest, uid


class Runtime:
    def __init__(self, store, kernel, model):
        self.store, self.kernel, self.model = store, kernel, model
        self.context = ContextBuilder(store)
        self.compiler = PlanCompiler()

    def process(self, observation, fault=None):
        event_id = self.store.ingest(observation)
        if observation.kind != "reading":
            with self.store.transaction("decision.no_goal", {"event_id": event_id,
                    "reason": "wake or unrelated observation does not establish a purpose"}):
                pass
            return None
        existing = self.store.db.execute("SELECT goal_id FROM goals WHERE event_id=?", (event_id,)).fetchone()
        if existing:
            return self.run_goal(existing[0], fault=fault)
        if any(g["state"] in {"PROPOSED", "ACTIVE", "BLOCKED"} for g in self.store.all("goals")):
            raise CoreError("ONE_ACTIVE_GOAL_LIMIT")
        request, strategies = self.context.build(event_id)
        proposal = self.model.propose(request)
        try:
            compiled = self.compiler.compile(proposal, request, strategies)
        except (ValidationError, CoreError) as exc:
            with self.store.transaction("decision.rejected", {"event_id": event_id,
                    "reason": getattr(exc, "code", type(exc).__name__)}):
                pass
            raise
        goal_id, plan_id, decision_id = uid(), uid(), uid()
        with self.store.transaction("goal.plan_accepted", {"event_id": event_id, "goal_id": goal_id}) as tx:
            tx.put("goals", {"goal_id": goal_id, "goal_key": digest([request.identity_id, event_id, "reading_card"]),
                "event_id": event_id, "template": "reading_card", "state": "ACTIVE", "version": 1,
                "body_json": canonical({"purpose": compiled["purpose"], "origin": "CARE",
                    "success_predicate": "all_steps_verified_and_card_matches_intent", "blocked_reason": None})})
            tx.put("plans", {"plan_id": plan_id, "goal_id": goal_id, "body_json": canonical(compiled)})
            tx.put("decisions", {"decision_id": decision_id, "goal_id": goal_id,
                "body_json": canonical({"model": self.model.descriptor, "request": request.model_dump(),
                    "proposal": self.compiler.validate(proposal, request).model_dump(),
                    "context_manifest": {"event_id": event_id, "artifact_id": self.store.event(event_id)["artifact_id"],
                        "coverage": request.event_text_coverage, "identity": self.store.identity,
                        "strategy_refs": request.strategy_refs}, "compiled": compiled})})
        return self.run_goal(goal_id, fault=fault)

    def _block(self, goal, reason):
        body = json.loads(goal["body_json"])
        body["blocked_reason"] = reason
        with self.store.transaction("goal.blocked", {"goal_id": goal["goal_id"], "reason": reason}) as tx:
            tx.update("goals", goal["goal_id"], state="BLOCKED", version=goal["version"] + 1, body_json=canonical(body))

    def run_goal(self, goal_id, fault=None):
        goal = self.store.one("goals", goal_id)
        if goal["state"] in {"COMPLETED", "FAILED", "ABANDONED", "REJECTED"}:
            return goal_id
        plan = next(p for p in self.store.all("plans") if p["goal_id"] == goal_id)
        compiled = json.loads(plan["body_json"])
        read_result, locator_result = None, None
        action_ids = []
        for index, step in enumerate(compiled["steps"]):
            capability = step["capability"]
            if capability == "reading.card.create":
                if not read_result:
                    raise CoreError("VERIFIED_SOURCE_REQUIRED")
                content = read_result["text"].split("\n", 1)[0][:240]
                locator = locator_result["locator"] if locator_result else None
                if locator:
                    content += "\nSource: " + locator
                args = {"source_id": read_result["source_id"], "source_digest": read_result["source_digest"],
                        "content": content, "locator": locator}
            else:
                args = {"source_id": step["resource"]}
            action_id = self.kernel.propose(capability, step["resource"], args, goal_id=goal_id,
                plan_id=plan["plan_id"], effect_slot=digest([goal_id, index, capability]))
            action_ids.append(action_id)
            callback = (lambda point: fault(point, capability)) if fault else None
            try:
                state = self.kernel.run(action_id, fault=callback)
            except CoreError as exc:
                self._block(self.store.one("goals", goal_id), exc.code)
                return goal_id
            if state != "SUCCEEDED":
                self._block(self.store.one("goals", goal_id), "PENDING_ACTION_VERIFICATION" if state == "UNKNOWN" else state)
                return goal_id
            result = json.loads(self.store.one("actions", action_id)["result_json"])
            if capability == "reading.source.read":
                read_result = result
            elif capability == "reading.source.locate":
                locator_result = result
        final = self.store.one("actions", action_ids[-1])
        final_result = json.loads(final["result_json"])
        if compiled["applied_strategies"] and not final_result.get("locator"):
            raise CoreError("LEARNED_POSTCONDITION_NOT_MET")
        goal = self.store.one("goals", goal_id)
        with self.store.transaction("goal.completed", {"goal_id": goal_id, "action_ids": action_ids}) as tx:
            body = json.loads(goal["body_json"])
            body.update({"action_ids": action_ids, "blocked_reason": None})
            tx.update("goals", goal_id, state="COMPLETED", version=goal["version"] + 1, body_json=canonical(body))
            tx.put("memory_items", {"memory_id": uid(), "kind": "EPISODE", "status": "ACTIVE",
                "body_json": canonical({"goal_id": goal_id, "what_happened": "Prepared a private reading card.",
                    "verified_outcome": "SUCCEEDED", "action_ids": action_ids,
                    "applied_strategy_refs": compiled["applied_strategies"],
                    "source_refs": [{"event_id": goal["event_id"], "coverage": "FULL"}] + [
                        {"event_id": json.loads(self.store.one("actions", a)["body_json"])["verification_event_id"],
                         "coverage": "FULL"} for a in action_ids]}), "created_event_id": tx.event_id})
        return goal_id

    def resume(self):
        recovered = self.kernel.recover()
        for goal in self.store.all("goals"):
            if goal["state"] in {"ACTIVE", "BLOCKED"}:
                self.run_goal(goal["goal_id"])
        return recovered

    def schedule_wake(self, schedule_id, due_at_us):
        key = canonical([schedule_id, due_at_us])
        existing = self.store.db.execute("SELECT job_id FROM jobs WHERE occurrence_key=?", (key,)).fetchone()
        if existing:
            return existing[0]
        job_id = uid()
        with self.store.transaction("scheduler.wake_scheduled") as tx:
            tx.put("jobs", {"job_id": job_id, "occurrence_key": key, "due_at_us": due_at_us,
                "state": "WAITING", "body_json": canonical({"purpose": None})})
        return job_id

    def tick(self):
        for job in self.store.all("jobs"):
            if job["state"] == "WAITING" and job["due_at_us"] <= self.store.clock.utc_now_us():
                with self.store.transaction("scheduler.wake", {"job_id": job["job_id"],
                        "scheduled_for_us": job["due_at_us"], "goal_created": False}) as tx:
                    tx.update("jobs", job["job_id"], state="DONE")
