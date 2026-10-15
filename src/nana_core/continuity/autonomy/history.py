"""Append-only typed dispositions on existing records/events, privacy-aware reads."""
import json
from ...contracts import CoreError
from ...storage import canonical
from ..records import RecordService
from .contracts import DispositionView

def enabled(store): return store.schema_target>=9

def record_disposition(store,tx,*,cycle_id,intention_id,intention_revision,scope,parent_record,stage,code,normative,wanted,reason_refs=()):
    body=dict(cycle_id=cycle_id,intention_id=intention_id,intention_revision=intention_revision,stage=stage,code=code,
        normative=normative,wanted=wanted,reason_refs=reason_refs,at_us=store.clock.utc_now_us())
    rid=RecordService(store).create(tx,kind='INTENTION_DISPOSITION',scope=scope,payload=body,records=(parent_record,),target_id=intention_id or cycle_id)
    return rid

def dispositions(store,*,scope,intention_id=None,privacy_classes=('PUBLIC','PROJECT','PERSONAL'),limit=64):
    if not enabled(store):return ()
    where=' AND target_id=?' if intention_id else ''
    params=(scope,intention_id,min(limit,128)) if intention_id else (scope,min(limit,128))
    rows=store.db.execute("SELECT * FROM continuity_records WHERE record_kind='INTENTION_DISPOSITION' AND scope=? AND lifecycle='ACTIVE'"+where+" ORDER BY created_at_us DESC,rowid DESC LIMIT ?",params).fetchall()
    out=[];records=RecordService(store)
    for raw in rows:
        r=dict(raw)
        if r['privacy_class'] not in privacy_classes or not records.current_support(r['record_id']):continue
        body=records.read(r['record_id'])['payload']
        if intention_id is None or body['intention_id']==intention_id:out.append(DispositionView.model_validate_json(canonical({'record_id':r['record_id'],**body})))
    return tuple(out)
