"""Bounded note-retrieval practice through original MemoryService and G.

No new memory, planner, grant or runtime. The corpus is retained PROJECT/PUBLIC
user statements; a successful lookup does not verify their content as truth.
Candidate methods are finite Core primitives, checked against an independent
normalized-substring oracle. Model-visible LearningProblem keeps heldouts out.
"""

import re
import sqlite3
import time
import unicodedata

from ..contracts import CoreError
from ..storage import canonical, digest
from .memory import MemoryService, is_user_note, USER_NOTE_QUALIFICATION
from .records import RecordService
from .open_agency.learning import IndependentEvaluator, LearningService
from .open_agency.world import transform, nfkc_casefold

DOMAIN = "retrieval.notes"
EVALUATOR = "CORE_NOTE_RETRIEVAL_V1"
MAX_NOTES = 16
METHODS = ("IDENTITY", "CASEFOLD", "UNICODE_WORDS", "JOIN")
SCOPE = {"max_notes": MAX_NOTES, "query_shape": "WORDLIKE", "read_only": True}
EXPANDED_MAX_NOTES = 32
EXPANDED_EVALUATOR = "CORE_NOTE_RETRIEVAL_V2"
EXPANDED_SCOPE = {**SCOPE, "max_notes": EXPANDED_MAX_NOTES}
TEXT_EVALUATORS = {16: "CORE_NOTE_RETRIEVAL_TEXT_V1_16", 32: "CORE_NOTE_RETRIEVAL_TEXT_V1_32"}
# Preserve the exact old candidate sets/order for pending and published V1/V2.
# The frozen diverse comparison supplies a preferred candidate, never a lesson.
TEXT_METHODS = ("IDENTITY", "NFKC_CASEFOLD", *METHODS[1:])
QUALIFICATION_SCOPES = {EVALUATOR: SCOPE, EXPANDED_EVALUATOR: EXPANDED_SCOPE,
    **{profile: {"max_notes": limit, "query_shape": "TEXT_2_64", "read_only": True}
       for limit, profile in TEXT_EVALUATORS.items()}}
QUALIFICATION_METHODS = {EVALUATOR: METHODS, EXPANDED_EVALUATOR: METHODS,
    **{profile: TEXT_METHODS for profile in TEXT_EVALUATORS.values()}}
ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def snapshot_evaluator(snapshot):
    return snapshot.get('profile') or (EXPANDED_EVALUATOR if snapshot.get('max_notes', MAX_NOTES) == EXPANDED_MAX_NOTES else EVALUATOR)


def word_queries(terms):
    return (
        type(terms) in (list, tuple)
        and 1 <= len(terms) <= 8
        and all(type(t) is str and re.fullmatch(r"\w{2,64}", t) for t in terms)
    )


def query_allowed(profile, terms):
    if type(profile) is not str or profile not in QUALIFICATION_SCOPES:
        return False
    if QUALIFICATION_SCOPES[profile]['query_shape'] == 'WORDLIKE':
        return word_queries(terms)
    return (type(terms) in (list, tuple) and 1 <= len(terms) <= 8
            and all(type(term) is str and 2 <= len(term) <= 64 for term in terms))


