"""Versioned cognitive contracts. Text is data, never identity or authority."""
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from ..contracts import DTO


class MemoryType(StrEnum):
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    RELATIONAL = "RELATIONAL"
    SELF = "SELF"
    PROCEDURAL = "PROCEDURAL"
    PROSPECTIVE = "PROSPECTIVE"
    PROJECT = "PROJECT"


class Provenance(DTO):
    domain: Literal["SYNTHETIC_ONLY"] = "SYNTHETIC_ONLY"
    source_namespace: str = Field(pattern=r"^synthetic[.:_-][A-Za-z0-9._:-]{1,96}$")
    source_reference: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    source_revision: str = Field(default="1", pattern=r"^[A-Za-z0-9._:-]{1,32}$")
    source_kind: Literal["USER_STATEMENT", "DIRECT_OBSERVATION", "MODEL_DERIVATION", "SYSTEM_VERIFICATION"]
    coverage: Literal["FULL", "EXCERPT", "SUMMARY", "UNKNOWN"] = "FULL"


class EvidenceInput(DTO):
    schema_version: Literal[1] = 1
    provenance: Provenance
    text: str = Field(min_length=1, max_length=65536)
    privacy_class: Literal["PUBLIC", "PROJECT", "PERSONAL", "SECRET"]
    event_time_us: int | None = Field(default=None, ge=0)
    observed_time_us: int = Field(ge=0)


class MemoryCandidate(DTO):
    schema_version: Literal[1] = 1
    entity_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    scope: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    memory_type: MemoryType
    epistemic_kind: Literal["OBSERVATION", "STATEMENT", "BELIEF", "SUMMARY", "INFERENCE", "LESSON"]
    source_evidence_id: str
    text: str = Field(min_length=1, max_length=65536)
    predicate_key: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    confidence: float = Field(default=0.0, ge=0, le=1)
    importance: float = Field(default=0.5, ge=0, le=1)
    significance: float = Field(default=0.0, ge=0, le=1)
    derived_from: tuple[str, ...] = Field(default=(), max_length=64)
    correction_of: str | None = None

    @model_validator(mode="after")
    def derived_summary(self):
        if self.epistemic_kind in {"SUMMARY", "INFERENCE", "LESSON"} and not self.derived_from:
            raise ValueError("derived memory requires memory backlinks")
        if self.correction_of and not self.predicate_key:
            raise ValueError("correction requires a claim family")
        return self


class IngressQualification(DTO):
    b5_3_qualified: bool = False
    explicit_authorization: bool = False
    privacy_classified: bool = False
    valid_provenance: bool = False
    deletion_available: bool = False
    entity_binding_valid: bool = False


class RealMemoryIngress:
    # No runtime flag, config, receipt, or forged qualification enables this.
    enabled = False

    def import_real(self, qualification: IngressQualification, payload=None):
        from ..contracts import CoreError
        raise CoreError("REAL_MEMORY_IMPORT_DISABLED")
