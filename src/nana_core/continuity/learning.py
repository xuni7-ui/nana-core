"""Bounded experience learning using the existing StrategyRule/PlanCompiler.

Occurrence and interpretation are different records. An independent local quality
check is required, then a narrow rule must pass trial before reviewed activation.
No arbitrary rule code, identity edits, Grant or capability registration exists.
"""
import json
from typing import Literal,Annotated

from pydantic import Field,TypeAdapter

from ..contracts import CoreError, DTO, StrategyRule
from ..actions import OperatorAuthority
from ..experience import OUTPUT_PRODUCERS
from ..planning import PlanCompiler
from ..storage import canonical, digest, uid
from .contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from .records import RecordService
from .subject.social import InteractionRule,propose_social
from .lived_language import ExpressionFeedbackCheck, ExpressionRule, sample_from_memory, learnable, report_matches
from .autonomy.experience import DispositionQualityCheck,DispositionRule,disposition_fact,lesson_method,ConsequenceObservation


class LocalQualityCheck(DTO):
    schema_version: Literal[1] = 1
    check: Literal["READING_CARD_LOCATOR"] = "READING_CARD_LOCATOR"
    result_memory_id: str
    result_artifact_digest: str
    passed: bool
    missing_field: Literal["locator"] | None


class InteractionOutcome(DTO):
    proposal_intention_id: str
    reaction: Literal['POSITIVE_PLAYFUL','NEUTRAL','NEGATIVE']
    external_delivery: Literal[False] = False
    provenance: Literal['SYNTHETIC_WORLD'] = 'SYNTHETIC_WORLD'


class InteractionQualityCheck(DTO):
    schema_version: Literal[1] = 1
    check: Literal['INTERACTION_FEEDBACK'] = 'INTERACTION_FEEDBACK'
    result_memory_id: str
    result_artifact_digest: str
    proposal_intention_id: str
    reaction: Literal['POSITIVE_PLAYFUL','NEUTRAL','NEGATIVE']
    passed: bool


class StructuredQualityCheck(DTO):
    check: Literal['STRUCTURED_EXPECTATION'] = 'STRUCTURED_EXPECTATION'
    result_memory_id: str
    result_artifact_digest: str
    expected_digest: str
    passed: bool


Verification = Annotated[LocalQualityCheck | InteractionQualityCheck | DispositionQualityCheck | StructuredQualityCheck | ExpressionFeedbackCheck,Field(discriminator='check')]
CHECKS = TypeAdapter(Verification)


class ExperienceInput(DTO):
    context_memory_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    scope: str
    task_class: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    decision: str = Field(min_length=1, max_length=2048)
    result_memory_id: str
    verification_memory_id: str
    proposed_update: str | None = Field(default=None, max_length=2048)


class ExperienceRecord(DTO):
    experience_id: str
    task_class: str
    context_memory_ids: tuple[str, ...]
    decision: str
    result: str
    verification: Verification
    proposed_update: str | None
    outcome: Literal["SUCCESS", "FAILURE", "NON_EXECUTION"]


