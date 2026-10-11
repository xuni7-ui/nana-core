"""Binding chain verification does not infer real runtime origin from a JSON flag.

No reviewed Nana receipt pins are available at development baseline. Host-origin
promotion stays closed until an independently reviewed sanitized runtime receipt
hash is explicitly added here, with its PROJECT_BRAIN/shared-commit reference.
No caller, fixture, CLI argument or report can add trusted origins dynamically.
"""
import hashlib
import json
import re
from datetime import datetime
from tools.nana_host_shadow.safety import digest

TRUSTED_NANA_RECEIPTS = frozenset()  # intentional, no reviewed host receipt yet
STAGES=('registry_before','registry_after_register','dispatch','callback','core','dedup','barrier','registry_after_unregister')

def _utc(value):
    try:
        t=datetime.fromisoformat(value)
        return t.tzinfo is not None and t.utcoffset().total_seconds()==0
    except (ValueError,TypeError): return False

class BindingRecorder:
    def __init__(self, registration_id, callback_fingerprint, *, evidence_origin='development_fixture', probe_class='C'):
        if not re.fullmatch(r'[0-9a-f]{64}',registration_id) or not re.fullmatch(r'[0-9a-f]{64}',callback_fingerprint):
            raise ValueError('HASHED_REGISTRATION_REQUIRED')
        if evidence_origin!='development_fixture' or probe_class not in {'B','C'}:
            raise ValueError('REAL_ORIGIN_REQUIRES_REVIEWED_NANA_RECEIPT')
        self.report={'schema_version':1,'evidence_origin':evidence_origin,'probe_class':probe_class,
            'observer_registration_id':registration_id,'observer_callback_fingerprint':callback_fingerprint,'stages':[]}
    def add(self, stage, values):
        if stage not in STAGES or type(values) is not dict: raise ValueError('PROOF_STAGE_INVALID')
        allowed={
            'registry_before':{'callback_present','registry_digest'},
            'registry_after_register':{'callback_present','registry_digest'},
            'dispatch':{'probe_id','event_id','event_timestamp','event_source','synthetic','external_delivery'},
            'callback':{'probe_id','event_id','event_timestamp','event_source','observer_received_at'},
            'core':{'core_evidence_id','observation_id','goal_candidate_id','shadow_plan_id','shadow_decision_id','metadata_hash'},
            'dedup':{'dedup_result','observation_id'},'barrier':{'barrier_result','zero_execution_counts'},
            'registry_after_unregister':{'callback_present','registry_digest'}}[stage]
        if set(values)!=allowed: raise ValueError('PROOF_FIELD_ALLOWLIST')
        # Caller values are schema-checked by verify before serialization/export.
        trial=json.loads(json.dumps(values,allow_nan=False))
        self.report['stages'].append({'stage':stage,**trial})
    def export(self):
        candidate=json.loads(json.dumps(self.report))
        # Validation catches accidental extra IDs/bodies before evidence emission.
        if verify(candidate)['missing']: raise ValueError('INCOMPLETE_OR_UNSAFE_BINDING_PROOF')
        return candidate

