"""Bounded, host-bound project status projection; not Subject memory or will.

One explicitly selected SSOT header, never whole documents, logs or arbitrary
retrieval. A status snapshot cannot become a personal experience or authority.
"""
import hashlib,json,os,stat
from pathlib import Path,PurePosixPath
from typing import Literal
from pydantic import Field,model_validator
from ..contracts import DTO,CoreError
from .privacy import _json_object

START=b'<!-- CORE_PROJECT_CURRENT_STATE_V1 -->'
END=b'<!-- /CORE_PROJECT_CURRENT_STATE_V1 -->'
PREFIX_LIMIT=12288

def relative(value):
 p=PurePosixPath(value)
 if not value or p.is_absolute() or any(x in {'.','..'} for x in value.split('/')) or '\\' in value or len(value)>256:
  raise ValueError('explicit relative project source required')
 return value

class ProjectStateBinding(DTO):
 relative_path:str
 source_id:str=Field(min_length=1,max_length=96)
 scope:str=Field(min_length=1,max_length=96)
 privacy_class:Literal['PUBLIC','PROJECT']='PROJECT'
 max_age_us:int=Field(default=86400_000_000,ge=60_000_000,le=7*86400_000_000)
 @model_validator(mode='after')
 def valid(self):relative(self.relative_path);return self

class ProjectCurrentState(DTO):
 schema_version:Literal[1]=1
 project_id:str=Field(min_length=1,max_length=96)
 scope:str=Field(min_length=1,max_length=96)
 privacy_class:Literal['PUBLIC','PROJECT']='PROJECT'
 revision:int=Field(ge=1)
 as_of_us:int=Field(ge=0)
 stage:str=Field(min_length=1,max_length=64)
 workstream:str=Field(min_length=1,max_length=128)
 status:str=Field(min_length=1,max_length=128)
 progress:tuple[str,...]=Field(min_length=1,max_length=8)
 open_gates:tuple[str,...]=Field(default=(),max_length=8)
 evidence_refs:tuple[str,...]=Field(default=(),max_length=8)
 @model_validator(mode='after')
 def bounded(self):
  if any(not 1<=len(s)<=240 for s in (*self.progress,*self.open_gates)):raise ValueError('bounded current-state statements required')
  for ref in self.evidence_refs:relative(ref)
  if len(self.model_dump_json().encode())>8192:raise ValueError('current-state projection too large')
  return self

class ProjectStateSource:
 def __init__(self,root,binding):
  if type(binding) is not ProjectStateBinding:raise CoreError('PROJECT_STATE_BINDING_REQUIRED')
  self.root=Path(root).absolute();self.binding=binding
 def projection(self,*,scopes,privacy_classes,now_us):
  b=self.binding
  # Scope/privacy before opening even a byte of the source.
  if b.scope not in scopes or b.privacy_class not in privacy_classes:return None
  try:
   path=self.root/b.relative_path
   if self.root.resolve()!=self.root or path.resolve()!=path:raise ValueError()
   fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
   with os.fdopen(fd,'rb') as stream:
    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError()
    prefix=stream.read(PREFIX_LIMIT)
   begin=prefix.find(START)
   if not 0<=begin<=512 or prefix.count(START)!=1:raise ValueError()
   end=prefix.find(END,begin+len(START))
   if end<0:raise ValueError()
   raw=prefix[begin+len(START):end].strip()
   if len(raw)>8192:raise ValueError()
   state=ProjectCurrentState.model_validate_json(json.dumps(json.loads(raw,object_pairs_hook=_json_object)))
   if state.scope!=b.scope or state.privacy_class!=b.privacy_class:raise ValueError()
   if state.as_of_us>now_us or now_us-state.as_of_us>b.max_age_us:raise CoreError('PROJECT_CURRENT_STATE_STALE')
  except CoreError:raise
  except (OSError,ValueError,TypeError):raise CoreError('PROJECT_CURRENT_STATE_UNAVAILABLE') from None
  return {'attribution':'EXTERNAL_PROJECT_STATUS_NOT_SUBJECT_EXPERIENCE','authority':'PROJECT_FACTS_ONLY_NOT_EXECUTION_AUTHORITY',
   'source':{'source_id':b.source_id,'relative_path':b.relative_path,'projection_version':1,'sha256':hashlib.sha256(raw).hexdigest()},
   'state':state.model_dump(mode='json')}
