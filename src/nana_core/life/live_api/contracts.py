"""Versioned transport contracts; caller input never supplies authority or scope.

Host-bound policy chooses a single existing Subject and its lineage. Production
activation is separate from this protocol's implementation and from dev fixtures.
"""

from enum import StrEnum
from typing import Literal
from pydantic import Field, JsonValue, model_validator, model_serializer, field_validator
from ...contracts import DTO
from ...continuity.lived_language import LanguageSample

CONTRACT = "nana-space-live/v2"


class Realm(StrEnum):
    DEVELOPMENT = "OWNED_DEVELOPMENT_ONLY"
    PRODUCTION = "PRODUCTION_SINGLE_SUBJECT"


class Role(StrEnum):
    READER = "READER"
    CONVERSATION = "CONVERSATION"
    MANAGER = "MANAGER"
    HOST_ADMIN = "HOST_ADMIN"
    PRIVATE_CONTEXT = "PRIVATE_CONTEXT"  # Explicit device scope, never a Core Grant.


class Page(StrEnum):
    HOME = "home"
    CHAT = "chat"
    MEMORIES = "memories"
    GOALS = "goals"
    JOURNAL = "journal"
    WORLD = "world"
    GROWTH = "growth"
    DEVICES = "devices"
    RUNTIME = "runtime"
    SETTINGS = "settings"


class Completion(StrEnum):
    REQUESTED = "REQUESTED"
    ADMITTED = "ADMITTED"
    REJECTED = "REJECTED"
    RUNNING = "RUNNING"
    UNKNOWN = "UNKNOWN"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"


class Binding(DTO):
    subject_id: str = Field(min_length=1, max_length=96)
    lineage_binding: str = Field(pattern=r"^[a-f0-9]{64}$")
    realm: Realm = Realm.DEVELOPMENT
    scope: str = Field(default="project-work", min_length=1, max_length=96)
    entity_id: str = Field(default="project-user", min_length=1, max_length=96)
    privacy: tuple[Literal["PUBLIC", "PROJECT", "PERSONAL"], ...] = ("PUBLIC", "PROJECT")
    surface_binding_id: str = Field(default="nana.space", min_length=1, max_length=96)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.privacy or len(self.privacy) != len(set(self.privacy)):
            raise ValueError("EXPLICIT_PRIVACY_REQUIRED")
        return self


class Envelope(DTO):
    contract: Literal["nana-space-live/v2"] = CONTRACT
    realm: Realm
    subject_id: str
    lineage_binding: str
    owner_epoch: int = Field(ge=0)
    run_generation: str = Field(pattern=r"^[a-f0-9]{32}$")
    session_generation: int = Field(ge=1)
    as_of_us: int = Field(ge=0)
    revision: int = Field(ge=0)
    coverage: Literal["CURRENT", "NO_DATA", "BLOCKED_SCOPE", "UNKNOWN", "UNAVAILABLE", "STALE"]
    privacy_scope: tuple[Literal["PUBLIC", "PROJECT", "PERSONAL"], ...]
    source_refs: tuple[str, ...] = ()
    capabilities: dict[str, bool | str]
    execution_authority: Literal[False] = False
    data: dict[str, JsonValue]


class Login(DTO):
    password: str = Field(min_length=12, max_length=128, repr=False, exclude=True)
    subject_id: str = Field(min_length=1, max_length=96)


class DeviceLogin(DTO):
    password: str = Field(min_length=12, max_length=128, repr=False, exclude=True)
    device_name: str = Field(min_length=1, max_length=64)


class PairRequest(DTO):
    code: str = Field(min_length=24, max_length=128, repr=False, exclude=True)
    subject_id: str = Field(min_length=1, max_length=96)
    device_name: str = Field(min_length=1, max_length=64)


class PairOffer(DTO):
    device_name: str = Field(min_length=1, max_length=64)
    roles: tuple[Role, ...] = (Role.READER, Role.CONVERSATION)
    lifetime_seconds: int = Field(default=120, ge=30, le=300)


class WriteRequest(DTO):
    client_request_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    expected_revision: int = Field(ge=0)
    run_generation: str = Field(pattern=r"^[a-f0-9]{32}$")
    owner_epoch: int = Field(ge=0)


class MessageRequest(WriteRequest):
    text: str = Field(min_length=1, max_length=2048, repr=False)
    topic: str = Field(default="daily", pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    thread_id: str = Field(default="daily", pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    privacy_class: Literal["PUBLIC", "PROJECT", "PERSONAL"] = "PROJECT"
    require_model: bool = False  # Additive: old v2 clients retain offline review.
    retain_shared_life: bool = False  # Explicit per-message consent, original Person-Self path.


class SequenceMessage(DTO):
    client_message_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    text: str = Field(min_length=1, max_length=2048, repr=False)


class MessageSequenceRequest(WriteRequest):
    messages: tuple[SequenceMessage,...] = Field(min_length=2,max_length=4)
    topic: str = Field(default="daily",pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    thread_id: str = Field(default="daily",pattern=r"^[A-Za-z0-9._:-]{1,96}$")
    privacy_class: Literal["PUBLIC","PROJECT","PERSONAL"] = "PROJECT"
    require_model: bool = False
    retain_shared_life: bool = False

    @model_validator(mode='after')
    def distinct_messages(self):
        if len({m.client_message_id for m in self.messages})!=len(self.messages):
            raise ValueError('distinct message IDs required')
        return self



class LanguageFeedbackRequest(WriteRequest):
    sample: LanguageSample = Field(repr=False)
    exchange_record_id: str = Field(min_length=1, max_length=128)
    consent: Literal[True]
    response_sha256: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')

    @model_serializer(mode='wrap')
    def compatible_response_binding(self, handler):
        value=handler(self)
        if self.response_sha256 is None:value.pop('response_sha256',None)
        return value

    @field_validator('consent', mode='before')
    @classmethod
    def explicit_feedback_consent(cls, value):
        if value is not True:
            raise ValueError('explicit feedback retention consent required')
        return value


class CommandRequest(WriteRequest):
    operation: Literal["PAUSE", "RESUME", "BUSY", "AVAILABLE", "REVOKE", "WITHDRAW", "SET_SURFACE"]
    target_id: str | None = Field(default=None, max_length=96)
    enabled: bool | None = None
    target_revision: int | None = Field(default=None, ge=1)


class HostRequest(WriteRequest):
    operation: Literal["START", "STOP", "RESTART", "BACKUP", "UPGRADE", "ROLLBACK"]
    confirmation_id: str = Field(min_length=24, max_length=128, repr=False)
    release_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")


class HostConfirmation(DTO):
    operation: Literal["START", "STOP", "RESTART", "BACKUP", "UPGRADE", "ROLLBACK"]
    expected_revision: int = Field(ge=0)
    release_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")


class Receipt(DTO):
    receipt_id: str
    client_request_id: str
    operation: str
    state: Completion
    dispatch_happened: bool
    no_retry: Literal[True] = True
    result: dict[str, JsonValue] = Field(default_factory=dict)
    error: str | None = None


class ApiError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = code, status
        super().__init__(code)
