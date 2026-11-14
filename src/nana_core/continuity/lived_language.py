"""Human language feedback uses existing Memory, Experience and Lesson authority.

Corpus examples are reports/evaluation material, never autobiographical facts.
Learning changes a narrow expression hypothesis, not identity or judgment.
"""
import json
import hashlib
from typing import Literal
from pydantic import Field, model_serializer
from ..contracts import DTO, CoreError
from ..storage import canonical, digest
from .contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from .records import RecordService
from .person_self import rows

Tag = Literal['TOO_FORMAL','TOO_VERBOSE','META_SUMMARIZING','ASSISTANT_VOICE',
              'OVER_DISCLAIMER','FAKE_MEMORY','FAKE_EMOTION','NATURAL','PLAYFUL',
              'WARM','MISCHIEVOUS','CONCISE','INDEPENDENT','DISAGREES_NATURALLY',
              'RELATIONALLY_GROUNDED','SELF_CONTINUOUS','TOO_TERSE','TOO_OBEDIENT','TOO_DEFENSIVE']


class MemoryUseFeedback(DTO):
    memory_id: str = Field(min_length=1,max_length=128)
    mode: Literal['EXPLICIT_RECALL','NATURAL_REFERENCE','IMPLICIT_REFERENCE','DO_NOT_MENTION']


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
    memory_use: MemoryUseFeedback | None = None

    @model_serializer(mode='wrap')
    def compatible_memory_use(self,handler):
        result=handler(self)
        if self.memory_use is None:result.pop('memory_use',None)
        return result


def response_matches(sample, response, response_sha256=None):
    """Bind an explicit review to the original speech, retaining the legacy sample bound."""
    if response_sha256 is None:
        return sample.candidate_response == response
    return (type(response) is str and 2048 < len(response) <= 16384
        and sample.candidate_response == 'DEPENDENT_RECORD_BODY'
        and type(response_sha256) is str and len(response_sha256) == 64
        and all(c in '0123456789abcdef' for c in response_sha256)
        and hashlib.sha256(response.encode('utf-8')).hexdigest() == response_sha256)


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
    # Once a real review exists, fixtures cannot outvote it by volume. A lone
    # review remains insufficient to adopt a new rule; it is not padded.
    winner = ('USER_PROVIDED_REVIEW' if support['USER_PROVIDED_REVIEW'] or counters['USER_PROVIDED_REVIEW']
              else 'PROJECT_SYNTHETIC')
    # A real negative report may still veto a synthetic hypothesis: synthetic
    # fixtures never overrule an explicitly stated human counterexample.
    veto = tuple(counters[winner]) + (tuple(counters['USER_PROVIDED_REVIEW']) if winner != 'USER_PROVIDED_REVIEW' else ())
    return {'eligible': len(support[winner]) >= 2 and not veto,
            'support_records': tuple(v[0] for v in support[winner].values())[:8],
            'support_memories': tuple(v[1] for v in support[winner].values())[:8],
            'counter_records': tuple(r for _, r in veto), 'evidence_level': winner}


