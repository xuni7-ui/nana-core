"""Finite offline procedure data. Adoption, desire and execution remain distinct."""
from typing import Literal
from pydantic import Field,model_validator
from ..contracts import DTO
from .autonomy.contracts import RealizationTarget

class GoalStepRef(DTO):
    work_id: str
    revision: int = Field(ge=1)
    cursor: int = Field(ge=0,le=32)

class PlanStepView(DTO):
    reference: GoalStepRef
    goal_id: str
    plan_id: str
    target: RealizationTarget
    record_id: str
    source_memory_ids: tuple[str,...]
    task_class: str

class OfflineProgram(DTO):
    program_id: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,31}\.[a-z][a-z0-9._-]{0,95}$')
    revision: int = Field(default=1,ge=1)
    scope: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    motivation_source: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,63}$')
    template: Literal['reading_card'] = 'reading_card'
    source_resource: str = Field(pattern=r'^synthetic://[A-Za-z0-9/._:-]{1,160}$')
    output_resource: str = Field(pattern=r'^synthetic://[A-Za-z0-9/._:-]{1,160}$')
    @model_validator(mode='after')
    def distinct(self):
        if self.source_resource==self.output_resource:raise ValueError('distinct source/output required')
        return self
