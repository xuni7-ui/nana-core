"""Explicitly opted-in source lifecycle, bounded to that configured source.

Source withdrawal can remove its own support, never another source, a Grant or
past physical effect. A correction is uncertainty-preserving, not model authority.
"""
import json
from ...contracts import CoreError
from ...storage import digest
from ..records import RecordService
from ..memory import MemoryService

def apply_lifecycle(intake,memory_id):
    records=RecordService(intake.runtime.store);m=records.memory.read(memory_id);raw=json.loads(m['text'])
    source=intake.sources.get(raw.get('source_id'))
    if not source or not source.accept_lifecycle:return 'CURRENT'
    body=json.loads(raw['content']);revision=body.get('revision');state=body.get('lifecycle','CURRENT')
    if type(revision)!=int or not 1<=revision<=1000000000 or state not in {'CURRENT','CORRECTED','WITHDRAWN'}:raise CoreError('SOURCE_LIFECYCLE_INVALID')
    key='source-lifecycle:'+digest([source.source_id,source.location,intake.scope])
    s=intake.runtime.store
    old=s.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='RUNTIME_WORK' AND target_id=? ORDER BY rowid DESC LIMIT 1",(key,)).fetchone()
    previous=records.read(old[0])['payload'] if old else None
    if previous:
        if revision<previous['revision']:raise CoreError('STALE_SOURCE_REVISION')
        if revision==previous['revision']:
            if previous['source_digest']!=raw['source_digest']:raise CoreError('SOURCE_REVISION_COLLISION')
            return state
    ids=[] if not previous else previous['supported_memory_ids']
    # Full input correlation is checked by intake before calling this function.
    # Only memories recorded under this source binding can be retired.
    if state in {'CORRECTED','WITHDRAWN'}:
        for mid in ids:
            h=s.one('memories',mid)
            if h and h['lifecycle']=='ACTIVE':MemoryService(s,intake.runtime.authority).set_lifecycle(mid,'SUPPRESSED',intake.runtime.authority)
        ids=[]
    if state!='WITHDRAWN':ids=list(dict.fromkeys((*ids,memory_id)))
    if len(ids)>32:raise CoreError('SOURCE_LIFECYCLE_BOUND_REVIEW_REQUIRED')
    with s.transaction('life.source_lifecycle_observed',{'source_id':source.source_id,'revision':revision,'state':state}) as tx:
        records.create(tx,kind='RUNTIME_WORK',scope=intake.scope,payload={'kind':'SOURCE_LIFECYCLE','revision':revision,'state':state,'source_digest':raw['source_digest'],'supported_memory_ids':ids,'source_binding_digest':digest(source.model_dump(mode='json'))},memories=(memory_id,),supersedes=old[0] if old else None,target_id=key)
    return state
