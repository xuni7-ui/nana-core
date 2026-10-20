"""Bounded problem hypotheses evaluated by C against visible observations.

The proposal supplies alternatives, not facts or adopted objectives. This is a
phase of the original SubjectLoop; the existing planner still plans objectives.
"""
import json
from typing import Literal
from pydantic import Field,model_validator
from ...contracts import DTO, CoreError


class FactCondition(DTO):
    memory_id: str
    field: str = Field(pattern=r'^[A-Za-z0-9_]{1,64}$')
    expected: str | int | bool

    @model_validator(mode='after')
    def bounded(self):
        if isinstance(self.expected,str) and len(self.expected)>512:raise ValueError('bounded factual value required')
        return self


class ProblemFrame(DTO):
    requested_problem: str = Field(min_length=1, max_length=256)
    assumed: tuple[FactCondition, ...] = Field(min_length=1, max_length=8)
    alternative_problem: str = Field(min_length=1, max_length=256)
    required: tuple[FactCondition, ...] = Field(min_length=1, max_length=8)
    program_id: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,31}\.[a-z][a-z0-9._-]{0,95}$')


class FrameAssessment(DTO):
    derived: Literal[True] = True
    state: Literal['REFRAME', 'PREMISE_SUPPORTED', 'INSUFFICIENT_EVIDENCE']
    original_problem: str
    considered_problem: str
    program_id: str | None = None
    source_memory_ids: tuple[str, ...]
    reason: str


def evaluate(frame, records, *, scope, privacy_classes):
    """Only direct, source-current observations can refute a factual premise."""
    def check(condition):
        head=records.store.one('memories', condition.memory_id)
        if not head or head['scope']!=scope or head['privacy_class'] not in privacy_classes:return None
        try:
            item=records.memory.read(condition.memory_id)
            if item['authority']!='DIRECT' or item['epistemic_kind']!='OBSERVATION':return None
            body=json.loads(item['text'])
        except (CoreError, ValueError):return None
        if not isinstance(body,dict) or condition.field not in body:return None
        actual=body[condition.field]
        return type(actual) is type(condition.expected) and actual==condition.expected
    premises=tuple(check(c) for c in frame.assumed)
    required=tuple(check(c) for c in frame.required)
    supported=all(x is True for x in premises)
    reframe=any(x is False for x in premises) and all(x is True for x in required)
    state='REFRAME' if reframe else 'PREMISE_SUPPORTED' if supported else 'INSUFFICIENT_EVIDENCE'
    return FrameAssessment(state=state,original_problem=frame.requested_problem,
        considered_problem=frame.alternative_problem if reframe else frame.requested_problem,
        program_id=frame.program_id if reframe else None,
        source_memory_ids=tuple(dict.fromkeys(c.memory_id for c in (*frame.assumed,*frame.required))),
        reason='Observed premise counterevidence and a supported underlying need justify a different problem' if reframe else
               'No evidenced reason to replace the stated problem' if supported else 'Insufficient direct evidence; ask rather than adopt a new framing')