def delivery_for_exchange(records, exchange, *, observed_at_us=None):
    """Original Kernel/readback provenance, not a user claim or human-read proof.

    First supported adapter is QQ. Missing/legacy/UNKNOWN evidence stays unproven;
    no network read, action retry, new receipt or second delivery journal occurs.
    All payload headers are scope/privacy checked before opening their bodies.
    """
    from ..contracts import Receipt, Verification
    from .memory import PRIVACY_RANK
    store=records.store
    def read_record(rid):
        head=store.one('continuity_records',rid)
        if (not head or head['scope']!=exchange['scope'] or head['lifecycle']!='ACTIVE'
                or PRIVACY_RANK[head['privacy_class']]>PRIVACY_RANK[exchange['privacy_class']]
                or not records.current_support(rid)):
            raise CoreError('DELIVERY_SOURCE_UNAVAILABLE')
        return records.read(rid)
    def event_payload(eid,kind,action_id):
        event=store.event(eid)
        if (event['kind']!=kind or event['identity_id']!=store.identity['identity_id']
                or not event['artifact_id'] or len(event['data_json'])>65536):
            raise CoreError('DELIVERY_EVENT_MISMATCH')
        body=json.loads(event['data_json'])
        if body['data'].get('action_id')!=action_id or len(body.get('changes',()))>64:
            raise CoreError('DELIVERY_EVENT_MISMATCH')
        ids=tuple(change['row']['record_id'] for change in body.get('changes',())
            if change.get('table')=='continuity_records'
            and change['row'].get('record_kind')=='ACTION_PAYLOAD'
            and change['row'].get('payload_artifact_id')==event['artifact_id'])
        if len(ids)!=1:raise CoreError('DELIVERY_EVENT_MISMATCH')
        record=read_record(ids[0])
        if record['record_kind']!='ACTION_PAYLOAD':raise CoreError('DELIVERY_EVENT_MISMATCH')
        return event,record
    try:
        if (exchange['payload'].get('person_kind')!='CONVERSATION_EXCHANGE'
                or not records.current_support(exchange['record_id'])):return None
        parents=store.db.execute("SELECT parent_id FROM record_dependencies WHERE record_id=? AND parent_kind='RECORD' AND relation_kind='SUPPORT' LIMIT 3",(exchange['record_id'],)).fetchall()
        cycles=[read_record(row[0]) for row in parents]
        cycles=[row for row in cycles if row['record_kind']=='SUBJECT_CYCLE']
        if len(cycles)!=1:return None
        cycle=cycles[0];decision=cycle['payload'];intention=decision.get('intention_id')
        if not intention or (decision.get('evaluation') or {}).get('normative')!='ENDORSED':return None
        event=store.one('subject_events',decision['event_id'])
        source=read_record(event['record_id'])['payload']['input']
        surface=source.get('surface') or {};target=decision.get('realization_target') or {}
        data=exchange['payload']
        if (surface.get('platform')!='qq.onebot' or source['entity_id']!=data['entity_id']
                or source['scope']!=exchange['scope'] or data['user_memory_id'] not in source['source_memory_ids']
                or target.get('capability')!='world.contact'):return None
        action=store.db.execute("SELECT * FROM actions WHERE effect_slot=? AND state='SUCCEEDED' LIMIT 1",('subject:'+intention,)).fetchone()
        if not action or action['capability']!='world.contact' or action['resource']!=target.get('resource'):return None
        args=read_record(json.loads(action['args_json'])['action_payload_record'])['payload']
        candidate=args.get('data') or {}
        if (args.get('data_privacy')!=exchange['privacy_class'] or candidate.get('cycle_record_id')!=cycle['record_id']
                or candidate.get('candidate_digest')!=digest([data['assistant_utterance'],cycle['record_id'],exchange['privacy_class']])):return None
        execute=store.one('attempts',action['attempt_id'])
        verify=store.db.execute("SELECT * FROM attempts WHERE action_id=? AND kind='VERIFY' AND outcome='SUCCEEDED' AND verification_event_id=? ORDER BY attempt_no DESC LIMIT 1",
            (action['action_id'],execute['verification_event_id'])).fetchone()
        if not verify or execute['kind']!='EXECUTE' or execute['outcome']!='SUCCEEDED':return None
        ack_event,ack_record=event_payload(execute['receipt_event_id'],'action.receipt_received',action['action_id'])
        checked_event,checked_record=event_payload(verify['verification_event_id'],'action.verified',action['action_id'])
        ack=Receipt.model_validate_json(canonical(ack_record['payload']))
        checked=Verification.model_validate_json(canonical(checked_record['payload']))
        receipt=ack.result;proof=checked.evidence;origin=receipt.get('platform_origin')
        if (origin not in {'SYNTHETIC_LOOPBACK','AUTHENTICATED_PLATFORM'} or proof.get('platform_origin')!=origin
                or checked.verdict!='MATCH' or proof.get('independent_readback') is not True
                or ack.external_id!=receipt.get('message_id') or proof.get('message_id')!=receipt.get('message_id')
                or proof.get('account_id')!=receipt.get('account_id') or proof.get('target_id')!=receipt.get('target_id')
                or receipt.get('echo')!=action['idempotency_key'] or receipt.get('text_digest')!=digest(data['assistant_utterance'])
                or surface.get('conversation_id')!='qq.'+str(receipt.get('target_kind'))+'.'+str(receipt.get('target_id'))
                or checked_event['recorded_at_us']<data['as_of_us']
                or (observed_at_us is not None and observed_at_us<checked_event['recorded_at_us'])):return None
        return {'state':'INDEPENDENT_PLATFORM_READBACK','origin':origin,'entity_id':data['entity_id'],
            'scope':exchange['scope'],'action_id':action['action_id'],'verified_at_us':checked_event['recorded_at_us'],
            'recipient_context':{'platform':surface['platform'],'binding_id':surface['session_id'],
                'conversation_id':surface['conversation_id']},
            'receipt_record_id':ack_record['record_id'],'verification_record_id':checked_record['record_id'],
            'human_read_proven':False,'memory_use_verified':False,'execution_authority':False}
    except CoreError as exc:
        if exc.code in {'PRIVACY_ANCHOR_INVALID','PRIVACY_ANCHOR_UNAVAILABLE','RUNTIME_LEASE_LOST'}:raise
        return None
    except (KeyError,ValueError,TypeError,AttributeError):
        return None


