"""Source-backed, privacy-filtered SelfFrame and bounded model context.

No persisted plaintext context cache. Packages are derived snapshots and are
checked again immediately before a ModelPort call. A fixture tokenizer is not a
claim about any commercial model's actual tokenization or semantic ability.
"""
from collections import deque
import json
from typing import Literal, Protocol

from pydantic import Field, model_validator

from ..contracts import CoreError, DTO
from ..actions import OperatorAuthority
from ..storage import canonical, digest
from .commitments import CommitmentService, CommitmentState
from .identity import CanonicalIdentity, IdentityService
from .memory import MemoryService
from .projects import ProjectService, ProjectState
from .records import RecordService
from .relationships import RelationshipView, relationship_view


class ObservationCoverage(DTO):
    scope: str
    start_us: int = Field(ge=0)
    end_us: int = Field(ge=0)
    status: Literal["FULL", "PARTIAL", "UNKNOWN"]
    dropped_count: int = Field(default=0, ge=0)
    disconnected: bool = False

    @model_validator(mode="after")
    def consistent(self):
        if self.end_us < self.start_us or (self.status == "FULL" and (self.dropped_count or self.disconnected)):
            raise ValueError("coverage window/loss inconsistent")
        return self


def record_coverage(store, coverage: ObservationCoverage):
    # Coverage is a source assertion, not inferred from an empty event stream.
    with store.transaction("self.coverage_reported", coverage.model_dump()) as tx:
        return tx.event_id


class SelfFrame(DTO):
    schema_version: Literal[1] = 1
    identity: CanonicalIdentity
    relationship: RelationshipView
    active_commitments: tuple[CommitmentState, ...]
    active_projects: tuple[ProjectState, ...]
    self_memory_ids: tuple[str, ...]
    capabilities: tuple[str, ...]
    limitations: tuple[str, ...]
    state_token: str
    derived: Literal[True] = True


class ContextPolicy(DTO):
    policy_id: str = Field(min_length=1, max_length=96)
    allowed_scopes: tuple[str, ...] = Field(min_length=1, max_length=32)
    readable_privacy: tuple[Literal["PUBLIC", "PROJECT", "PERSONAL", "SECRET"], ...]
    remote_privacy: tuple[Literal["PUBLIC", "PROJECT", "PERSONAL"], ...] = ()


class ContextRequest(DTO):
    schema_version: Literal[1] = 1
    entity_id: str
    scopes: tuple[str, ...] = Field(min_length=1, max_length=32)
    task_class: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    task: str = Field(min_length=1, max_length=4096)
    task_privacy_class: Literal["PUBLIC", "PROJECT", "PERSONAL", "SECRET"] = "PERSONAL"
    query_terms: tuple[str, ...] = Field(default=(), max_length=32)
    destination: Literal["LOCAL_FIXTURE", "DEVELOPMENT_REMOTE"] = "LOCAL_FIXTURE"
    max_input_tokens: int = Field(default=12000, ge=256, le=131072)
    output_reserve_tokens: int = Field(default=512, ge=0, le=16384)


class ContextBlock(DTO):
    block_id: str
    kind: str
    data_json: str
    source_memory_ids: tuple[str, ...] = ()
    source_record_ids: tuple[str, ...] = ()
    source_evidence_ids: tuple[str, ...] = ()
    source_event_ids: tuple[str, ...] = ()


class ContextManifest(DTO):
    schema_version: Literal[1] = 1
    identity_id: str
    identity_revision: int
    state_token: str
    event_cutoff: int
    as_of_us: int
    policy_digest: str
    request_digest: str
    coverage: tuple[ObservationCoverage, ...]
    selected_ids: tuple[str, ...]
    omitted_ids: tuple[str, ...]
    omitted_total:int=0
    omitted_tail_digest:str|None=None
    conflicts: tuple[str, ...]
    counter: str
    input_tokens: int
    input_limit: int
    retrieval_candidate_count: int
    retrieval_total_visible: int


class ContextPackage(DTO):
    manifest: ContextManifest
    blocks: tuple[ContextBlock, ...]
    content_digest: str


