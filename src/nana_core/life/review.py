"""A local chat client and human-authored structured review, not another Subject.

Private IPC only; no HTTP/UI framework or delivery surface. Review files are
host-local ratings, never source truth or an automatic readiness decision.
"""
import json,os,tempfile
from pathlib import Path
from uuid import UUID,uuid4
from typing import Literal
from pydantic import Field,model_validator
from ..contracts import DTO,CoreError
from .config import home_path
from .control import request

class HumanReview(DTO):
    review_id:str
    identity_id:str
    reviewer:Literal['HUMAN']='HUMAN'
    category:Literal['NATURALNESS','SHARED_LIFE']
    observed_minutes:int=Field(ge=1,le=1440)
    naturalness:int=Field(ge=1,le=5)
    grounding:int=Field(ge=1,le=5)
    continuity:int=Field(ge=1,le=5)
    boundaries:int=Field(ge=1,le=5)
    excessive_analysis:bool
    unsupported_experience:bool
    result:Literal['PASS','NEEDS_WORK']

    @model_validator(mode='after')
    def valid_ids(self):
        if str(UUID(self.review_id))!=self.review_id or str(UUID(self.identity_id))!=self.identity_id:raise ValueError('UUID required')
        return self


def record_review(home,review):
    if type(review) is not HumanReview:raise CoreError('HUMAN_TYPED_REVIEW_REQUIRED')
    review=HumanReview.model_validate_json(review.model_dump_json());home=home_path(home)
    import sqlite3
    # Read only; do not acquire an operator token or a second writer lock.
    try:
        with sqlite3.connect('file:'+str(home/'subject/self.db')+'?mode=ro',uri=True) as db:
            row=db.execute('SELECT identity_id FROM identities').fetchone()
        if row is None:raise CoreError('HUMAN_REVIEW_SUBJECT_UNAVAILABLE')
        identity=row[0]
    except sqlite3.Error:raise CoreError('HUMAN_REVIEW_SUBJECT_UNAVAILABLE') from None
    if review.identity_id!=identity:raise CoreError('HUMAN_REVIEW_SUBJECT_MISMATCH')
    folder=home/'human-reviews'
    if folder.is_symlink():raise CoreError('HUMAN_REVIEW_PATH_DENIED')
    folder.mkdir(mode=0o700,exist_ok=True)
    if folder.stat().st_mode&0o077 or folder.stat().st_uid!=os.getuid():raise CoreError('HUMAN_REVIEW_PATH_DENIED')
    target=folder/(review.review_id+'.json')
    if target.exists() or target.is_symlink():raise CoreError('HUMAN_REVIEW_ALREADY_RECORDED')
    fd,tmp=tempfile.mkstemp(dir=folder,prefix='.review-')
    try:
        with os.fdopen(fd,'w') as out:out.write(review.model_dump_json());out.flush();os.fsync(out.fileno())
        os.link(tmp,target);directory=os.open(folder,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:os.unlink(tmp)
    return {'state':'HUMAN_DECLARED_RATINGS_RECORDED','review_id':review.review_id,'category':review.category,
        'transcript_saved':False,'subject_memory_changed':False,'readiness_upgraded':False}


def chat(home,*,binding_id='cloud.cli',topic='daily',privacy='PROJECT'):
    # Explicit public/project review only; never silently relabel PERSONAL.
    print('本入口仅用于 PUBLIC/PROJECT 内容。不要输入密钥、私人历史或 SECRET。/quit 退出；不保存对话原文。',flush=True)
    while True:
        try:text=input('你: ')
        except (EOFError,KeyboardInterrupt):return
        if text=='/quit':return
        if not text.strip():continue
        if len(text)>2048:print('输入超过2048字符，未发送。',flush=True);continue
        event_id=str(uuid4())
        try:
            response=request(home,{'operation':'surface','observation':{'binding_id':binding_id,'event_id':event_id,'topic':topic,'text':text,'privacy_class':privacy}})
        except (CoreError,OSError):
            print('请求状态未确认；不会自动重发。事件ID '+event_id,flush=True);return
        if not response['ok']:
            print('未生成候选：'+response.get('code','REJECTED'),flush=True);continue
        result=response['result']
        if result.get('text'):print('回应: '+result['text'],flush=True)
        print('['+result.get('render_state',result.get('state','UNKNOWN'))+'; event '+event_id+']',flush=True)
