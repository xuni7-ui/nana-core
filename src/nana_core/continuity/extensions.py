"""Open descriptive vocabulary; closed authority/privacy domains stay elsewhere."""
from typing import Literal
from pydantic import Field
from ..contracts import DTO

Namespaced = str
NAME_PATTERN = r'^[a-z][a-z0-9_-]{0,31}\.[a-z][a-z0-9._-]{0,95}$'

class ExtensionDescriptor(DTO):
    key: str = Field(pattern=NAME_PATTERN)
    kind: Literal['PLATFORM','SURFACE','DEVICE','ACTIVITY','SKILL','MEDIA','INTEREST','PROJECT','PERCEPTION']
    version: str = Field(pattern=r'^[0-9]+\.[0-9]+(?:\.[0-9]+)?$')
    source_reference: str = Field(min_length=1, max_length=256)
    tags: tuple[str, ...] = Field(default=(), max_length=32)
    execution_authority: Literal[False] = False

class SurfaceEnvelope(DTO):
    schema_version: Literal[1] = 1
    domain: Literal['SYNTHETIC_ONLY'] = 'SYNTHETIC_ONLY'
    subject_id: str = Field(min_length=1, max_length=128)
    platform: str = Field(pattern=NAME_PATTERN)
    surface: str = Field(pattern=NAME_PATTERN)
    adapter: str = Field(pattern=NAME_PATTERN)
    device_id: str | None = Field(default=None, pattern=NAME_PATTERN)
    entity_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    conversation_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    session_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    event_kind: str = Field(pattern=NAME_PATTERN)
    occurred_at_us: int | None = Field(default=None, ge=0)
    observed_at_us: int = Field(ge=0)
    correlation_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    privacy_class: Literal['PUBLIC','PROJECT','PERSONAL','SECRET']
    source_reference: str = Field(pattern=r'^synthetic[.:_-][A-Za-z0-9._:-]{1,128}$')
    source_event_key: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
