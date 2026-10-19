"""Finite synthetic content/workspace port implementation, not a real adapter.

World JSON holds external fixture state/effect receipts only. Subject authority,
learning and source records remain exclusively in the existing Store.
"""
import json, re, unicodedata
from typing import Literal, Any
from types import MappingProxyType
from pydantic import Field
from ...contracts import DTO,CoreError
from ...storage import canonical,digest

URI=r'^(?:synthetic|project)://[A-Za-z0-9/._:-]{1,160}$'
class ObserveArgs(DTO): pass
class ComputeArgs(DTO):
    method: Literal['IDENTITY','NAIVE_SUM','NUMERIC_SUM','SPLIT_SPACE','UNICODE_WORDS','SORT','JOIN','CASEFOLD','PYTHON_TOP_DEFS','PYTHON_AST_API']
    data_privacy: Literal['PUBLIC','PROJECT','PERSONAL','SECRET'] = 'PUBLIC'
    data: Any = None
    input_from: str | None = Field(default=None,pattern=r'^[a-z][a-z0-9._-]{0,63}$')
class PublishArgs(DTO):
    data_privacy: Literal['PUBLIC','PROJECT','PERSONAL','SECRET'] = 'PUBLIC'
    data: Any = None
    input_from: str | None = Field(default=None,pattern=r'^[a-z][a-z0-9._-]{0,63}$')
class ContactArgs(PublishArgs):
    admission_id: str | None = None
class SkillArgs(PublishArgs):
    skill_record_id: str

MODELS={'world.observe':ObserveArgs,'world.compute':ComputeArgs,'world.publish':PublishArgs,'world.contact':ContactArgs,'world.skill':SkillArgs}

def bounded_data(data):
    raw=canonical(data)
    if len(raw.encode())>8192:raise CoreError('WORLD_DATA_BOUND')
    def depth(v,n=0):
        if n>8:raise CoreError('WORLD_DEPTH_BOUND')
        if isinstance(v,(list,dict)):
            if len(v)>256:raise CoreError('WORLD_COLLECTION_BOUND')
            for x in (v.values() if isinstance(v,dict) else v):depth(x,n+1)
    depth(data);return data

class LocalWorldRegistry:
    """Exact sealed catalogue; declarations are not Grants or model-written code."""
    definitions=MappingProxyType(MODELS)
    verify_capability='world.action.verify'
    @staticmethod
    def is_write(capability):return capability in {'world.publish','world.contact'}
    @staticmethod
    def payload_privacy(payload):
        from ..memory import PRIVACY_RANK
        labels=['PUBLIC']
        def visit(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    if key in {'privacy_class','data_privacy'} and isinstance(item,str) and item in PRIVACY_RANK:labels.append(item)
                    visit(item)
            elif isinstance(value,(list,tuple)):
                for item in value:visit(item)
        visit(payload);return max(labels,key=PRIVACY_RANK.get)
    def validate(self,capability,resource,args):
        if capability not in MODELS or not re.fullmatch(URI,resource):raise CoreError('WORLD_SCOPE_DENIED')
        result=MODELS[capability].model_validate(args).model_dump()
        bounded_data(result)
        return result

def transform(method,data):
    bounded_data(data)
    if method in {'PYTHON_TOP_DEFS','PYTHON_AST_API'}:
        from ..project_work.analysis import inventory
        return inventory(method,data)
    if method=='IDENTITY':return data
    if method in {'NAIVE_SUM','NUMERIC_SUM'}:
        if not isinstance(data,list):raise CoreError('WORLD_NUMERIC_INPUT_REQUIRED')
        values=[x for x in data if type(x) in (int,float)]
        if method=='NAIVE_SUM':return sum(int(x) for x in values) # testable loss of fractional precision
        return sum(values)
    if method=='SORT':
        if not isinstance(data,list) or any(type(x) not in (int,float) for x in data):raise CoreError('WORLD_SORT_INPUT_REQUIRED')
        return sorted(data)
    if method=='JOIN':
        if not isinstance(data,list) or any(type(x) is not str for x in data):raise CoreError('WORLD_TEXT_INPUT_REQUIRED')
        return ' '.join(data)
    if type(data) is not str:raise CoreError('WORLD_TEXT_INPUT_REQUIRED')
    if method=='CASEFOLD':return data.casefold()
    if method=='SPLIT_SPACE':return data.split(' ')
    if method=='UNICODE_WORDS':return unicodedata.normalize('NFKC',data).split()
    raise CoreError('WORLD_METHOD_UNKNOWN')

def execute_world(port,inv):
    args=LocalWorldRegistry().validate(inv.capability,inv.resource,inv.args)
    body=port._load()
    if inv.capability=='world.observe':
        classification=body.get('observation_privacy',{}).get(inv.resource,'UNKNOWN')
        if classification not in getattr(port,'permitted_privacy',('PUBLIC',)):raise CoreError('WORLD_DATA_PRIVACY_DENIED')
        value=body.get('observables',{}).get(inv.resource)
        if value is None:raise CoreError('WORLD_OBSERVATION_UNAVAILABLE')
        return {'data':value,'data_privacy':classification,'revision':digest(value),'origin':'SYNTHETIC_WORLD_OBSERVATION'}
    if inv.capability=='world.compute':return {'data':transform(args['method'],args['data']),'data_privacy':args['data_privacy'],'method':args['method']}
    if inv.capability=='world.skill':
        controller=getattr(port,'code_skills',None)
        if controller is None:raise CoreError('CODE_SKILL_CONTROLLER_UNAVAILABLE')
        return {'data':controller.invoke(args['skill_record_id'],args['data']),'data_privacy':args['data_privacy'], 'skill_record_id':args['skill_record_id']}
    if inv.capability=='world.contact':
        # Admission is checked again at dispatch through a trusted callback.
        if not getattr(port,'delivery',None):raise CoreError('DELIVERY_ADMISSION_REQUIRED')
        port.delivery.require(args['admission_id'],inv.resource,invocation=inv)
        contact=body.get('observables',{}).get(inv.resource,{})
        if contact.get('availability')!='AVAILABLE':raise CoreError('RECIPIENT_NOT_AVAILABLE')
        return {'data':args['data'],'data_privacy':args['data_privacy'],'delivered':'SYNTHETIC_ONLY','reaction':contact.get('reaction','NO_RESPONSE')}
    return {'data':args['data'],'data_privacy':args['data_privacy'],'published':'SYNTHETIC_ONLY'}
