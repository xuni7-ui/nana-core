"""Rebuildable, bounded living journal; never a second personality/history store."""
import json
from typing import Literal
from ..contracts import DTO,CoreError
from .records import RecordService
from .revision import state_token

class JournalEntry(DTO):
    entry_id: str
    kind: str
    phase: str
    record_id: str | None
    occurred_at_us: int | None
    observed_at_us: int
    recorded_at_us: int
    linkage_ids: tuple[str,...]
    facts: dict

class LivingJournal(DTO):
    derived: Literal[True] = True
    state_token: str
    entries: tuple[JournalEntry,...]
    coverage: Literal['BOUNDED_FILTERED_VIEW'] = 'BOUNDED_FILTERED_VIEW'


def living_journal(store,*,scopes,privacy_classes,limit=32):
    if not 1<=limit<=128 or not scopes:raise CoreError('JOURNAL_REQUEST_INVALID')
    store.ensure_privacy_current();token=state_token(store);records=RecordService(store);entries=[]
    kinds={'SUBJECT_CYCLE','CONSTRAINT_OUTCOME','ADOPTED_GOAL','EXPERIENCE','REFLECTION','LESSON','MAINTENANCE_CANDIDATE','SKILL_PROPOSAL','OPEN_LEARNING','LEARNING_TRIAL','CODE_SKILL','DELIVERY_DECISION'}
    sql=f"SELECT * FROM continuity_records WHERE scope IN ({','.join('?' for _ in scopes)}) AND lifecycle='ACTIVE' ORDER BY created_at_us DESC,rowid DESC LIMIT ?"
    for row in store.db.execute(sql,(*scopes,limit*4)):
        if row['record_kind'] not in kinds or row['privacy_class'] not in privacy_classes or not records.current_support(row['record_id']):continue
        body=records.read(row['record_id'])['payload'];event=store.event(row['event_id']);facts={};links=[];phase='RECORDED'
        if row['record_kind']=='SUBJECT_CYCLE':
            phase=body.get('evaluation',{}).get('disposition','CONSIDERED') if body.get('evaluation') else 'CONSIDERED'
            facts={'judgment':body['judgment']['stance'],'normative':body.get('evaluation',{}).get('normative') if body.get('evaluation') else None,'intention_kind':body['intention']['kind'],'self_generated':body['intention']['self_generated'],'behavior':body['intention'].get('behavior'),'actual_effect':'NOT_ESTABLISHED_BY_INTENTION'}
            links=[x for x in (body['cycle_id'],body.get('intention_id')) if x]
        elif row['record_kind']=='CONSTRAINT_OUTCOME':
            phase='MANAGER_'+body['result'];facts={'wanted':True,'actual_effect':body['actual_effect'],'reason_codes':body['reason_codes']};links=[body['intention_id']]
        elif row['record_kind']=='EXPERIENCE':phase='VERIFIED_EXPERIENCE';facts={'meaning':'OUTCOME_NOT_PERSONALITY_BY_FIAT'}
        elif row['record_kind']=='MAINTENANCE_CANDIDATE':phase='INFERRED_CANDIDATE';facts={'coverage':body['coverage'],'authority':body['authority']}
        elif row['record_kind']=='SKILL_PROPOSAL':phase='TESTED_OFFLINE_PROCEDURE';facts={'real_installation':False}
        elif row['record_kind']=='OPEN_LEARNING':phase=body['stage'];facts={'cause':body['cause'],'domain':body['spec']['domain'],'learning_not_fact_invention':True}
        elif row['record_kind']=='LEARNING_TRIAL':phase='INDEPENDENT_TRIAL';facts={'domain':body['domain'],'transfer_passed':body['results']['TRANSFER']['all_passed']}
        elif row['record_kind']=='CODE_SKILL':phase=body['state'];facts={'source_digest':body['source_digest'],'realm':body['realm'],'installation_authority':False}
        elif row['record_kind']=='DELIVERY_DECISION':phase=body['result'];facts={'desire_not_erased':True,'authority_granted':False};links=[body['intention_id']]
        entries.append(JournalEntry(entry_id=event['event_id']+':'+row['record_id'],kind=row['record_kind'],phase=phase,record_id=row['record_id'],occurred_at_us=event['occurred_at_us'],observed_at_us=event['observed_at_us'],recorded_at_us=event['recorded_at_us'],linkage_ids=tuple(links),facts=facts))
    # An action state is a separate fact from wanting/planning and from quality.
    for action in store.db.execute('SELECT * FROM actions ORDER BY rowid DESC LIMIT ?',(limit,)):
        marker=json.loads(action['args_json']);rid=marker.get('action_payload_record') if isinstance(marker,dict) else None
        head=store.one('continuity_records',rid) if rid else None
        if not head or head['scope'] not in scopes or head['privacy_class'] not in privacy_classes or head['lifecycle']!='ACTIVE' or not records.current_support(rid):continue
        meta=json.loads(action['body_json']);event=store.event(meta.get('verification_event_id') or head['event_id'])
        phase='VERIFIED_EFFECT' if action['state']=='SUCCEEDED' else 'UNKNOWN' if action['state'] in {'DISPATCHING','UNKNOWN','PENDING_VERIFY'} else 'ACTION_BLOCKED_EXECUTION' if action['state']=='BLOCKED' else 'PLANNED_OR_CANCELLED'
        entries.append(JournalEntry(entry_id=action['action_id'],kind='ACTION',phase=phase,record_id=rid,occurred_at_us=event['occurred_at_us'],observed_at_us=event['observed_at_us'],recorded_at_us=event['recorded_at_us'],linkage_ids=tuple(x for x in (action['action_id'],action['goal_id'],action['plan_id']) if x),facts={'action_state':action['state'],'blocked_reason':meta.get('blocked_reason'),'quality_correctness':'SEPARATELY_VERIFIED'}))
    if token!=state_token(store):raise CoreError('JOURNAL_STALE')
    return LivingJournal(state_token=token,entries=tuple(sorted(entries,key=lambda x:(x.recorded_at_us,x.entry_id),reverse=True)[:limit]))