class NoteRetrievalEvaluator:
    """App-owned real Store reads, plus original evaluator for other domains."""

    def __init__(self, store, entity_id, scopes, privacy_classes, *, fallback=None):
        self.store, self.entity_id = store, entity_id
        self.scopes = tuple(scopes)
        self.privacy = tuple(p for p in privacy_classes if p in {"PUBLIC", "PROJECT"})
        self.fallback = fallback or IndependentEvaluator()

    def snapshot(self, scope, *, timeout_ms=100, max_notes=MAX_NOTES, profile=None):
        if scope not in self.scopes or not self.privacy or type(max_notes) is not int or max_notes not in {MAX_NOTES, EXPANDED_MAX_NOTES}:
            raise CoreError("NOTE_STRATEGY_SCOPE_BOUND")
        if profile is not None and (profile not in QUALIFICATION_SCOPES
                or QUALIFICATION_SCOPES[profile]['max_notes'] != max_notes):
            raise CoreError("NOTE_STRATEGY_SCOPE_BOUND")
        memory = MemoryService(self.store)
        memory._fresh()
        db = self.store.db
        if db.in_transaction:
            raise CoreError("NOTE_RECALL_SAFE_POINT_REQUIRED")
        deadline = time.monotonic() + timeout_ms / 1000
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        try:
            where, args = memory._query_filter((self.entity_id,), (scope,), self.privacy, False, ("SEMANTIC",))
            rows = db.execute(
                "SELECT m.memory_id,m.rowid AS lookup_ordinal FROM memories m "
                "JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE "
                + where + USER_NOTE_QUALIFICATION + " ORDER BY m.rowid DESC LIMIT ?",
                (*args, max_notes + 1),
            ).fetchall()
            if len(rows) > max_notes:
                raise CoreError("NOTE_STRATEGY_SCOPE_BOUND")
            notes = []
            for header in rows:
                if time.monotonic() > deadline:
                    raise CoreError("NOTE_RECALL_TIME_BOUND")
                row = memory.read(header['memory_id'])
                if is_user_note(row):
                    notes.append({**row, "lookup_ordinal": header['lookup_ordinal']})
            notes.sort(key=lambda row: row["lookup_ordinal"])
            stamp = digest(
                [
                    (
                        r["memory_id"],
                        r["source_evidence_id"],
                        r["updated_at_us"],
                        digest(r["text"]),
                        r["privacy_class"],
                        r["lookup_ordinal"],
                    )
                    for r in notes
                ]
            )
            return {"scope": scope, "stamp": stamp, "notes": notes, "max_notes": max_notes,
                    **({'profile': profile} if profile in TEXT_EVALUATORS.values() else {})}
        except sqlite3.OperationalError as exc:
            if "interrupt" in str(exc).lower():
                raise CoreError("NOTE_RECALL_TIME_BOUND") from None
            raise
        finally:
            db.set_progress_handler(None, 0)

    @staticmethod
    def oracle(snapshot, terms):
        """Independent spec: old literal matches first, then NFKC substring."""
        literal = [
            r
            for r in reversed(snapshot["notes"])
            if any(t.translate(ASCII_LOWER) in r["text"].translate(ASCII_LOWER) for t in terms)
        ]
        if literal:
            return sorted(r["memory_id"] for r in literal[:4])
        normalized = [unicodedata.normalize("NFKC", t).casefold() for t in terms]
        matches = [
            r
            for r in reversed(snapshot["notes"])
            if any(t in unicodedata.normalize("NFKC", r["text"]).casefold() for t in normalized)
        ]
        return sorted(r["memory_id"] for r in matches[:4])

    def lookup(self, method, terms, snapshot):
        if method not in QUALIFICATION_METHODS.get(snapshot_evaluator(snapshot), ()) or not query_allowed(snapshot_evaluator(snapshot), terms):
            raise CoreError("NOTE_STRATEGY_INPUT_BOUND")
        rows = MemoryService(self.store).literal_notes(
            entity_ids=(self.entity_id,), scopes=(snapshot["scope"],), privacy_classes=self.privacy, terms=tuple(terms)
        )
        if rows or method == "IDENTITY":
            return rows
        return self._normalized_lookup(method,terms,snapshot)

    def _normalized_lookup(self, method, terms, snapshot):
        """Trusted caller already checked literal priority at this safe point.

        No cached miss, user flag or persisted result; ordinary evaluator entry
        still runs the original literal query before invoking this primitive.
        """
        if method not in QUALIFICATION_METHODS.get(snapshot_evaluator(snapshot), ()) or not query_allowed(snapshot_evaluator(snapshot), terms):
            raise CoreError("NOTE_STRATEGY_INPUT_BOUND")
        if method == "IDENTITY":return []
        folded = [t.casefold() if method == "CASEFOLD" else unicodedata.normalize("NFKC", t).casefold() for t in terms]
        result = []
        for row in reversed(snapshot["notes"]):
            if method == "CASEFOLD":
                matched = any(t in transform("CASEFOLD", row["text"]) for t in folded)
            elif method == 'NFKC_CASEFOLD':
                # Notes already have their own exact text bound; do not apply
                # world.compute's JSON-envelope byte bound to a source read.
                matched = any(t in nfkc_casefold(row['text']) for t in folded)
            else:
                words = [t.casefold() for t in transform("UNICODE_WORDS", row["text"])]
                matched = (
                    any(t in words for t in folded)
                    if method == "UNICODE_WORDS"
                    else any(t in transform("JOIN", words) for t in folded)
                )
            if matched:
                result.append(row)
            if len(result) == 4:
                break
        return result

    def practice_evaluate(self, method, cases):
        return self.evaluate(method, cases)

    def evaluate(self, method, cases):
        note_cases = [type(c.data) is dict and type(c.data.get("kind")) is str
                      and c.data["kind"] in QUALIFICATION_SCOPES for c in cases]
        if not any(note_cases):
            return self.fallback.evaluate(method, cases)
        if not all(note_cases) or len({c.data['kind'] for c in cases}) != 1:
            raise CoreError("NOTE_STRATEGY_MIXED_EVALUATION")
        evaluator = cases[0].data['kind']
        qualification = QUALIFICATION_SCOPES[evaluator]
        results = []
        for case in cases:
            data = case.data
            if set(data) != {"kind", "scope", "source_stamp", "terms"} or not query_allowed(evaluator, data["terms"]):
                raise CoreError("NOTE_STRATEGY_INPUT_BOUND")
            snapshot = self.snapshot(data["scope"], max_notes=qualification['max_notes'], profile=evaluator)
            if snapshot["stamp"] != data["source_stamp"]:
                raise CoreError("NOTE_STRATEGY_SOURCE_CHANGED")
            if case.expected != self.oracle(snapshot, data["terms"]):
                raise CoreError("NOTE_STRATEGY_ORACLE_MISMATCH")
            actual = sorted(r["memory_id"] for r in self.lookup(method, data["terms"], snapshot))
            results.append(
                {
                    "case_id": case.case_id,
                    "context": case.context,
                    "input_digest": digest(data),
                    "actual": actual,
                    "expected_digest": digest(case.expected),
                    "passed": actual == case.expected,
                }
            )
        return {
            "checked": len(results),
            "passed": sum(r["passed"] for r in results),
            "cases": results,
            "all_passed": all(r["passed"] for r in results),
            "evaluator": evaluator,
            "entity_id": self.entity_id,
            "qualification_scope": qualification,
        }


