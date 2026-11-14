"""Recoverable learning stages with independent evaluation and held-out transfer.

Uses existing jobs, experiences, lessons, records and the same privacy graph.
No model response or summary counts as a successful trial.
"""

import json
from typing import Literal, Any, Protocol
from pydantic import Field, model_validator, model_serializer
from ...contracts import DTO, CoreError
from ...storage import canonical, digest, uid
from ..records import RecordService
from ..learning import ExperienceService
from .world import ComputeArgs, transform, bounded_data

STAGES = ("OBSERVE", "VALUE", "HYPOTHESIZE", "BASELINE", "PRACTICE", "EVALUATE", "TRANSFER", "CONSOLIDATE", "MONITOR")


class LearningCase(DTO):
    case_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    context: str = Field(min_length=1, max_length=96)
    data: Any
    expected: Any


class LearningProblem(DTO):
    """Candidate-visible practice only. Held-out inputs/answers stay with evaluator."""

    learning_key: str
    domain: str
    baseline_method: str
    hypotheses: tuple[str, ...] = Field(min_length=1, max_length=8)
    practice: tuple[LearningCase, ...] = Field(min_length=1, max_length=8)

    @classmethod
    def from_spec(cls, spec):
        return cls.model_validate(spec.model_dump(include=set(cls.model_fields)))


class LearningSpec(DTO):
    learning_key: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}\.[a-z][a-z0-9._-]{0,95}$")
    domain: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    baseline_method: str
    hypotheses: tuple[str, ...] = Field(min_length=1, max_length=8)
    practice: tuple[LearningCase, ...] = Field(min_length=1, max_length=8)
    evaluation: tuple[LearningCase, ...] = Field(min_length=1, max_length=8)
    transfer: tuple[LearningCase, ...] = Field(min_length=1, max_length=8)
    estimated_cost_micro: int = Field(default=0, ge=0, le=10000)
    hypothesis_policy: Literal["PROPOSER_ONLY", "PRACTICE_COMPARE"] = "PROPOSER_ONLY"

    @model_serializer(mode="wrap")
    def compatible_wire(self, handler):
        value = handler(self)
        if self.hypothesis_policy == "PROPOSER_ONLY":
            value.pop("hypothesis_policy", None)
        return value

    @model_validator(mode="after")
    def distinct_splits(self):
        cases = (*self.practice, *self.evaluation, *self.transfer)
        if len({c.case_id for c in cases}) != len(cases):
            raise ValueError("independent case IDs required")
        splits = [{digest(c.data) for c in group} for group in (self.practice, self.evaluation, self.transfer)]
        if any(splits[a] & splits[b] for a, b in ((0, 1), (0, 2), (1, 2))):
            raise ValueError("held-out inputs required")
        if {c.context for c in self.transfer} & {c.context for c in (*self.practice, *self.evaluation)}:
            raise ValueError("transfer needs new context")
        for c in cases:
            bounded_data(c.data)
            bounded_data(c.expected)
        for method in (self.baseline_method, *self.hypotheses):
            ComputeArgs(method=method)
        return self


class MethodStrategyRule(DTO):
    kind: Literal["METHOD_SELECTION"] = "METHOD_SELECTION"
    scope: str
    method: str
    trial_record_id: str
    grants_authority: Literal[False] = False


class LearningProposerPort(Protocol):
    def propose_method(self, spec: LearningProblem) -> str: ...


class FixtureLearningProposer:
    def propose_method(self, spec):
        return spec.hypotheses[0]


class IndependentEvaluator:
    """Application-owned oracle and real candidate computation, not candidate prose."""

    def evaluate(self, method, cases):
        rows = []
        for c in cases:
            actual = transform(method, c.data)
            rows.append(
                {
                    "case_id": c.case_id,
                    "context": c.context,
                    "input_digest": digest(c.data),
                    "actual": actual,
                    "expected_digest": digest(c.expected),
                    "passed": digest(actual) == digest(c.expected),
                }
            )
        return {
            "checked": len(rows),
            "passed": sum(r["passed"] for r in rows),
            "cases": rows,
            "all_passed": all(r["passed"] for r in rows),
        }