def communication_feedback_key(store, scope, entity_id, topic, recipient):
    if hasattr(recipient,'model_dump'):recipient=recipient.model_dump(mode='json')
    return 'communication-feedback.'+digest([store.identity['identity_id'],scope,entity_id,topic,recipient])


def communication_for_exchange(records, exchange):
    """Bind an opinion to C's actual method, never to a model's proposed reason."""
    from ..life.dialogue_contracts import CommunicationChoice
    store=records.store;data=exchange['payload']
    if not records.current_support(exchange['record_id']):return None
    parents=store.db.execute("SELECT parent_id FROM record_dependencies WHERE record_id=? AND parent_kind='RECORD' AND relation_kind='SUPPORT' LIMIT 3",
        (exchange['record_id'],)).fetchall()
    cycles=[]
    for (rid,) in parents:
        head=store.one('continuity_records',rid)
        if (not head or head['scope']!=exchange['scope'] or head['lifecycle']!='ACTIVE'
                or head['privacy_class']!=exchange['privacy_class'] or not records.current_support(rid)):continue
        if head['record_kind']=='SUBJECT_CYCLE':cycles.append(records.read(rid))
    if len(cycles)!=1:return None
    cycle=cycles[0];decision=cycle['payload'];choice=decision.get('communication_choice')
    if choice is None:return None
    event=store.one('subject_events',decision['event_id'])
    if not event:return None
    if event['entity_id']!=data['entity_id'] or event['scope']!=exchange['scope']:return None
    # Local interaction input may deliberately remain TEMPORARY. Its accepted
    # INTERPRET request already binds the exact message/topic/recipient, without
    # retaining a second copy of the input solely for this feedback feature.
    proposals=[]
    for rid in (decision.get('context_fit') or {}).get('source_record_ids',()):
        head=store.one('continuity_records',rid)
        if (not head or head['record_kind']!='COGNITION_PROPOSAL' or head['scope']!=exchange['scope']
                or head['privacy_class']!=exchange['privacy_class'] or not records.current_support(rid)):continue
        reply=records.read(rid)['payload']['reply'];request=store.one('cognitive_requests',reply['request_id'])
        if not request or request['state']!='PROPOSED':continue
        head=store.one('continuity_records',request['record_id'])
        if (not head or head['scope']!=exchange['scope'] or head['privacy_class']!=exchange['privacy_class']
                or not records.current_support(head['record_id'])):continue
        body=records.read(head['record_id'])['payload']['request'];dialogue=body.get('role_input',{}).get('dialogue',{})
        if (body['cognitive_role']=='INTERPRET' and dialogue.get('message_memory_id')==data['user_memory_id']
                and dialogue.get('topic')==data['topic']):proposals.append(dialogue)
    if len(proposals)!=1:return None
    recipient=proposals[0].get('recipient_context')
    return {'cycle_record_id':cycle['record_id'],'reviewed_choice':CommunicationChoice.model_validate_json(canonical(choice)).model_dump(mode='json'),
        'entity_id':data['entity_id'],'topic':data['topic'],'recipient_context':recipient}


