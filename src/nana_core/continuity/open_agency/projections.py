"""Typed, bounded, erasable-source-filtered B10 views; no mutation authority."""
import json
from typing import Literal
from ...contracts import DTO,CoreError
from ..records import RecordService
from ..revision import state_token

class GoalNode(DTO):
    goal_id:str
    parent_id:str|None
    dependencies:tuple[str,...]
    state:str
    version:int
    priority:int
    deadline_us:int|None
    work_state:str
    cursor:int
    plan_record_id:str
    source_record_ids:tuple[str,...]
class LearningWorkView(DTO):
    work_id:str
    state:str
    stage:str
    revision:int
    domain:str
    cause:str
    baseline_passed:int|None
    transfer_passed:int|None
    lesson_id:str|None
    source_record_ids:tuple[str,...]
class SkillVersionView(DTO):
    record_id:str
    name:str
    revision:int
    state:str
    source_digest:str
    realm:str
    installation_authority:Literal[False]=False
class DeliveryView(DTO):
    record_id:str
    intention_id:str
    result:str
    expires_at_us:int
    execution_authority:Literal[False]=False
class OpenAutonomyView(DTO):
    derived:Literal[True]=True
    subject_id:str
    state_token:str
    goals:tuple[GoalNode,...]
    learning:tuple[LearningWorkView,...]
    skills:tuple[SkillVersionView,...]
    delivery:tuple[DeliveryView,...]
    coverage:Literal['BOUNDED_SOURCE_FILTERED']='BOUNDED_SOURCE_FILTERED'

def project_open(store,policy,*,scopes,limit=32):
    if store.schema_target<12:raise CoreError('OPEN_AGENCY_SCHEMA_REQUIRED')
    if not scopes or not set(scopes)<=set(policy.allowed_scopes) or not 1<=limit<=64:raise CoreError('OPEN_VIEW_SCOPE_DENIED')
    token=state_token(store);records=RecordService(store)
    def visible(rid):
        row=store.one('continuity_records',rid)
        return bool(row and row['scope'] in scopes and row['privacy_class'] in policy.readable_privacy and row['lifecycle']=='ACTIVE' and records.current_support(rid))
    goals=[];learning=[];skills=[];delivery=[]
    for g in store.db.execute('SELECT * FROM goals ORDER BY last_served_us DESC,rowid DESC LIMIT ?',(limit,)):
        meta=json.loads(g['body_json']);rid=meta.get('plan_record_id')
        if not rid or not visible(rid):continue
        j=store.one('jobs',meta['work_id'])
        goals.append(GoalNode(goal_id=g['goal_id'],parent_id=g['parent_id'],dependencies=tuple(json.loads(g['depends_json'])),state=g['state'],version=g['version'],priority=g['priority'],deadline_us=g['deadline_us'],work_state=j['state'],cursor=j['cursor'],plan_record_id=rid,source_record_ids=(rid,)))
    for j in store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY updated_at_us DESC LIMIT ?",(limit,)):
        if not visible(j['record_id']):continue
        b=records.read(j['record_id'])['payload'];results=b['results']
        learning.append(LearningWorkView(work_id=j['job_id'],state=j['state'],stage=b['stage'],revision=j['revision'],domain=b['spec']['domain'],cause=b['cause'],baseline_passed=results.get('BASELINE',{}).get('passed'),transfer_passed=results.get('TRANSFER',{}).get('passed'),lesson_id=b.get('lesson_id'),source_record_ids=(j['record_id'],)))
    for row in store.db.execute("SELECT * FROM continuity_records WHERE record_kind IN ('CODE_SKILL','DELIVERY_DECISION') AND lifecycle='ACTIVE' ORDER BY rowid DESC LIMIT ?",(limit*2,)):
        if not visible(row['record_id']):continue
        b=records.read(row['record_id'])['payload']
        if row['record_kind']=='CODE_SKILL':skills.append(SkillVersionView(record_id=row['record_id'],name=b['spec']['name'],revision=b['spec']['revision'],state=b['state'],source_digest=b['source_digest'],realm=b['realm']))
        else:delivery.append(DeliveryView(record_id=row['record_id'],intention_id=b['intention_id'],result=b['result'],expires_at_us=b['expires_at_us']))
    if token!=state_token(store):raise CoreError('OPEN_VIEW_SOURCE_STALE')
    return OpenAutonomyView(subject_id=store.identity['identity_id'],state_token=token,goals=tuple(goals),learning=tuple(learning),skills=tuple(skills),delivery=tuple(delivery))
