"""Semantic proposals, never identity, relationship, goal or execution authority."""
from typing import Literal, Annotated
from pydantic import Field, StringConstraints, model_serializer
from ..contracts import DTO
from ..continuity.person_self import ConversationProposal, ConversationDecision

MeaningKind=Literal['VENT','CHAT','HELP','SHARE','DECLINE_DEPTH','DECLINE_DELIVERY','REOPEN','REOPEN_DELIVERY','FOCUS','CORRECTION','UNCLEAR','IMPORTANT','PROJECT_STATUS']

class DialogueMeaning(DTO):
    kind:MeaningKind
    confidence:Literal['LOW','RELEVANT','HIGH']='LOW'
    conversation_proposal:ConversationProposal|None=None
    recall_query_terms:tuple[Annotated[str,StringConstraints(min_length=2,max_length=64)],...]=Field(default=(),max_length=8)
    @model_serializer(mode='wrap')
    def legacy_wire(self,handler):
        value=handler(self)
        if not self.recall_query_terms:value.pop('recall_query_terms',None)
        return value

class DialogueDraft(DTO):
    text:str|None=Field(default=None,max_length=16384)
    claim_memory_ids:tuple[str,...]=Field(default=(),max_length=16)
    effect_status:Literal['NONE','VERIFIED_EFFECT','UNKNOWN']='NONE'

class DialogueRecipient(DTO):
    platform: str = Field(min_length=1, max_length=96)
    binding_id: str = Field(min_length=1, max_length=96)
    conversation_id: str = Field(min_length=1, max_length=128)


class DialogueTurn(DTO):
    recipient_context: DialogueRecipient | None = None
    text_truncated: bool = False
    message_memory_id:str
    topic:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    privacy_class:Literal['PUBLIC','PROJECT','PERSONAL']
    speaker:Literal['USER','ASSISTANT']
    support_memory_ids:tuple[str,...]=Field(default=(),max_length=64)
    text:str=Field(min_length=1,max_length=1024)

    @model_serializer(mode='wrap')
    def legacy_turn_wire(self, handler):
        value = handler(self)
        if not self.text_truncated:
            value.pop('text_truncated', None)
        if self.recipient_context is None:
            value.pop('recipient_context', None)
        return value


class CommunicationPurpose(DTO):
    """Projection of this original C decision, bounded by its cognition request."""
    cycle_id: str = Field(min_length=1, max_length=128)
    respond_to_memory_ids: tuple[str, ...] = Field(min_length=1, max_length=12)
    purpose: str = Field(min_length=1, max_length=512)
    validity: Literal['CURRENT_COGNITIVE_REQUEST_ONLY'] = 'CURRENT_COGNITIVE_REQUEST_ONLY'
    execution_authority: Literal[False] = False


class DialogueContext(DTO):
    recipient_context: DialogueRecipient | None = None
    reply_character_limit: int = Field(default=16384, ge=1, le=16384)
    communication_purpose: CommunicationPurpose | None = None
    recent_history_truncated:bool=False
    retain_shared_life:bool=False
    conversation_decision:ConversationDecision|None=None
    recent_turns:tuple[DialogueTurn,...]=Field(default=(),max_length=12)
    message_memory_id:str
    topic:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    privacy_class:Literal['PUBLIC','PROJECT','PERSONAL']
    project_status_query:bool=False
    phase:Literal['INTERPRET','RENDER']
    text:str|None=Field(default=None,max_length=2048)
    judgment:str|None=Field(default=None,max_length=64)
    intention:str|None=Field(default=None,max_length=64)
    context_mode:str|None=Field(default=None,max_length=64)
    effect_status:Literal['NONE','VERIFIED_EFFECT','UNKNOWN']='NONE'

    @model_serializer(mode='wrap')
    def legacy_communication_wire(self, handler):
        value = handler(self)
        if self.communication_purpose is None:
            value.pop('communication_purpose', None)
        if self.recipient_context is None:
            value.pop('recipient_context', None)
        if self.reply_character_limit == 16384:
            value.pop('reply_character_limit', None)
        return value
