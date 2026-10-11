"""Native-field wrapper interoperability, no Iris execution or production reader.

L1 has a volatile runtime queue, not a native disk snapshot format. Its operator
snapshot envelope is explicitly labeled here. Profiles use native KV keys with
profile_to_dict values. Only synthetic frozen envelopes can be read this round.
"""
import json
from .safety import checked_path,digest,canonical

COMMIT='0557a4c1de1969bdccdb5a5de4b3724dc94aa6f6'
L1_FIELDS={'role','content','timestamp','token_count','source','metadata','persona_id'}
USER_FIELDS={'user_id','user_name','version','historical_names','personality_tags','interests','occupation',
 'language_style','communication_style','emotional_baseline','favorability','bot_relationship','important_dates',
 'taboo_topics','important_events','custom_fields','field_meta','update_tracker'}
GROUP_FIELDS={'group_id','group_name','version','interests','atmosphere_tags','long_term_tags','blacklist_topics','custom_fields','field_meta','update_tracker'}


def schema():
    return {'status':'UNASSESSED','mode':'schema-only','source_commit':COMMIT,
        'l1':{'fields':sorted(L1_FIELDS),'container':'L1Buffer._queues[session].segment_1/segment_2/segment_3',
              'native_persistent_wrapper':'ABSENT_IN_LOCKED_UPSTREAM','snapshot_envelope':'operator-created; not invented Iris disk schema',
              'source':'iris_memory/l1_buffer/models.py:37; buffer.py:101'},
        'user_profile':{'fields':sorted(USER_FIELDS),'KV_key':'user_profile:{persona_id}:{group_id}:{user_id}',
                        'source':'iris_memory/profile/storage.py:212; models.py:391'},
        'group_profile':{'fields':sorted(GROUP_FIELDS),'KV_key':'group_profile:{persona_id}:{group_id}',
                         'source':'iris_memory/profile/storage.py:158; models.py:391'},
        'private_records_read':0,'secret_values_read':0,'production_reader_enabled':False,'Core_assessment':'UNASSESSED'}


def records(data):
    if not isinstance(data,dict) or data.get('synthetic') is not True or data.get('private') is not False:
        raise ValueError('BLOCKED_PRIVACY_SCOPE')
    if set(data)-{'synthetic','private','source_identity','l1_queues','profile_kv'}:raise ValueError('WRAPPER_SCHEMA_DRIFT')
    result=[]
    for queue in data.get('l1_queues',[]):
        if set(queue)!={'session_id','segment_1','segment_2','segment_3'}:raise ValueError('WRAPPER_SCHEMA_DRIFT')
        for segment in ('segment_1','segment_2','segment_3'):
            for i,row in enumerate(queue[segment]):
                if not isinstance(row,dict) or not {'role','content','timestamp','token_count','source'}<=set(row) or set(row)-L1_FIELDS:
                    raise ValueError('WRAPPER_SCHEMA_DRIFT')
                # Slot is stable only inside this frozen operator snapshot. Do
                # not claim native message IDs or dedup across unrelated snapshots.
                result.append(('l1',canonical([queue['session_id'],segment,i]),row))
    for key,row in data.get('profile_kv',{}).items():
        parts=key.split(':');kind='user_profile' if parts[0]=='user_profile' else 'group_profile' if parts[0]=='group_profile' else None
        fields=USER_FIELDS if kind=='user_profile' else GROUP_FIELDS
        if not kind or len(parts)!=(4 if kind=='user_profile' else 3) or not all(parts) or not isinstance(row,dict) or set(row)-fields:
            raise ValueError('WRAPPER_SCHEMA_DRIFT')
        identifier='user_id' if kind=='user_profile' else 'group_id'
        if row.get(identifier)!=parts[-1]:raise ValueError('WRAPPER_KEY_PAYLOAD_CONFLICT')
        result.append((kind,key,row))
    if len(result)>100:raise ValueError('WRAPPER_RECORD_LIMIT')
    return result


def count_metadata(counts):
    """Future wrapper supplies pre-authorized numeric metadata, not get_kv_data."""
    if set(counts)!={'l1','user_profile','group_profile'} or any(type(v)!=int or v<0 for v in counts.values()):
        raise ValueError('COUNT_METADATA_REJECTED')
    return {'mode':'count-only','record_counts':counts,'private_records_read':0,'source_commit':COMMIT,
            'assessment':'UNASSESSED','production_reader_enabled':False}


def export(fixture=None,*,mode='schema-only'):
    if mode=='schema-only':return schema()  # Do not even open a supplied file.
    if mode not in {'count-only','hash-only','redacted-sample'} or fixture is None:raise ValueError('SYNTHETIC_FROZEN_FIXTURE_REQUIRED')
    p=checked_path(fixture)
    if p.stat().st_size>1024*1024:raise ValueError('WRAPPER_INPUT_LIMIT')
    data=json.loads(p.read_text());rows=records(data)
    from nana_core.integration.exporter import bundle
    # Reuse canonical exporter checks, including nested secret rejection.
    exported=bundle(rows,data.get('source_identity','synthetic:iris-wrapper'),mode='redact' if mode=='redacted-sample' else 'hash-only')
    if mode=='count-only':
        counts={k:sum(row[0]==k for row in rows) for k in ('l1','user_profile','group_profile')}
        result=count_metadata(counts)
    else:result=exported
    result.update(synthetic_fixture=True,production_reader_enabled=False,private_records_read=0,
                  wrapper_snapshot_scope='L1 stable slots apply to one frozen operator snapshot only')
    return result
