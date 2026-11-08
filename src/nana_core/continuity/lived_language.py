"""Human language feedback uses existing Memory, Experience and Lesson authority.

Corpus examples are reports/evaluation material, never autobiographical facts.
Learning changes a narrow expression hypothesis, not identity or judgment.
"""
import json
from typing import Literal
from pydantic import Field
from ..contracts import DTO, CoreError
from ..storage import canonical, digest
from .contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from .records import RecordService
from .person_self import rows

Tag = Literal['TOO_FORMAL','TOO_VERBOSE','META_SUMMARIZING','ASSISTANT_VOICE',
              'OVER_DISCLAIMER','FAKE_MEMORY','FAKE_EMOTION','NATURAL','PLAYFUL',
              'WARM','MISCHIEVOUS','CONCISE','INDEPENDENT','DISAGREES_NATURALLY',
              'RELATIONALLY_GROUNDED','SELF_CONTINUOUS','TOO_TERSE','TOO_OBEDIENT','TOO_DEFENSIVE']


class LanguageSample(DTO):
    body_storage: Literal['SOURCE_REPORT','DEPENDENT_RECORD'] = 'SOURCE_REPORT'
    sample_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    review_target: str = Field(min_length=1, max_length=128)
    mode: Literal['CASUAL','PROJECT','TECHNICAL']
    context: str = Field(min_length=1, max_length=1024)
    relationship_context: str = Field(default='UNSPECIFIED', max_length=512)
    current_self_state: str = Field(default='UNSPECIFIED', max_length=512)
    candidate_response: str = Field(min_length=1, max_length=2048)
    human_judgment: Literal['ACCEPTED','REJECTED','PARTIAL','UNREVIEWED']
    exact_feedback: str = Field(default='', max_length=1024)
    reason_tags: tuple[Tag, ...] = Field(default=(), max_length=8)
    style_tags: tuple[Tag, ...] = Field(default=(), max_length=8)
    truthfulness_tags: tuple[Tag, ...] = Field(default=(), max_length=8)
    memory_use_tags: tuple[Tag, ...] = Field(default=(), max_length=8)
    autonomy_tags: tuple[Tag, ...] = Field(default=(), max_length=8)
    provenance: Literal['USER_PROVIDED_REVIEW','PROJECT_SYNTHETIC']
    provenance_reference: str = Field(default='LOCAL_REVIEW',min_length=1,max_length=512)
    observed_at_us: int = Field(ge=0)


class ExpressionFeedbackCheck(DTO):
    check: Literal['EXPRESSION_FEEDBACK'] = 'EXPRESSION_FEEDBACK'
    result_memory_id: str
    result_artifact_digest: str
    sample_record_id: str
    passed: bool


class ExpressionRule(DTO):
    kind: Literal['CONTEXTUAL_EXPRESSION'] = 'CONTEXTUAL_EXPRESSION'
    scope: Literal['interaction.expression'] = 'interaction.expression'
    mode: Literal['CASUAL'] = 'CASUAL'
    hypothesis: Literal['REDUCE_UNNECESSARY_META_AND_VERBOSITY'] = 'REDUCE_UNNECESSARY_META_AND_VERBOSITY'
    grants_authority: Literal[False] = False
    changes_judgment: Literal[False] = False
    fixed_utterance: None = None


def sample_from_memory(store, result):
    if result['source_provenance']['source_namespace'] != 'recorded.conversation.feedback':
        raise CoreError('LANGUAGE_FEEDBACK_SOURCE_UNTRUSTED')
    if result['source_provenance']['source_kind'] != 'USER_STATEMENT':
        raise CoreError('LANGUAGE_FEEDBACK_NOT_HUMAN_REPORT')
    return LanguageSample.model_validate_json(result['text'])


def source_report(sample):
    if sample.body_storage!='DEPENDENT_RECORD':return sample
    # A crash between evidence capture and linking a Memory must not strand a
    # copied private transcript in an independent source. Full review wording is
    # written only in the atomic dependency-bound sample record transaction.
    return sample.model_copy(update={k:'DEPENDENT_RECORD_BODY' for k in ('context','relationship_context','current_self_state','candidate_response','exact_feedback')})


def report_matches(sample, report):
    return source_report(LanguageSample.model_validate_json(canonical(sample)))==report


