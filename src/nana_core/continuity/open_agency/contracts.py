"""Typed data proposals; no Grant, Store, callable or authority in planner input."""
from typing import Literal, Protocol
from pydantic import Field, model_validator,model_serializer
from ...contracts import DTO
from ..autonomy.contracts import RealizationTarget

Fact = str
class Operator(DTO):
    operator_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    capability: Literal['world.observe','world.compute','world.publish','world.contact','world.skill']
    resource: str = Field(pattern=r'^(?:synthetic|project|hands)://[A-Za-z0-9/._:-]{1,160}$')
    requires: tuple[Fact,...] = Field(default=(),max_length=16)
    produces: tuple[Fact,...] = Field(min_length=1,max_length=16)
    consumes: tuple[Fact,...] = Field(default=(),max_length=16)
    cost: int = Field(default=1,ge=1,le=100)
    args: dict
    expected_digest: str | None = Field(default=None,pattern=r'^[a-f0-9]{64}$')
    strategy_selectable: bool = False
    def target(self):
        return RealizationTarget(capability=self.capability,resource=self.resource,resource_class='ORDINARY',
            operation='READ' if self.capability in {'world.observe','world.compute','world.skill'} else 'CONTACT' if self.capability=='world.contact' else 'WRITE')

class Objective(DTO):
    objective_id: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,31}\.[a-z][a-z0-9._-]{0,95}$')
    scope: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    motivation_source: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,63}$')
    task_domain: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    desired: tuple[Fact,...] = Field(min_length=1,max_length=8)
    initial: tuple[Fact,...] = Field(default=(),max_length=32)
    operators: tuple[Operator,...] = Field(min_length=1,max_length=32)
    priority: int = Field(default=1,ge=0,le=3)
    deadline_us: int | None = Field(default=None,ge=0)
    depends_on: tuple[str,...] = Field(default=(),max_length=8)
    parent_id: str | None = None
    max_steps: int = Field(default=12,ge=1,le=32)
    horizon: Literal['IMMEDIATE','SHORT','ONGOING']='SHORT'
    review_after_us: int | None = Field(default=None,ge=0)
    @model_serializer(mode='wrap')
    def compatible_wire(self,handler):
        value=handler(self)
        if self.horizon=='SHORT':value.pop('horizon',None)
        if self.review_after_us is None:value.pop('review_after_us',None)
        return value
    @model_validator(mode='after')
    def unique_ops(self):
        if len(set(x.operator_id for x in self.operators))!=len(self.operators):raise ValueError('duplicate operator')
        if any(not 1<=len(f)<=96 for f in (*self.initial,*self.desired,*(f for op in self.operators for f in (*op.requires,*op.produces,*op.consumes)))):raise ValueError('bounded facts required')
        return self

class PlannerInput(DTO):
    objective: Objective
    source_record_id: str
    world_revision: str
class PlanCandidate(DTO):
    source_record_ids: tuple[str,...] = Field(default=(),max_length=8)
    provenance: Literal['PROPOSAL_NOT_AUTHORITY'] = 'PROPOSAL_NOT_AUTHORITY'
    operator_ids: tuple[str,...] = Field(min_length=0,max_length=32)
    source_record_id: str
    world_revision: str
class PlannerPort(Protocol):
    def plan(self,request:PlannerInput) -> PlanCandidate: ...
