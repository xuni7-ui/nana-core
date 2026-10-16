"""Standalone D runtime contracts. All ingress remains synthetic/dev only."""
from typing import Literal
from pydantic import Field, model_validator
from ..contracts import DTO
from ..continuity.subject.contracts import SubjectInput
from ..continuity.recurrence import RecurrenceSpec

SECOND = 1_000_000
HOUR = 3600 * SECOND
DAY = 24 * HOUR
EventType = Literal['USER_EVENT','TIME_EVENT','WORLD_EVENT','DEVICE_EVENT','PLATFORM_EVENT','PROJECT_EVENT','RELATIONSHIP_EVENT','GOAL_EVENT','SELF_EVENT','REFLECTION_EVENT','CAPABILITY_EVENT']
Trigger = Literal['INCOMING_EVENT','TIME_TRIGGER','GOAL_TRIGGER','ANOMALY','RELATIONSHIP_TRIGGER','SELF_TRIGGER','REFLECTION_TRIGGER','DEVICE_TRIGGER','ENVIRONMENT_CHANGE']


class CapabilitySnapshot(DTO):
    revision: int = Field(default=1,ge=1)
    capabilities: tuple[str,...] = Field(default=(),max_length=32)
    devices: tuple[str,...] = Field(default=(),max_length=32)
    platforms: tuple[str,...] = Field(default=(),max_length=16)
    provenance: Literal['SYNTHETIC_OPERATOR_SNAPSHOT'] = 'SYNTHETIC_OPERATOR_SNAPSHOT'
    execution_authority: Literal[False] = False


class LivingRuntimeConfig(DTO):
    max_idle_seconds: float = Field(default=2,ge=.02,le=30)
    maintenance_interval_us: int = Field(default=HOUR,ge=100_000)
    slice_items: int = Field(default=4,ge=1,le=16)
    max_model_bytes_per_day: int = Field(default=2_000_000,ge=0)
    max_estimated_cost_micro_per_day: int = Field(default=100000,ge=0)
    background_fraction_percent: int = Field(default=25,ge=0,le=90)
    call_reserved_bytes: int = Field(default=229376,ge=1024,le=1048576)
    call_estimated_cost_micro: int = Field(default=1000,ge=0)
    step_interval_us: int = Field(default=SECOND,ge=100_000)

class RuntimeConfig(DTO):
    schema_target: Literal[8,9,10,11,12] = 8
    living: LivingRuntimeConfig | None = None
    domain: Literal['SYNTHETIC_ONLY'] = 'SYNTHETIC_ONLY'
    scopes: tuple[str, ...] = Field(min_length=1,max_length=16)
    entity_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    privacy_classes: tuple[Literal['PUBLIC','PROJECT','PERSONAL'], ...] = ('PUBLIC','PROJECT','PERSONAL')
    lease_us: int = Field(default=30*SECOND,ge=100_000,le=4*HOUR)
    heartbeat_us: int = Field(default=5*SECOND,ge=20_000)
    review_interval_us: int = Field(default=6*HOUR,ge=100_000)
    idle_recall_us: int = Field(default=4*HOUR,ge=100_000)
    cognition_cooldown_us: int = Field(default=10*60*SECOND,ge=0)
    cognition_backoff_us: int = Field(default=30*60*SECOND,ge=0)
    max_calls_per_day: int = Field(default=8,ge=0,le=128)
    model_timeout_seconds: float = Field(default=1.5,ge=0.05,le=30)
    queue_capacity: int = Field(default=256,ge=4,le=4096)
    schedule_capacity: int = Field(default=128,ge=4,le=1024)
    poll_seconds: float = Field(default=0.1,ge=.01,le=5)
    model: Literal['analytical','cautious','unavailable','timeout'] | None = None
    capability_snapshot: CapabilitySnapshot = Field(default_factory=CapabilitySnapshot)

    @model_validator(mode='after')
    def heartbeat_window(self):
        if self.living and self.schema_target<11:raise ValueError('living runtime requires explicit development11')
        if self.heartbeat_us * 2 >= self.lease_us:
            raise ValueError('heartbeat must leave a lease safety margin')
        return self


class Cause(DTO):
    kind: Literal['CANONICAL_SELF','MEMORY','COMMITMENT','PROJECT','EXPERIENCE','INTENTION','ASSERTION']
    reference_id: str = Field(min_length=1,max_length=128)
    revision: int | None = Field(default=None,ge=1)


class RuntimeEvent(DTO):
    schema_version: Literal[1] = 1
    event_type: EventType
    trigger: Trigger
    input: SubjectInput
    causes: tuple[Cause, ...] = Field(min_length=1,max_length=32)
    priority: int = Field(default=1,ge=0,le=3)
    due_at_us: int = Field(ge=0)
    expires_at_us: int | None = Field(default=None,ge=0)
    stream_key: str | None = Field(default=None,pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    source_sequence: int | None = Field(default=None,ge=0)

    @model_validator(mode='after')
    def ordering(self):
        if (self.stream_key is None) != (self.source_sequence is None):
            raise ValueError('stream and sequence must be supplied together')
        if self.expires_at_us is not None and self.expires_at_us <= self.due_at_us:
            raise ValueError('expiry must follow due time')
        return self


class ScheduleSpec(DTO):
    dedupe_key: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    kind: Literal['ONE_SHOT','DEADLINE','PERIODIC','CONDITION','CALENDAR']
    due_at_us: int = Field(ge=0)
    interval_us: int | None = Field(default=None,ge=100_000)
    event: RuntimeEvent
    calendar: RecurrenceSpec | None = None

    @model_validator(mode='after')
    def periodic(self):
        if (self.kind=='PERIODIC') != (self.interval_us is not None):
            raise ValueError('only periodic schedules have an interval')
        if (self.kind=='CALENDAR') != (self.calendar is not None):raise ValueError('calendar spec/kind mismatch')
        if self.kind=='CALENDAR' and (self.event.input.kind!='WAKE' or self.event.input.origin!='SELF_WAKE'):raise ValueError('calendar emits check opportunities only')
        if any(getattr(self.event.input,k) is not None for k in ('text','preference_signal','relationship_kind','proposed_method','topic')):
            raise ValueError('scheduler cannot manufacture a lived experience')
        return self


class RuntimeHealth(DTO):
    status: Literal['ACTIVE','WATCHING','DEGRADED','STOPPED','LOST']
    runtime_instance_id: str
    epoch: int
    lease_status: str
    identity_id: str
    last_event: str | None
    last_wake_us: int | None
    last_cognition_us: int | None
    queue_depth: int
    deferred_count: int
    model_availability: str
    subject_revision: int
    last_successful_checkpoint_us: int | None
    clock_us: int
    time_since_interaction_us: int | None
    time_since_activity_us: int | None
    derived: Literal[True] = True
