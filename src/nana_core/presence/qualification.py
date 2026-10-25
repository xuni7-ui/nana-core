"""Offline scenario matrix and runtime system qualification. No production input.

Only scenario inputs and expectations live here. Runtime/C never see case IDs.
"""

import argparse
import json
from pathlib import Path
from ..actions import OperatorAuthority
from ..storage import canonical
from ..continuity import ContinuityStore, IdentityService
from ..continuity.memory import MemoryService
from ..continuity.subject import SubjectInput, PreferenceSignal
from ..continuity.subject.contracts import StandingDelegation
from ..continuity.subject.opportunities import ConcernCue
from ..continuity.learning import ExperienceService, ExperienceInput, InteractionOutcome
from ..continuity.subject.reflection import ReflectionService
from ..continuity.projects import ProjectService, ProjectContent
from . import NanaRuntime, RuntimeConfig
from .authority import VirtualClock
from .contracts import RuntimeEvent, Cause, HOUR, DAY
from .fixtures import memory, concern, advance, familiar_relationship
from .adapters import FilePerceptionPort, ScreenPerceptionPort, PresencePerceptionPort, PlatformEventPort


CONFIG = RuntimeConfig(
    scopes=("synthetic-life",), entity_id="synthetic-person", lease_us=3 * HOUR, heartbeat_us=HOUR, idle_recall_us=HOUR
)


def fresh(path, config=CONFIG, clock=None):
    clock = clock or VirtualClock()
    with ContinuityStore(path, clock, schema_target=8) as store:
        IdentityService(store, OperatorAuthority())
        MemoryService(store).entity(config.entity_id, "PERSON")
    return NanaRuntime(path, config, clock=clock), clock


def event(rt, key, **updates):
    now = rt.clock.utc_now_us()
    data = dict(
        source_key="synthetic.qualification." + key,
        kind="INTERACTION",
        origin="USER",
        entity_id=rt.config.entity_id,
        scope=rt.config.scopes[0],
        observed_at_us=now,
        occurred_at_us=now,
        text="A fictional input",
        significance="RELEVANT",
    )
    data.update(updates)
    inp = SubjectInput(**data)
    return RuntimeEvent(
        event_type="SELF_EVENT" if inp.kind == "WAKE" else "USER_EVENT",
        trigger="SELF_TRIGGER" if inp.kind == "WAKE" else "INCOMING_EVENT",
        input=inp,
        causes=tuple(Cause(kind="MEMORY", reference_id=x) for x in inp.source_memory_ids)
        or (Cause(kind="CANONICAL_SELF", reference_id=rt.store.identity["identity_id"]),),
        due_at_us=now,
    )


def cycles(outputs):
    return [x["cycle"] for x in outputs if x["cycle"]]


def summarize(cycle):
    return {
        "judgment": cycle.judgment.stance,
        "behavior": cycle.intention.behavior,
        "kind": cycle.intention.kind,
        "intention_id": cycle.intention_id,
        "goal_candidate_id": cycle.goal_candidate_id,
        "barrier": cycle.barrier,
        "motives": [m.source for m in cycle.motivations],
        "source_ids": cycle.judgment.source_ids,
        "social": cycle.social_proposal.model_dump(mode="json") if cycle.social_proposal else None,
    }


def zero_actions(rt):
    return not any(rt.store.all(t) for t in ("actions", "attempts", "grants", "budgets"))


