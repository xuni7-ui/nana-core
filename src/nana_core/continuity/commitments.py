"""Mention != promise; adoption is reviewed authority, fulfillment needs evidence."""
from typing import Literal

from pydantic import Field

from ..contracts import CoreError, DTO
from ..actions import OperatorAuthority
from ..storage import uid,digest
from .records import RecordService
from .recurrence import RecurrenceSpec
from .relational.contracts import VoluntaryTerms


class CommitmentCandidate(DTO):
    entity_id: str
    scope: str
    description: str = Field(min_length=1, max_length=2048)
    support_memory_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    due_at_us: int | None = Field(default=None, ge=0)
    recurrence: RecurrenceSpec | None = None
    voluntary: VoluntaryTerms | None = None
    decision_record_id: str | None = None


class CommitmentState(DTO):
    commitment_id: str
    revision: int
    state: Literal["PROPOSED", "ADOPTED", "ACTIVE", "FULFILLED", "CANCELLED", "FAILED", "SUPERSEDED"]
    description: str
    due_at_us: int | None
    overdue: bool
    source_memory_ids: tuple[str, ...]
    adoption_event_id: str | None
    support_current: bool


class AdoptedCommitment(CommitmentState):
    state: Literal["ADOPTED", "ACTIVE", "FULFILLED", "CANCELLED", "FAILED", "SUPERSEDED"]
    adoption_event_id: str


class FulfillmentCheck(DTO):
    """Produced by a trusted independent checker, not a conversational assertion."""
    check: Literal["COMMITMENT_FULFILLMENT"] = "COMMITMENT_FULFILLMENT"
    commitment_id: str
    commitment_revision: int = Field(ge=1)
    satisfied: bool
    result_reference: str = Field(min_length=1, max_length=128)


LEGAL = {"PROPOSED": {"ADOPTED", "CANCELLED"}, "ADOPTED": {"ACTIVE", "CANCELLED", "SUPERSEDED"},
         "ACTIVE": {"FULFILLED", "FAILED", "CANCELLED", "SUPERSEDED"}}