def qualified_method(store, authority, entity_id, scope, privacy_classes):
    """Read original G only; a provider/user statement cannot mint a lesson."""
    if store.schema_target < 13:
        return None
    reader = LearningService(store, authority, (), scopes=(scope,), privacy_classes=privacy_classes)
    selected = reader.strategy(DOMAIN, scope)
    if not selected:
        return None
    lesson_record, method = selected
    if not any(method in methods for methods in QUALIFICATION_METHODS.values()):
        return None
    records = RecordService(store)
    rule = records.read(lesson_record)["payload"]["rule"]
    trial = records.read(rule["trial_record_id"])
    if trial["record_kind"] != "LEARNING_TRIAL" or trial["payload"].get("domain") != DOMAIN:
        return None
    profiles = []
    for stage in ("EVALUATE", "TRANSFER"):
        result = trial["payload"]["results"].get(stage, {})
        profile = result.get('evaluator')
        if (
            type(profile) is not str or profile not in QUALIFICATION_SCOPES
            or result.get("entity_id") != entity_id
            or result.get("qualification_scope") != QUALIFICATION_SCOPES.get(profile)
            or result.get("all_passed") is not True
            or method not in QUALIFICATION_METHODS.get(profile, ())
        ):
            return None
        profiles.append(profile)
    if len(set(profiles)) != 1:
        return None
    return lesson_record, method


def qualified_query_profile(store, selected):
    """Read the independently checked query shape, not a host/model preference."""
    records = RecordService(store)
    rule = records.read(selected[0])['payload']['rule']
    trial = records.read(rule['trial_record_id'])['payload']
    profile = trial['results']['EVALUATE']['evaluator']
    if profile not in QUALIFICATION_SCOPES:
        raise CoreError('NOTE_STRATEGY_SCOPE_BOUND')
    return profile


def qualified_note_limit(store, selected):
    """Old lessons inherit neither a wider corpus nor broader query shapes."""
    return QUALIFICATION_SCOPES[qualified_query_profile(store, selected)]['max_notes']


def case_for(snapshot, terms, label):
    from .open_agency.learning import LearningCase

    return LearningCase(
        case_id=label,
        context="retained-notes-" + label,
        data={"kind": snapshot_evaluator(snapshot), "scope": snapshot["scope"], "source_stamp": snapshot["stamp"], "terms": list(terms)},
        expected=NoteRetrievalEvaluator.oracle(snapshot, terms),
    )


