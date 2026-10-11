"""Iris 0.3.0 export/row interoperability, not a production DB reader.

All records are explicitly synthetic. Exact supplied JSON is preserved through
LegacyImporter; normalized semantics are a resumable projection of that evidence.
No Iris executable code, model, grants, strategies or execution receipts imported.
"""
from datetime import datetime,timezone
import json
from typing import Literal,Protocol
from pydantic import Field,ValidationError
from ..clock import parse_utc
from ..contracts import DTO,CoreError
from ..storage import canonical,digest
from .legacy import LegacyRecord,LegacyImporter

KINDS={'l1','l2','l2_row','kg_node','kg_edge','user_profile','group_profile','action_ledger','decision_log','conversation_flow','index_meta'}
REQUIRED={
 'l1':('role','content','timestamp','token_count','source'),
 'l2':('id','content'), 'l2_row':('memory_id','content'),
 'kg_node':('id','label','name','content'), 'kg_edge':('source_id','target_id','relation_type'),
 'user_profile':('user_id',),'group_profile':('group_id',),
 'action_ledger':('key','state','updated_at'),'decision_log':('tier','reason','query'),
 'conversation_flow':('ts','umo','role','text'), 'index_meta':('version','embedding_model','embedding_dimensions')}
FIELDS={
 'l1':set(REQUIRED['l1'])|{'metadata','persona_id'},
 'l2':{'id','content','metadata','persona_id','embedding'},
 'l2_row':{'faiss_idx','memory_id','content','metadata','group_id','user_id','timestamp','kg_processed','persona_id'},
 'kg_node':{'id','label','name','content','confidence','access_count','last_access_time','created_time','source_memory_id','group_id','properties'},
 'kg_edge':{'source_id','target_id','relation_type','weight','confidence','access_count','last_access_time','created_time','source_memory_id','properties'},
 'user_profile':{'user_id','user_name','version','historical_names','personality_tags','interests','occupation','language_style','communication_style','emotional_baseline','favorability','bot_relationship','important_dates','taboo_topics','important_events','custom_fields','field_meta','update_tracker'},
 'group_profile':{'group_id','group_name','version','interests','atmosphere_tags','long_term_tags','blacklist_topics','custom_fields','field_meta','update_tracker'},
 'action_ledger':{'key','state','updated_at','op','verify','note','actor','first_at','revision'},
 'decision_log':{'t','t_utc','tier','reason','query','top_k','hits','route','soft_confirm','window','ms','extra'},
 'conversation_flow':{'ts','ts_cst','umo','role','sender_id','sender_name','text','extra'},
 'index_meta':{'version','embedding_model','embedding_dimensions','persona_id','free_list'}}


class ClaimAnnotation(DTO):
    """Operator semantic sidecar, not an invented legacy column or verified fact."""
    subject:str=Field(pattern=r'^synthetic:[a-zA-Z0-9_-]+$')
    predicate:str=Field(min_length=1,max_length=128)
    value:str=Field(min_length=1,max_length=128)
    polarity:bool


class IrisRecord(DTO):
    synthetic_only:Literal[True]
    dataset_id:str=Field(pattern=r'^synthetic:[a-zA-Z0-9_-]{1,64}$')
    kind:str=Field(min_length=1,max_length=32)
    legacy_key:str=Field(min_length=1,max_length=256)
    revision:str=Field(default='1',min_length=1,max_length=32)
    raw_json:str=Field(min_length=2,max_length=150_000)
    legacy_observed_at:str|None=None
    annotation:ClaimAnnotation|None=None


class LegacyMemorySource(Protocol):
    def records(self)->tuple[IrisRecord,...]:...


def iris_time(value):
    if not isinstance(value,str):return None,'UNKNOWN'
    parsed=parse_utc(value)
    if parsed is not None:return parsed,'EXPLICIT_ZONE'
    try:
        dt=datetime.fromisoformat(value)
        if dt.tzinfo is None:
            # Locked Iris/timeutil contract, NOT a global naive-time default.
            return parse_utc(dt.replace(tzinfo=timezone.utc).isoformat()),'LEGACY_NAIVE_UTC_ASSUMPTION'
    except (ValueError,OverflowError):pass
    return None,'UNKNOWN'


def decode(raw):
    try:
        row=json.loads(raw,parse_constant=lambda x:(_ for _ in ()).throw(ValueError()))
        if not isinstance(row,dict):raise ValueError()
        canonical(row)
        return row
    except (ValueError,TypeError):raise CoreError('IRIS_INVALID_JSON') from None


