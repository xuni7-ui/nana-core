"""Versioned context-based ModelPort. Model instances are disposable resources.

The original reading-only ports.ModelPort remains compatible. This v2 contract
adds general state context, rather than encoding continuity in a rationale string.
No response here can contain a Grant, Receipt, success state or Store mutation.
"""
import json
from typing import Literal, Protocol

from pydantic import Field,model_serializer,model_validator

from ..contracts import CoreError, DTO
from .autonomy.private_intent import PrivateQuestionProposal,PrivatePlanProposal


class FrozenModelInput(DTO):
    schema_version: Literal[2] = 2
    task_class: str
    context_json: str
    context_digest: str


class CognitiveProposal(DTO):
    model_config={**DTO.model_config, "hide_input_in_errors":True}
    # Optional current-process association, not a memory, fact, goal or a
    # request to persist. C may simply let it end in this cognition.
    passing_thought:str|None=Field(default=None,min_length=1,max_length=512)
    private_question:PrivateQuestionProposal|None=None
    private_plan:PrivatePlanProposal|None=None
    schema_version: Literal[2] = 2
    identity_id: str
    identity_revision: int = Field(ge=1)
    interpretation: str = Field(min_length=1, max_length=2048)
    proposed_operations: tuple[Literal["READ_SOURCE", "LOCATE_SOURCE", "DRAFT", "ASK", "WAIT"], ...] = Field(min_length=1, max_length=8)
    memory_refs: tuple[str, ...] = Field(default=(), max_length=64)
    lesson_refs: tuple[str, ...] = Field(default=(), max_length=32)

    @model_validator(mode='after')
    def one_private_edit(self):
        if self.private_question is not None and self.private_plan is not None:
            raise ValueError('one private edit per formation intention; existing thoughts coexist')
        return self

    @model_serializer(mode='wrap')
    def compatible_wire(self,handler):
        value=handler(self)
        if self.passing_thought is None:value.pop('passing_thought',None)
        if self.private_question is None:value.pop('private_question',None)
        if self.private_plan is None:value.pop('private_plan',None)
        return value


class ContinuityModelPort(Protocol):
    descriptor: str
    def propose(self, request: FrozenModelInput) -> str: ...


class DeliberationResult(DTO):
    model_descriptor: str
    context_digest: str
    raw_proposal_json: str
    proposal: CognitiveProposal
    execution: Literal["NOT_EXECUTED"] = "NOT_EXECUTED"


class DeliberationSession:
    def __init__(self, assembler):
        self.assembler = assembler

    def run(self, model: ContinuityModelPort, context, request, policy):
        self.assembler.validate(context, request, policy)
        envelope = FrozenModelInput(task_class=request.task_class,
            context_json=context.model_dump_json(), context_digest=context.content_digest)
        # The adapter gets immutable serialized data, no service/authority handles.
        raw = model.propose(envelope)
        if type(raw) is not str or len(raw.encode()) > 32768:
            raise CoreError("INVALID_COGNITIVE_REPLY")
        proposal = CognitiveProposal.model_validate_json(raw)
        manifest = context.manifest
        if (proposal.identity_id, proposal.identity_revision) != (manifest.identity_id, manifest.identity_revision):
            raise CoreError("MODEL_IDENTITY_MISMATCH")
        available = {m for b in context.blocks for m in b.source_memory_ids}
        lessons = {json.loads(b.data_json)["lesson_id"] for b in context.blocks if b.kind == "LESSON"}
        if not set(proposal.memory_refs) <= available or not set(proposal.lesson_refs) <= lessons:
            raise CoreError("UNSUPPORTED_COGNITIVE_REFERENCE")
        for candidate,category in ((proposal.private_question,'PRIVATE_QUESTION'),(proposal.private_plan,'PRIVATE_PLAN')):
            if candidate is None:continue
            private_refs={rid for b in context.blocks if b.kind=='PRIVATE_INTERNAL_STATE' for rid in b.source_record_ids}
            if not set(candidate.related_private_record_ids)<=private_refs:
                raise CoreError('UNSUPPORTED_'+category+'_REFERENCE')
            if candidate.revises_record_id is not None:
                target=next((json.loads(b.data_json) for b in context.blocks if b.kind=='PRIVATE_INTERNAL_STATE'
                    and candidate.revises_record_id in b.source_record_ids),None)
                if target is None or target['category']!=category:
                    raise CoreError('UNSUPPORTED_'+category+'_REVISION')
        self.assembler.validate(context, request, policy)  # state may change during inference
        return DeliberationResult(model_descriptor=model.descriptor, context_digest=context.content_digest,
                                  raw_proposal_json=raw, proposal=proposal)


class AnalyticalFixturePort:
    """Deterministic structured-rule interpreter, not an LLM or E12 evidence."""
    descriptor = "offline-analytical-fixture-v2"

    def propose(self, request):
        data = json.loads(request.context_json)
        operations, lessons, memories = ["READ_SOURCE", "DRAFT"], [], []
        for block in data["blocks"]:
            memories.extend(block["source_memory_ids"])
            if block["kind"] == "LESSON":
                lesson = json.loads(block["data_json"])
                if lesson["rule"].get("required_output") == "locator":
                    operations = ["READ_SOURCE", "LOCATE_SOURCE", "DRAFT"]
                    lessons.append(lesson["lesson_id"])
        return CognitiveProposal(identity_id=data["manifest"]["identity_id"],
            identity_revision=data["manifest"]["identity_revision"],
            interpretation="Use supplied current evidence and scoped procedures; no execution authority.",
            proposed_operations=tuple(operations), memory_refs=tuple(dict.fromkeys(memories))[:64],
            lesson_refs=tuple(lessons)).model_dump_json()


class CautiousFixturePort:
    """A second fixture planner: absent evidence asks, contradictions defer."""
    descriptor = "offline-cautious-fixture-v2"

    def propose(self, request):
        data = json.loads(request.context_json)
        blocks = data["blocks"]
        memories = tuple(dict.fromkeys(m for b in blocks for m in b["source_memory_ids"]))[:64]
        lessons = [json.loads(b["data_json"]) for b in blocks if b["kind"] == "LESSON"]
        if any(b["kind"] == "UNRESOLVED_CONFLICT" for b in blocks):
            operations = ("ASK",)
        elif not memories:
            operations = ("WAIT",)
        else:
            operations = ("READ_SOURCE", "DRAFT")
            if any(x["rule"].get("capability") == "reading.source.locate" for x in lessons):
                operations = ("READ_SOURCE", "LOCATE_SOURCE", "DRAFT")
        return CognitiveProposal(identity_id=data["manifest"]["identity_id"],
            identity_revision=data["manifest"]["identity_revision"],
            interpretation="Separate known history from uncertainty; resolve conflict before drafting.",
            proposed_operations=operations, memory_refs=memories,
            lesson_refs=tuple(x["lesson_id"] for x in lessons) if "LOCATE_SOURCE" in operations else ()).model_dump_json()