def probes(snapshot, *, partial=False):
    """Source-derived probes, never a model/user assertion of the expected answer."""
    seen = set()
    for row in snapshot["notes"]:
        text = unicodedata.normalize("NFKC", row["text"])
        for word in re.findall(r"[^\W_]{2,64}", text):
            terms = (word[:-1] if partial and len(word) >= 5 else word,)
            if terms in seen:
                continue
            seen.add(terms)
            if len(seen) > 64:
                return
            if word_queries(terms):
                yield row["memory_id"], terms


def text_probes(snapshot):
    """Retained-source shape gaps only, never transient ordinary chat content."""
    for row in snapshot['notes']:
        normalized = unicodedata.normalize('NFKC', row['text']).casefold()
        spans = list(re.finditer(r'\S+', normalized))
        candidates = []
        for left, right in zip(spans, spans[1:]):
            separator = normalized[left.end():right.start()]
            if len(separator) > 1:
                candidates.append(normalized[left.start():right.end()])
        for span in spans:
            term = span.group().rstrip('.,;:!?')
            if re.search(r'\w[+/:.-]|[+/]\w', term) and not word_queries((term,)):
                candidates.append(term)
        seen = set()
        for term in candidates:
            if query_allowed(TEXT_EVALUATORS[snapshot['max_notes']], (term,)) and term not in seen:
                seen.add(term)
                yield row['memory_id'], (term,)


def study_cases(snapshot, terms, label):
    positive = case_for(snapshot, terms, label)
    result = [positive]
    if snapshot_evaluator(snapshot) in TEXT_EVALUATORS.values():
        collapsed = tuple(re.sub(r'\s+', ' ', term) for term in terms)
        if collapsed != terms and not NoteRetrievalEvaluator.oracle(snapshot, collapsed):
            result.append(case_for(snapshot, collapsed, label+'-spacing-near-miss'))
    return tuple(result)


