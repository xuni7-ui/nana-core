"""Pure selection among explicitly supplied, validated endpoint authorizations.

Metadata is operator-declared and never proves inference or grants a new budget.
Selection does not load credentials, invoke endpoints, retry or buy services.
"""
from typing import Literal
from pydantic import Field
from ..contracts import DTO,CoreError
from .contracts import Endpoint


class ModelCapabilities(DTO):
    alias:str
    model_id:str
    provider:str=Field(min_length=1,max_length=128)
    service_kind:Literal['real_model','protocol_simulator','unverified']
    context_limit:int=Field(ge=256,le=2_000_000)
    tool_support:tuple[str,...]=()
    privacy_class:Literal['local_only','development_remote']
    cost_class:Literal['free','low','medium','high']
    latency_class:Literal['fast','normal','slow']
    allowed_task_classes:tuple[str,...]=Field(min_length=1)


class TaskRequirements(DTO):
    task_class:str=Field(min_length=1,max_length=128)
    context_tokens:int=Field(ge=1,le=2_000_000)
    tools:tuple[str,...]=()
    privacy:Literal['local_only','development_remote']='local_only'
    max_cost_class:Literal['free','low','medium','high']='free'


class ModelSelectionPolicy:
    COST={'free':0,'low':1,'medium':2,'high':3}
    LATENCY={'fast':0,'normal':1,'slow':2}
    def select(self,requirements,authorized_endpoints,metadata):
        requirements=TaskRequirements.model_validate(requirements.model_dump())
        endpoints=[Endpoint.model_validate(e.model_dump()) for e in authorized_endpoints]
        if len({e.alias for e in endpoints})!=len(endpoints):raise CoreError('MODEL_SELECTION_ALIAS_COLLISION')
        candidates=[]
        for raw in metadata:
            m=ModelCapabilities.model_validate(raw.model_dump())
            e=next((e for e in endpoints if e.alias==m.alias),None)
            if not e:continue
            if (m.model_id,m.service_kind)!=(e.model,e.service_kind):raise CoreError('MODEL_METADATA_BINDING_MISMATCH')
            if m.service_kind!='real_model':continue
            actual_local=e.account_scope=='local_offline'
            if (m.privacy_class=='local_only')!=actual_local:raise CoreError('MODEL_PRIVACY_METADATA_MISMATCH')
            if requirements.privacy=='local_only' and not actual_local:continue
            if requirements.context_tokens>m.context_limit or requirements.task_class not in m.allowed_task_classes:continue
            if not set(requirements.tools)<=set(m.tool_support):continue
            if self.COST[m.cost_class]>self.COST[requirements.max_cost_class]:continue
            candidates.append((self.COST[m.cost_class],self.LATENCY[m.latency_class],m.alias,e))
        if not candidates:raise CoreError('MODEL_SELECTION_BLOCKED')
        return min(candidates,key=lambda c:c[:3])[-1]