def matrix(path):
    results = {}
    # S1 is one source configuration, never a Runtime policy branch.
    rt, clock = fresh(path / "s1" / "self.db")
    with rt:
        familiar_relationship(rt)
        hint = memory(
            rt,
            "past-hint",
            "In a fictional relaxed chat, an ordinary resource was described as interesting but not for Nana to see",
        )
        resource = "synthetic://ordinary/opaque-resource"
        concern(
            rt,
            "open-question",
            ConcernCue(
                cue_kind="OPEN_LOOP",
                motivation_source="CURIOSITY",
                topic_key="unexpected_topic",
                resource_ref=resource,
                resource_class="ORDINARY",
            ),
            derived_from=(hint,),
        )
        initial = cycles(advance(rt, clock, 2 * HOUR))
        inspect = next(c for c in initial if c.action_proposal)
        delegation = StandingDelegation(
            delegation_id="synthetic-exact-read",
            subject=rt.store.identity["identity_id"],
            capability="synthetic.resource.read",
            resource_scope=(resource,),
            operations=("READ",),
            risk_ceiling="READ_ONLY",
            privacy_scope=("PERSONAL",),
            issued_at_us=clock.utc_now_us(),
            expires_at_us=clock.utc_now_us() + HOUR,
            provenance="separate-explicit-synthetic-snapshot",
        )
        port = FilePerceptionPort(
            rt.store.identity["identity_id"],
            CONFIG.entity_id,
            CONFIG.scopes[0],
            {resource: ("ORDINARY", "A fictional unexpected finding")},
        )
        rt.submit(
            port.simulate_read(
                inspect.action_proposal,
                delegation,
                clock,
                intention_id=inspect.intention_id,
                novelty="HIGH",
                observed_availability="AVAILABLE",
            )
        )
        social = next(c for c in cycles(rt.drain()) if c.social_proposal)
        reaction = memory(
            rt,
            "positive-reaction",
            InteractionOutcome(
                proposal_intention_id=social.intention_id, reaction="POSITIVE_PLAYFUL"
            ).model_dump_json(),
        )
        learning = ExperienceService(rt.store, rt.authority)
        proof = learning.verify_interaction_result(reaction, rt.authority)
        exp = learning.record(
            ExperienceInput(
                context_memory_ids=(hint,),
                scope=CONFIG.scopes[0],
                task_class="interaction.shared_discovery",
                decision=social.intention.purpose,
                result_memory_id=reaction,
                verification_memory_id=proof,
            )
        )
        rt.refresh_attention()
        reflect = cycles(advance(rt, clock, 2 * HOUR))
        row = rt.store.db.execute("SELECT * FROM subject_reflections WHERE experience_id=?", (exp,)).fetchone()
        lesson = ReflectionService(rt.store, rt.authority).apply(
            row["reflection_id"], expected_revision=row["revision"], authority=rt.authority
        )

        def future(key):
            concern(
                rt,
                key,
                ConcernCue(
                    cue_kind="DISCOVERY", motivation_source="RELATIONSHIP", topic_key=key, availability="AVAILABLE"
                ),
            )
            return next(c for c in cycles(advance(rt, clock, 2 * HOUR)) if c.social_proposal)

        learned = future("new-finding")
        learning.suspend(lesson, rt.authority)
        control = future("control-finding")
        results["S1"] = {
            "first": summarize(inspect),
            "discovery": summarize(social),
            "learned": summarize(learned),
            "without_lesson": summarize(control),
            "reflection": any(c.judgment.stance == "REFLECT" for c in reflect),
            "causal_lesson_difference": learned.social_proposal.act != control.social_proposal.act,
            "real_file_reads": 0,
            "real_messages": 0,
            "zero_actions": zero_actions(rt),
        }
    rt, clock = fresh(path / "s2" / "self.db")
    with rt:
        mid = memory(rt, "project-history", "A fictional parser project has an unresolved implementation blocker")
        ProjectService(rt.store, rt.authority).save(
            project_id="synthetic-parser",
            entity_id=CONFIG.entity_id,
            scope=CONFIG.scopes[0],
            content=ProjectContent(
                goal="Finish a fictional parser", current_state="Awaiting research", blockers=("Unknown data shape",)
            ),
            source_memory_ids=(mid,),
            expected_revision=0,
            authority=rt.authority,
        )
        rt.refresh_attention()
        out = cycles(advance(rt, clock, 2 * HOUR))
        results["S2"] = summarize(next(c for c in out if c.intention.behavior == "CONTINUE_PROJECT"))
    rt, clock = fresh(path / "s3" / "self.db")
    with rt:
        evidence = [
            memory(
                rt,
                "gap-" + str(i),
                canonical({"capability": "synthetic.parse", "available": False}),
                source_kind="SYSTEM_VERIFICATION",
            )
            for i in range(2)
        ]
        concern(
            rt,
            "capability-gap",
            ConcernCue(
                cue_kind="OPEN_LOOP",
                motivation_source="CAPABILITY_GAP",
                topic_key="parse_gap",
            ),
            derived_from=tuple(evidence),
        )
        results["S3"] = summarize(next(c for c in cycles(advance(rt, clock, 2 * HOUR)) if c.goal_candidate_id))
        results["S3"]["zero_grants"] = not rt.store.all("grants")
    rt, clock = fresh(path / "s4" / "self.db")
    with rt:
        roots = []
        for i in range(2):
            e = event(
                rt,
                "creative-" + str(i),
                kind="OUTCOME",
                origin="ENVIRONMENT",
                text="A fictional design attempt produced a useful new idea",
                preference_signal=PreferenceSignal(
                    topic="creative_design", direction="SUPPORT", interpretation="Direct creative outcome"
                ),
            )
            e = e.model_copy(update={"event_type": "WORLD_EVENT"})
            rt.submit(e)
            c = cycles(rt.drain())[-1]
            roots.append(rt.store.one("subject_events", c.event_id)["memory_id"])
        concern(
            rt,
            "design-interest",
            ConcernCue(
                cue_kind="OPEN_LOOP",
                motivation_source="CREATIVE_INTEREST",
                topic_key="design_concept",
                required_preference_id=rt.subject.growth.assertions(CONFIG.scopes[0])[0]["assertion_id"],
            ),
            derived_from=tuple(roots),
        )
        results["S4"] = summarize(
            next(c for c in cycles(advance(rt, clock, 2 * HOUR)) if c.intention.behavior == "CREATE")
        )
        results["S4"]["preference_adopted"] = any(
            a["state"] == "ADOPTED" for a in rt.subject.growth.assertions(CONFIG.scopes[0])
        )
    rt, clock = fresh(path / "s5" / "self.db")
    with rt:
        familiar_relationship(rt)
        concern(
            rt,
            "busy-recall",
            ConcernCue(
                cue_kind="DISCOVERY", motivation_source="RELATIONSHIP", topic_key="shared_topic", availability="BUSY"
            ),
        )
        results["S5"] = summarize(cycles(advance(rt, clock, 2 * HOUR))[-1])
    rt, clock = fresh(path / "s6" / "self.db")
    with rt:
        concern(
            rt,
            "norm",
            ConcernCue(
                cue_kind="CONSTRAINT",
                motivation_source="NORM",
                topic_key="bounded_topic",
                prohibited_behaviors=("EXPLORE",),
            ),
        )
        concern(
            rt,
            "possible-opportunity",
            ConcernCue(
                cue_kind="OPPORTUNITY",
                motivation_source="OPPORTUNITY",
                topic_key="bounded_topic",
                resource_ref="synthetic://ordinary/possible",
                resource_class="ORDINARY",
            ),
        )
        results["S6"] = summarize(cycles(advance(rt, clock, 2 * HOUR))[-1])
    rt, clock = fresh(path / "s7" / "self.db")
    with rt:
        for i in range(6):
            concern(
                rt,
                "open-" + str(i),
                ConcernCue(
                    cue_kind="OPEN_LOOP",
                    motivation_source="LONG_TERM_GOAL",
                    topic_key="open_" + str(i),
                ),
            )
        advance(rt, clock, 2 * HOUR)
        if not (len(rt.subject.pending(CONFIG.scopes[0])) == 6):
            raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
        concern(
            rt,
            "optional-maintenance",
            ConcernCue(
                cue_kind="OPPORTUNITY",
                motivation_source="MAINTENANCE",
                topic_key="optional_work",
            ),
        )
        results["S7"] = summarize(cycles(advance(rt, clock, 2 * HOUR))[-1])
        results["S7"]["presence"] = rt.living()[0].presence
    rt, clock = fresh(path / "s8" / "self.db")
    with rt:
        context = memory(rt, "failed-task-context", "Prepare a fictional reading card")
        learning = ExperienceService(rt.store, rt.authority)
        exp_ids = []
        for i in range(2):
            result = memory(rt, "bad-result-" + str(i), canonical({"text": "A fictional draft", "success": True}))
            proof = learning.verify_reading_result(result, rt.authority)
            exp_ids.append(
                learning.record(
                    ExperienceInput(
                        context_memory_ids=(context,),
                        scope=CONFIG.scopes[0],
                        task_class="reading_card",
                        decision="Drafted without locating original source",
                        result_memory_id=result,
                        verification_memory_id=proof,
                    )
                )
            )
        rt.refresh_attention()
        out = cycles(advance(rt, clock, 2 * HOUR))
        reflection = rt.store.db.execute(
            "SELECT * FROM subject_reflections WHERE experience_id=?", (exp_ids[0],)
        ).fetchone()
        lesson = ReflectionService(rt.store, rt.authority).apply(
            reflection["reflection_id"], expected_revision=1, authority=rt.authority
        )
        rt.submit(event(rt, "future-reading", task_class="reading_card"))
        changed = cycles(rt.drain())[-1]
        results["S8"] = {
            "reflected": any(c.judgment.stance == "REFLECT" for c in out),
            "independently_verified_failures": len(exp_ids),
            "future_method": changed.judgment.selected_method,
            "lesson_id": lesson,
            "identity_unchanged": rt.store.identity["revision"] == 1,
        }
    rt, clock = fresh(path / "s9" / "self.db")
    with rt:
        constraint = memory(
            rt, "method-constraint", canonical({"allowed_methods": ["verify_first"]}), source_kind="USER_STATEMENT"
        )
        rt.submit(
            event(
                rt, "inefficient-user-proposal", proposed_method="skip_validation", constraint_memory_ids=(constraint,)
            )
        )
        results["S9"] = summarize(cycles(rt.drain())[-1])
    rt, clock = fresh(path / "s10" / "self.db")
    with rt:
        ports = [ScreenPerceptionPort, FilePerceptionPort, PresencePerceptionPort, PlatformEventPort]
        for i, port in enumerate(ports):
            adapter = port(rt.store.identity["identity_id"], CONFIG.entity_id, CONFIG.scopes[0])
            rt.submit(
                adapter.observe(
                    clock, "change-" + str(i), "A synthetic environment delta", novelty="HIGH" if i == 0 else "LOW"
                )
            )
        out = cycles(rt.drain())
        results["S10"] = {
            "judgments": [c.judgment.stance for c in out],
            "source_types": list({r["event_type"] for r in rt.store.all("runtime_queue")}),
            "memory_count": len(rt.store.all("memories")),
            "zero_actions": zero_actions(rt),
            "real_sensors": 0,
        }
    return results


