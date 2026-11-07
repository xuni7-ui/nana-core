"""Body-free usage metadata in the original request ledger/Store.

Reported tokens are neither an invoice nor execution permission. Erasing source
content must not erase non-content usage or refund an uncertain reservation.
"""
import json
import re

from ..contracts import CoreError
from ..storage import canonical
from .privacy import _json_object

PREFIX='cognition.usage.'
FIELDS={'version','request_id','origin','input_tokens','output_tokens'}


def reported_usage_pair(usage):
    if type(usage) is not dict:return None
    values=[]
    for aliases in (('prompt_tokens','input_tokens'),('completion_tokens','output_tokens')):
        present=[usage[key] for key in aliases if key in usage]
        if not present or any(type(n) is not int or not 0<=n<=2**53-1 for n in present) or len(set(present))!=1:return None
        values.append(present[0])
    total=usage.get('total_tokens')
    if total is not None and (type(total) is not int or total!=sum(values)):return None
    return tuple(values)


def decode_usage_receipt(key,raw):
    if type(key) is not str or not key.startswith(PREFIX) or type(raw) is not str or len(raw)>1024:return None
    try:
        value=json.loads(raw,object_pairs_hook=_json_object)
        if (type(value) is not dict or set(value)!=FIELDS or type(value['version']) is not int or value['version']!=1
                or type(value['request_id']) is not str or not re.fullmatch(r'[A-Za-z0-9._:-]{1,96}',value['request_id'])
                or key!=PREFIX+value['request_id'] or value['origin'] not in {'SYNTHETIC','REAL_PROVIDER'}
                or reported_usage_pair({'input_tokens':value['input_tokens'],'output_tokens':value['output_tokens']}) is None):
            return None
        return value
    except (ValueError,TypeError,KeyError):return None


def record_usage(tx,reply):
    pair=reported_usage_pair(reply.usage)
    if pair is None:return
    value={'version':1,'request_id':reply.request_id,'origin':reply.origin,'input_tokens':pair[0],'output_tokens':pair[1]}
    key=PREFIX+reply.request_id;encoded=canonical(value)
    if decode_usage_receipt(key,encoded) is None:raise CoreError('USAGE_RECEIPT_INVALID')
    previous=tx.store.one('core_meta',key)
    if previous:
        if previous['value_json']!=encoded:raise CoreError('USAGE_RECEIPT_CONFLICT')
        return
    tx.put('core_meta',{'key':key,'value_json':encoded})


def portable_usage_metadata(store,row):
    """Exact numeric contract; never allow arbitrary prefixed host settings."""
    if store.schema_target<13:return False
    value=decode_usage_receipt(row['key'],row['value_json'])
    return bool(value and store.one('cognitive_requests',value['request_id']))
