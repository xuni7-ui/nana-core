"""Mention != promise; adoption is reviewed authority, fulfillment needs evidence."""
from typing import Literal

from pydantic import Field

from ..contracts import CoreError, DTO
from ..storage import uid
from .records import RecordService


class CommitmentCandidate(DTO):
    entity_id: str
    scope: str
    description: str = Field(min_length=1, max_length=2048)
    support_memory_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    due_at_us: int | None = Field(default=None, ge=0)


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


LEGAL = {"PROPOSED": {"ADOPTED", "CANCELLED"}, "ADOPTED": {"ACTIVE", "CANCELLED", "SUPERSEDED"},
         "ACTIVE": {"FULFILLED", "FAILED", "CANCELLED", "SUPERSEDED"}}


class CommitmentService:
    def __init__(self, store, authority):
        self.store, self._authority = store, authority
        self.records = RecordService(store)

    def propose(self, candidate: CommitmentCandidate):
        if not self.store.one("entities", candidate.entity_id):
            raise CoreError("ENTITY_BINDING_REQUIRED")
        now, commitment_id = self.store.clock.utc_now_us(), uid()
        with self.store.transaction("commitment.proposed") as tx:
            record_id = self.records.create(tx, kind="COMMITMENT", scope=candidate.scope,
                payload={"description": candidate.description}, memories=candidate.support_memory_ids)
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
                if source["source_kind"] != "SYSTEM_VERIFICATION" or proof["scope"] != row["scope"]:
                    raise CoreError("INDEPENDENT_FULFILLMENT_EVIDENCE_REQUIRED")
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