def communication_feedback(store, *, scope, entity_id, topic, recipient_context, privacy):
    """Latest exact-conversation explicit opinion; not an effectiveness verdict.

    The existing target index avoids scanning general reviews. No fallback to an
    older opinion after withdrawal/withholding, and no raw feedback/private text.
    """
    if not privacy or store.schema_target<13:return None
    from .subject.context_fit import communication_strategy_projection
    strategy=communication_strategy_projection(store,scope=scope,entity_id=entity_id,topic=topic,
        recipient_context=recipient_context,privacy_classes=privacy)
    if strategy is None:return None
    key=communication_feedback_key(store,scope,entity_id,topic,recipient_context)
    head=store.db.execute("SELECT * FROM continuity_records WHERE record_kind='ASSERTION' AND scope=? AND target_id=? ORDER BY created_at_us DESC,rowid DESC LIMIT 1",(scope,key)).fetchone()
    if not head or head['lifecycle']!='ACTIVE' or head['privacy_class'] not in privacy:return None
    records=RecordService(store)
    if not records.current_support(head['record_id']):return None
    ref=records.read(head['record_id'])['payload'];rid=ref['review_record_id'];review=store.one('continuity_records',rid)
    if not review or review['scope']!=scope or review['privacy_class'] not in privacy or not records.current_support(rid):return None
    row=records.read(rid)['payload'];sample=row['sample'];binding=row['communication_attribution'];delivery=row.get('delivery_attribution')
    if (binding['reviewed_choice']!=strategy['choice'] or sample['observed_at_us']<strategy['created_at_us']
            or sample['observed_at_us']>=strategy['expires_at_us']):return None
    return {'record_id':head['record_id'],'review_record_id':rid,'reviewed_choice':binding['reviewed_choice'],
        'human_judgment':sample['human_judgment'],'reason_tags':sample['reason_tags'],'provenance':sample['provenance'],
        'observed_at_us':sample['observed_at_us'],'delivery_state':delivery['state'] if delivery else 'NOT_PROVEN',
        'delivery_origin':delivery['origin'] if delivery else None,'human_read_proven':False,
        'effect_status':'NOT_EVALUATED_NO_EFFECT_INFERRED','semantics':'EXPLICIT_OPINION_RECONSIDER_NOT_A_COMMAND',
        'execution_authority':False}


def selected_communication_feedback(store, record_ids, *, scope, entity_id, privacy):
    """Only original C's selected current references may reveal an opinion excerpt.

    No conversation body, public-context search or fallback after withdrawal.
    Each block competes in the existing complete-request context budget.
    """
    records=RecordService(store);result=[]
    for rid in dict.fromkeys(record_ids):
        head=store.one('continuity_records',rid)
        if (not head or head['record_kind']!='ASSERTION' or head['scope']!=scope
                or head['privacy_class'] not in privacy or head['lifecycle']!='ACTIVE'
                or not head['target_id'] or not head['target_id'].startswith('communication-feedback.')
                or not records.current_support(rid)):continue
        reference=records.read(rid)['payload']
        if reference.get('person_kind')!='COMMUNICATION_FEEDBACK_REFERENCE':continue
        review=store.one('continuity_records',reference['review_record_id'])
        if (not review or review['scope']!=scope or review['privacy_class'] not in privacy
                or review['lifecycle']!='ACTIVE' or not records.current_support(review['record_id'])):continue
        payload=records.read(review['record_id'])['payload'];binding=payload.get('communication_attribution')
        if not binding or binding['entity_id']!=entity_id:continue
        opinion=communication_feedback(store,scope=scope,entity_id=entity_id,topic=binding['topic'],
            recipient_context=binding['recipient_context'],privacy=privacy)
        if not opinion or opinion['record_id']!=rid or opinion['review_record_id']!=review['record_id']:continue
        text=payload['sample']['exact_feedback']
        result.append({**opinion,'exact_feedback_excerpt':text[:384],'feedback_truncated':len(text)>384,
            'quotation_semantics':'DECLARED_OPINION_NOT_FACT_OR_INSTRUCTION'})
    return tuple(result)