def learnable(store, scope, privacy):
    records = RecordService(store)
    samples = rows(store, 'LIVED_LANGUAGE_SAMPLE', scope, privacy, target='CASUAL')
    # Human reviews and project fixtures are distinct evidence populations in
    # both directions: synthetic counterexamples cannot veto human feedback,
    # and a human report cannot silently validate/suspend a fixture lesson.
    kinds = ('USER_PROVIDED_REVIEW','PROJECT_SYNTHETIC')
    support = {kind:{} for kind in kinds}; counters = {kind:[] for kind in kinds}
    for row in samples:
        sample = LanguageSample.model_validate_json(canonical(row['payload']['sample']))
        if sample.human_judgment == 'UNREVIEWED':
            continue
        group = sample.provenance
        # One occurrence contributes once, even if reviewed/replayed repeatedly.
        if sample.review_target in support[group] or any(t == sample.review_target for t, _ in counters[group]):
            continue
        if 'TOO_TERSE' in sample.reason_tags:
            counters[group].append((sample.review_target, row['record_id']))
        elif sample.human_judgment == 'REJECTED' and set(sample.reason_tags) & {'TOO_VERBOSE','META_SUMMARIZING','OVER_DISCLAIMER'}:
            mid = next(m for m in records.support(row['record_id']) if records.memory.read(m)['source_provenance']['source_namespace']=='recorded.conversation.feedback' and records.memory.read(m)['source_provenance']['source_reference']==sample.sample_id)
            support[group][sample.review_target] = (row['record_id'], mid)
    # Synthetic contrast pairs do not combine with actual human observations to
    # manufacture a threshold. Both kinds can qualify only within their scope.
    winner = max(kinds, key=lambda key: len(support[key]))
    # A real negative report may still veto a synthetic hypothesis: synthetic
    # fixtures never overrule an explicitly stated human counterexample.
    veto = tuple(counters[winner]) + (tuple(counters['USER_PROVIDED_REVIEW']) if winner != 'USER_PROVIDED_REVIEW' else ())
    return {'eligible': len(support[winner]) >= 2 and not veto,
            'support_records': tuple(v[0] for v in support[winner].values())[:8],
            'support_memories': tuple(v[1] for v in support[winner].values())[:8],
            'counter_records': tuple(r for _, r in veto), 'evidence_level': winner}


class LanguageService:
    def __init__(self, store, authority):
        from ..actions import OperatorAuthority
        if not isinstance(authority, OperatorAuthority):
            raise CoreError('OPERATOR_AUTHORITY_REQUIRED')
        self.store, self._authority, self.records = store, authority, RecordService(store)

    def record(self, sample, *, scope, entity_id, privacy, authority, exchange_record_id=None):
        if authority is not self._authority or type(sample) is not LanguageSample:
            raise CoreError('LANGUAGE_REVIEW_AUTHORITY_REQUIRED')
        if sample.observed_at_us > self.store.clock.utc_now_us():
            raise CoreError('LANGUAGE_REVIEW_TIME_INVALID')
        if not exchange_record_id and sample.body_storage!='SOURCE_REPORT':raise CoreError('LANGUAGE_REVIEW_BINDING_REQUIRED')
        if exchange_record_id:sample=sample.model_copy(update={'body_storage':'DEPENDENT_RECORD'})
        old = self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='language.review' AND source_key=?", (sample.sample_id,)).fetchone()
        if old:
            rid = json.loads(old[0])['data']['record_id']
            existing = self.records.read(rid)
            if existing['scope'] != scope or existing['payload']['sample'] != sample.model_dump(mode='json'):
                raise CoreError('LANGUAGE_REVIEW_COLLISION')
            if not self.records.current_support(rid):
                raise CoreError('LANGUAGE_REVIEW_SOURCE_WITHDRAWN')
            return rid
        parents = ()
        if exchange_record_id:
            exchange = self.records.read(exchange_record_id)
            if exchange['payload'].get('person_kind') != 'CONVERSATION_EXCHANGE' or exchange['scope'] != scope or exchange['payload']['entity_id'] != entity_id or sample.review_target != exchange_record_id or sample.candidate_response != exchange['payload']['assistant_utterance']:
                raise CoreError('LANGUAGE_REVIEW_TURN_MISMATCH')
            parents = (exchange_record_id,)
            from .memory import PRIVACY_RANK
            privacy=max((privacy,exchange['privacy_class']),key=PRIVACY_RANK.get)
        memory = self.records.memory
        inherited=tuple(dict.fromkeys(m for rid in parents for m in self.records.support(rid)))
        if len(inherited)>64:raise CoreError('LANGUAGE_REVIEW_SOURCE_BOUND')
        report=source_report(sample)
        eid = memory.capture(EvidenceInput(provenance=Provenance(domain='CONSENTED_INTERACTION',source_namespace='recorded.conversation.feedback', source_reference=sample.sample_id, source_kind='USER_STATEMENT'), text=report.model_dump_json(), privacy_class=privacy, retention_consent_ref=sample.sample_id, observed_time_us=sample.observed_at_us))
        mid = memory.add(MemoryCandidate(entity_id=entity_id, scope=scope, memory_type=MemoryType.EPISODIC, epistemic_kind='STATEMENT', source_evidence_id=eid, text=report.model_dump_json(),derived_from=inherited))
        data = {}
        with self.store.transaction('subject.language_review_recorded', data, source_namespace='language.review', source_key=sample.sample_id) as tx:
            rid = self.records.create(tx, kind='EXPERIENCE_CANDIDATE', scope=scope, target_id=sample.mode, payload={'person_kind':'LIVED_LANGUAGE_SAMPLE','sample': sample.model_dump(mode='json'), 'not_subject_experience': sample.provenance == 'PROJECT_SYNTHETIC'}, memories=(mid,), records=parents)
            data['record_id'] = rid
        return rid

    def experience(self, record_id, authority):
        if authority is not self._authority:
            raise CoreError('LANGUAGE_REVIEW_AUTHORITY_REQUIRED')
        row = self.records.read(record_id)
        if row['payload'].get('person_kind') != 'LIVED_LANGUAGE_SAMPLE' or not self.records.current_support(record_id):
            raise CoreError('LANGUAGE_FEEDBACK_UNAVAILABLE')
        mids = self.records.support(record_id)
        result = next((m for m in mids if self.records.memory.read(m)['source_provenance']['source_namespace'] == 'recorded.conversation.feedback' and self.records.memory.read(m)['source_provenance']['source_reference']==row['payload']['sample']['sample_id']), None)
        if not result:
            raise CoreError('LANGUAGE_FEEDBACK_UNAVAILABLE')
        from .learning import ExperienceService, ExperienceInput
        service = ExperienceService(self.store, authority)
        verification = service.verify_expression_result(result, record_id, authority)
        existing = self.store.db.execute("SELECT experience_id FROM experiences WHERE result_memory_id=? AND task_class='interaction.expression'", (result,)).fetchone()
        if existing:
            return existing[0]
        return service.record(ExperienceInput(context_memory_ids=(result,), scope=row['scope'], task_class='interaction.expression',
            decision='Review a declared language reaction as opinion, not objective naturalness or world truth', result_memory_id=result,
            verification_memory_id=verification, proposed_update='Consider a contextual expression hypothesis; a single review cannot overwrite personality'))