def map_record(record):
    record=IrisRecord.model_validate(record.model_dump())
    if record.kind not in KINDS:raise CoreError('IRIS_UNMAPPED_KIND')
    row=decode(record.raw_json);kind=record.kind
    if any(k not in row for k in REQUIRED[kind]):raise CoreError('IRIS_REQUIRED_FIELD_MISSING')
    non_text={'token_count','state','version','embedding_dimensions'}
    if any(not isinstance(row[k],str) or not row[k] for k in REQUIRED[kind] if k not in non_text):
        raise CoreError('IRIS_FIELD_TYPE_REJECTED')
    metadata=row.get('metadata',{})
    if isinstance(metadata,str):metadata=decode(metadata)
    if not isinstance(metadata,dict):raise CoreError('IRIS_INVALID_METADATA')
    if kind=='l2_row':
        for field in ('group_id','user_id','timestamp','kg_processed'):
            if field in row and field in metadata and row[field] is not None and row[field]!=metadata[field]:
                raise CoreError('IRIS_DUPLICATE_FIELD_CONFLICT')
    if kind in {'l1','conversation_flow'} and row['role'] not in {'user','assistant','system','unknown'}:
        raise CoreError('IRIS_INVALID_ROLE')
    unknown=sorted(set(row)-FIELDS[kind])
    raw_time=(row.get('timestamp') if kind in {'l1','l2_row'} else metadata.get('timestamp') if kind=='l2'
        else row.get('ts') if kind=='conversation_flow' else row.get('t_utc',row.get('t')) if kind=='decision_log'
        else row.get('updated_at') if kind=='action_ledger' else row.get('created_time'))
    timestamp,quality=iris_time(raw_time)
    for primary,mirror in [('ts','ts_cst'),('t_utc','t')]:
        if primary in row and mirror in row:
            a,_=iris_time(row[primary]);b,_=iris_time(row[mirror])
            if a is not None and b is not None and a!=b:raise CoreError('IRIS_TIME_MIRROR_CONFLICT')
    if kind in {'l1','conversation_flow'}:
        epistemic='USER_STATEMENT' if row['role']=='user' else 'MODEL_INFERENCE' if row['role']=='assistant' else 'OBSERVATION'
    elif kind in {'l2','l2_row'}:epistemic='SUMMARY' if metadata.get('source') in {'l1_summary','summary'} else 'MODEL_INFERENCE'
    elif kind=='action_ledger':epistemic='ACTION_CLAIM'
    else:epistemic='MODEL_INFERENCE' if kind in {'kg_node','kg_edge','user_profile','group_profile'} else 'OBSERVATION'
    if record.annotation and epistemic!='USER_STATEMENT':raise CoreError('IRIS_UNSUPPORTED_CLAIM_ANNOTATION')
    content=row.get('content',row.get('text'))
    if not isinstance(content,str) or not content:content=canonical(row)
    refs=[]
    if row.get('source_memory_id'):refs.append('iris-memory:'+str(row['source_memory_id']))
    if row.get('source'):refs.append('iris-conversation:'+str(row['source']))
    if row.get('umo'):refs.append('iris-conversation:'+str(row['umo']))
    if metadata.get('source'):refs.append('iris-producer:'+str(metadata['source']))
    if row.get('metadata',{}) and isinstance(metadata,dict) and metadata.get('message_id'):
        refs.append('iris-message:'+str(metadata['message_id']))
    origin={'legacy_kind':kind,'legacy_key':record.legacy_key,'dataset_id':record.dataset_id,
        'legacy_persona_id':row.get('persona_id',None),'group_id':row.get('group_id',metadata.get('group_id')),
        'user_id':row.get('user_id',metadata.get('user_id')),'missing_persona':'persona_id' not in row}
    normalized={'mapping_version':2,'origin':origin,'epistemic_kind':epistemic,'assessment':'UNASSESSED',
        'legacy_fields':row,'unmapped_fields':unknown,'legacy_refs':refs,'content':content,
        'time':{'legacy_time_raw':raw_time,'legacy_record_time_us':timestamp,'quality':quality,
            'underlying_event_time_us':timestamp if kind in {'l1','conversation_flow'} else None,
            'legacy_observed_time_raw':record.legacy_observed_at,'legacy_observed_time_us':iris_time(record.legacy_observed_at)[0]},
        'legacy_confidence':row.get('confidence',metadata.get('confidence')),'confidence_is_core_assessment':False,
        'relation':{'subject':row['source_id'],'predicate':row['relation_type'],'object':row['target_id']}
            if kind=='kg_edge' else None,
        'claim':record.annotation.model_dump() if record.annotation else None,
        'experience_candidate':False,'execution_evidence':False,
        'retention':'original supplied evidence retained; absence is not a deletion tombstone',
        'warnings':unknown+(['NO_ORIGINAL_SOURCE_LINK'] if not refs else [])+(['UNKNOWN_TIME'] if timestamp is None else [])}
    # Event's occurrence is legacy record occurrence, not invented underlying history.
    original=datetime.fromtimestamp(timestamp/1e6,tz=timezone.utc).isoformat() if timestamp is not None else None
    try:
        envelope=LegacyRecord(synthetic_only=True,source_system='iris',dataset_id=record.dataset_id,
        record_id=digest([kind,record.legacy_key]),revision=record.revision,epistemic_kind=epistemic,
        content=content,content_coverage='SUMMARY' if epistemic=='SUMMARY' else 'FULL',source_payload=record.raw_json,
        source_coverage='FULL',original_time=original,time_format='iso8601',legacy_source_refs=tuple(refs))
    except ValidationError:raise CoreError('IRIS_CONTRACT_REJECTED') from None
    return envelope,normalized


