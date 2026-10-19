"""Finite host binding. Neither a target description nor a command is a Grant."""
import os,stat,json
from pathlib import Path
from typing import Literal
from pydantic import Field,model_validator
from ...contracts import DTO,CoreError
from ...storage import digest

class ApplicationTask(DTO):
    task_id:str=Field(pattern=r'^[a-z][a-z0-9_-]{0,31}$')
    kind:Literal['DOCUMENT','FORM']
    initial:str=Field(default='',max_length=1024)
    wanted:str|dict[str,str]
    fields:tuple[str,...]=Field(default=(),max_length=4)
    context:str=Field(default='notes',min_length=1,max_length=64)
    @model_validator(mode='after')
    def valid(self):
        if self.kind=='DOCUMENT':
            if type(self.wanted)!=str or len(self.wanted)>512 or self.fields:raise ValueError('document contract')
        else:
            if type(self.wanted)!=dict or not 1<=len(self.wanted)<=4 or len(set(self.fields))!=len(self.fields) or not set(self.wanted)<=set(self.fields):raise ValueError('form contract')
            if any(not k.isidentifier() or len(k)>32 for k in self.fields) or any(type(v)!=str or len(v)>128 for v in self.wanted.values()):raise ValueError('form bound')
        return self

class OwnedTarget(DTO):
    version:Literal[1]=1
    workspace:str
    pid:int=Field(gt=0)
    uid:int=Field(ge=0)
    process_start:str
    directory_inode:int=Field(gt=0)
    control_inode:int=Field(gt=0)
    query_inode:int=Field(gt=0)
    instance_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    tasks:tuple[ApplicationTask,...]=Field(min_length=1,max_length=16)
    @model_validator(mode='after')
    def unique(self):
        if len({t.task_id for t in self.tasks})!=len(self.tasks):raise ValueError('duplicate task')
        keys={t.task_id for t in self.tasks}
        if any(key+'-batch' in keys for key in keys):raise ValueError('derived objective collision')
        return self
    @property
    def binding(self):return digest(self.model_dump(mode='json'))

def process_start(pid):
    try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
    except (OSError,IndexError):raise CoreError('HANDS_TARGET_UNAVAILABLE') from None

def private_directory(root):
    p=Path(root).absolute()
    if p!=p.resolve():raise CoreError('HANDS_SYMLINK_DENIED')
    s=p.stat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077:raise CoreError('HANDS_PRIVATE_OWNER_REQUIRED')
    return p

def load_target(path):
    p=Path(path).absolute();private_directory(p.parent)
    if p.name!='profile.json':raise CoreError('HANDS_EXPLICIT_PROFILE_REQUIRED')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise CoreError('HANDS_PROFILE_INVALID')
        raw=f.read(32769)
    if len(raw)>32768:raise CoreError('HANDS_PROFILE_BOUND')
    try:return OwnedTarget.model_validate_json(raw)
    except ValueError:raise CoreError('HANDS_PROFILE_INVALID') from None

def command_plan(method,data):
    task=data['task'];wanted=task['wanted']
    if task['kind']=='DOCUMENT':
        if method not in {'HANDS_APPEND','HANDS_REPLACE'}:raise CoreError('HANDS_METHOD_TASK_MISMATCH')
        commands=[{'op':'APPEND' if method=='HANDS_APPEND' else 'REPLACE','value':wanted.strip()}]
    else:
        if method not in {'HANDS_POSITIONAL','HANDS_NAMED'}:raise CoreError('HANDS_METHOD_TASK_MISMATCH')
        name=next(iter(wanted));field=task['fields'][0] if method=='HANDS_POSITIONAL' else name
        commands=([{'op':'SET_FIELD','field':k,'value':''} for k in task['fields']] if method=='HANDS_NAMED' else [])+[{'op':'SET_FIELD','field':field,'value':wanted[name]},{'op':'SUBMIT'}]
    return {'task_id':task['task_id'],'revision':data['revision'],'commands':commands}

class HandsEffectContext(DTO):
    action_id:str
    subject_id:str
    goal_id:str
    plan_id:str
    plan_step_id:str
    capability:Literal['world.publish']='world.publish'
    target_kind:Literal['OWNED_APPLICATION_PROCESS']='OWNED_APPLICATION_PROCESS'
    target_identity:str
    target_ownership_evidence:str
    allowed_effect:tuple[str,...]=Field(min_length=1,max_length=9)
    expected_outcome_digest:str=Field(pattern=r'^[a-f0-9]{64}$')
    verification_method:Literal['READ_ONLY_IPC_AND_EXTERNAL_FILE']='READ_ONLY_IPC_AND_EXTERNAL_FILE'
    grant_reference:str
    budget_reference:tuple[str,...]=Field(min_length=1,max_length=3)
    created_at_us:int=Field(ge=0)
    deadline_us:int=Field(ge=0)
    idempotency_key:str
    grants_authority:Literal[False]=False
