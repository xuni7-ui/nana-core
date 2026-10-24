"""Typed data proposals; no Grant, Store, callable or authority in planner input."""
from typing import Literal, Protocol
from pydantic import Field, model_validator,model_serializer
from ...contracts import DTO
from ..autonomy.contracts import RealizationTarget

Fact = str

class TaskGroup(DTO):
    """Finite AND decomposition over operators/nested groups; never authority."""
    group_id: str = Field(pattern=r'^group\.[a-z][a-z0-9._-]{0,57}$')
    members: tuple[str,...] = Field(min_length=1,max_length=128)
    depends_on: tuple[str,...] = Field(default=(),max_length=32)

class InputStateGuard(DTO):
    """Required recent independently verified observation, not a model claim."""
    observation_operator_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    max_age_us: int = Field(ge=1,le=86400_000_000)
    expected_revision: str | None = Field(default=None,pattern=r'^[a-f0-9]{64}$')

class CheckpointOutput(DTO):
    goal_id:str
    work_id:str
    plan_record_id:str
    operator_id:str
    cursor:int=Field(ge=0,le=128)
    action_id:str
    memory_id:str
    experience_id:str|None
    quality:Literal[True]

class CheckpointCheck(DTO):
    operator_id:str
    action_id:str
    record_id:str
    event_id:str
    verdict:Literal['MATCH']

class TaskCheckpoint(DTO):
    format:Literal['VERIFIED_TASK_PREFIX_V1']='VERIFIED_TASK_PREFIX_V1'
    completed_operator_ids:tuple[str,...]=Field(min_length=1,max_length=128)
    facts:tuple[str,...]=Field(max_length=2048)
    outputs:tuple[CheckpointOutput,...]=Field(min_length=1,max_length=128)
    checks:tuple[CheckpointCheck,...]=Field(min_length=1,max_length=128)
    grants_authority:Literal[False]=False
    @model_validator(mode='after')
    def correlated(self):
        ids=set(self.completed_operator_ids)
        outputs={row.operator_id:row for row in self.outputs}
        if len(ids)!=len(self.completed_operator_ids) or len(outputs)!=len(self.outputs) or ids!=outputs.keys():raise ValueError('checkpoint output correlation')
        if len({(row.goal_id,row.work_id) for row in self.outputs})!=1:raise ValueError('checkpoint goal lineage')
        for check in self.checks:
            if check.operator_id not in outputs or outputs[check.operator_id].action_id!=check.action_id:raise ValueError('checkpoint independent check correlation')
        return self

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
    input_guard: InputStateGuard | None = None
    task_domain: str | None = Field(default=None,pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    @model_serializer(mode='wrap')
    def compatible_wire(self,handler):
        value=handler(self)
        if self.input_guard is None:value.pop('input_guard',None)
        if self.task_domain is None:value.pop('task_domain',None)
        return value
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
    operators: tuple[Operator,...] = Field(min_length=1,max_length=128)
    task_groups: tuple[TaskGroup,...] = Field(default=(),max_length=32)
    priority: int = Field(default=1,ge=0,le=3)
    deadline_us: int | None = Field(default=None,ge=0)
    depends_on: tuple[str,...] = Field(default=(),max_length=8)
    parent_id: str | None = None
    max_steps: int = Field(default=12,ge=1,le=128)
    horizon: Literal['IMMEDIATE','SHORT','ONGOING']='SHORT'
    review_after_us: int | None = Field(default=None,ge=0)
    @model_serializer(mode='wrap')
    def compatible_wire(self,handler):
        value=handler(self)
        if self.horizon=='SHORT':value.pop('horizon',None)
        if self.review_after_us is None:value.pop('review_after_us',None)
        if not self.task_groups:value.pop('task_groups',None)
        return value
    @model_validator(mode='after')
    def unique_ops(self):
        if len(set(x.operator_id for x in self.operators))!=len(self.operators):raise ValueError('duplicate operator')
        if any(not 1<=len(f)<=96 for f in (*self.initial,*self.desired,*(f for op in self.operators for f in (*op.requires,*op.produces,*op.consumes)))):raise ValueError('bounded facts required')
        if self.task_groups or any(op.input_guard for op in self.operators):
            from .task_graph import predecessors
            predecessors(self)
        return self

class PlannerInput(DTO):
    objective: Objective
    source_record_id: str
    world_revision: str
    completed_operator_ids: tuple[str,...] = Field(default=(),max_length=128)
    checkpoint_facts: tuple[str,...] = Field(default=(),max_length=2048)
    @model_validator(mode='after')
    def checked_shape(self):
        known={op.operator_id for op in self.objective.operators}
        if len(set(self.completed_operator_ids))!=len(self.completed_operator_ids) or not set(self.completed_operator_ids)<=known:raise ValueError('unknown or duplicate checkpoint operator')
        if self.checkpoint_facts and not self.completed_operator_ids:raise ValueError('checkpoint facts need completed work')
        if any(not 1<=len(f)<=96 for f in self.checkpoint_facts):raise ValueError('bounded checkpoint fact required')
        return self
class PlanCandidate(DTO):
    source_record_ids: tuple[str,...] = Field(default=(),max_length=8)
    provenance: Literal['PROPOSAL_NOT_AUTHORITY'] = 'PROPOSAL_NOT_AUTHORITY'
    operator_ids: tuple[str,...] = Field(min_length=0,max_length=128)
    source_record_id: str
    world_revision: str
class PlannerPort(Protocol):
    def plan(self,request:PlannerInput) -> PlanCandidate: ...