class LanguageService:
    def __init__(self, store, authority):
        from ..actions import OperatorAuthority
        if not isinstance(authority, OperatorAuthority):
            raise CoreError('OPERATOR_AUTHORITY_REQUIRED')
        self.store, self._authority, self.records = store, authority, RecordService(store)

    def record(self, sample, *, scope, entity_id, privacy, authority, exchange_record_id=None, request_digest=None, response_sha256=None):
        if authority is not self._authority or type(sample) is not LanguageSample:
            raise CoreError('LANGUAGE_REVIEW_AUTHORITY_REQUIRED')
        if request_digest is not None and (type(request_digest) is not str or len(request_digest)!=64 or any(c not in '0123456789abcdef' for c in request_digest)):
            raise CoreError('LANGUAGE_REVIEW_REQUEST_DIGEST_INVALID')
        if sample.observed_at_us > self.store.clock.utc_now_us():
            raise CoreError('LANGUAGE_REVIEW_TIME_INVALID')
        if not exchange_record_id and sample.body_storage!='SOURCE_REPORT':raise CoreError('LANGUAGE_REVIEW_BINDING_REQUIRED')
        if response_sha256 is not None and not exchange_record_id:raise CoreError('LANGUAGE_REVIEW_BINDING_REQUIRED')
        if sample.memory_use is not None and (not exchange_record_id or sample.provenance!='USER_PROVIDED_REVIEW' or sample.human_judgment=='UNREVIEWED'):
            raise CoreError('MEMORY_USE_REVIEW_BINDING_REQUIRED')
        if exchange_record_id:sample=sample.model_copy(update={'body_storage':'DEPENDENT_RECORD'})
        use=sample.memory_use
        # Old binaries strictly parse the sample and evidence. Keep those
        # bodies unchanged; optional use feedback lives in the same generic
        # dependency-bound record envelope, which old readers already ignore.
        stored_sample=sample.model_copy(update={'memory_use':None})
        old = self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='language.review' AND source_key=?", (sample.sample_id,)).fetchone()
        if old:
            rid = json.loads(old[0])['data']['record_id']
            existing = self.records.read(rid)
            if (existing['scope'] != scope or existing['payload']['sample'] != stored_sample.model_dump(mode='json')
                    or existing['payload'].get('memory_use_feedback') != (use.model_dump(mode='json') if use else None)
                    or existing['payload'].get('response_sha256') != response_sha256
                    or existing['payload'].get('request_digest') != request_digest):
                raise CoreError('LANGUAGE_REVIEW_COLLISION')
            if not self.records.current_support(rid):
                raise CoreError('LANGUAGE_REVIEW_SOURCE_WITHDRAWN')
            return rid
        parents = ();delivery=None;communication=None
        if exchange_record_id:
            exchange = self.records.read(exchange_record_id)
            if exchange['payload'].get('person_kind') != 'CONVERSATION_EXCHANGE' or exchange['scope'] != scope or exchange['payload']['entity_id'] != entity_id or sample.review_target != exchange_record_id or not response_matches(sample, exchange['payload']['assistant_utterance'], response_sha256):
                raise CoreError('LANGUAGE_REVIEW_TURN_MISMATCH')
            if sample.observed_at_us < exchange['payload']['as_of_us']:
                raise CoreError('LANGUAGE_REVIEW_TIME_INVALID')
            parents = (exchange_record_id,)
            delivery=delivery_for_exchange(self.records,exchange,observed_at_us=sample.observed_at_us)
            if sample.human_judgment!='UNREVIEWED':communication=communication_for_exchange(self.records,exchange)
            if delivery:
                parents=(*parents,delivery['receipt_record_id'],delivery['verification_record_id'])
            if sample.memory_use is not None:
                mid=sample.memory_use.memory_id
                if not self.records.current_support(exchange_record_id) or mid not in self.records.support(exchange_record_id):
                    raise CoreError('MEMORY_USE_REVIEW_SOURCE_MISMATCH')
                target=self.records.memory.read(mid)
                if target['entity_id']!=entity_id or target['scope']!=scope:
                    raise CoreError('MEMORY_USE_REVIEW_SOURCE_MISMATCH')
            from .memory import PRIVACY_RANK
            privacy=max((privacy,exchange['privacy_class']),key=PRIVACY_RANK.get)
        memory = self.records.memory
        inherited=tuple(dict.fromkeys(m for rid in parents for m in self.records.support(rid)))
        if len(inherited)>64:raise CoreError('LANGUAGE_REVIEW_SOURCE_BOUND')
        report=source_report(stored_sample)
        eid = memory.capture(EvidenceInput(provenance=Provenance(domain='CONSENTED_INTERACTION',source_namespace='recorded.conversation.feedback', source_reference=sample.sample_id, source_kind='USER_STATEMENT'), text=report.model_dump_json(), privacy_class=privacy, retention_consent_ref=sample.sample_id, observed_time_us=sample.observed_at_us))
        mid = memory.add(MemoryCandidate(entity_id=entity_id, scope=scope, memory_type=MemoryType.EPISODIC, epistemic_kind='STATEMENT', source_evidence_id=eid, text=report.model_dump_json(),derived_from=inherited))
        data = {}
        with self.store.transaction('subject.language_review_recorded', data, source_namespace='language.review', source_key=sample.sample_id) as tx:
            payload={'person_kind':'LIVED_LANGUAGE_SAMPLE','sample': stored_sample.model_dump(mode='json'), 'not_subject_experience': sample.provenance == 'PROJECT_SYNTHETIC'}
            if delivery:payload['delivery_attribution']=delivery
            if communication:payload['communication_attribution']=communication
            if request_digest is not None:payload['request_digest']=request_digest
            if response_sha256 is not None:payload['response_sha256']=response_sha256
            if use:payload['memory_use_feedback']=use.model_dump(mode='json')
            rid = self.records.create(tx, kind='EXPERIENCE_CANDIDATE', scope=scope, target_id=sample.mode, payload=payload, memories=(mid,), records=parents)
            if use:
                self.records.create(tx,kind='ASSERTION',scope=scope,target_id='memory-use.'+use.memory_id,
                    payload={'person_kind':'MEMORY_USE_FEEDBACK_REFERENCE','review_record_id':rid,
                             'execution_authority':False,'changes_fact_credibility':False},records=(rid,))
            if communication:
                self.records.create(tx,kind='ASSERTION',scope=scope,
                    target_id=communication_feedback_key(self.store,scope,entity_id,communication['topic'],communication['recipient_context']),
                    payload={'person_kind':'COMMUNICATION_FEEDBACK_REFERENCE','review_record_id':rid,'execution_authority':False},records=(rid,))
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
    records = RecordService(store)
    samples = rows(store, 'LIVED_LANGUAGE_SAMPLE', scope, privacy, target=mode, limit=16)[:2]
    examples=[]
    for row in samples:
        item=row['payload']['sample']
        example={k:item[k][:384] if k in {'context','candidate_response','exact_feedback'} else item[k] for k in ('context','candidate_response','human_judgment','exact_feedback','reason_tags','provenance','provenance_reference')}
        if row['payload'].get('response_sha256') is not None:
            try:
                original=records.read(item['review_target'])['payload']['assistant_utterance']
                sample=LanguageSample.model_validate_json(canonical(item))
                if not response_matches(sample,original,row['payload']['response_sha256']):continue
            except (CoreError,ValueError,KeyError):continue
            example['candidate_response']=original[:384]
            example['candidate_response_truncated']=len(original)>384
        examples.append(example)
    return {'policy': policy, 'examples': examples,
            'examples_are_not_autobiography': True, 'human_naturalness_qualified': False,
            'source_record_ids': tuple(dict.fromkeys((*policy['source_record_ids'], *(r['record_id'] for r in samples))))}