class NoteRetrievalGrowth:
    """A due-maintenance adapter to existing C/G, not an autonomous scheduler.

    Inspects only a small explicitly retained corpus. No external call, generated
    code, new grant or user-query retention. C may rest or decline. Study state,
    independent trials, lessons and source invalidation stay in original G.
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.max_notes = runtime.config.living.note_retrieval_notes_limit if runtime.config.living else MAX_NOTES
        self.evaluator = NoteRetrievalEvaluator(
            runtime.store, runtime.config.entity_id, runtime.config.scopes, runtime.config.privacy_classes
        )
        self.restore()

    def service(self):
        work = self.runtime.work
        if work.open_learning is None:
            work.configure_open_learning(())
        learning = work.open_learning
        if learning.evaluator is not self.evaluator:
            self.evaluator.fallback = learning.evaluator
            learning.evaluator = self.evaluator
        return learning

    def restore(self):
        """Recover trusted pending specs only after rechecking current sources."""
        r = self.runtime
        self.restored_specs = {}
        # RUNTIME_WORK preserves the frozen proposed spec before queued C runs;
        # OPEN_LEARNING remains original G's authoritative job/trial state.
        rows = r.store.db.execute(
            "SELECT * FROM continuity_records WHERE record_kind='RUNTIME_WORK' "
            "AND lifecycle='ACTIVE' AND target_id LIKE 'learn.note-retrieval.%' ORDER BY rowid DESC LIMIT 16"
        ).fetchall()
        from .open_agency.learning import LearningSpec

        for row in rows:
            if row['scope'] not in r.config.scopes or row['privacy_class'] not in r.config.privacy_classes:
                continue
            if not RecordService(r.store).current_support(row["record_id"]):
                continue
            body = RecordService(r.store).read(row["record_id"])["payload"]
            if type(body.get("kind")) is not str or body["kind"] not in QUALIFICATION_SCOPES or body.get("entity_id") != r.config.entity_id:
                continue
            spec = LearningSpec.model_validate_json(canonical(body["spec"]))
            if (
                spec.domain != DOMAIN
                or spec.hypothesis_policy != "PRACTICE_COMPARE"
                or spec.hypotheses != QUALIFICATION_METHODS[body['kind']][1:]
                or any(type(case.data) is not dict or case.data.get('kind') != body['kind'] for case in (*spec.practice, *spec.evaluation, *spec.transfer))
                or spec.baseline_method != "IDENTITY"
                or spec.estimated_cost_micro != 0
            ):
                continue
            try:
                for case in (*spec.practice, *spec.evaluation, *spec.transfer):
                    self.evaluator.evaluate("IDENTITY", (case,))
            except CoreError:
                continue
            service = self.service()
            if len(service.specs) < 16:
                service.specs[spec.learning_key] = spec
                self.restored_specs[spec.learning_key] = row['record_id']

    def resume_selected(self, scope):
        """Reconnect retained C choices to original G after a missing-spec host.

        This neither asks C again nor resurrects a dropped/expired intention.
        G retains its occurrence-key, concurrency and source admission checks.
        """
        from .subject.contracts import SubjectInput
        from .subject.state import visible

        r = self.runtime
        if not self.restored_specs:
            return
        records = RecordService(r.store)
        for intention in r.subject.pending(scope):
            cycle_row = r.store.db.execute(
                'SELECT * FROM subject_cycles WHERE subject_event_id=? ORDER BY revision DESC LIMIT 1',
                (intention['subject_event_id'],),
            ).fetchone()
            if not cycle_row or not visible(r.store, cycle_row['record_id'], scope, r.config.privacy_classes):
                continue
            cycle = r.subject.result(cycle_row)
            checkpoint = self.restored_specs.get(cycle.proposed_program_id)
            if (not checkpoint or cycle.intention_id != intention['intention_id']
                    or cycle.intention.behavior != 'LEARN'
                    or not visible(r.store, checkpoint, scope, r.config.privacy_classes)):
                continue
            source = r.store.one('subject_events', intention['subject_event_id'])
            if not source or not visible(r.store, source['record_id'], scope, r.config.privacy_classes):
                continue
            event = SubjectInput.model_validate_json(canonical(records.read(source['record_id'])['payload']['input']))
            if event.entity_id != r.config.entity_id or event.privacy_class not in r.config.privacy_classes:
                continue
            self.service().after_cycle(r, cycle, event)

    def capture(self, key, text, scope, parents, *, predicate=None):
        from .contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType

        memory = MemoryService(self.runtime.store)
        previous = self.runtime.store.db.execute(
            "SELECT observed_time_us FROM continuity_evidence WHERE source_namespace=? AND source_reference=?",
            ("recorded.project.note-retrieval", key),
        ).fetchone()
        now = previous[0] if previous else self.runtime.clock.utc_now_us()
        eid = memory.capture(
            EvidenceInput(
                provenance=Provenance(
                    domain="DEVELOPMENT_PROJECT",
                    source_namespace="recorded.project.note-retrieval",
                    source_reference=key,
                    source_kind="SYSTEM_VERIFICATION",
                ),
                text=text,
                privacy_class="PROJECT",
                observed_time_us=now,
            )
        )
        return memory.add(
            MemoryCandidate(
                entity_id=self.runtime.config.entity_id,
                scope=scope,
                memory_type=MemoryType.EPISODIC,
                epistemic_kind="OBSERVATION",
                source_evidence_id=eid,
                text=text,
                predicate_key=predicate,
                derived_from=tuple(parents),
            )
        )

    def experience(self, snapshot, terms, method, key):
        from .learning import ExperienceInput, ExperienceService

        r = self.runtime
        parents = tuple(n["memory_id"] for n in snapshot["notes"])
        actual = sorted(n["memory_id"] for n in self.evaluator.lookup(method, terms, snapshot))
        expected = self.evaluator.oracle(snapshot, terms)
        result = self.capture(
            key,
            canonical(
                {
                    "data": actual,
                    "method": method,
                    "check": "RETAINED_NOTE_LOOKUP_NOT_FACT_TRUTH",
                    "source_stamp": snapshot["stamp"],
                }
            ),
            snapshot["scope"],
            parents,
        )
        experiences = ExperienceService(r.store, r.authority)
        verification = experiences.verify_structured_result(result, digest(expected), r.authority)
        prior = r.store.db.execute(
            "SELECT experience_id FROM experiences WHERE result_memory_id=? AND task_class=? ORDER BY rowid DESC LIMIT 1",
            (result, DOMAIN),
        ).fetchone()
        if prior:
            experiences.get(prior[0])
            return prior[0], result, verification
        eid = experiences.record(
            ExperienceInput(
                context_memory_ids=parents,
                scope=snapshot["scope"],
                task_class=DOMAIN,
                decision="Check actual retained-note lookup against independent source normalization",
                result_memory_id=result,
                verification_memory_id=verification,
            )
        )
        return eid, result, verification

    def assess(self, selected, snapshot, terms, key):
        from .world_loop.learning import EpisodeLearning

        r = self.runtime
        lesson_record, _ = selected
        lesson = r.store.db.execute("SELECT lesson_id FROM lessons WHERE record_id=?", (lesson_record,)).fetchone()
        case = case_for(snapshot, terms, "later-use")
        proof = self.capture(
            "episode." + key,
            canonical(
                {"strategy_episode": {"episode_key": key, "lesson_id": lesson[0], "case": case.model_dump(mode="json")}}
            ),
            snapshot["scope"],
            tuple(n["memory_id"] for n in snapshot["notes"]),
        )
        return EpisodeLearning(
            r.store,
            r.authority,
            scopes=r.config.scopes,
            privacy_classes=r.config.privacy_classes,
            evaluator=self.evaluator,
        ).assess(lesson[0], proof, authority=r.authority)

    def slice(self, scope):
        r = self.runtime
        if r.work.paused or "PROJECT" not in r.config.privacy_classes:
            return None
        self.resume_selected(scope)
        try:
            snapshot = self.evaluator.snapshot(scope, max_notes=self.max_notes)
        except CoreError as exc:
            if exc.code in {"NOTE_RECALL_TIME_BOUND", "NOTE_RECALL_SAFE_POINT_REQUIRED", "NOTE_STRATEGY_SCOPE_BOUND"}:
                return {"note_retrieval": "DEFER", "reason": exc.code}
            raise
        if len(snapshot["notes"]) < 3:
            return None  # no independent practice/evaluation/transfer yet
        selected = qualified_method(r.store, r.authority, r.config.entity_id, scope, r.config.privacy_classes)
        profile = qualified_query_profile(r.store, selected) if selected else None
        candidates = tuple(text_probes(snapshot))
        if profile in TEXT_EVALUATORS.values():
            return self._review({**snapshot, 'profile': TEXT_EVALUATORS[self.max_notes]}, candidates=candidates)
        result = self._review(snapshot)
        if result and result['note_retrieval'] == 'OFFERED_TO_C':
            return result
        if candidates:
            # A new query shape needs a new trial, never a counterexample to a
            # method that was only qualified for WORDLIKE inputs.
            text_result = self._review({**snapshot, 'profile': TEXT_EVALUATORS[self.max_notes]}, candidates=candidates)
            if text_result is not None:
                return text_result
        return result

    def _review(self, snapshot, *, candidates=None):
        r = self.runtime
        scope = snapshot['scope']
        profile = snapshot_evaluator(snapshot)
        key = digest([r.config.entity_id, scope, snapshot["stamp"], *([self.max_notes] if self.max_notes != MAX_NOTES else []),
                      *([profile] if profile in TEXT_EVALUATORS.values() else [])])
        if r.store.db.execute(
            "SELECT 1 FROM events WHERE source_namespace='living.note-retrieval' AND source_key=?", (key,)
        ).fetchone():
            return None
        selected = qualified_method(r.store, r.authority, r.config.entity_id, scope, r.config.privacy_classes)
        if selected and qualified_note_limit(r.store, selected) < self.max_notes:
            selected = None  # Independent scope qualification, not a counterexample to16.
        if selected and qualified_query_profile(r.store, selected) != profile:
            selected = None
        gaps = []
        checked = []
        for mid, terms in (candidates if candidates is not None else probes(snapshot, partial=selected is not None)):
            method = selected[1] if selected else "IDENTITY"
            expected = self.evaluator.oracle(snapshot, terms)
            literal = self.evaluator.lookup('IDENTITY', terms, snapshot)
            actual_rows = literal or self.evaluator._normalized_lookup(method, terms, snapshot)
            actual = sorted(n["memory_id"] for n in actual_rows)
            checked.append((mid, terms, expected, actual, literal))
            if actual != expected and expected and mid not in {m for m, _ in gaps}:
                gaps.append((mid, terms))
                if len(gaps) == 3:
                    break
        # Source changes cannot turn a timeout/unknown into a counterexample.
        # Only an actually executed discrepancy suspends an existing method.
        if selected and gaps:
            self.assess(selected, snapshot, gaps[0][1], "counter." + key[:24])
        elif selected:
            support = set(RecordService(r.store).support(selected[0]))
            # A literal hit does not demonstrate that the learned method was
            # used. Credit only an actual source-distinct normalized success.
            later = next(((mid, terms) for mid, terms, expected, actual, literal in checked
                          if mid not in support and expected and not literal and actual == expected), None)
            if later:
                self.assess(selected, snapshot, later[1], "reuse." + key[:24])
        study = None
        if len(gaps) >= 3:
            from .open_agency.learning import LearningSpec
            from .subject.opportunities import ConcernCue, LearningValue
            from .subject.contracts import SubjectInput
            from ..presence.contracts import RuntimeEvent, Cause

            service = self.service()
            learning_key = "learn.note-retrieval." + key[:24]
            # Registry holds executable configurations, not authoritative history.
            # Do not evict another domain or an unfinished/UNKNOWN study.
            for old in tuple(service.specs):
                if (
                    old.startswith("learn.note-retrieval.")
                    and not r.store.db.execute(
                        "SELECT 1 FROM jobs j JOIN continuity_records c ON c.record_id=j.record_id "
                        "WHERE c.target_id=? AND j.state NOT IN ('DONE','CANCELLED')",
                        (old,),
                    ).fetchone()
                ):
                    service.specs.pop(old)
            if len(service.specs) >= 16:
                return {"note_retrieval": "DEFER", "reason": "LEARNING_POLICY_BOUND"}
            spec = LearningSpec(
                learning_key=learning_key,
                domain=DOMAIN,
                baseline_method="IDENTITY",
                hypotheses=QUALIFICATION_METHODS[profile][1:],
                hypothesis_policy="PRACTICE_COMPARE",
                practice=study_cases(snapshot, gaps[0][1], "practice"),
                evaluation=study_cases(snapshot, gaps[1][1], "evaluation"),
                transfer=study_cases(snapshot, gaps[2][1], "transfer"),
            )
            service.specs[learning_key] = spec
            _, result, verification = self.experience(
                snapshot, gaps[0][1], selected[1] if selected else "IDENTITY", "gap." + key
            )
            cue = ConcernCue(
                cue_kind="OPEN_LOOP",
                motivation_source="CAPABILITY_GAP",
                topic_key="note-retrieval",
                program_id=learning_key,
                possible_behaviors=("LEARN", "WATCH", "REST"),
                learning_value=LearningValue(goal_value="RELEVANT", future_reuse="RELEVANT"),
            )
            existing_spec = r.store.db.execute(
                "SELECT 1 FROM continuity_records WHERE record_kind='RUNTIME_WORK' AND target_id=? AND lifecycle='ACTIVE'",
                (learning_key,),
            ).fetchone()
            if not existing_spec:
                with r.store.transaction("living.note_retrieval_spec") as tx:
                    RecordService(r.store).create(
                        tx,
                        kind="RUNTIME_WORK",
                        scope=scope,
                        target_id=learning_key,
                        payload={
                            "kind": snapshot_evaluator(snapshot),
                            "entity_id": r.config.entity_id,
                            "spec": spec.model_dump(mode="json"),
                        },
                        memories=(result, verification),
                    )
            source = self.capture(
                "cue." + key,
                cue.model_dump_json(),
                scope,
                (result, verification),
                predicate="concern.note-retrieval." + key[:24],
            )
            now = MemoryService(r.store).read(source)["observed_time_us"]
            event = SubjectInput(
                domain="SOURCED_LIFE",
                source_key="local.note-retrieval." + key,
                kind="WAKE",
                origin="SELF_WAKE",
                entity_id=r.config.entity_id,
                scope=scope,
                privacy_class="PROJECT",
                observed_at_us=now,
                source_memory_ids=(source,),
                task_class=DOMAIN,
            )
            study = r.submit(
                RuntimeEvent(
                    event_type="SELF_EVENT",
                    trigger="SELF_TRIGGER",
                    input=event,
                    causes=(Cause(kind="MEMORY", reference_id=source),),
                    due_at_us=now,
                    priority=0,
                )
            )
        with r.store.transaction(
            "living.note_retrieval_reviewed",
            {"study_queue_id": study, "source_stamp": snapshot["stamp"], "scope": scope, "gap_count": len(gaps)},
            source_namespace="living.note-retrieval",
            source_key=key,
        ):
            pass
        return {"note_retrieval": "OFFERED_TO_C" if study else "CHECKED", "queue_id": study}
