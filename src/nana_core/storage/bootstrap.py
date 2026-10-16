"""Initial instance data, not a framework persona or a revision bypass."""
from pydantic import Field
from ..contracts import DTO

class IdentityBootstrap(DTO):
    name: str = Field(min_length=1,max_length=96)
    expression_style: str = Field(default='unspecified',min_length=1,max_length=128)
    source_reference: str = Field(pattern=r'^synthetic[.:_-][A-Za-z0-9._:-]{1,128}$')
