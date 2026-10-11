"""Bounded Iris export from explicitly selected frozen snapshots, no Iris imports.

Live SQLite is deliberately refused: immutable reads require a consistent frozen
backup. No index rebuild, migration, model call, compaction or source write.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
from ..contracts import CoreError
from ..storage import canonical, digest
from ..clock import Clock
from ..migration.iris import FIELDS, iris_time

TABLES = {'memories': ('l2_row','memory_id'), 'nodes': ('kg_node','id'), 'edges': ('kg_edge',None)}
PRIVATE_FIELDS={'content','text','name','user_name','group_name','sender_name','query','reason','note','op','verify','metadata','properties','custom_fields','interests','important_events'}
SECRET_NAMES={'api_key','apikey','token','cookie','password','secret','authorization','credentials'}

def _safe_payload(value):
    if isinstance(value,dict):
        if any(str(k).lower() in SECRET_NAMES for k in value):raise CoreError('SECRET_FIELD_IN_EXPORT')
        for v in value.values():_safe_payload(v)
    elif isinstance(value,list):
        for v in value:_safe_payload(v)

def bundle(records, source_identity, *, mode='hash-only', clock=None, source_version='iris-0.3.0', max_records=100):
    if mode not in {'include','redact','hash-only'}:raise CoreError('INVALID_EXPORT_MODE')
    if len(records)>max_records:raise CoreError('EXPORT_RECORD_LIMIT')
    output=[];counts=Counter();seen={}
    for kind,key,payload in records:
        if kind not in FIELDS or not key:raise CoreError('UNMAPPED_EXPORT_RECORD')
        raw=canonical(payload);_safe_payload(payload)
        if len(raw.encode())>150000:raise CoreError('EXPORT_PAYLOAD_LIMIT')
        stable=digest([source_identity,kind,key]); h=digest(raw.encode())
        if stable in seen:
            if seen[stable]!=h:raise CoreError('EXPORT_KEY_COLLISION')
            raise CoreError('EXPORT_DUPLICATE_KEY')
        seen[stable]=h
        t=payload.get('timestamp',payload.get('created_time',payload.get('updated_at',payload.get('ts',payload.get('t_utc')))))
        us,quality=iris_time(t)
        # Opaque hashes preserve equality/linkage without exposing names or text.
        relation={k:digest([source_identity,payload[k]]) for k in ('source_id','target_id','source_memory_id') if payload.get(k)}
        shown=payload if mode=='include' else ({k:(v if k in {'role','version','confidence','weight','timestamp','created_time','updated_at','ts','t_utc'} else '[REDACTED]') for k,v in payload.items()} if mode=='redact' else None)
        item={'stable_legacy_id':stable,'legacy_kind':kind,'legacy_key':key if mode=='include' else digest(key),
            'payload_hash':h,'payload':shown,'coverage':'FULL_SUPPLIED_ROW' if mode=='include' else 'REDACTED' if mode=='redact' else 'HASH_ONLY',
            'source_identity':source_identity,'provenance':{'producer':'iris-readonly-snapshot-export','schema':'iris-0.3.0','upstream_commit':'0557a4c1de1969bdccdb5a5de4b3724dc94aa6f6'},
            'original_record_time_us':us,'underlying_occurrence_time_us':us if kind in {'l1','conversation_flow'} else None,
            'time_quality':quality,'relationship':relation,'assessment':{'Core':'UNASSESSED','legacy_confidence':payload.get('confidence')}}
        output.append(item);counts[kind]+=1
    result={'schema_version':1,'source_version':source_version,'source_identity':source_identity,'exported_at_us':(clock or Clock()).utc_now_us(),
        'mode':mode,'record_counts':dict(counts),'total_records':len(output),'records':output,
        'source_untouched':True,'snapshot_consistency':'operator supplied frozen snapshot; not live transaction parity','secrets_allowed':False}
    if len(canonical(result).encode())>8*1024*1024:raise CoreError('EXPORT_BUNDLE_LIMIT')
    result['manifest_hash']=digest(result)
    return result

def read_sqlite_snapshot(path, table, *, frozen=False, limit=100):
    if not frozen:raise CoreError('FROZEN_SNAPSHOT_REQUIRED')
    if table not in TABLES or type(limit)!=int or not 1<=limit<=100:raise CoreError('EXPORT_QUERY_REJECTED')
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise CoreError('REGULAR_SNAPSHOT_REQUIRED')
    if any(p.exists() and p.stat().st_size for p in (Path(str(path)+'-wal'),Path(str(path)+'-journal'))):raise CoreError('UNRESOLVED_SNAPSHOT_JOURNAL')
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        rows=[dict(row) for row in db.execute(f'SELECT * FROM {table} LIMIT ?', (limit+1,))]
    if len(rows)>limit:raise CoreError('EXPORT_RECORD_LIMIT')
    kind,key=TABLES[table];result=[]
    for row in rows:
        for field in ('metadata','properties'):
            if isinstance(row.get(field),str):row[field]=json.loads(row[field])
        stable=row[key] if key else canonical([row['source_id'],row['target_id'],row['relation_type']])
        result.append((kind,str(stable),row))
    return tuple(result)

def read_json_snapshot(path, kind, *, frozen=False):
    if not frozen:raise CoreError('FROZEN_SNAPSHOT_REQUIRED')
    p=Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>1024*1024:raise CoreError('EXPORT_INPUT_REJECTED')
    data=json.loads(p.read_text());rows=data if isinstance(data,list) else [data]
    if len(rows)>100:raise CoreError('EXPORT_RECORD_LIMIT')
    # The explicit input format is a list of {legacy_key,payload}; native wrapper
    # extraction belongs to a reviewed host exporter, not recursive data scanning.
    return tuple((kind,r['legacy_key'],r['payload']) for r in rows)

def main():
    p=argparse.ArgumentParser(description='Read an operator-selected frozen Iris snapshot; stdout is sensitive in include mode')
    p.add_argument('--snapshot',required=True);p.add_argument('--source-identity',required=True)
    p.add_argument('--table',choices=tuple(TABLES));p.add_argument('--json-kind',choices=tuple(FIELDS))
    p.add_argument('--frozen',action='store_true');p.add_argument('--mode',choices=['hash-only','redact','include'],default='hash-only')
    a=p.parse_args()
    if bool(a.table)==bool(a.json_kind):p.error('select exactly one table or json-kind')
    try:
        records=read_sqlite_snapshot(a.snapshot,a.table,frozen=a.frozen) if a.table else read_json_snapshot(a.snapshot,a.json_kind,frozen=a.frozen)
        print(canonical(bundle(records,a.source_identity,mode=a.mode)))
    except (CoreError,ValueError,KeyError,sqlite3.Error,OSError) as exc:
        print(canonical({'status':'BLOCKED','error':exc.code if isinstance(exc,CoreError) else type(exc).__name__}));raise SystemExit(2)
if __name__=='__main__':main()