class TokenCounter(Protocol):
    descriptor: str
    def count(self, text: str) -> int: ...


class ConservativeCounter:
    descriptor = "UTF8_BYTE_ESTIMATE_v1_NOT_PROVIDER_TOKENIZER"

    def count(self, text):
        # One byte per token is deliberately conservative for engineering
        # fixtures. A real adapter must supply its actual framing/token counter.
        return len(text.encode("utf-8"))


from .revision import state_token


def _visible(store, row, scopes, privacy_classes):
    record = store.one("continuity_records", row["record_id"])
    return record["lifecycle"] == "ACTIVE" and record["scope"] in scopes and record["privacy_class"] in privacy_classes


def self_frame(store, authority, *, entity_id, scopes, privacy_classes, capabilities=(), limitations=()):
    identity = IdentityService(store, authority).current()
    token = state_token(store)
    commitments, projects = CommitmentService(store, authority), ProjectService(store, authority)
    frame = SelfFrame(identity=identity,
        relationship=relationship_view(store, entity_id, scopes=scopes, privacy_classes=privacy_classes),
        active_commitments=tuple(commitments.get(r["commitment_id"]) for r in store.all("commitments")
            if r["entity_id"] == entity_id and r["state"] in {"ADOPTED", "ACTIVE"}
            and _visible(store, r, scopes, privacy_classes)),
        active_projects=tuple(projects.get(r["project_id"]) for r in store.all("projects")
            if r["entity_id"] == entity_id and r["state"] in {"ACTIVE", "PAUSED"}
            and _visible(store, r, scopes, privacy_classes)),
        self_memory_ids=tuple(r["memory_id"] for r in MemoryService(store).query(
            entity_ids=(identity.identity_id,), scopes=scopes,
            privacy_classes=privacy_classes, memory_types=("SELF",))),
        capabilities=tuple(capabilities), limitations=tuple(limitations), state_token=token)
    if state_token(store) != token:
        raise CoreError("STATE_CHANGED_DURING_PROJECTION")
    return frame