class CommitmentService:
    def __init__(self, store, authority):
        if not isinstance(authority, OperatorAuthority):
            raise CoreError("OPERATOR_AUTHORITY_REQUIRED")
        self.store, self._authority = store, authority
        self.records = RecordService(store)

    def propose(self, candidate: CommitmentCandidate, *, source_key=None):
        if (candidate.voluntary or candidate.decision_record_id) and self.store.schema_target<10:raise CoreError('RELATIONAL_SCHEMA_REQUIRED')
        if candidate.voluntary and candidate.recurrence:raise CoreError('VOLUNTARY_CALENDAR_NOT_ALLOWED')
        if candidate.recurrence and self.store.schema_target<9:raise CoreError('AUTONOMY_SCHEMA_REQUIRED')
        if source_key:
            import json
            old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='commitment.request' AND source_key=?",(source_key,)).fetchone()
            if old:
                data=json.loads(old[0])['data']
                if data['candidate_digest']!=digest(candidate.model_dump(mode='json')):raise CoreError('COMMITMENT_REQUEST_COLLISION')
                return data['commitment_id']
        if not self.store.one("entities", candidate.entity_id):
            raise CoreError("ENTITY_BINDING_REQUIRED")
        now, commitment_id = self.store.clock.utc_now_us(), uid()
        data={'commitment_id':commitment_id,'candidate_digest':digest(candidate.model_dump(mode='json'))} if source_key else None
        with self.store.transaction("commitment.proposed",data,source_namespace='commitment.request' if source_key else None,source_key=source_key) as tx:
            record_id = self.records.create(tx, kind="COMMITMENT", scope=candidate.scope,
                records=(candidate.decision_record_id,) if candidate.decision_record_id else (),
                payload={"description": candidate.description,**({'voluntary':candidate.voluntary.model_dump(mode='json')} if candidate.voluntary else {}),**({'recurrence':candidate.recurrence.model_dump(mode='json')} if candidate.recurrence else {})}, memories=candidate.support_memory_ids)
            tx.put("commitments", {"commitment_id": commitment_id, "entity_id": candidate.entity_id,
                "scope": candidate.scope, "record_id": record_id, "revision": 1, "state": "PROPOSED",
                "due_at_us": candidate.due_at_us, "adoption_event_id": None, "fulfillment_memory_id": None,
                "superseded_by": None, "created_at_us": now, "updated_at_us": now})
        return commitment_id

    def transition(self, commitment_id, state, *, expected_revision, authority,
                   fulfillment_memory_id=None, superseded_by=None):
        if authority is not self._authority:
            raise CoreError("UNAUTHENTICATED_OPERATOR")
        with self.store.transaction("commitment.transitioned") as tx:
            row = self.store.one("commitments", commitment_id)
            if not row or type(expected_revision) is not int or row["revision"] != expected_revision:
                raise CoreError("STALE_COMMITMENT_REVISION")
            self.records.read(row["record_id"])
            if state not in LEGAL.get(row["state"], set()):
                raise CoreError("ILLEGAL_COMMITMENT_TRANSITION")
            if state in {"ADOPTED", "ACTIVE", "FULFILLED"} and not self.records.current_support(row["record_id"]):
                raise CoreError("COMMITMENT_SUPPORT_REQUIRES_REVIEW")
            if state == "FULFILLED":
                if not fulfillment_memory_id:
                    raise CoreError("INDEPENDENT_FULFILLMENT_EVIDENCE_REQUIRED")
                proof = self.records.memory.read(fulfillment_memory_id)
                source = self.records.memory.evidence(proof["source_evidence_id"])
                if (source["source_kind"] != "SYSTEM_VERIFICATION" or proof["scope"] != row["scope"]
                        or proof["epistemic_kind"] != "OBSERVATION"):
                    raise CoreError("INDEPENDENT_FULFILLMENT_EVIDENCE_REQUIRED")
                check = FulfillmentCheck.model_validate_json(proof["text"])
                if (not check.satisfied or check.commitment_id != commitment_id or
                        check.commitment_revision != expected_revision):
                    raise CoreError("FULFILLMENT_TARGET_MISMATCH")
                # Erasing the fulfillment proof also invalidates this record.
                tx.put("record_dependencies", {"link_id": uid(), "record_id": row["record_id"],
                    "parent_kind": "MEMORY", "parent_id": fulfillment_memory_id, "relation_kind": "SUPPORT"})
            if state == "SUPERSEDED":
                replacement = self.store.one("commitments", superseded_by)
                if not replacement or replacement["entity_id"] != row["entity_id"] or replacement["state"] not in {"ADOPTED", "ACTIVE"}:
                    raise CoreError("ADOPTED_REPLACEMENT_REQUIRED")
            tx.update("commitments", commitment_id, state=state, revision=row["revision"] + 1,
                adoption_event_id=tx.event_id if state == "ADOPTED" else row["adoption_event_id"],
                fulfillment_memory_id=fulfillment_memory_id if state == "FULFILLED" else row["fulfillment_memory_id"],
                superseded_by=superseded_by if state == "SUPERSEDED" else None,
                updated_at_us=self.store.clock.utc_now_us())
        return self.get(commitment_id)

    def review_voluntary(self,cycle_id,*,authority):
        import json
        from ..storage import canonical
        from .relational.contracts import RelationalDecision
        if self.store.schema_target<10 or authority is not self._authority:raise CoreError('UNAUTHENTICATED_VOLUNTARY_REVIEW')
        cycle=self.store.db.execute('SELECT * FROM subject_cycles WHERE cycle_id=?',(cycle_id,)).fetchone()
        if not cycle or not self.records.current_support(cycle['record_id']):raise CoreError('VOLUNTARY_REVIEW_SOURCE_RETIRED')
        body=self.records.read(cycle['record_id'])['payload']
        decision=RelationalDecision.model_validate_json(canonical(body['relational_decision']))
        if decision.phase!='REVIEW' or not decision.review_choice:raise CoreError('VOLUNTARY_REVIEW_DECISION_REQUIRED')
        cid=decision.review_commitment_id
        old=self.store.db.execute("SELECT 1 FROM events WHERE source_namespace='commitment.voluntary-review' AND source_key=?",(cycle_id,)).fetchone()
        if old:return cid
        with self.store.transaction('commitment.voluntary_reviewed',{'cycle_id':cycle_id,'commitment_id':cid},source_namespace='commitment.voluntary-review',source_key=cycle_id) as tx:
            row=self.store.one('commitments',cid)
            if not row or row['revision']!=decision.review_revision or row['state'] not in {'ADOPTED','ACTIVE'}:raise CoreError('STALE_VOLUNTARY_REVIEW')
            prior=self.records.read(row['record_id']);terms=VoluntaryTerms.model_validate_json(canonical(prior['payload']['voluntary']))
            if decision.review_choice=='END':
                tx.update('commitments',cid,state='CANCELLED',revision=row['revision']+1,updated_at_us=self.store.clock.utc_now_us())
            else:
                now=cycle['created_at_us'];new_end=min(terms.end_us,now+decision.accepted_duration_us)
                revised=terms.model_copy(update={'end_us':new_end,'review_at_us':new_end,'accepted_scope':'TARGETED' if decision.review_choice=='MODIFY' else terms.accepted_scope})
                VoluntaryTerms.model_validate_json(revised.model_dump_json())
                rid=self.records.create(tx,kind='COMMITMENT',scope=row['scope'],payload={**prior['payload'],'voluntary':revised.model_dump(mode='json'),'last_review_cycle_id':cycle_id},
                    memories=self.records.support(row['record_id']),records=(cycle['record_id'],),supersedes=row['record_id'])
                tx.update('commitments',cid,record_id=rid,due_at_us=new_end,revision=row['revision']+1,updated_at_us=self.store.clock.utc_now_us())
        return cid

    def get(self, commitment_id):
        row = self.store.one("commitments", commitment_id)
        if not row:
            raise CoreError("COMMITMENT_MISSING")
        body = self.records.read(row["record_id"])["payload"]
        cls = AdoptedCommitment if row["adoption_event_id"] else CommitmentState
        return cls(commitment_id=commitment_id, revision=row["revision"], state=row["state"],
            description=body["description"], due_at_us=row["due_at_us"],
            overdue=row["due_at_us"] is not None and row["due_at_us"] < self.store.clock.utc_now_us()
                and row["state"] in {"ADOPTED", "ACTIVE"},
            source_memory_ids=self.records.support(row["record_id"]), adoption_event_id=row["adoption_event_id"],
            support_current=self.records.current_support(row["record_id"]))