def no_input(path, hours=72):
    rt, clock = fresh(path)
    with rt:
        prior = memory(rt, "old-interest", "A fictional unanswered question is worth revisiting")
        concern(
            rt,
            "quiet-question",
            ConcernCue(
                cue_kind="OPEN_LOOP",
                motivation_source="UNRESOLVED_QUESTION",
                topic_key="unanswered",
            ),
            derived_from=(prior,),
        )
        before = rt.living()[0].model_dump(mode="json")
        identity = rt.store.identity.copy()
        user_before = rt.store.db.execute(
            "SELECT count(*) FROM runtime_queue WHERE event_type='USER_EVENT'"
        ).fetchone()[0]
        states = []
        out = []
        for _ in range(hours):
            out.extend(advance(rt, clock, HOUR))
            states.append(rt.health().model_dump(mode="json"))
        user_after = rt.store.db.execute("SELECT count(*) FROM runtime_queue WHERE event_type='USER_EVENT'").fetchone()[
            0
        ]
        cs = cycles(out)
        return {
            "virtual_hours": hours,
            "identity_stable": rt.store.identity == identity,
            "new_user_events": user_after - user_before,
            "self_intentions": sum(c.intention.self_generated and c.intention_id is not None for c in cs),
            "self_goal_candidates": sum(c.intention.self_generated and c.goal_candidate_id is not None for c in cs),
            "silence_hours": sum(h["last_cognition_us"] is None for h in states),
            "self_state_time_changed": rt.living()[0].as_of_us > before["as_of_us"],
            "health_samples": states,
            "calls": len(rt.store.all("runtime_cognition_calls")),
            "queue_depth": rt.queue.depth(),
            "distinct_internal_sources": len(rt.store.all("runtime_schedules")),
            "social_proposals": sum(c.social_proposal is not None for c in cs),
            "zero_actions": zero_actions(rt),
            "cause_backlinks": all(bool(r["cause_json"]) for r in rt.store.all("runtime_queue")),
        }