class LearningService:
    def __init__(
        self,
        store,
        authority,
        specs,
        *,
        privacy_classes,
        scopes,
        proposer=None,
        evaluator=None,
        max_pending=4,
        cost_ceiling_micro=10000,
        source_memory_ids=(),
    ):
        if store.schema_target < 12:
            raise CoreError("OPEN_AGENCY_SCHEMA_REQUIRED")
        self.store, self.authority = store, authority
        self.records = RecordService(store)
        self.specs = {s.learning_key: LearningSpec.model_validate_json(s.model_dump_json()) for s in specs}
        if len(self.specs) > 16 or not 1 <= max_pending <= 8:
            raise CoreError("LEARNING_POLICY_BOUND")
        self.source_memory_ids = tuple(source_memory_ids)
        if len(self.source_memory_ids) > 32:
            raise CoreError("LEARNING_SOURCE_BOUND")
        self.proposer = proposer or FixtureLearningProposer()
        self.evaluator = evaluator or IndependentEvaluator()
        self.scopes = tuple(scopes)
        if not self.scopes:
            raise CoreError("LEARNING_SCOPE_REQUIRED")
        self.privacy = tuple(privacy_classes)
        self.max_pending = max_pending
        self.ceiling = cost_ceiling_micro

    def program_options(self,*,scope,privacy_classes):
        """Read-only descriptors from this G; never practice or held-out data.

        Reuse the existing sixteen-spec policy bound and current source checks.
        """
        if scope not in self.scopes:return ()
        for mid in self.source_memory_ids:
            row=self.store.one('memories',mid)
            if (not row or row['scope']!=scope or row['privacy_class'] not in self.privacy
                    or row['privacy_class'] not in privacy_classes):return ()
            try:self.records.memory.read(mid)
            except CoreError as exc:
                if exc.code not in {'MEMORY_UNAVAILABLE','MEMORY_NOT_CURRENT'}:raise
                return ()
        from ..subject.opportunities import LearningProgramOption
        return tuple(LearningProgramOption(learning_key=s.learning_key,domain=s.domain,spec_digest=digest(s.model_dump(mode='json')))
            for s in self.specs.values())

    def after_cycle(self, runtime, cycle, event):
        if event.scope not in self.scopes:
            raise CoreError("LEARNING_SCOPE_DENIED")
        if not cycle.evaluation or cycle.evaluation.normative != "ENDORSED":
            return None
        spec = self.specs.get(cycle.proposed_program_id)
        experience = None
        if cycle.intention.kind == "REFLECTION" and event.reflection_experience_id:
            experience = self.store.one("experiences", event.reflection_experience_id)
            if experience:
                spec = next((s for s in self.specs.values() if s.domain == experience["task_class"]), None)
        if not spec:
            return None
        key = digest([cycle.cycle_id, spec.learning_key, event.reflection_experience_id])
        old = self.store.db.execute("SELECT * FROM jobs WHERE occurrence_key=?", ("learning:" + key,)).fetchone()
        if old:
            return old["job_id"]
        # Repeated wakes reuse current work. A completed problem may only reopen
        # after a distinct, later checked failure and the old method's withdrawal;
        # otherwise one early lesson permanently prevents future growth.
        previous = self.store.db.execute(
            "SELECT j.* FROM jobs j JOIN continuity_records r ON r.record_id=j.record_id WHERE j.work_kind='LEARNING' AND r.target_id=? AND r.scope=? AND r.lifecycle='ACTIVE' ORDER BY j.rowid DESC LIMIT 1",
            (spec.learning_key, event.scope),
        ).fetchone()
        reconsider = previous is not None and self._new_verified_gap(previous, experience, spec, event.scope)
        if previous and not reconsider:
            b = self.records.read(previous["record_id"])["payload"]
            if previous["state"] == "BLOCKED" and b.get("context_paused"):
                binding = b["context_binding"]
                from ..subject.context_fit import depth_boundary

                closed, _, _ = depth_boundary(
                    self.store, binding["entity_id"], event.scope, binding["topic"], self.privacy, purpose="COGNITION"
                )
                if not closed:
                    with self.store.transaction(
                        "open.learning_context_reconsidered",
                        {"work_id": previous["job_id"], "cycle_id": cycle.cycle_id},
                    ) as tx:
                        if self.store.one("jobs", previous["job_id"])["revision"] != previous["revision"]:
                            raise CoreError("STALE_LEARNING_WORK")
                        rid = self.records.create(
                            tx,
                            kind="OPEN_LEARNING",
                            scope=event.scope,
                            payload={**b, "context_paused": False},
                            records=(previous["record_id"], cycle.record_id),
                            supersedes=previous["record_id"],
                            target_id=spec.learning_key,
                        )
                        tx.update(
                            "jobs",
                            previous["job_id"],
                            record_id=rid,
                            state="WAITING",
                            revision=previous["revision"] + 1,
                        )
            i = self.store.one("subject_intentions", cycle.intention_id)
            if i and i["state"] == "PENDING":
                with self.store.transaction("open.learning_already_selected", {"work_id": previous["job_id"]}) as tx:
                    tx.update("subject_intentions", i["intention_id"], state="COMPLETED", revision=i["revision"] + 1)
            return previous["job_id"]
        if (
            self.store.db.execute(
                "SELECT count(*) FROM jobs WHERE work_kind='LEARNING' AND state IN ('WAITING','RUNNING','UNKNOWN')"
            ).fetchone()[0]
            >= self.max_pending
        ):
            return None
        for mid in self.source_memory_ids:
            m = self.records.memory.read(mid)
            if m["scope"] != event.scope or m["privacy_class"] not in self.privacy:
                raise CoreError("LEARNING_SOURCE_DENIED")
        parents = (cycle.record_id, *((experience["record_id"],) if experience else ()))
        now = self.store.clock.utc_now_us()
        wid = uid()
        with self.store.transaction("open.learning_selected", {"work_id": wid, "cycle_id": cycle.cycle_id}) as tx:
            rid = self.records.create(
                tx,
                kind="OPEN_LEARNING",
                scope=event.scope,
                payload={
                    "stage": "OBSERVE",
                    "spec": spec.model_dump(mode="json"),
                    "results": {},
                    "cause": "VERIFIED_FAILURE"
                    if experience and experience["outcome"] == "FAILURE"
                    else "SOURCED_INTEREST_OR_GAP",
                    "context_binding": {"entity_id": event.entity_id, "topic": cycle.context_fit.topic_key}
                    if cycle.context_fit
                    else None,
                    "selected_method": None,
                    "trial_record_id": None,
                    "lesson_id": None,
                    **({"origin_private_thought_ref":event.private_thought_ref.model_dump(mode='json')}
                        if event.private_thought_ref is not None and cycle.intention.behavior=='LEARN' else {}),
                    **({"previous_work_id": previous["job_id"],
                        "reconsidered_experience_id": experience["experience_id"]} if reconsider else {}),
                },
                records=parents,
                memories=self.source_memory_ids,
                target_id=spec.learning_key,
            )
            tx.put(
                "jobs",
                {
                    "job_id": wid,
                    "occurrence_key": "learning:" + key,
                    "due_at_us": now,
                    "state": "WAITING",
                    "body_json": "{}",
                    "work_kind": "LEARNING",
                    "record_id": rid,
                    "revision": 1,
                    "cursor": 0,
                    "owner_epoch": None,
                    "updated_at_us": now,
                },
            )
            i = self.store.one("subject_intentions", cycle.intention_id)
            if i and i["state"] == "PENDING":
                tx.update("subject_intentions", i["intention_id"], state="COMPLETED", revision=i["revision"] + 1)
            if cycle.goal_candidate_id:
                tx.update("subject_goal_candidates", cycle.goal_candidate_id, state="ADOPTED")
        return wid

    def _new_verified_gap(self, previous, experience, spec, scope):
        """Reconsideration is new C-endorsed work, never an UNKNOWN retry.

        Event order, rather than host time, proves a new occurrence. A suggestion,
        wake, changed model or changed practice file alone cannot restart work.
        Source withdrawal still invalidates both the gap and its derived work.
        """
        if previous["state"] not in {"DONE", "BLOCKED"} or not experience:
            return False
        if experience["outcome"] != "FAILURE" or experience["task_class"] != spec.domain:
            return False
        head = self.store.one("continuity_records", experience["record_id"])
        if (not head or head["scope"] != scope or head["privacy_class"] not in self.privacy
                or head["lifecycle"] != "ACTIVE" or not self.records.current_support(head["record_id"])):
            return False
        body = self.records.read(previous["record_id"])["payload"]
        if body.get("context_paused") or body["spec"]["domain"] != spec.domain:
            return False
        # Another failure is not new learning material. Repeating unchanged
        # practice would reproduce the same suspended rule, qualify it on the
        # same holdouts and loop forever. Compare candidate-visible material
        # only: changing heldout answers must never enable another experiment.
        old_problem = LearningProblem.from_spec(LearningSpec.model_validate_json(canonical(body["spec"])))
        if old_problem == LearningProblem.from_spec(spec):
            return False
        if body.get("lesson_id"):
            lesson = self.store.one("lessons", body["lesson_id"])
            if not lesson or lesson["state"] not in {"SUSPENDED", "REJECTED", "RETIRED"}:
                return False
        newer = self.store.db.execute(
            "SELECT 1 FROM continuity_records gap JOIN events ge ON ge.event_id=gap.event_id "
            "JOIN continuity_records prior ON prior.record_id=? JOIN events pe ON pe.event_id=prior.event_id "
            "WHERE gap.record_id=? AND ge.rowid>pe.rowid",
            (previous["record_id"], head["record_id"]),
        ).fetchone()
        return newer is not None

    def next_job(self):
        scopes = ",".join("?" for _ in self.scopes)
        privacy = ",".join("?" for _ in self.privacy)
        return self.store.db.execute(
            f"SELECT j.* FROM jobs j JOIN continuity_records r ON r.record_id=j.record_id WHERE r.scope IN ({scopes}) AND r.privacy_class IN ({privacy}) AND j.work_kind='LEARNING' AND j.state='WAITING' AND j.due_at_us<=? ORDER BY j.due_at_us LIMIT 1",
            (*self.scopes, *self.privacy, self.store.clock.utc_now_us()),
        ).fetchone()

    def slice(self):
        job = self.next_job()
        if not job:
            return None
        rid = job["record_id"]
        head = self.store.one("continuity_records", rid)
        if not self.records.current_support(rid) or head["lifecycle"] != "ACTIVE":
            return self._terminal(job, "CANCELLED", "SOURCE_RETIRED")
        body = self.records.read(rid)["payload"]
        spec = LearningSpec.model_validate_json(canonical(body["spec"]))
        if body.get("learning_strategy_record_id"):
            meta = self.store.db.execute(
                "SELECT state FROM lessons WHERE record_id=?", (body["learning_strategy_record_id"],)
            ).fetchone()
            if not meta or meta["state"] != "ACTIVE":
                return self._terminal(job, "BLOCKED", "LEARNING_STRATEGY_SUSPENDED")
        if spec.learning_key not in self.specs or self.specs[spec.learning_key] != spec:
            return self._terminal(job, "BLOCKED", "LEARNING_POLICY_CHANGED")
        binding = body.get("context_binding")
        if binding:
            from ..subject.context_fit import depth_boundary

            closed, _, _ = depth_boundary(
                self.store, binding["entity_id"], head["scope"], binding["topic"], self.privacy, purpose="COGNITION"
            )
            if closed:
                with self.store.transaction("open.learning_context_paused", {"work_id": job["job_id"]}) as tx:
                    if self.store.one("jobs", job["job_id"])["revision"] != job["revision"]:
                        raise CoreError("STALE_LEARNING_WORK")
                    newrid = self.records.create(
                        tx,
                        kind="OPEN_LEARNING",
                        scope=head["scope"],
                        payload={**body, "context_paused": True},
                        records=(rid,),
                        supersedes=rid,
                        target_id=spec.learning_key,
                    )
                    tx.update("jobs", job["job_id"], record_id=newrid, state="BLOCKED", revision=job["revision"] + 1)
                return {"work_id": job["job_id"], "reason": "CONTEXT_TOPIC_CLOSED"}
        stage = STAGES[job["cursor"]]
        new = json.loads(canonical(body))
        next_cursor = job["cursor"] + 1
        # Computation/validation happens BEFORE advancing cursor. An exception,
        # timeout or killed process leaves this exact stage pending on reopen.
        if stage == "VALUE" and spec.estimated_cost_micro > self.ceiling:
            return self._terminal(job, "BLOCKED", "LEARNING_COST_CEILING")
        if stage == "HYPOTHESIZE":
            from ..open_life.meta_learning import select

            problem = LearningProblem.from_spec(spec)
            method, strategy_record = select(self.store, problem, scope=head["scope"], privacy=self.privacy)
            if method is None:
                method = self.proposer.propose_method(problem)
            else:
                new["learning_strategy_record_id"] = strategy_record
            if method not in spec.hypotheses:
                raise CoreError("LEARNING_HYPOTHESIS_REJECTED")
            nominated_method = method
            if spec.hypothesis_policy == "PRACTICE_COMPARE":
                # Only public practice crosses this boundary. Final evaluation
                # and transfer remain untouched application-owned holdouts.
                from .practice import compare_practice

                method, trials = compare_practice(problem, preferred=method, evaluator=getattr(self.evaluator, "practice_evaluate", None))
                new["practice_competition"] = {
                    "nominee": nominated_method,
                    "selected": method,
                    "trials": trials,
                    "selection_scope": "PRACTICE_ONLY_NOT_QUALIFICATION",
                }
            new["selected_method"] = method
            parent = getattr(self.proposer, "last_record_id", None)
            if parent:
                record = self.records.read(parent)
                if (
                    record["record_kind"] != "COGNITION_PROPOSAL"
                    or record["scope"] != head["scope"]
                    or record["privacy_class"] not in self.privacy
                    or not self.records.current_support(parent)
                    or record["payload"]["reply"]["proposal"]["method"] != nominated_method
                ):
                    raise CoreError("LEARNING_COGNITION_SOURCE_MISMATCH")
                new["hypothesis_source"] = parent
        if stage in {"BASELINE", "PRACTICE", "EVALUATE", "TRANSFER"}:
            method = spec.baseline_method if stage == "BASELINE" else body["selected_method"]
            cases = (
                spec.evaluation
                if stage in {"BASELINE", "EVALUATE"}
                else spec.practice
                if stage == "PRACTICE"
                else spec.transfer
            )
            new["results"][stage] = self.evaluator.evaluate(method, cases)
            result = new["results"][stage]
            if result["checked"] != len(cases) or len(result["cases"]) != len(cases):
                raise CoreError("LEARNING_EVALUATION_INCOMPLETE")
            for case, row in zip(cases, result["cases"]):
                if (
                    row["case_id"] != case.case_id
                    or row["input_digest"] != digest(case.data)
                    or row["expected_digest"] != digest(case.expected)
                    or row["passed"] != (digest(row["actual"]) == digest(case.expected))
                ):
                    raise CoreError("LEARNING_EVALUATION_INVALID")
            if result["passed"] != sum(x["passed"] for x in result["cases"]) or result["all_passed"] != all(
                x["passed"] for x in result["cases"]
            ):
                raise CoreError("LEARNING_EVALUATION_INVALID")
        if stage == "CONSOLIDATE":
            results = body["results"]
            if (
                not results["EVALUATE"]["all_passed"]
                or not results["TRANSFER"]["all_passed"]
                or results["EVALUATE"]["passed"] <= results["BASELINE"]["passed"]
            ):
                return self._terminal(job, "BLOCKED", "LEARNING_NOT_TRANSFERRED_OR_NO_IMPROVEMENT")
            exp = None
            for parent in self.store.db.execute(
                "SELECT parent_id FROM record_dependencies WHERE record_id=? AND parent_kind='RECORD'", (rid,)
            ):
                row = self.store.db.execute(
                    "SELECT experience_id FROM experiences WHERE record_id=?", (parent[0],)
                ).fetchone()
                if row:
                    exp = row[0]
            # The learning test itself is an independently verified outcome. The
            # original goal failure remains distinct, not overwritten by success.
            memory = self.records.memory
            now = head["created_at_us"]
            text = canonical({"data": results["TRANSFER"]})
            from ..contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType

            # Dataset observations and the private reason for learning have
            # different provenance. Memory backlinks remain below; the original
            # G work/trial/lesson Records retain the private cause and its floor.
            dataset_sources=self.source_memory_ids or self.records.support(rid)
            project = any(
                memory.read(mid)["source_provenance"]["domain"] == "DEVELOPMENT_PROJECT"
                for mid in dataset_sources
            )
            from ..memory import PRIVACY_RANK
            observation_privacy=max((memory.read(mid)['privacy_class'] for mid in dataset_sources),key=PRIVACY_RANK.get,default=head['privacy_class'])
            eid = memory.capture(
                EvidenceInput(
                    provenance=Provenance(
                        domain="DEVELOPMENT_PROJECT" if project else "SYNTHETIC_ONLY",
                        source_namespace="recorded.project.learning-transfer"
                        if project
                        else "synthetic.learning-transfer",
                        source_reference=job["job_id"],
                        source_kind="SYSTEM_VERIFICATION",
                    ),
                    text=text,
                    privacy_class=observation_privacy,
                    observed_time_us=now,
                )
            )
            existing = self.store.db.execute(
                "SELECT memory_id FROM memories WHERE source_evidence_id=? AND lifecycle='ACTIVE' LIMIT 1", (eid,)
            ).fetchone()
            mid = (
                existing[0]
                if existing
                else memory.add(
                    MemoryCandidate(
                        entity_id=self.store.identity["identity_id"],
                        scope=head["scope"],
                        memory_type=MemoryType.PROCEDURAL,
                        epistemic_kind="OBSERVATION",
                        source_evidence_id=eid,
                        text=text,
                        derived_from=self.records.support(rid),
                        confidence=1.0,
                    )
                )
            )
            service = ExperienceService(self.store, self.authority)
            old = self.store.db.execute(
                "SELECT experience_id FROM experiences WHERE result_memory_id=?", (mid,)
            ).fetchone()
            if old:
                exp = old[0]
            else:
                check = service.verify_structured_result(mid, digest(results["TRANSFER"]), self.authority)
                from ..learning import ExperienceInput

                exp = service.record(
                    ExperienceInput(
                        context_memory_ids=self.records.support(rid)[:32],
                        scope=head["scope"],
                        task_class=spec.domain,
                        decision="Checked transfer, not a self-report",
                        result_memory_id=mid,
                        verification_memory_id=check,
                    )
                )
            old_lesson = self.store.db.execute("SELECT lesson_id FROM lessons WHERE experience_id=?", (exp,)).fetchone()
            if old_lesson:
                lesson_id = old_lesson[0]
            else:
                lesson_id = uid()
                with self.store.transaction("open.method_trial_verified", {"work_id": job["job_id"]}) as tx:
                    trial = self.records.create(
                        tx,
                        kind="LEARNING_TRIAL",
                        scope=head["scope"],
                        payload={
                            "work_id": job["job_id"],
                            "method": body["selected_method"],
                            "domain": spec.domain,
                            "results": results,
                            "origin": "INDEPENDENT_EXECUTED_TRIALS",
                        },
                        records=(rid,),
                    )
                    rule = MethodStrategyRule(scope=spec.domain, method=body["selected_method"], trial_record_id=trial)
                    lesson = self.records.create(
                        tx,
                        kind="LESSON",
                        scope=head["scope"],
                        payload={"rule": rule.model_dump(mode="json")},
                        records=(trial,),
                    )
                    tx.put(
                        "lessons",
                        {
                            "lesson_id": lesson_id,
                            "experience_id": exp,
                            "record_id": lesson,
                            "task_class": spec.domain,
                            "revision": 1,
                            "state": "CANDIDATE",
                            "tested_rule_hash": None,
                            "test_event_id": None,
                        },
                    )
            state = self.store.one("lessons", lesson_id)["state"]
            if state == "CANDIDATE":
                service.test_lesson(lesson_id)
                state = self.store.one("lessons", lesson_id)["state"]
            if state == "TESTED":
                service.activate(lesson_id, self.authority)
                state = "ACTIVE"
            if state != "ACTIVE":
                return self._terminal(job, "BLOCKED", "LESSON_REVIEW_FAILED")
            new["lesson_id"] = lesson_id
        new["stage"] = STAGES[min(next_cursor, len(STAGES) - 1)]
        with self.store.transaction("open.learning_stage_committed", {"work_id": job["job_id"], "stage": stage}) as tx:
            current = self.store.one("jobs", job["job_id"])
            if current["revision"] != job["revision"]:
                raise CoreError("STALE_LEARNING_WORK")
            newrid = self.records.create(
                tx,
                kind="OPEN_LEARNING",
                scope=head["scope"],
                payload=new,
                records=(
                    rid,
                    *((new["hypothesis_source"],) if new.get("hypothesis_source") else ()),
                    *((new["learning_strategy_record_id"],) if new.get("learning_strategy_record_id") else ()),
                ),
                supersedes=rid,
                target_id=spec.learning_key,
            )
            tx.update(
                "jobs",
                job["job_id"],
                record_id=newrid,
                cursor=next_cursor,
                state="DONE" if stage == "MONITOR" else "WAITING",
                revision=job["revision"] + 1,
                updated_at_us=self.store.clock.utc_now_us(),
            )
        return {"work_id": job["job_id"], "stage": stage, "next_stage": new["stage"], "lesson_id": new.get("lesson_id")}

    def _terminal(self, job, state, reason):
        with self.store.transaction("open.learning_parked", {"work_id": job["job_id"], "reason": reason}) as tx:
            tx.update("jobs", job["job_id"], state=state, revision=job["revision"] + 1)
        return {"work_id": job["job_id"], "reason": reason}

    def resume(self, work_id, *, expected_revision, cause_memory_id, authority):
        if authority is not self.authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")
        job = self.store.one("jobs", work_id)
        if (
            not job
            or job["work_kind"] != "LEARNING"
            or job["state"] != "UNKNOWN"
            or job["revision"] != expected_revision
        ):
            raise CoreError("STALE_LEARNING_WORK")
        parent = self.records.read(job["record_id"])
        cause = self.records.memory.read(cause_memory_id)
        if (
            parent["scope"] not in self.scopes
            or not self.records.current_support(job["record_id"])
            or cause["scope"] != parent["scope"]
            or cause["authority"] != "DIRECT"
        ):
            raise CoreError("LEARNING_RECOVERY_SOURCE_REQUIRED")
        with self.store.transaction(
            "open.learning_reconsidered", {"work_id": work_id, "cause_memory_id": cause_memory_id}
        ) as tx:
            tx.update("jobs", work_id, state="WAITING", revision=job["revision"] + 1)

    def strategy(self, domain, scope):
        if scope not in self.scopes:
            raise CoreError("LEARNING_SCOPE_DENIED")
        for row in self.store.db.execute(
            "SELECT * FROM lessons WHERE task_class=? AND state='ACTIVE' ORDER BY rowid DESC LIMIT 16", (domain,)
        ):
            head = self.store.one("continuity_records", row["record_id"])
            if (
                head["scope"] != scope
                or head["privacy_class"] not in self.privacy
                or head["lifecycle"] != "ACTIVE"
                or not self.records.current_support(head["record_id"])
            ):
                continue
            rule = ExperienceService(self.store, self.authority)._rule(row)
            if isinstance(rule, MethodStrategyRule):
                return row["record_id"], rule.method
        return None

    def monitor(self, lesson_id, cases, *, authority):
        if authority is not self.authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")
        service = ExperienceService(self.store, self.authority)
        row = self.store.one("lessons", lesson_id)
        if not row or row["state"] != "ACTIVE":
            raise CoreError("ACTIVE_LESSON_REQUIRED")
        rule = service._rule(row)
        result = self.evaluator.evaluate(rule.method, cases)
        if not result["all_passed"]:
            service.suspend(lesson_id, self.authority)
        with self.store.transaction(
            "open.learning_monitored", {"lesson_id": lesson_id, "passed": result["all_passed"]}
        ):
            pass
        return result