class ExperienceService:
    def __init__(self, store, authority):
        if not isinstance(authority, OperatorAuthority):
            raise CoreError("OPERATOR_AUTHORITY_REQUIRED")
        self.store, self._authority, self.records = store, authority, RecordService(store)

    def _operator(self, authority):
        if authority is not self._authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")

    def verify_reading_result(self, result_memory_id, authority):
        self._operator(authority)
        memory = self.records.memory
        result = memory.read(result_memory_id)
        try:
            card = json.loads(result["text"])
        except (ValueError, TypeError):
            raise CoreError("INVALID_READING_RESULT") from None
        if type(card) is not dict:
            raise CoreError("INVALID_READING_RESULT")
        # Model saying {success:true} is irrelevant; inspect the actual field.
        passed = type(card.get("locator")) is str and bool(card["locator"].strip())
        check = LocalQualityCheck(result_memory_id=result_memory_id,
            result_artifact_digest=digest(self.store.artifact(result["payload_artifact_id"])),
            passed=passed, missing_field=None if passed else "locator")
        now = self.store.clock.utc_now_us()
        source = memory.capture(EvidenceInput(provenance=Provenance(
            source_namespace="synthetic.quality-check", source_reference=result_memory_id,
            source_kind="SYSTEM_VERIFICATION"), text=check.model_dump_json(),
            privacy_class=result["privacy_class"], event_time_us=now, observed_time_us=now))
        return memory.add(MemoryCandidate(entity_id=result["entity_id"], scope=result["scope"],
            memory_type=MemoryType.EPISODIC, epistemic_kind="OBSERVATION", source_evidence_id=source,
            text=check.model_dump_json(), confidence=1.0, derived_from=(result_memory_id,)))

    def verify_structured_result(self,result_memory_id,expected_digest,authority):
        self._operator(authority)
        if self.store.schema_target<12:raise CoreError('OPEN_AGENCY_SCHEMA_REQUIRED')
        result=self.records.memory.read(result_memory_id)
        actual=json.loads(result['text'])
        check=StructuredQualityCheck(result_memory_id=result_memory_id,
            result_artifact_digest=digest(self.store.artifact(result['payload_artifact_id'])),
            expected_digest=expected_digest,passed=digest(actual.get('data'))==expected_digest)
        namespace='recorded.project.structured-check' if result['source_provenance']['domain']=='DEVELOPMENT_PROJECT' else 'synthetic.structured-check'
        previous=self.store.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace=? AND source_reference=?",(namespace,result_memory_id)).fetchone()
        now=previous[0] if previous else self.store.clock.utc_now_us()
        eid=self.records.memory.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT' if namespace.startswith('recorded.project.') else 'SYNTHETIC_ONLY',source_namespace=namespace,source_reference=result_memory_id,source_kind='SYSTEM_VERIFICATION'),text=check.model_dump_json(),privacy_class=result['privacy_class'],observed_time_us=now))
        return self.records.memory.add(MemoryCandidate(entity_id=result['entity_id'],scope=result['scope'],memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=check.model_dump_json(),derived_from=(result_memory_id,),confidence=1.))

    def _interaction_outcome(self,result):
        source=self.records.memory.evidence(result['source_evidence_id'])
        if source['source_kind']!='DIRECT_OBSERVATION' or result['epistemic_kind']!='OBSERVATION':
            raise CoreError('INDEPENDENT_INTERACTION_OUTCOME_REQUIRED')
        outcome=InteractionOutcome.model_validate_json(result['text'])
        intention=self.store.one('subject_intentions',outcome.proposal_intention_id)
        if not intention or intention['kind']!='SOCIAL_INTERACTION' or intention['scope']!=result['scope']:
            raise CoreError('INTERACTION_PROPOSAL_MISMATCH')
        self.records.read(intention['record_id'])
        parent=self.store.one('subject_events',intention['subject_event_id'])
        if parent['entity_id']!=result['entity_id']:raise CoreError('INTERACTION_ENTITY_MISMATCH')
        return outcome

    def verify_interaction_result(self,result_memory_id,authority):
        self._operator(authority)
        memory=self.records.memory
        result=memory.read(result_memory_id)
        outcome=self._interaction_outcome(result)
        check=InteractionQualityCheck(result_memory_id=result_memory_id,
            result_artifact_digest=digest(self.store.artifact(result['payload_artifact_id'])),
            proposal_intention_id=outcome.proposal_intention_id,reaction=outcome.reaction,passed=outcome.reaction=='POSITIVE_PLAYFUL')
        now=self.store.clock.utc_now_us()
        eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.interaction-check',
            source_reference=result_memory_id,source_kind='SYSTEM_VERIFICATION'),text=check.model_dump_json(),
            privacy_class=result['privacy_class'],event_time_us=now,observed_time_us=now))
        return memory.add(MemoryCandidate(entity_id=result['entity_id'],scope=result['scope'],memory_type=MemoryType.EPISODIC,
            epistemic_kind='OBSERVATION',source_evidence_id=eid,text=check.model_dump_json(),confidence=1.,derived_from=(result_memory_id,)))

    def verify_expression_result(self, result_memory_id, sample_record_id, authority):
        self._operator(authority)
        memory=self.records.memory;result=memory.read(result_memory_id)
        sample=sample_from_memory(self.store,result)
        row=self.records.read(sample_record_id)
        if row['payload'].get('person_kind')!='LIVED_LANGUAGE_SAMPLE' or row['scope']!=result['scope'] or not report_matches(row['payload']['sample'],sample) or result_memory_id not in self.records.support(sample_record_id) or not self.records.current_support(sample_record_id):raise CoreError('LANGUAGE_FEEDBACK_BINDING_INVALID')
        check=ExpressionFeedbackCheck(result_memory_id=result_memory_id,result_artifact_digest=digest(self.store.artifact(result['payload_artifact_id'])),sample_record_id=sample_record_id,passed=sample.human_judgment=='ACCEPTED')
        eid=memory.capture(EvidenceInput(provenance=Provenance(domain='CONSENTED_INTERACTION',source_namespace='recorded.conversation.feedback-check',source_reference=sample_record_id,source_kind='SYSTEM_VERIFICATION'),text=check.model_dump_json(),privacy_class=result['privacy_class'],retention_consent_ref=sample_record_id,observed_time_us=row['created_at_us']))
        return memory.add(MemoryCandidate(entity_id=result['entity_id'],scope=result['scope'],memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=check.model_dump_json(),derived_from=(result_memory_id,)))

    def record(self, candidate: ExperienceInput):
        memory = self.records.memory
        result = memory.read(candidate.result_memory_id)
        verification = memory.read(candidate.verification_memory_id)
        source = memory.evidence(verification["source_evidence_id"])
        if source["source_kind"] != "SYSTEM_VERIFICATION":
            raise CoreError("INDEPENDENT_EXPERIENCE_VERIFICATION_REQUIRED")
        check = CHECKS.validate_json(verification["text"])
        if (check.result_memory_id != candidate.result_memory_id or
                check.result_artifact_digest != digest(self.store.artifact(result["payload_artifact_id"]))):
            raise CoreError("EXPERIENCE_VERIFICATION_MISMATCH")
        actual = json.loads(result["text"])
        if isinstance(check,LocalQualityCheck):
            passed = type(actual) is dict and type(actual.get("locator")) is str and bool(actual["locator"].strip())
            if candidate.task_class!='reading_card' or check.passed != passed or check.missing_field != (None if passed else "locator"):
                raise CoreError("EXPERIENCE_VERIFICATION_MISMATCH")
        elif isinstance(check,StructuredQualityCheck):
            if self.store.schema_target<12 or source['source_namespace'] not in {'synthetic.structured-check','recorded.project.structured-check'} or check.passed!=(digest(actual.get('data'))==check.expected_digest):raise CoreError('EXPERIENCE_VERIFICATION_MISMATCH')
        elif isinstance(check,ExpressionFeedbackCheck):
            sample=sample_from_memory(self.store,result)
            parent=self.records.read(check.sample_record_id)
            if candidate.task_class!='interaction.expression' or source['source_namespace']!='recorded.conversation.feedback-check' or parent['payload'].get('person_kind')!='LIVED_LANGUAGE_SAMPLE' or parent['scope']!=candidate.scope or not report_matches(parent['payload']['sample'],sample) or not self.records.current_support(check.sample_record_id) or check.passed!=(sample.human_judgment=='ACCEPTED'):raise CoreError('EXPERIENCE_VERIFICATION_MISMATCH')
        elif isinstance(check,InteractionQualityCheck):
            outcome=self._interaction_outcome(result)
            if candidate.task_class!='interaction.shared_discovery' or check.proposal_intention_id!=outcome.proposal_intention_id or check.reaction!=outcome.reaction or check.passed!=(outcome.reaction=='POSITIVE_PLAYFUL'):
                raise CoreError("EXPERIENCE_VERIFICATION_MISMATCH")
        else:
            if self.store.schema_target<9 or candidate.task_class!='disposition.review' or source['source_namespace']!='synthetic.disposition-check':raise CoreError('EXPERIENCE_VERIFICATION_MISMATCH')
            fact=disposition_fact(self.store,check.disposition_record_id)
            parent=self.records.read(check.candidate_record_id)
            if parent['record_kind']!='EXPERIENCE_CANDIDATE' or parent['scope']!=candidate.scope or not self.records.current_support(check.candidate_record_id):raise CoreError('EXPERIENCE_CANDIDATE_UNAVAILABLE')
            if actual!={'candidate_record_id':check.candidate_record_id,'fact':fact,'reasoning_assessment':check.reasoning_assessment} or check.factual_code!=fact['code']:raise CoreError('EXPERIENCE_VERIFICATION_MISMATCH')
            assessment='UNASSESSED'
            if parent['payload']['consequence_memory_id']:
                consequence=self.records.memory.read(parent['payload']['consequence_memory_id'])
                assessment=ConsequenceObservation.model_validate_json(consequence['text']).assessment
            if assessment!=check.reasoning_assessment:raise CoreError('CONSEQUENCE_ASSESSMENT_MISMATCH')
            old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='experience.disposition' AND source_key=?",(check.candidate_record_id,)).fetchone()
            if old:
                eid=json.loads(old[0])['data']['experience_id'];self.get(eid);return eid
        experience_id = uid()
        disposition=isinstance(check,DispositionQualityCheck)
        with self.store.transaction("self.experience_recorded",{'experience_id':experience_id} if disposition else None,
                source_namespace='experience.disposition' if disposition else None,source_key=check.candidate_record_id if disposition else None) as tx:
            record_id = self.records.create(tx, kind="EXPERIENCE", scope=candidate.scope,
                payload={"decision": candidate.decision, "context_memory_ids": candidate.context_memory_ids,
                         "proposed_update": candidate.proposed_update},
                memories=(*candidate.context_memory_ids, candidate.result_memory_id, candidate.verification_memory_id))
            tx.put("experiences", {"experience_id": experience_id, "record_id": record_id,
                "task_class": candidate.task_class, "result_memory_id": candidate.result_memory_id,
                "verification_memory_id": candidate.verification_memory_id,
                "outcome": "NON_EXECUTION" if disposition else "SUCCESS" if check.passed else "FAILURE", "created_at_us": self.store.clock.utc_now_us()})
        return experience_id

    def get(self, experience_id):
        row = self.store.one("experiences", experience_id)
        if not row:
            raise CoreError("EXPERIENCE_MISSING")
        record = self.records.read(row["record_id"])
        result = self.records.memory.read(row["result_memory_id"])
        verification = self.records.memory.read(row["verification_memory_id"])
        return ExperienceRecord(experience_id=experience_id, task_class=row["task_class"],
            context_memory_ids=tuple(record["payload"]["context_memory_ids"]), decision=record["payload"]["decision"],
            result=result["text"], verification=CHECKS.validate_json(verification["text"]),
            proposed_update=record["payload"]["proposed_update"], outcome=row["outcome"])

    def derive_lesson(self, experience_id):
        experience = self.get(experience_id)
        if experience.task_class=='reading_card' and experience.outcome=='FAILURE' and isinstance(experience.verification,LocalQualityCheck):
            missing=experience.verification.missing_field
            producer=OUTPUT_PRODUCERS.get(missing)
            if not producer:raise CoreError('NO_SUPPORTED_LESSON')
            rule=StrategyRule(capability=producer,required_output=missing)
        elif experience.task_class=='interaction.shared_discovery' and experience.outcome=='SUCCESS' and isinstance(experience.verification,InteractionQualityCheck):
            rule=InteractionRule()
        elif experience.task_class=='disposition.review' and isinstance(experience.verification,DispositionQualityCheck) and experience.verification.reasoning_assessment!='UNASSESSED':
            rule=DispositionRule(assessment=experience.verification.reasoning_assessment)
        elif experience.task_class=='interaction.expression' and isinstance(experience.verification,ExpressionFeedbackCheck) and experience.outcome=='FAILURE':
            sample=sample_from_memory(self.store,self.records.memory.read(self.store.one('experiences',experience_id)['result_memory_id']))
            if sample.mode!='CASUAL' or not set(sample.reason_tags)&{'TOO_VERBOSE','META_SUMMARIZING','OVER_DISCLAIMER'}:raise CoreError('NO_SUPPORTED_LESSON')
            rule=ExpressionRule()
        else:raise CoreError('NO_SUPPORTED_LESSON')
        previous = self.store.db.execute("SELECT lesson_id FROM lessons WHERE experience_id=?", (experience_id,)).fetchone()
        if previous:
            return previous[0]
        lesson_id = uid()
        parent = self.store.one("experiences", experience_id)
        with self.store.transaction("self.lesson_proposed") as tx:
            record_id = self.records.create(tx, kind="LESSON", scope=self.records.read(parent["record_id"])["scope"],
                payload={"rule": rule.model_dump(mode="json")}, records=(parent["record_id"],))
            tx.put("lessons", {"lesson_id": lesson_id, "experience_id": experience_id,
                "record_id": record_id, "task_class": rule.scope, "revision": 1,
                "state": "CANDIDATE", "tested_rule_hash": None, "test_event_id": None})
        return lesson_id

    def test_lesson(self, lesson_id):
        row = self.store.one("lessons", lesson_id)
        if not row or row["state"] not in {"CANDIDATE", "SUSPENDED"}:
            raise CoreError("ILLEGAL_LESSON_TRANSITION")
        if not self.records.current_support(row["record_id"]):
            raise CoreError("LESSON_SUPPORT_REQUIRES_REVIEW")
        rule = self._rule(row)
        compiler_version=PlanCompiler.version
        from .open_agency.learning import MethodStrategyRule
        from .open_life.meta_learning import LearningStrategyLesson,checks as meta_checks
        if isinstance(rule,LearningStrategyLesson):
            checks=meta_checks(self.records,rule);compiler_version='PRACTICE_ONLY_HYPOTHESIS_SELECTION_V1'
        elif isinstance(rule,MethodStrategyRule):
            trial=self.records.read(rule.trial_record_id)
            data=trial['payload'];results=data.get('results',{})
            checks={'source_backed_trial':trial['record_kind']=='LEARNING_TRIAL' and self.records.current_support(rule.trial_record_id),
                'domain_and_method':data.get('domain')==rule.scope and data.get('method')==rule.method,
                'heldout_and_transfer':all(results.get(k,{}).get('all_passed') and results[k].get('checked',0)>0 for k in ('EVALUATE','TRANSFER')),
                'improvement':results.get('EVALUATE',{}).get('passed',0)>results.get('BASELINE',{}).get('passed',0),
                'not_authority':rule.grants_authority is False}
            compiler_version='BOUNDED_OPERATOR_METHOD_V1'
        elif isinstance(rule,DispositionRule):
            checks={'source_assessment_required':rule.assessment in {'HELPFUL','HARMFUL'},'changes_review_method':lesson_method(rule)!=lesson_method(),
                'no_authority':rule.grants_authority is False,'scope_limited':rule.scope=='disposition.review'}
            compiler_version='C_DISPOSITION_REVIEW_v1'
        elif isinstance(rule,ExpressionRule):
            head=self.records.read(row['record_id'])
            q=learnable(self.store,head['scope'],('PUBLIC','PROJECT','PERSONAL','SECRET'))
            checks={'two_distinct_review_occurrences':q['eligible'],'no_counterexample':not q['counter_records'],'context_limited':rule.mode=='CASUAL','no_fixed_utterance':rule.fixed_utterance is None,'judgment_unchanged':not rule.changes_judgment,'no_authority':not rule.grants_authority}
            compiler_version='CONTEXTUAL_EXPRESSION_HYPOTHESIS_V1'
        elif isinstance(rule,InteractionRule):
            baseline=propose_social(topic='trial',style='WARM_PLAYFUL',available=True,source_ids=('source',),last_act='TEASE')
            learned=propose_social(topic='trial',style='WARM_PLAYFUL',available=True,source_ids=('source',),lesson_ids=(lesson_id,),last_act='TEASE')
            unavailable=propose_social(topic='trial',style='WARM_PLAYFUL',available=False,source_ids=('source',),lesson_ids=(lesson_id,),last_act='TEASE')
            stranger=propose_social(topic='trial',style='RESPECTFUL_EXPLICIT',available=True,source_ids=('source',),lesson_ids=(lesson_id,),last_act='TEASE')
            checks={'changes_semantic_proposal':baseline.act!=learned.act,'no_fixed_utterance':learned.utterance is None,
                'availability_inhibits':unavailable.act=='STAY_SILENT','scope_and_relationship_limited':stranger.act=='ASK',
                'no_authority_fields':set(rule.model_dump())=={'kind','scope','vary_expression','require_receptive_context'}}
            compiler_version='C_SOCIAL_VARIATION_v1'
        else:
            compiler = PlanCompiler()
            preview = {"strategy_id": lesson_id, "revision": row["revision"], "status": "ACTIVE",
                       "body_json": canonical({"rule_json": rule.model_dump_json()})}
            base = [{"capability": "reading.source.read", "resource": "source://synthetic/lesson-trial"},
                    {"capability": "reading.card.create", "resource": "notebook://synthetic/lesson-trial"}]
            applied = compiler.apply(base, [preview])
            checks = {"adds_required_read": applied["steps"] == [base[0], {"capability": rule.capability,
                      "resource": base[0]["resource"]}, base[1]],
                "idempotent": compiler.apply(applied["steps"], [preview])["steps"] == applied["steps"],
                "scope_limited": compiler.apply(base, [preview], template="unrelated")["steps"] == base,
                "write_unchanged": applied["steps"][-1] == base[-1],
                "no_authority_fields": set(rule.model_dump()) == {"kind", "capability", "scope", "required_output"}}
        with self.store.transaction("self.lesson_tested", {"lesson_id": lesson_id, "checks": checks,
                "rule_hash": digest(rule.model_dump()), "compiler_version": compiler_version}) as tx:
            if isinstance(rule,ExpressionRule) and all(checks.values()):
                supported=self.records.create(tx,kind='LESSON',scope=head['scope'],payload={'rule':rule.model_dump(mode='json')},records=(row['record_id'],*q['support_records']))
                tx.update('lessons',lesson_id,record_id=supported)
            tx.update("lessons", lesson_id, state="TESTED" if all(checks.values()) else "REJECTED",
                revision=row["revision"] + 1, tested_rule_hash=digest(rule.model_dump()), test_event_id=tx.event_id)
        return checks

    def activate(self, lesson_id, authority):
        self._operator(authority)
        row = self.store.one("lessons", lesson_id)
        if not row or row["state"] != "TESTED":
            raise CoreError("UNTESTED_LESSON")
        if not self.records.current_support(row["record_id"]):
            raise CoreError("LESSON_SUPPORT_REQUIRES_REVIEW")
        rule = self._rule(row)
        test = json.loads(self.store.event(row["test_event_id"])["data_json"])["data"]
        if isinstance(rule,ExpressionRule) and not learnable(self.store,self.records.read(row['record_id'])['scope'],('PUBLIC','PROJECT','PERSONAL','SECRET'))['eligible']:raise CoreError('EXPRESSION_LESSON_REQUIRES_REVIEW')
        if row["tested_rule_hash"] != digest(rule.model_dump()) or not all(test["checks"].values()):
            raise CoreError("STALE_LESSON_EVALUATION")
        with self.store.transaction("self.lesson_activated") as tx:
            tx.update("lessons", lesson_id, state="ACTIVE", revision=row["revision"] + 1)

    def suspend(self, lesson_id, authority, *, retire=False):
        self._operator(authority)
        row = self.store.one("lessons", lesson_id)
        if not row or row["state"] in {"RETIRED", "REJECTED"}:
            raise CoreError("ILLEGAL_LESSON_TRANSITION")
        with self.store.transaction("self.lesson_suspended") as tx:
            tx.update("lessons", lesson_id, state="RETIRED" if retire else "SUSPENDED", revision=row["revision"] + 1)

    def _rule(self, row):
        payload=self.records.read(row['record_id'])['payload']['rule']
        if payload.get('kind')=='LEARNING_STRATEGY':
            from .open_life.meta_learning import LearningStrategyLesson
            return LearningStrategyLesson.model_validate_json(canonical(payload))
        if payload.get('kind')=='CONTEXTUAL_EXPRESSION':return ExpressionRule.model_validate_json(canonical(payload))
        if payload.get('kind')=='METHOD_SELECTION':
            from .open_agency.learning import MethodStrategyRule
            return MethodStrategyRule.model_validate_json(canonical(payload))
        kind=DispositionRule if row['task_class']=='disposition.review' else InteractionRule if row['task_class']=='interaction.shared_discovery' else StrategyRule
        return kind.model_validate_json(canonical(payload))

    def context_blocks(self, request, privacy):
        from .context import ContextBlock
        blocks = []
        for row in self.store.all("experiences")[-16:]:
            record = self.store.one("continuity_records", row["record_id"])
            if (row["task_class"] != request.task_class or record["scope"] not in request.scopes
                    or record["privacy_class"] not in privacy or record["lifecycle"] != "ACTIVE"
                    or not self.records.current_support(record["record_id"])):
                continue
            blocks.append((650.0, ContextBlock(block_id="experience:" + row["experience_id"], kind="EXPERIENCE",
                data_json=self.get(row["experience_id"]).model_dump_json(),
                source_memory_ids=self.records.support(row["record_id"]), source_record_ids=(row["record_id"],))))
        for row in self.store.all("lessons"):
            record = self.store.one("continuity_records", row["record_id"])
            if (row["state"] != "ACTIVE" or row["task_class"] != request.task_class or record["scope"] not in request.scopes
                    or record["privacy_class"] not in privacy or record["lifecycle"] != "ACTIVE"
                    or not self.records.current_support(row["record_id"])):
                continue
            blocks.append((950.0, ContextBlock(block_id="lesson:" + row["lesson_id"], kind="INTERACTION_LESSON" if row["task_class"]=="interaction.shared_discovery" else "LESSON",
                data_json=canonical({"lesson_id": row["lesson_id"], "experience_id": row["experience_id"],
                    "rule": self._rule(row).model_dump(mode="json"), "authority_granted": False}),
                source_memory_ids=self.records.support(row["record_id"]), source_record_ids=(row["record_id"],))))
        return blocks
