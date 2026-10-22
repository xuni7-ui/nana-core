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


def chat(home,*,binding_id='cloud.cli',topic='daily',privacy='PROJECT',retain_shared_life=False):
    # Explicit public/project review only; never silently relabel PERSONAL.
    print('本入口仅用于 PUBLIC/PROJECT 内容。不要输入密钥、私人历史或 SECRET。/quit 退出；不保存对话原文。',flush=True)
    last=None
    if retain_shared_life:print('已显式启用本入口对话留存：双方发言及其来源进入当前Subject，可撤回；不会发送真实社交消息。',flush=True)
    while True:
        try:text=input('你: ')
        except (EOFError,KeyboardInterrupt):return
        if text=='/quit':return
        if text=='/self':
            print(json.dumps(request(home,{'operation':'view','view':'self'}),ensure_ascii=False),flush=True);continue
        ratings={'/like':('ACCEPTED',('NATURAL',)),'/partial':('PARTIAL',()),'/ai':('REJECTED',('ASSISTANT_VOICE',)),'/verbose':('REJECTED',('TOO_VERBOSE',)),'/formal':('REJECTED',('TOO_FORMAL',)),'/fake-memory':('REJECTED',('FAKE_MEMORY',)),'/fake-emotion':('REJECTED',('FAKE_EMOTION',)),'/obedient':('REJECTED',('TOO_OBEDIENT',)),'/defensive':('REJECTED',('TOO_DEFENSIVE',))}
        if text in ratings:
            if not last or not last['exchange_record_id']:
                print('该轮未显式留存，不能把评分绑定到持久交流；请用 --retain-shared-life 开始新的授权轮次。',flush=True);continue
            from ..continuity.lived_language import LanguageSample
            from ..clock import Clock
            judgment,tags=ratings[text]
            sample=LanguageSample(sample_id=str(uuid4()),review_target=last['exchange_record_id'],mode='PROJECT' if topic=='project' else 'CASUAL',context=last['input'],candidate_response=last['text'],human_judgment=judgment,exact_feedback=text,reason_tags=tags,provenance='USER_PROVIDED_REVIEW',observed_at_us=Clock().utc_now_us())
            print(json.dumps(request(home,{'operation':'language-feedback','sample':sample.model_dump(mode='json'),'exchange_record_id':last['exchange_record_id']}),ensure_ascii=False),flush=True);continue
        if not text.strip():continue
        if len(text)>2048:print('输入超过2048字符，未发送。',flush=True);continue
        event_id=str(uuid4())
        try:
            response=request(home,{'operation':'surface','observation':{'binding_id':binding_id,'event_id':event_id,'topic':topic,'text':text,'privacy_class':privacy,'retain_shared_life':retain_shared_life}})
        except (CoreError,OSError):
            print('请求状态未确认；不会自动重发。事件ID '+event_id,flush=True);return
        if not response['ok']:
            print('未生成候选：'+response.get('code','REJECTED'),flush=True);continue
        result=response['result']
        last={'input':text[:1024],'text':result.get('text',''),'exchange_record_id':result.get('exchange_record_id')}
        if result.get('text'):print('回应: '+result['text'],flush=True)
        print('['+result.get('render_state',result.get('state','UNKNOWN'))+'; event '+event_id+']',flush=True)


def main():
    import argparse
    p=argparse.ArgumentParser(description='Private human review on the original Runtime; no provider calls until you submit a turn.')
    p.add_argument('--home',type=Path,required=True);p.add_argument('--binding',default='cloud.cli');p.add_argument('--topic',default='daily');p.add_argument('--privacy',choices=['PUBLIC','PROJECT'],default='PROJECT');p.add_argument('--retain-shared-life',action='store_true')
    a=p.parse_args();chat(a.home,binding_id=a.binding,topic=a.topic,privacy=a.privacy,retain_shared_life=a.retain_shared_life)

if __name__=='__main__':main()