class ContextAssembler:
    def __init__(self, store, authority, *, counter=None, project_state_source=None):
        if not isinstance(authority, OperatorAuthority):
            raise CoreError("OPERATOR_AUTHORITY_REQUIRED")
        self.store, self.authority = store, authority
        from .current_state import ProjectStateSource
        if project_state_source is not None and type(project_state_source) is not ProjectStateSource:raise CoreError("PROJECT_STATE_BINDING_REQUIRED")
        self.project_state_source=project_state_source
        self.counter = counter or ConservativeCounter()
        self._issued = deque(maxlen=64)  # hashes only, never a plaintext context cache

    def assemble(self, request: ContextRequest, policy: ContextPolicy, *, capabilities=(), limitations=(), subject_frame=None, required_memory_ids=(), source_only=False, pinned_only=False, require_current_state=False, conversation_topic=None):
        if not set(request.scopes) <= set(policy.allowed_scopes):
            raise CoreError("CONTEXT_SCOPE_DENIED")
        privacy = tuple(p for p in policy.readable_privacy if request.destination == "LOCAL_FIXTURE" or p in policy.remote_privacy)
        if conversation_topic is not None:
            from .memory import PRIVACY_RANK
            privacy=tuple(p for p in privacy if PRIVACY_RANK[p]<=PRIVACY_RANK[request.task_privacy_class])
        if request.task_privacy_class not in privacy:
            raise CoreError("CONTEXT_TASK_PRIVACY_DENIED")
        frame = self_frame(self.store, self.authority, entity_id=request.entity_id,
            scopes=request.scopes, privacy_classes=privacy, capabilities=capabilities, limitations=limitations)
        memory_service = MemoryService(self.store)
        memory_query = dict(scopes=request.scopes, privacy_classes=privacy,
            entity_ids=(request.entity_id, frame.identity.identity_id), include_conflicts=True)
        # Pinned dialogue discards unrelated raw-memory blocks below anyway.
        # Fetch its explicit sources/notes only; self/relationship/lessons still
        # use their original independent sourced projections.
        memories = [] if pinned_only else memory_service.query(**memory_query, query_terms=request.query_terms)
        note_ids=set();note_strategy_refs=();recall_gap=None
        note_terms=tuple(t for t in request.query_terms if 2<=len(t)<=64)[:8]
        if pinned_only and conversation_topic is not None and note_terms:
            try:
                notes=memory_service.literal_notes(entity_ids=(request.entity_id,),scopes=request.scopes,
                    privacy_classes=privacy,terms=note_terms)
                if not notes and 'PROJECT' in privacy:
                    from .retrieval_growth import NoteRetrievalEvaluator, qualified_method, word_queries
                    if word_queries(note_terms):
                        for scope in request.scopes:
                            selected=qualified_method(self.store,self.authority,request.entity_id,scope,privacy)
                            if selected:
                                evaluator=NoteRetrievalEvaluator(self.store,request.entity_id,request.scopes,privacy)
                                snapshot=evaluator.snapshot(scope)
                                notes=evaluator.lookup(selected[1],note_terms,snapshot)
                                if notes:
                                    note_strategy_refs=(selected[0],)
                                    break
                note_ids={m['memory_id'] for m in notes}
                memories.extend(m for m in notes if not any(old['memory_id']==m['memory_id'] for old in memories))
            except CoreError as exc:
                if exc.code not in {'NOTE_RECALL_TIME_BOUND','NOTE_RECALL_SAFE_POINT_REQUIRED','NOTE_RECALL_INDEX_DEFINITION_MISMATCH','NOTE_STRATEGY_SCOPE_BOUND'}:raise
                recall_gap=exc.code+'_NO_ABSENCE_CLAIM'
        if len(required_memory_ids)>16:raise CoreError('CONTEXT_REQUIRED_SOURCE_BOUND')
        for mid in required_memory_ids:
            head=self.store.one('memories',mid)
            if not head or head['scope'] not in request.scopes or head['privacy_class'] not in privacy or head['entity_id'] not in {request.entity_id,frame.identity.identity_id}:
                raise CoreError('CONTEXT_REQUIRED_SOURCE_DENIED')
            row=memory_service.read(mid)
            if not any(m['memory_id']==mid for m in memories):memories.append(row)
        retrieval_total = memory_service.query_count(**memory_query)
        self._retrieval = (len(memories), retrieval_total)
        coverage = self._coverage(request.scopes)
        candidates = []
        self_fallbacks = {}
        mandatory = [ContextBlock(block_id="identity", kind="IDENTITY",
            data_json=frame.identity.model_dump_json(),
            source_event_ids=(self.store.all("identity_revisions")[-1]["event_id"],)),
            ContextBlock(block_id="task", kind="TASK_CONSTRAINTS", data_json=canonical({
                "task": request.task, "task_class": request.task_class, "capabilities": frame.capabilities,
                "limitations": frame.limitations, "execution_authority": "NONE", "context_is_derived": True}))]
        current=None
        if self.project_state_source is not None:
            current=self.project_state_source.projection(scopes=request.scopes,privacy_classes=privacy,now_us=self.store.clock.utc_now_us())
        if require_current_state and current is None:raise CoreError('PROJECT_CURRENT_STATE_NOT_BOUND_OR_DENIED')
        if current is not None:
            block=ContextBlock(block_id='project-current-state',kind='PROJECT_CURRENT_STATE',data_json=canonical(current))
            if require_current_state:mandatory.append(block)
            else:candidates.append((950.0,block))
        if subject_frame is not None:
            from .subject.contracts import DeliberationFrame
            if not isinstance(subject_frame, DeliberationFrame) or subject_frame.scope not in request.scopes:
                raise CoreError("INVALID_SUBJECT_DELIBERATION_FRAME")
            source = self.store.one("subject_events", subject_frame.subject_event_id)
            if not source or source["scope"] != subject_frame.scope:
                raise CoreError("INVALID_SUBJECT_DELIBERATION_SOURCE")
            for mid in subject_frame.source_memory_ids:
                row = self.store.one("memories", mid)
                if not row or row["scope"] not in request.scopes or row["privacy_class"] not in privacy:
                    raise CoreError("SUBJECT_FRAME_PRIVACY_DENIED")
                memory_service.read(mid)
            for rid in subject_frame.source_record_ids:
                row = self.store.one("continuity_records", rid)
                if not row or row["scope"] not in request.scopes or row["privacy_class"] not in privacy:
                    raise CoreError("SUBJECT_FRAME_PRIVACY_DENIED")
                RecordService(self.store).read(rid)
            mandatory.append(ContextBlock(block_id="subject-deliberation",kind="SUBJECT_APPRAISAL",
                data_json=subject_frame.model_dump_json(), source_memory_ids=subject_frame.source_memory_ids,
                source_record_ids=subject_frame.source_record_ids))
        # No duplicate relationship prose; it is supplied as individual memory blocks.
        candidates.append((900.0, ContextBlock(block_id="relationship", kind="RELATIONSHIP_LINKS", data_json=canonical({
            "entity_id": frame.relationship.entity_id,
            "adopted_commitment_ids": frame.relationship.adopted_commitment_ids,
            "shared_project_ids": frame.relationship.shared_project_ids}))))
        for promise in frame.active_commitments:
            row = self.store.one("commitments", promise.commitment_id)
            data = promise.model_dump(mode="json") if promise.support_current else {
                "commitment_id": promise.commitment_id, "state": promise.state, "support": "REQUIRES_REVIEW"}
            candidates.append((1000.0, ContextBlock(block_id="commitment:" + promise.commitment_id,
                kind="COMMITMENT", data_json=canonical(data), source_memory_ids=promise.source_memory_ids,
                source_record_ids=(row["record_id"],))))
        for project in frame.active_projects:
            row = self.store.one("projects", project.project_id)
            data = project.model_dump(mode="json") if project.support_current else {
                "project_id": project.project_id, "state": project.state, "support": "REQUIRES_REVIEW"}
            candidates.append((800.0, ContextBlock(block_id="project:" + project.project_id,
                kind="PROJECT", data_json=canonical(data), source_memory_ids=project.source_memory_ids,
                source_record_ids=(row["record_id"],))))
        conflicts = {}
        now = self.store.clock.utc_now_us()
        for row in memories:
            if row["assessment"] == "DISPUTED":
                family = canonical([row["entity_id"], row["scope"], row["predicate_key"]])
                if family not in conflicts:
                    conflicts[family] = memory_service.conflict_bundle(row, privacy)
                continue
            text = row["text"].casefold()
            relevance = sum(t.casefold() in text for t in request.query_terms)
            occurrence = row["event_time_us"] if row["event_time_us"] is not None else row["ingested_time_us"]
            age_days = max(0, now - occurrence) / 86_400_000_000
            score = (100 if row["authority"] == "DIRECT" else 10) + 200 * relevance
            score += 100 * row["importance"] + 50 * row["significance"] + 20 / (1 + age_days)
            # Explicit task-relevant evidence must survive optional generic
            # projections at scale. Identity/required sources remain mandatory;
            # retrieval rank never changes memory truth or execution authority.
            if relevance:score += 1000
            if row["memory_type"] == "SELF":
                score += 50
            if row['memory_id'] in note_ids and row['memory_id'] not in required_memory_ids:
                # Keep person-self and established language policy ahead of
                # optional lookup, while questions outrank generic projections.
                score=975.0
            block = ContextBlock(block_id="memory:" + row["memory_id"], kind="MEMORY",
                data_json=canonical({k: row[k] for k in ("memory_id", "memory_type", "epistemic_kind", "text",
                    "assessment", "confidence", "authority", "event_time_us", "observed_time_us", "ingested_time_us")}),
                source_memory_ids=(row["memory_id"],), source_event_ids=(row["event_id"],))
            block = block.model_copy(update={"source_evidence_ids": (row["source_evidence_id"],)})
            if row['memory_id'] in note_ids:
                block=block.model_copy(update={'data_json':canonical({**json.loads(block.data_json),
                    'provenance':'EXPLICIT_USER_NOTE_NOT_VERIFIED_WORLD_FACT',
                    'nana_lived_experience':False,'execution_authority':'NONE'}),
                    'source_record_ids':note_strategy_refs})
            candidates.append((score, block))
        # Disputes are whole bundles; never keep one side because of token limits.
        for key, rows in conflicts.items():
            candidates.append((1100.0, ContextBlock(block_id="conflict:" + digest(key), kind="UNRESOLVED_CONFLICT",
                data_json=canonical({"assessment": "DISPUTED", "claims": [
                    {k: row[k] for k in ("memory_id", "text", "event_time_us", "authority", "confidence")} for row in rows]}),
                source_memory_ids=tuple(r["memory_id"] for r in rows))))
        # Persistent Self is another derived block in this SAME context builder.
        # Only scopes with accepted subject events participate; legacy callers and
        # default v1 runtime remain unchanged. Filter privacy before projection.
        if "subject_events" in self.store.keys:
            from .subject.projections import Environment, project_self
            for scope in request.scopes:
                if not self.store.db.execute("SELECT 1 FROM subject_events WHERE scope=? LIMIT 1", (scope,)).fetchone():
                    continue
                living, personality, relation = project_self(self.store, entity_id=request.entity_id,
                    scope=scope, privacy_classes=privacy,
                    environment=Environment(capabilities=tuple(capabilities)))
                candidates.append((925.0, ContextBlock(block_id="persistent-self:" + scope, kind="PERSISTENT_SELF",
                    data_json=canonical({"living": living.model_dump(mode="json"),
                        "personality": personality.model_dump(mode="json"), "relationship": relation}),
                    source_record_ids=living.source_record_ids, source_memory_ids=living.source_memory_ids)))
        # Future lessons are selected by exact task scope, never arbitrary global advice.
        if self.store.schema_target>=9:
            from .autonomy.relationships import relationship_influence
            from .autonomy.governance import manager_views
            for scope in request.scopes:
                influence=relationship_influence(self.store,request.entity_id,scope=scope,privacy_classes=privacy)
                outcomes=manager_views(self.store,scope=scope,privacy_classes=privacy)
                refs=tuple(dict.fromkeys((*influence.source_record_ids,*(o['record_id'] for o in outcomes))))
                candidates.append((930.0,ContextBlock(block_id='subject-influence:'+scope,kind='SUBJECT_INFLUENCE',
                    data_json=canonical({'relationship':influence.model_dump(mode='json'),'manager_outcomes':outcomes,
                        'governance_is_external_fact_not_normative_directive':True,'execution_authority':'NONE'}),
                    source_record_ids=refs,source_memory_ids=tuple(sorted({m for rid in refs for m in RecordService(self.store).support(rid)})))))
        if self.store.schema_target>=10:
            from .relational.bootstrap import anchor_view
            from .relational.projections import personality_tendencies,social_appetite,self_narrative
            for scope in request.scopes:
                anchor=anchor_view(self.store,request.entity_id,scope=scope,privacy_classes=privacy)
                tendency=personality_tendencies(self.store,scope=scope,privacy_classes=privacy,entity_id=request.entity_id)
                appetite=social_appetite(self.store,scope=scope,privacy_classes=privacy)
                narrative=self_narrative(self.store,scope=scope,privacy_classes=privacy,entity_id=request.entity_id)
                refs=tuple(dict.fromkeys((*tendency.source_record_ids,*appetite.source_record_ids,*((anchor.source_record_id,) if anchor else ()))))
                data={'anchor':anchor.model_dump(mode='json') if anchor else None,'personality':tendency.model_dump(mode='json'),
                    'social_appetite':appetite.model_dump(mode='json'),'self_narrative':narrative.model_dump(mode='json'),'execution_authority':'NONE'}
                previous=self.store.db.execute('SELECT c.* FROM subject_cycles c JOIN subject_events e ON e.subject_event_id=c.subject_event_id WHERE e.entity_id=? AND e.scope=? ORDER BY c.revision DESC LIMIT 1',(request.entity_id,scope)).fetchone()
                if previous and previous['record_id']:
                    h=self.store.one('continuity_records',previous['record_id'])
                    if h['lifecycle']=='ACTIVE' and h['privacy_class'] in privacy and RecordService(self.store).current_support(h['record_id']):
                        past=RecordService(self.store).read(h['record_id'])['payload'].get('relational_decision')
                        if past:
                            data['historical_tradeoff_not_current_policy']=past;refs=(*refs,h['record_id'])
                candidates.append((935.0,ContextBlock(block_id='relational-subject:'+scope,kind='RELATIONAL_SUBJECT',data_json=canonical(data),source_record_ids=refs,
                    source_memory_ids=tuple(sorted({*appetite.source_memory_ids,*(m for rid in refs for m in RecordService(self.store).support(rid))})))))
        if self.store.schema_target>=13:
            from .world_loop.world import WorldModel
            records=RecordService(self.store)
            for view in WorldModel(self.store,scopes=request.scopes,privacy_classes=privacy).snapshot(limit=16):
                candidates.append((945.0,ContextBlock(block_id='world:'+digest([view.entity_id,view.predicate]),kind='WORLD_BELIEF',data_json=view.model_dump_json(),source_record_ids=view.support_records,source_memory_ids=tuple(sorted({m for rid in view.support_records for m in records.support(rid)})))))
        if self.store.schema_target>=13:
            from .autonomy.private_intent import metadata as private_metadata
            for scope in request.scopes:
                values=private_metadata(self.store,scope,privacy)[:2]
                if values:
                    # Recipient expression may know a private activity exists,
                    # never its purpose/content, even when data privacy is PUBLIC.
                    safe=[{k:v[k] for k in ('category','status','disclosure_policy','risk_class','authority_need','external_effect','execution_authority')} for v in values]
                    candidates.append((936.0,ContextBlock(block_id='private-intent-state:'+scope,kind='PRIVATE_INTENT_STATE',data_json=canonical({'activities':safe,'content_withheld':True,'delivery_authority':False}),source_record_ids=tuple(v['record_id'] for v in values),source_memory_ids=tuple(sorted({m for v in values for m in v['source_memory_ids']})))))
        if conversation_topic is not None and self.store.schema_target>=13:
            from .person_self import project, compact, stable_core
            for scope in request.scopes:
                person=project(self.store,entity_id=request.entity_id,scope=scope,privacy=privacy,topic=conversation_topic)
                candidates.append((980.0,ContextBlock(block_id='person-self:'+scope,kind='PERSON_SELF',
                    data_json=canonical(compact(person)),source_record_ids=person['source_record_ids'],source_memory_ids=person['source_memory_ids'])))
                refs=person['stable_source_record_ids']
                self_fallbacks['person-self:'+scope]=ContextBlock(block_id='person-self:'+scope,kind='PERSON_SELF',data_json=canonical(stable_core(person)),source_record_ids=refs,source_memory_ids=tuple(sorted({m for rid in refs for m in RecordService(self.store).support(rid)})))
        if conversation_topic is not None and self.store.schema_target>=13:
            from .lived_language import context as language_context
            for scope in request.scopes:
                language=language_context(self.store,scope=scope,privacy=privacy,mode='PROJECT' if require_current_state or conversation_topic in {'project','technical'} else 'CASUAL')
                refs=language['policy']['source_record_ids']
                if refs:
                    candidates.append((979.0,ContextBlock(block_id='lived-language:'+scope,kind='LIVED_LANGUAGE',data_json=canonical({'policy':language['policy'],'examples_are_not_autobiography':True}),source_record_ids=refs,source_memory_ids=tuple(sorted({m for rid in refs for m in RecordService(self.store).support(rid)})))))
                if language['examples']:
                    refs=language['source_record_ids']
                    candidates.append((500.0,ContextBlock(block_id='language-examples:'+scope,kind='LANGUAGE_EXAMPLES',data_json=canonical({'examples':language['examples'],'examples_are_not_autobiography':True}),source_record_ids=refs,source_memory_ids=tuple(sorted({m for rid in refs for m in RecordService(self.store).support(rid)})))))
        candidates.extend(self._lessons(request, privacy))
        if required_memory_ids:
            required=[block for _,block in candidates if block.kind in {'MEMORY','UNRESOLVED_CONFLICT'} and set(block.source_memory_ids)&set(required_memory_ids)]
            if not set(required_memory_ids)<={m for block in required for m in block.source_memory_ids}:raise CoreError('CONTEXT_REQUIRED_SOURCE_UNAVAILABLE')
            mandatory.extend(required)
        if pinned_only:
            # Dialogue gets explicit verified facts plus existing filtered self/
            # relation projections; never the whole unrelated source corpus.
            candidates=[(score,block) for score,block in candidates if (block.kind in {'MEMORY','UNRESOLVED_CONFLICT'} and set(block.source_memory_ids)&(set(required_memory_ids)|note_ids)) or block.kind in {'RELATIONSHIP_LINKS','SUBJECT_INFLUENCE','RELATIONAL_SUBJECT','PRIVATE_INTENT_STATE','PERSON_SELF','LIVED_LANGUAGE','LANGUAGE_EXAMPLES'}]
        if source_only:
            # Media processors receive only the pinned, policy-filtered source,
            # never unrelated relationship, project or memory context.
            candidates=[(score,block) for score,block in candidates if block.kind in {'MEMORY','UNRESOLVED_CONFLICT'} and set(block.source_memory_ids)&set(required_memory_ids)]
            def source_metadata(block):
                if block.kind not in {'MEMORY','UNRESOLVED_CONFLICT'}:return block
                body=json.loads(block.data_json)
                if block.kind=='MEMORY':body.pop('text',None)
                else:
                    for claim in body['claims']:claim.pop('text',None)
                body['content_routed_in_typed_parts']=True
                return block.model_copy(update={'data_json':canonical(body)})
            mandatory=[source_metadata(block) for block in mandatory]
            candidates=[(score,source_metadata(block)) for score,block in candidates]
        candidates.sort(key=lambda item: (-item[0], item[1].block_id))
        selected, omitted = list(mandatory), [recall_gap] if recall_gap else []
        if retrieval_total > len(memories):
            omitted.append("EXPLICIT_SOURCE_SELECTION" if pinned_only else "RETRIEVAL_CANDIDATE_LIMIT")
        conflict_ids = tuple(block.block_id for _, block in candidates if block.kind == "UNRESOLVED_CONFLICT")
        for _, block in candidates:
            if block.block_id in {x.block_id for x in selected}:
                continue
            proposed = self._package(frame, request, policy, coverage, selected + [block], omitted, conflict_ids)
            if proposed.manifest.input_tokens <= proposed.manifest.input_limit:
                selected.append(block)
            elif block.block_id in self_fallbacks:
                fallback=self_fallbacks[block.block_id]
                partial_omission=omitted+[block.block_id+':CURRENT_AND_LIVED_DETAIL']
                proposed=self._package(frame,request,policy,coverage,selected+[fallback],partial_omission,conflict_ids)
                if proposed.manifest.input_tokens<=proposed.manifest.input_limit:
                    selected.append(fallback);omitted=partial_omission
                else:omitted.append(block.block_id)
            else:
                omitted.append(block.block_id)
        package = self._package(frame, request, policy, coverage, selected, omitted, conflict_ids)
        # Omission metadata itself consumes budget; drop complete optional blocks
        # until the whole serialized input (not only prose) fits.
        while package.manifest.input_tokens > package.manifest.input_limit and len(selected) > len(mandatory):
            omitted.append(selected.pop().block_id)
            package = self._package(frame, request, policy, coverage, selected, omitted, conflict_ids)
        if package.manifest.input_tokens > package.manifest.input_limit:
            raise CoreError("INSUFFICIENT_CONTEXT_BUDGET")
        if any(c not in package.manifest.selected_ids for c in conflict_ids):
            raise CoreError("INSUFFICIENT_CONTRADICTION_CONTEXT")
        if state_token(self.store) != frame.state_token:
            raise CoreError("STATE_CHANGED_DURING_ASSEMBLY")
        self._issued.append(package.content_digest)
        return package

    def _lessons(self, request, privacy):
        from .learning import ExperienceService
        return ExperienceService(self.store, self.authority).context_blocks(request, privacy)

    def _coverage(self, scopes):
        by_scope = {}
        for row in self.store.db.execute("SELECT event_id,data_json FROM events WHERE kind='self.coverage_reported' ORDER BY seq"):
            body = json.loads(row["data_json"])["data"]
            if body["scope"] in scopes:
                by_scope[body["scope"]] = ObservationCoverage.model_validate(body)
        return tuple(by_scope.get(s, ObservationCoverage(scope=s, start_us=0,
            end_us=self.store.clock.utc_now_us(), status="UNKNOWN")) for s in scopes)

    def _package(self, frame, request, policy, coverage, selected, omitted, conflicts):
        manifest = ContextManifest(identity_id=frame.identity.identity_id, identity_revision=frame.identity.revision,
            state_token=frame.state_token,
            event_cutoff=self.store.db.execute("SELECT coalesce(max(seq),0) FROM events").fetchone()[0],
            as_of_us=self.store.clock.utc_now_us(), policy_digest=digest(policy.model_dump(mode="json")),
            request_digest=digest(request.model_dump(mode="json")), coverage=coverage,
            selected_ids=tuple(b.block_id for b in selected), omitted_ids=tuple(omitted[:16]),
            omitted_total=len(omitted),omitted_tail_digest=digest(omitted[16:]) if len(omitted)>16 else None,conflicts=conflicts,
            counter=self.counter.descriptor, input_tokens=0,
            input_limit=request.max_input_tokens - request.output_reserve_tokens,
            retrieval_candidate_count=self._retrieval[0], retrieval_total_visible=self._retrieval[1])
        package = ContextPackage(manifest=manifest, blocks=tuple(selected), content_digest="0" * 64)
        for _ in range(8):
            tokens = self.counter.count(package.model_dump_json())
            if tokens == package.manifest.input_tokens:
                break
            package = package.model_copy(update={"manifest": package.manifest.model_copy(update={"input_tokens": tokens})})
        payload = package.model_dump(mode="json", exclude={"content_digest"})
        return package.model_copy(update={"content_digest": digest(payload)})

    def validate(self, package, request, policy):
        if package.content_digest not in self._issued:
            raise CoreError("CONTEXT_NOT_ISSUED_BY_ASSEMBLER")
        if (package.manifest.state_token != state_token(self.store) or
                package.manifest.request_digest != digest(request.model_dump(mode="json")) or
                package.manifest.policy_digest != digest(policy.model_dump(mode="json"))):
            raise CoreError("STALE_CONTEXT")
        if package.content_digest != digest(package.model_dump(mode="json", exclude={"content_digest"})):
            raise CoreError("CONTEXT_TAMPERED")
        if self.counter.count(package.model_dump_json()) != package.manifest.input_tokens:
            raise CoreError("CONTEXT_TOKEN_MISMATCH")
        self.validate_project_state(package,request,policy)
        for block in package.blocks:
            for memory_id in block.source_memory_ids:
                row = self.store.one("memories", memory_id)
                if not row or row["lifecycle"] == "DELETED":
                    raise CoreError("CONTEXT_SOURCE_DELETED")

    def validate_project_state(self,package,request,policy):
        blocks=[b for b in package.blocks if b.kind=='PROJECT_CURRENT_STATE']
        if not blocks:return
        if len(blocks)!=1 or self.project_state_source is None:raise CoreError('PROJECT_CURRENT_STATE_NOT_BOUND_OR_DENIED')
        privacy=tuple(p for p in policy.readable_privacy if request.destination=='LOCAL_FIXTURE' or p in policy.remote_privacy)
        current=self.project_state_source.projection(scopes=request.scopes,privacy_classes=privacy,now_us=self.store.clock.utc_now_us())
        if current is None or canonical(current)!=blocks[0].data_json:raise CoreError('PROJECT_CURRENT_STATE_CHANGED')
