"""Versioned, source-preserving platform envelopes; never authority claims."""
from enum import StrEnum
from typing import Literal
from pydantic import Field, model_validator
from ..contracts import DTO
from ..storage import digest


class Outcome(StrEnum):
    CONFIRMED_SUCCESS = 'CONFIRMED_SUCCESS'
    CONFIRMED_FAILURE = 'CONFIRMED_FAILURE'
    UNKNOWN = 'UNKNOWN'
    UNSUPPORTED = 'UNSUPPORTED'
    CANCELLED = 'CANCELLED'


class Account(DTO):
    platform: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    account_id: str = Field(min_length=1, max_length=128)
    adapter_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')

    @property
    def key(self):
        # Nicknames never participate in identity or cross-platform binding.
        return digest([self.platform, self.adapter_id, self.account_id])


class Capability(DTO):
    name: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,95}$')
    available: bool
    reason: str = Field(default='', max_length=96)


class Segment(DTO):
    kind: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    text: str | None = Field(default=None, max_length=2048, repr=False)
    # References are opaque platform identifiers, not auto-fetched URLs.
    reference: str | None = Field(default=None, max_length=512, repr=False)
    content_sha256: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    inspected: bool = False


class Event(DTO):
    schema_version: Literal[1] = 1
    account: Account
    event_id: str = Field(min_length=1, max_length=128)
    kind: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,95}$')
    conversation_id: str = Field(min_length=1, max_length=128)
    sender_id: str | None = Field(default=None, max_length=128)
    conversation_kind: Literal['private', 'group', 'channel', 'feed', 'account']
    message_id: str | None = Field(default=None, max_length=128)
    parent_id: str | None = Field(default=None, max_length=128)
    occurred_at_us: int | None = Field(default=None, ge=0)
    observed_at_us: int = Field(ge=0)
    privacy: Literal['PUBLIC', 'PROJECT', 'PERSONAL']
    origin: Literal['AUTHENTICATED_PLATFORM', 'ACCOUNT_API_UNATTESTED', 'SYNTHETIC_LOOPBACK']
    segments: tuple[Segment, ...] = Field(default=(), max_length=64, repr=False)
    raw_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    # Original fields/attachments may be read through the connector using this
    # reference under its budget. They are never silently put in model context.
    raw_reference: str = Field(min_length=1, max_length=256, repr=False)
    sequence: int | None = Field(default=None, ge=0)
    priority: int = Field(default=1, ge=0, le=2)

    @property
    def key(self):
        return digest([self.account.key, self.kind, self.event_id])

    @property
    def ordering_key(self):
        return digest([self.account.key, self.conversation_kind, self.conversation_id])


class OperationReceipt(DTO):
    schema_version: Literal[1] = 1
    operation_id: str = Field(min_length=1, max_length=128)
    outcome: Outcome
    reason: str = Field(pattern=r'^[A-Z][A-Z0-9_]{0,127}$')
    action_id: str | None = Field(default=None, max_length=128)
    source_key: str | None = Field(default=None, max_length=128)
    external_delivery: bool = False
    retry_allowed: Literal[False] = False

    @model_validator(mode='after')
    def confirmed_delivery(self):
        if self.external_delivery and self.outcome != Outcome.CONFIRMED_SUCCESS:
            raise ValueError('only independent confirmed success can attest delivery')
        return self


class SessionHealth(DTO):
    connection: Literal['DISABLED', 'DISCONNECTED', 'CONNECTING', 'CONNECTED', 'DEGRADED'] = 'DISCONNECTED'
    login: Literal['UNKNOWN', 'AUTHENTICATED', 'REQUIRED'] = 'UNKNOWN'
    receive: Literal['NOT_OBSERVED', 'HEALTHY', 'STALE', 'BACKPRESSURE'] = 'NOT_OBSERVED'
    last_event_us: int | None = None
    last_heartbeat_us: int | None = None
    reconnects: int = 0
    error: str | None = Field(default=None, pattern=r'^[A-Z][A-Z0-9_]{0,95}$')
    compatibility: Literal['UNVERIFIED', 'ONEBOT11_MINIMUM', 'NATIVE_CORE', 'RSS_ATOM'] = 'UNVERIFIED'