def memory_use_guidance(store, *, entity_id, scope, privacy, memory_ids, recipient_context=None):
    """Bounded explicit user reports, advisory to C; never fact assessment.

    Selection targets only sources already chosen for this request. No automatic
    interpretation of silence, sentiment, generated drafts or delivery success.
    """
    wanted=set(memory_ids);seen=set();items=[];refs=[]
    records=RecordService(store)
    if not wanted:return {'items':(), 'source_record_ids':()}
    # Original indexed generic records preserve a preference when unrelated
    # reviews grow; never rely on the last32 dialogue reviews to find it.
    if not privacy:return {'items':(), 'source_record_ids':()}
    targets=tuple('memory-use.'+mid for mid in sorted(wanted)[:128])
    # Interleave each selected memory's newest reviews. A frequently reviewed
    # memory must not evict every other selected memory from the bounded scan.
    heads=store.db.execute("SELECT record_id FROM (SELECT record_id, rowid AS sequence, "
        "row_number() OVER (PARTITION BY target_id ORDER BY rowid DESC) AS review_rank "
        "FROM continuity_records WHERE record_kind='ASSERTION' AND scope=? AND lifecycle='ACTIVE' AND target_id IN ("+
        ','.join('?' for _ in targets)+") AND privacy_class IN ("+','.join('?' for _ in privacy)+")) "
        "ORDER BY review_rank, sequence DESC LIMIT 256",(scope,*targets,*privacy)).fetchall()
    for head in heads:
        try:
            if not records.current_support(head['record_id']):continue
            reference=records.read(head['record_id'])['payload']
            if reference.get('person_kind')!='MEMORY_USE_FEEDBACK_REFERENCE':continue
            row=records.read(reference['review_record_id'])
        except CoreError:
            continue
        sample=LanguageSample.model_validate_json(canonical(row['payload']['sample']))
        raw_use=row['payload'].get('memory_use_feedback')
        use=MemoryUseFeedback.model_validate_json(canonical(raw_use)) if raw_use is not None else None
        if (use is None or use.memory_id not in wanted or use.memory_id in seen
                or sample.provenance!='USER_PROVIDED_REVIEW' or sample.human_judgment=='UNREVIEWED'
                or sample.body_storage!='DEPENDENT_RECORD'):continue
        try:exchange=records.read(sample.review_target)
        except CoreError:continue
        if (exchange['payload'].get('entity_id')!=entity_id or exchange['scope']!=scope
                or not records.current_support(exchange['record_id'])
                or use.memory_id not in records.support(exchange['record_id'])):continue
        delivery=row['payload'].get('delivery_attribution')
        # Delivery-qualified feedback belongs to its exact recipient context;
        # it is not a global preference for every other surface/contact.
        if delivery is not None and delivery.get('recipient_context')!=recipient_context:continue
        target=records.memory.read(use.memory_id)
        if target['entity_id']!=entity_id or target['scope']!=scope or target['privacy_class'] not in privacy:continue
        seen.add(use.memory_id);refs.append(row['record_id'])
        items.append({'memory_id':use.memory_id,'requested_mode':use.mode,
            'basis':'EXPLICIT_USER_REVIEW_NOT_DELIVERY_PROOF','fact_assessment_unchanged':True,
            'advisory_to_subject':True,'execution_authority':False})
        if len(items)==4:break
    return {'items':tuple(items),'source_record_ids':tuple(refs)}