def verify(report):
    missing=[]
    if type(report) is not dict or set(report)-{'schema_version','evidence_origin','probe_class','observer_registration_id','observer_callback_fingerprint','stages'}:
        return {'status':'BINDING_PROOF_INCOMPLETE','host_binding':'UNVERIFIED','missing':['REPORT_SCHEMA']}
    if report.get('schema_version')!=1: missing.append('SCHEMA_VERSION')
    for f in ('observer_registration_id','observer_callback_fingerprint'):
        if type(report.get(f)) is not str or not re.fullmatch('[0-9a-f]{64}',report[f]): missing.append(f)
    rows=report.get('stages',[])
    if type(rows) is not list or len(rows)!=len(STAGES) or any(type(r) is not dict for r in rows):
        return {'status':'BINDING_PROOF_INCOMPLETE','host_binding':'UNVERIFIED','missing':missing+['STAGE_SEQUENCE']}
    if [r.get('stage') for r in rows]!=list(STAGES): missing.append('STAGE_SEQUENCE')
    stage=dict(zip(STAGES,rows))
    for name,present in [('registry_before',False),('registry_after_register',True),('registry_after_unregister',False)]:
        if stage[name].get('callback_present') is not present: missing.append(name)
        if type(stage[name].get('registry_digest')) is not str or not re.fullmatch('[0-9a-f]{64}',stage[name]['registry_digest']): missing.append(name+'_digest')
    if stage['registry_before'].get('registry_digest') != stage['registry_after_unregister'].get('registry_digest'): missing.append('UNLOAD_REGISTRY_DRIFT')
    if stage['registry_before'].get('registry_digest') == stage['registry_after_register'].get('registry_digest'): missing.append('REGISTER_REGISTRY_UNCHANGED')
    dispatch,callback=stage['dispatch'],stage['callback']
    for field in ('probe_id','event_id','event_timestamp','event_source'):
        if dispatch.get(field)!=callback.get(field): missing.append('CALLBACK_'+field)
    from .sanitize import PROBE
    if type(dispatch.get('probe_id')) is not str or not PROBE.fullmatch(dispatch['probe_id']): missing.append('PROBE_ID')
    if type(dispatch.get('event_id')) is not str or not re.fullmatch('[0-9a-f]{64}',dispatch['event_id']): missing.append('EVENT_ID_HASH')
    if dispatch.get('event_source')!='operator_probe' or dispatch.get('synthetic') is not True or dispatch.get('external_delivery') is not False:
        missing.append('SYNTHETIC_DISPATCH_SCOPE')
    if dispatch.get('event_timestamp') is not None and not _utc(dispatch['event_timestamp']): missing.append('EVENT_TIMESTAMP')
    if not _utc(callback.get('observer_received_at')): missing.append('CALLBACK_TIME')
    core=stage['core']
    for field in ('core_evidence_id','observation_id','goal_candidate_id','shadow_plan_id','shadow_decision_id','metadata_hash'):
        v=core.get(field)
        patterns={'core_evidence_id':r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', 'metadata_hash':r'[0-9a-f]{64}', 'observation_id':r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', 'goal_candidate_id':r'[0-9a-f]{64}', 'shadow_plan_id':r'cloud\.shadow:[0-9a-f]{64}#plan_draft', 'shadow_decision_id':r'cloud\.shadow:[0-9a-f]{64}'}
        if type(v) is not str or not re.fullmatch(patterns[field],v): missing.append('CORE_'+field)
    if stage['dedup'].get('dedup_result')!='DUPLICATE' or stage['dedup'].get('observation_id')!=core.get('observation_id'):
        missing.append('PERSISTENT_DEDUP')
    counts=stage['barrier'].get('zero_execution_counts')
    if stage['barrier'].get('barrier_result')!='SHADOW_BLOCKED' or type(counts) is not dict or set(counts)!={'actions','attempts','grants','budgets','strategies'} or any(type(v) is not int or v!=0 for v in counts.values()):
        missing.append('SHADOW_BARRIER')
    # Recreate field allowlists without trusting arbitrary added bodies/metadata.
    for name,row in stage.items():
        try:
            r=BindingRecorder('0'*64,'0'*64)
            r.add(name,{k:v for k,v in row.items() if k!='stage'})
        except (TypeError,ValueError): missing.append('FIELD_POLICY_'+name)
    origin=report.get('evidence_origin'); level=report.get('probe_class')
    if origin=='development_fixture' and level not in {'B','C'}: missing.append('SIMULATED_DISPATCH_LEVEL')
    if origin not in {'development_fixture','real_astrbot_runtime'}: missing.append('ORIGIN')
    if missing: return {'status':'BINDING_PROOF_INCOMPLETE','host_binding':'UNVERIFIED','missing':sorted(set(missing))}
    if origin=='development_fixture':
        return {'status':'SIMULATED_BINDING_PROOF_PASS','host_binding':'UNVERIFIED','missing':[]}
    # Whole receipt bytes, not origin text/provider string, must have been
    # reviewed by Nana. Local C cannot prove dispatcher even on a real host.
    if level!='A' or digest(report) not in TRUSTED_NANA_RECEIPTS:
        return {'status':'HOST_ORIGIN_UNTRUSTED','host_binding':'UNVERIFIED','missing':[],
                'review_required':'Nana source-backed dispatcher receipt + independently reviewed hash pin'}
    return {'status':'HOST_BINDING_PROOF_COMPLETE','host_binding':'VERIFIED','missing':[]}


def verify_core_links(report, store):
    """Independent read-back; receipt IDs alone are not proof of persistence."""
    result=verify(report)
    if result['missing']:return {**result,'core_links_verified':False}
    try:
        rows={r['stage']:r for r in report['stages']};core=rows['core']
        event=store.event(core['observation_id'])
        if event['kind']!='observation.received' or event['artifact_id']!=core['core_evidence_id']:
            raise ValueError()
        host=json.loads(store.artifact(core['core_evidence_id']))['host_event']
        metadata=json.loads(host['content'])
        dispatch=rows['dispatch']
        if digest(metadata)!=core['metadata_hash'] or any(metadata[k]!=dispatch[field] for k,field in (
            ('event_id','event_id'),('probe_id','probe_id'),('timestamp','event_timestamp'),('event_source','event_source'))):
            raise ValueError()
        candidate=store.one('memory_items',core['goal_candidate_id'])
        c=json.loads(candidate['body_json'])
        if c['type']!='GOAL_CANDIDATE' or c['proposal']['evidence_event_ids']!=[event['event_id']]:raise ValueError()
        draft=json.loads(store.one('memory_items',core['shadow_decision_id'])['body_json'])
        if draft['type']!='SHADOW_DECISION' or draft['observation_event_id']!=event['event_id'] or draft['execution_state']!='SHADOW_BLOCKED':raise ValueError()
        if not draft['plan_draft'] or core['shadow_plan_id']!=core['shadow_decision_id']+'#plan_draft':raise ValueError()
        if any(store.all(t) for t in ('actions','attempts','grants','budgets','strategies')):raise ValueError()
        return {**result,'core_links_verified':True}
    except Exception:
        return {'status':'CORE_BINDING_LINKS_INCOMPLETE','host_binding':'UNVERIFIED','missing':['CORE_READBACK'],
                'core_links_verified':False}