def mixed(path, days=30):
    rt, clock = fresh(path, CONFIG.model_copy(update={"model": "analytical", "cognition_cooldown_us": 0}))
    initial_id = rt.store.identity["identity_id"]
    samples = []
    model_changes = {4: "unavailable", 7: "cautious", 11: "timeout", 12: "analytical"}
    try:
        familiar_relationship(rt)
        history = memory(rt, "mixed-project-history", "A fictional long project has an unresolved design blocker")
        ProjectService(rt.store, rt.authority).save(
            project_id="mixed-project",
            entity_id=CONFIG.entity_id,
            scope=CONFIG.scopes[0],
            content=ProjectContent(
                goal="Complete a fictional design",
                current_state="Research needed",
                blockers=("Unresolved design question",),
            ),
            source_memory_ids=(history,),
            expected_revision=0,
            authority=rt.authority,
        )
        concern(
            rt,
            "mixed-interest",
            ConcernCue(cue_kind="OPEN_LOOP", motivation_source="UNRESOLVED_QUESTION", topic_key="long_project"),
            derived_from=(history,),
        )
        for day in range(days):
            if day in model_changes:
                rt.cognition.set_model(model_changes[day])
            if day in (1, 5, 8, 11, 13):
                e = event(rt, "uncertain-" + str(day), significance="HIGH", uncertainty="HIGH")
                rt.submit(e)
                rt.drain()
            if day == 15:
                bad = memory(rt, "mixed-failed-result", canonical({"text": "A fictional draft", "success": True}))
                learning = ExperienceService(rt.store, rt.authority)
                proof = learning.verify_reading_result(bad, rt.authority)
                learning.record(
                    ExperienceInput(
                        context_memory_ids=(history,),
                        scope=CONFIG.scopes[0],
                        task_class="reading_card",
                        decision="Source was not located",
                        result_memory_id=bad,
                        verification_memory_id=proof,
                    )
                )
                rt.refresh_attention()
            advance(rt, clock, DAY)
            if day in (9, 19):
                identity = rt.store.identity.copy()
                pending = [r["intention_id"] for r in rt.subject.pending(CONFIG.scopes[0])]
                cfg = rt.config
                rt.stop()
                rt = NanaRuntime(path, cfg, clock=clock)
                if not (
                    rt.store.identity == identity
                    and [r["intention_id"] for r in rt.subject.pending(CONFIG.scopes[0])] == pending
                ):
                    raise AssertionError("QUALIFICATION_INVARIANT_FAILED")
            samples.append(
                {
                    "day": day + 1,
                    "epoch": rt.lease.epoch,
                    "identity_id": rt.store.identity["identity_id"],
                    "pending": len(rt.subject.pending(CONFIG.scopes[0])),
                    "queue_depth": rt.queue.depth(),
                    "model": rt.cognition.availability,
                    "calls": len(rt.store.all("runtime_cognition_calls")),
                }
            )
        return {
            "virtual_days": days,
            "samples": samples,
            "identity_stable": all(x["identity_id"] == initial_id for x in samples),
            "max_pending": max(x["pending"] for x in samples),
            "max_queue_depth": max(x["queue_depth"] for x in samples),
            "call_states": [r["state"] for r in rt.store.all("runtime_cognition_calls")],
            "reflection_count": len(rt.store.all("subject_reflections")),
            "project_count": len(rt.store.all("projects")),
            "calls": len(rt.store.all("runtime_cognition_calls")),
            "zero_actions": zero_actions(rt),
        }
    finally:
        rt.stop()


