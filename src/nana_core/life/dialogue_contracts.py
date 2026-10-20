"""Semantic proposals, never identity, relationship, goal or execution authority."""
from typing import Literal
from pydantic import Field
from ..contracts import DTO

MeaningKind=Literal['VENT','CHAT','HELP','SHARE','DECLINE_DEPTH','REOPEN','FOCUS','CORRECTION','UNCLEAR','IMPORTANT','PROJECT_STATUS']

class DialogueMeaning(DTO):
    kind:MeaningKind
    confidence:Literal['LOW','RELEVANT','HIGH']='LOW'

class DialogueDraft(DTO):
    text:str|None=Field(default=None,max_length=2048)
    claim_memory_ids:tuple[str,...]=Field(default=(),max_length=16)
    effect_status:Literal['NONE','VERIFIED_EFFECT','UNKNOWN']='NONE'

class DialogueTurn(DTO):
    message_memory_id:str
    topic:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    privacy_class:Literal['PUBLIC','PROJECT','PERSONAL']
    speaker:Literal['USER']
    text:str=Field(min_length=1,max_length=1024)

class DialogueContext(DTO):
    recent_turns:tuple[DialogueTurn,...]=Field(default=(),max_length=6)
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