def expression_policy(store, *, scope, privacy, mode):
    qualification = learnable(store, scope, privacy)
    if mode != 'CASUAL' or not qualification['eligible']:
        return {'state': 'BASELINE_OR_REVIEW_REQUIRED', 'rule': None, 'source_record_ids': ()}
    records = RecordService(store)
    for raw in store.db.execute("SELECT * FROM lessons WHERE task_class='interaction.expression' AND state='ACTIVE' ORDER BY rowid DESC LIMIT 16"):
        h = store.one('continuity_records', raw['record_id'])
        if h['scope'] != scope or h['privacy_class'] not in privacy or h['lifecycle'] != 'ACTIVE' or not records.current_support(h['record_id']):
            continue
        experience=store.one('experiences',raw['experience_id'])
        if not experience:
            continue
        try:
            origin=sample_from_memory(store,records.memory.read(experience['result_memory_id'])).provenance
        except CoreError:
            continue
        if origin != qualification['evidence_level']:
            continue
        return {'state': 'ACTIVE_BOUNDED_HYPOTHESIS', 'rule': ExpressionRule().model_dump(mode='json'),
                'source_record_ids': (h['record_id'], *qualification['support_records']),
                'evidence_level': qualification['evidence_level'], 'lesson_id': raw['lesson_id']}
    return {'state': 'CANDIDATE_NOT_ADOPTED', 'rule': None, 'source_record_ids': ()}


def context(store, *, scope, privacy, mode):
    policy = expression_policy(store, scope=scope, privacy=privacy, mode=mode)
    samples = rows(store, 'LIVED_LANGUAGE_SAMPLE', scope, privacy, target=mode, limit=16)[:2]
    examples=[]
    for row in samples:
        item=row['payload']['sample']
        examples.append({k:item[k][:384] if k in {'context','candidate_response','exact_feedback'} else item[k] for k in ('context','candidate_response','human_judgment','exact_feedback','reason_tags','provenance','provenance_reference')})
    return {'policy': policy, 'examples': examples,
            'examples_are_not_autobiography': True, 'human_naturalness_qualified': False,
            'source_record_ids': tuple(dict.fromkeys((*policy['source_record_ids'], *(r['record_id'] for r in samples))))}
