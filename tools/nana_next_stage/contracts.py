"""VNext-1 Phase A boundary contracts, outside the approved Core.

RealCapturePlan is metadata-only planning, never permission to read or import.
Synthetic records alone can enter the readiness prototype.
"""
import json
from datetime import datetime, timezone
from typing import Literal
from pydantic import Field, model_validator, field_validator
from nana_core.contracts import DTO, CoreError
from nana_core.migration.iris import IrisRecord
from nana_core.storage import canonical, digest


def utc_us(value):
    if type(value) is not str or len(value) > 40:
        raise ValueError('TIME_REJECTED')
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError('TIME_ZONE_REQUIRED')
    dt = dt.astimezone(timezone.utc)
    delta = dt - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def strict_json(raw, maximum=1_000_000):
    if type(raw) is not bytes or len(raw) > maximum:
        raise CoreError('INPUT_BYTES_REJECTED')
    def pairs(values):
        out = {}
        for key, value in values:
            if key in out:
                raise ValueError('DUPLICATE_KEY')
            out[key] = value
        return out
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        canonical(value)
        return value
    except (ValueError, TypeError, RecursionError):
        raise CoreError('INPUT_JSON_REJECTED') from None


class ReadinessDTO(DTO):
    # Field validators preserve Pydantic's JSON array-to-strict-tuple boundary;
    # a model-before dict rewrite changes that boundary to Python validation.
    @field_validator('schema_version', mode='before', check_fields=False)
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int:
            raise ValueError('SCHEMA_INTEGER_REQUIRED')
        return value

    @field_validator('reader_enabled', 'authority_change', mode='before', check_fields=False)
    @classmethod
    def exact_boolean(cls, value):
        if type(value) is not bool:
            raise ValueError('BOOLEAN_REQUIRED')
        return value


class SyntheticIrisRecord(IrisRecord):
    synthetic_only: bool = Field(strict=True)

    @field_validator('synthetic_only')
    @classmethod
    def only_true(cls, value):
        if value is not True:
            raise ValueError('EXPLICIT_SYNTHETIC_TRUE_REQUIRED')
        return value


class Coverage(ReadinessDTO):
    source_instance: str = Field(pattern=r'^synthetic:[a-zA-Z0-9_-]{1,64}$')
    observed_from: str
    observed_until: str
    event_scope: Literal['result_path', 'explicit_capture', 'fixture_full']
    completeness: Literal['PARTIAL', 'FULL_FOR_DECLARED_SCOPE', 'UNKNOWN']
    dropped: int = Field(ge=0, le=1_000_000)
    disconnected: bool

    @model_validator(mode='after')
    def interval(self):
        if utc_us(self.observed_until) < utc_us(self.observed_from):
            raise ValueError('COVERAGE_INTERVAL_REJECTED')
        if self.completeness == 'FULL_FOR_DECLARED_SCOPE' and (self.dropped or self.disconnected):
            raise ValueError('FULL_COVERAGE_WITH_LOSS_REJECTED')
        return self


class CaptureScope(ReadinessDTO):
    domain: Literal['SYNTHETIC_ONLY'] = 'SYNTHETIC_ONLY'
    dataset_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    record_kinds: tuple[str, ...] = Field(min_length=1, max_length=11)
    max_records: int = Field(ge=1, le=100)
    privacy: Literal['PROJECT', 'PRIVATE_SIMULATED'] = 'PROJECT'
    destination: Literal['local_only'] = 'local_only'
    retention: Literal['fixture_only_not_private_purge'] = 'fixture_only_not_private_purge'

    @model_validator(mode='after')
    def domain_scope(self):
        if any(not d.startswith('synthetic:') for d in self.dataset_ids):
            raise ValueError('SYNTHETIC_SOURCE_REQUIRED')
        if len(set(self.dataset_ids)) != len(self.dataset_ids) or len(set(self.record_kinds)) != len(self.record_kinds):
            raise ValueError('DUPLICATE_SCOPE')
        from nana_core.migration.iris import KINDS
        if not set(self.record_kinds) <= KINDS:
            raise ValueError('UNKNOWN_KIND')
        return self