def run(output, *, with_process=False):
    output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    scenarios = matrix(output / "matrix")
    quiet = no_input(output / "no-input" / "self.db")
    life = mixed(output / "mixed" / "self.db")
    behaviors = {v.get("behavior") for v in scenarios.values() if "behavior" in v}
    behaviors.update((scenarios["S1"]["first"]["behavior"], scenarios["S1"]["discovery"]["behavior"]))
    behaviors.discard(None)
    checks = {
        "ONE_SUBJECT_LOOP_MANY_BEHAVIORS": len(behaviors) >= 8,
        "S1_CAUSAL_SOCIAL_LEARNING": scenarios["S1"]["causal_lesson_difference"],
        "S2_PROJECT": scenarios["S2"]["behavior"] == "CONTINUE_PROJECT",
        "S3_CAPABILITY_GAP": scenarios["S3"]["behavior"] == "SEEK_CAPABILITY" and scenarios["S3"]["zero_grants"],
        "S4_CREATIVE": scenarios["S4"]["behavior"] == "CREATE" and scenarios["S4"]["preference_adopted"],
        "S5_SOCIAL_SILENCE": scenarios["S5"]["behavior"] == "STAY_SILENT",
        "S6_NORM_INHIBITION": scenarios["S6"]["kind"] == "NO_ACTION",
        "S7_REST": scenarios["S7"]["behavior"] == "REST" and scenarios["S7"]["presence"] == "RESTING",
        "S8_SELF_DEVELOPMENT": scenarios["S8"]["reflected"] and scenarios["S8"]["future_method"] == "locate_then_draft",
        "S9_INDEPENDENT_OPINION": scenarios["S9"]["judgment"] in {"ALTERNATIVE", "DISAGREE"},
        "S10_WORLD": scenarios["S10"]["memory_count"] >= 4,
        "NO_USER_INPUT_RUNTIME_CONTINUES": quiet["new_user_events"] == 0
        and quiet["identity_stable"]
        and len(quiet["health_samples"]) == 72,
        "TIME_CAN_TRIGGER_SELF_UPDATE": quiet["self_state_time_changed"],
        "SELF_WAKE_WITH_CAUSAL_SOURCE": quiet["cause_backlinks"],
        "SPONTANEOUS_INTENTION_WITH_CAUSE": quiet["self_intentions"] > 0,
        "SPONTANEOUS_GOAL_CANDIDATE_WITH_CAUSE": quiet["self_goal_candidates"] > 0,
        "SILENCE_IS_VALID": quiet["silence_hours"] >= 60,
        "NO_SOCIAL_SPAM": quiet["social_proposals"] == 0,
        "NO_RANDOM_PERSONALITY_MUTATION": quiet["identity_stable"] and life["identity_stable"],
        "COGNITION_CALLS_BOUNDED": quiet["calls"] == 0 and life["calls"] <= CONFIG.max_calls_per_day * 30,
        "EVENT_QUEUE_BOUNDED": quiet["queue_depth"] <= CONFIG.queue_capacity
        and life["max_queue_depth"] <= CONFIG.queue_capacity,
        "MODEL_UNAVAILABLE_SELF_PERSISTS": life["identity_stable"] and "TIMED_OUT" in life["call_states"],
        "MODEL_SWAP_SELF_PERSISTS": life["identity_stable"],
        "REAL_EXTERNAL_ACTIONS_ZERO": quiet["zero_actions"] and life["zero_actions"],
    }
    process_report = None
    if with_process:
        from .process_qualification import wall_soak, crash_matrix

        wall = wall_soak(output / "wall-process", sample_count=100)
        crashes = crash_matrix(output / "crash-matrix")
        process_report = {"wall": wall, "crashes": crashes}
        checks.update(
            PERSISTENT_RUNTIME=wall["heartbeat_progressed"] and wall["graceful_shutdown"],
            PROCESS_RESTART_SELF_PERSISTS=all(x["identity_stable"] for x in crashes) and all(wall["checks"].values()),
            SINGLE_RUNTIME_AUTHORITY=wall["double_start_blocked"],
            NO_DOUBLE_WRITER=wall["double_start_blocked"],
            NO_DUPLICATE_INTENTION_AFTER_CRASH=all(
                x["cycles"] == x["intentions"] == x["candidates"] == 1 for x in crashes
            ),
            UNKNOWN_NOT_RETRIED=all(
                x["call_states"] == ["UNKNOWN"] for x in crashes if x["cut"] in {"after_reservation", "during_model"}
            ),
            NO_RESOURCE_CHILD_AFTER_PARENT_DEATH=next(x for x in crashes if x["cut"] == "during_model")[
                "resource_child_reaped"
            ],
        )
    checks["SUBJECT_LOOP_REMAINS_SINGLE"] = all(
        bool(v.get("source_ids")) for v in scenarios.values() if "source_ids" in v
    )
    report = {
        "origin": "SYNTHETIC_OFFLINE",
        "checks": checks,
        "scenario_matrix": scenarios,
        "distinct_behaviors": sorted(behaviors),
        "72h": quiet,
        "30d": life,
        "real_model_calls": 0,
        "real_external_actions": 0,
        "real_private_files_read": 0,
        "E12": "NOT_RUN",
        "real_local_process": process_report,
    }
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--with-process", action="store_true")
    args = parser.parse_args()
    report = run(args.output, with_process=args.with_process)
    print(json.dumps({"checks": report["checks"], "report": str(Path(args.output) / "results.json")}))
    if not all(report["checks"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
