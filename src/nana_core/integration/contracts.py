"""Host data is evidence, never authorization. No host SDK imports."""
from typing import Literal, Protocol
from pydantic import Field
from ..contracts import DTO, Observation, CoreError
from ..ports import CapabilityPort
from ..migration.iris import LegacyMemorySource

class Attachment(DTO):
    kind: str = Field(min_length=1, max_length=64)
    source_reference: str = Field(min_length=1, max_length=512)
    mime_type: str | None = None
    bytes_hint: int | None = Field(default=None, ge=0)

class HostEvent(DTO):
    host_instance: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    platform: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    channel: str = Field(min_length=1, max_length=128)
    sender_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    conversation_id: str = Field(min_length=1, max_length=256)
    revision: str = Field(default='1', min_length=1, max_length=32)
    timestamp: str | None = None
    content: str = Field(max_length=65536)
    raw_content_reference: str = Field(min_length=1, max_length=512)
    reply_to: str | None = Field(default=None, max_length=256)
    attachments: tuple[Attachment, ...] = Field(default=(), max_length=16)
    observation_source: str = Field(default='astrbot', max_length=64)

class RuntimeIntegrationContext(DTO):
    mode: Literal['SHADOW'] = 'SHADOW'
    host_instance: str
    expected_identity_id: str
    external_execute: Literal[False] = False
    production_budget_enabled: Literal[False] = False

class HostObservationAdapter(Protocol):
    def adapt(self, event: HostEvent) -> Observation: ...

# CapabilityPort/LegacyMemorySource are reused, not parallel protocols.
HostCapabilityAdapter = CapabilityPort

class ShadowCapabilityPort:
    """A structural barrier, not a configurable live backend."""
    def execute(self, invocation): raise CoreError('SHADOW_BLOCKED')
    def verify(self, invocation): raise CoreError('SHADOW_NO_EXECUTION_EVIDENCE')
