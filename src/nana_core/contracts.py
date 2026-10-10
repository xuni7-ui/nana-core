"""Strict boundary objects. Model proposals never contain execution authority."""
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class DTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class ActionState(StrEnum):
    PROPOSED = "PROPOSED"
    BLOCKED = "BLOCKED"
    READY = "READY"
    DISPATCHING = "DISPATCHING"
    PENDING_VERIFY = "PENDING_VERIFY"
    UNKNOWN = "UNKNOWN"
    SUCCEEDED = "SUCCEEDED"
    NOT_APPLIED = "NOT_APPLIED"
    FAILED_EFFECT = "FAILED_EFFECT"
    CANCELLED = "CANCELLED"


class Observation(DTO):
    source_namespace: str = Field(min_length=1, max_length=128)
    object_id: str = Field(min_length=1, max_length=256)
    revision: str = "1"
    channel: str = "offline"
    kind: Literal["reading", "unrelated", "wake"] = "reading"
    raw_text: str = Field(min_length=1)
    occurred_at: str | None = None
    source_id: str | None = None
    card_resource: str | None = None


class EvidenceRef(DTO):
    event_id: str
    artifact_id: str | None = None
    coverage: Literal["FULL", "EXCERPT", "SUMMARY"] = "FULL"


class StepProposal(DTO):
    capability: Literal["reading.source.read", "reading.source.locate", "reading.card.create"]
    resource: str


class PlanProposal(DTO):
    goal_template: Literal["reading_card"] = "reading_card"
    purpose: str = Field(min_length=1, max_length=512)
    steps: tuple[StepProposal, ...] = Field(min_length=1, max_length=5)


class ModelRequest(DTO):
    identity_id: str
    identity_revision: int
    event_id: str
    event_text: str
    source_id: str
    card_resource: str
    strategy_refs: tuple[str, ...] = ()


class GrantSpec(DTO):
    capabilities: tuple[str, ...] = Field(min_length=1)
    resources: tuple[str, ...] = Field(min_length=1)
    not_before_us: int
    expires_at_us: int
    max_attempts: int = Field(default=1, ge=1, le=1)


class StrategyRule(DTO):
    kind: Literal["ADD_READ_STEP"] = "ADD_READ_STEP"
    capability: Literal["reading.source.locate"] = "reading.source.locate"
    scope: Literal["reading_card"] = "reading_card"
    required_output: Literal["locator"] = "locator"


class Feedback(DTO):
    goal_id: str
    text: str = Field(min_length=1)
    requested_fields: tuple[Literal["locator"], ...] = ()


class Invocation(DTO):
    action_id: str
    attempt_id: str
    capability: str
    resource: str
    args: dict
    args_hash: str
    idempotency_key: str


class Receipt(DTO):
    external_id: str
    result: dict


class Verification(DTO):
    verdict: Literal["MATCH", "FINAL_NO_EFFECT", "EFFECT_MISMATCH", "INCONCLUSIVE"]
    evidence: dict


class CoreError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