class IrisAdapter:
    def __init__(self,store):self.store=store;self.importer=LegacyImporter(store)
    def import_record(self,record,fault=None):
        envelope,projection=map_record(record)
        declaration_key='iris.record_declaration:'+digest([record.dataset_id,record.kind,record.legacy_key,record.revision])
        fingerprint=digest(record.model_dump());raw_hash=digest(record.raw_json.encode())
        prior=self.store.one('core_meta',declaration_key)
        if prior:
            declaration=json.loads(prior['value_json'])
            if declaration['raw_hash']!=raw_hash:raise CoreError('LEGACY_SOURCE_KEY_COLLISION')
            if declaration['fingerprint']!=fingerprint:raise CoreError('IRIS_MAPPING_INPUT_COLLISION')
        else:
            with self.store.transaction('migration.iris_record_declared',{'record_key':declaration_key}) as tx:
                tx.payload_id=tx.artifact(record.model_dump_json().encode())
                declaration={'fingerprint':fingerprint,'raw_hash':raw_hash,'event_id':tx.event_id,'artifact_id':tx.payload_id}
                tx.put('core_meta',{'key':declaration_key,'value_json':canonical(declaration)})
        projection['mapping_declaration_event_id']=declaration['event_id']
        result=self.importer.import_record(envelope)
        if fault:fault('after_original_commit',record.legacy_key)
        memory=self.store.one('memory_items',result['event_id']);body=json.loads(memory['body_json'])
        old_projection=body.get('iris')
        ignored={'mapping_version','mapping_declaration_event_id'}
        if old_projection and {k:v for k,v in old_projection.items() if k not in ignored}!={k:v for k,v in projection.items() if k not in ignored}:
            raise CoreError('IRIS_CANONICAL_COLLISION')
        if old_projection!=projection:
            body['iris']=projection
            ref={'event_id':declaration['event_id'],'artifact_id':declaration['artifact_id'],
                'coverage':'FULL','meaning':'operator supplied mapping envelope/annotation; not original historical evidence'}
            if not any(r['event_id']==ref['event_id'] for r in body['source_refs']):body['source_refs'].append(ref)
            with self.store.transaction('migration.iris_mapped',{'source_event_id':result['event_id'],'mapping_version':2,
                    'upgraded_from':old_projection.get('mapping_version') if old_projection else None}) as tx:
                tx.update('memory_items',memory['memory_id'],body_json=canonical(body))
        return {**result,'legacy_key':record.legacy_key,'kind':record.kind,'status':'IMPORTED' if result['added'] else 'DUPLICATE',
            'unmapped_fields':projection['unmapped_fields'],'warnings':projection['warnings']}
    def import_batch(self,records,fault=None):
        if not isinstance(records,(list,tuple)) or len(records)>100:raise CoreError('IRIS_BATCH_BOUND')
        # Typed envelopes and entire manifest are fixed before any per-record writes.
        records=tuple(IrisRecord.model_validate(r.model_dump()) for r in records)
        raw_batch=canonical([r.model_dump() for r in records]).encode()
        if len(raw_batch)>8*1024*1024:raise CoreError('IRIS_BATCH_BYTES_EXCEEDED')
        manifest_hash=digest([r.model_dump() for r in records]);results=[]
        for record in records:
            try:result=self.import_record(record,fault)
            except CoreError as exc:result={'legacy_key':record.legacy_key,'kind':record.kind,'status':'REJECTED','error':exc.code,
                'raw_sha256':digest(record.raw_json.encode())}
            results.append(result)
        manifest={'manifest_hash':manifest_hash,'input_count':len(records),'results':results,
            'raw_hashes':[digest(r.raw_json.encode()) for r in records],'source_identities':sorted({r.dataset_id for r in records})}
        key='iris.import_manifest:'+manifest_hash
        # Store last run report (including duplicate/rejected), with complete raw batch
        # evidence even for rejected/unmapped rows. Resume rereads frozen input.
        with self.store.transaction('migration.iris_batch_reported',{'manifest_hash':manifest_hash}) as tx:
            tx.payload_id=tx.artifact(raw_batch)
            tx.put('core_meta',{'key':key,'value_json':canonical(manifest)})
        return manifest