class SyntheticCapture(ReadinessDTO):
    schema_version: Literal[1] = 1
    provenance: Literal['SYNTHETIC_FIXTURE'] = 'SYNTHETIC_FIXTURE'
    scope: CaptureScope
    records: tuple[SyntheticIrisRecord, ...] = Field(max_length=100)
    coverage: Coverage

    @model_validator(mode='after')
    def scoped(self):
        if len(self.records) > self.scope.max_records:
            raise ValueError('CAPTURE_RECORD_LIMIT')
        if any(r.dataset_id not in self.scope.dataset_ids or r.kind not in self.scope.record_kinds for r in self.records):
            raise ValueError('CAPTURE_SCOPE_MISMATCH')
        if self.coverage.source_instance not in self.scope.dataset_ids:
            raise ValueError('COVERAGE_SCOPE_MISMATCH')
        return self


class RealCapturePlan(ReadinessDTO):
    """Future review input. No record payload, path, credential or trust pin."""
    schema_version: Literal[1] = 1
    kind: Literal['REAL_CAPTURE_PLAN_ONLY'] = 'REAL_CAPTURE_PLAN_ONLY'
    source_version: Literal['iris-0.3.0'] = 'iris-0.3.0'
    source_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    record_kinds: tuple[Literal['l1', 'l2_row', 'kg_node', 'kg_edge', 'user_profile'], ...] = Field(min_length=1, max_length=5)
    maximum_records: int = Field(ge=1, le=100)
    output_mode: Literal['schema-only', 'hash-only', 'redact'] = 'schema-only'
    reader_enabled: Literal[False] = False
    authorization_status: Literal['NOT_RUN_REAL_DEPENDENCY'] = 'NOT_RUN_REAL_DEPENDENCY'


class Claim(ReadinessDTO):
    claim_id: str = Field(pattern=r'^synthetic:[a-zA-Z0-9_-]{1,64}$')
    subject: str = Field(pattern=r'^synthetic:[a-zA-Z0-9_-]{1,64}$')
    predicate: str = Field(pattern=r'^[a-z][a-z0-9_.-]{0,63}$')
    value: str = Field(min_length=1, max_length=256)
    scope: str = Field(pattern=r'^synthetic:[a-zA-Z0-9_-]{1,64}$')
    epistemic_kind: Literal['USER_STATEMENT', 'MODEL_INFERENCE', 'SUMMARY', 'ACTION_CLAIM']
    valid_from: str | None = None
    expressed_at: str | None = None
    supporting_memory_ids: tuple[str, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode='after')
    def times(self):
        for value in (self.valid_from, self.expressed_at):
            if value is not None:
                utc_us(value)
        return self

    @property
    def family(self):
        return digest([self.subject, self.predicate, self.scope])


class Relationship(ReadinessDTO):
    person_id: str = Field(pattern=r'^synthetic:[a-zA-Z0-9_-]{1,64}$')
    role: Literal['sister_fixture', 'other_fixture']
    address_term: str = Field(min_length=1, max_length=64)
    supporting_memory_ids: tuple[str, ...] = Field(min_length=1, max_length=8)


class Commitment(ReadinessDTO):
    commitment_id: str = Field(pattern=r'^synthetic:[a-zA-Z0-9_-]{1,64}$')
    beneficiary_id: str = Field(pattern=r'^synthetic:[a-zA-Z0-9_-]{1,64}$')
    outcome: str = Field(min_length=1, max_length=256)
    due_at: str
    status: Literal['OFFERED', 'ACCEPTED', 'FULFILLED', 'RENEGOTIATED', 'WITHDRAWN']
    supporting_memory_ids: tuple[str, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode='after')
    def time(self):
        utc_us(self.due_at)
        return self


class SelfChangeCandidate(ReadinessDTO):
    change_id: str = Field(pattern=r'^synthetic:[a-zA-Z0-9_-]{1,64}$')
    dimension: Literal['expression_preference', 'interest']
    proposed_value: str = Field(min_length=1, max_length=128)
    supporting_memory_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    state: Literal['CANDIDATE'] = 'CANDIDATE'
    authority_change: Literal[False] = False
