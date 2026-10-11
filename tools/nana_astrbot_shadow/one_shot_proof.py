"""Read-only mechanical proof. Receipt review is NOT runtime provenance proof."""
import json
from types import MappingProxyType
from .one_shot import ProductionTrustStore, FixtureTrustStore, Provenance, utc, review_document
from tools.nana_host_shadow.safety import digest

REAL_RUNTIME_PROOF_PINS=MappingProxyType({})  # report hash -> independently reviewed Nana evidence hash
ZERO_KEYS={'iris_writes','external_output','model_calls','network_calls','authority_transfers'}
REPORT_KEYS={'schema_version','receipt_id','receipt_digest','source_provenance','trust_domain',
             'observer_callback_received','sanitizer_accepted','core','noncore_zero','binding_evidence_digest'}


def collect(ledger,rid,*,observer_callback_received=False,sanitizer_accepted=False,
            noncore_zero=None,binding_evidence_digest=None):
    r,v=ledger.record(rid)
    return {'schema_version':1,'receipt_id':rid,'receipt_digest':r.receipt_digest,
        'source_provenance':r.review_provenance.value,'trust_domain':ledger.trust.domain,
        'observer_callback_received':observer_callback_received,'sanitizer_accepted':sanitizer_accepted,
        'core':v['core'],'noncore_zero':noncore_zero,
        'binding_evidence_digest':binding_evidence_digest}


def verify_first_real_message_shadow(report,ledger):
    missing=[]
    try:
        if type(report) is not dict or set(report)!=REPORT_KEYS or type(report['schema_version']) is not int or report['schema_version']!=1:
            raise ValueError('REPORT_SCHEMA')
        r,v=ledger.record(report['receipt_id'])
        if report['receipt_digest']!=r.receipt_digest:missing.append('RECEIPT_DIGEST')
        if not ledger._review_valid(r,v['review']):missing.append('TRUSTED_REVIEW')
        if report['source_provenance']!=r.review_provenance.value or report['trust_domain']!=ledger.trust.domain:
            missing.append('PROVENANCE_DOMAIN')
        if v['uses']!=1 or v['state'] not in ('CONSUMED','VERIFIED'):missing.append('CONSUMED_EXACTLY_ONCE')
        if utc(v['consumed_at'])>=utc(r.expires_at):missing.append('EXPIRED_AT_CONSUMPTION')
        if report['observer_callback_received'] is not True:missing.append('OBSERVER_CALLBACK')
        if report['sanitizer_accepted'] is not True:missing.append('SANITIZER_ACCEPTANCE')
        meta=v['matched_metadata'];core=v['core']
        if (not meta or meta['platform']!=r.platform_scope or meta['type']!=r.event_type_scope
            or meta['conversation_hash']!=r.conversation_hash or meta['sender_hash']!=r.sender_hash
            or meta['event_source']!=r.event_source or meta['synthetic'] is not False):missing.append('EXACT_SCOPE')
        if type(core) is not dict or report['core']!=core:raise ValueError('CORE_RECORD_MISSING_OR_TAMPERED')
        store=ledger.store
        event=store.event(core['observation_id'])
        if event['kind']!='observation.received' or event['artifact_id']!=core['core_evidence_id']:raise ValueError('EVENT_EVIDENCE_LINK')
        host=json.loads(store.artifact(core['core_evidence_id']))['host_event']
        if json.loads(host['content'])!=meta or digest(meta)!=core['metadata_hash']:raise ValueError('EVIDENCE_CONTENT_LINK')
        if host['observation_source']!=r.event_source or host['timestamp']!=meta['timestamp']:raise ValueError('SOURCE_TIME_LINK')
        candidate=json.loads(store.one('memory_items',core['goal_candidate_id'])['body_json'])
        if candidate['type']!='GOAL_CANDIDATE' or candidate['proposal']['evidence_event_ids']!=[event['event_id']]:raise ValueError('CANDIDATE_LINK')
        draft=json.loads(store.one('memory_items',core['shadow_decision_id'])['body_json'])
        if (draft['type']!='SHADOW_DECISION' or draft['observation_event_id']!=event['event_id']
            or draft['execution_state']!='SHADOW_BLOCKED' or not draft['plan_draft']
            or core['shadow_plan_id']!=core['shadow_decision_id']+'#plan_draft'):raise ValueError('SHADOW_PLAN_DECISION_LINK')
        if core['identity_id']!=store.identity['identity_id'] or core['identity_revision']!=store.identity['revision']:
            raise ValueError('IDENTITY_LINK')
        events=store.all('events')
        consumed=[e for e in events if e['kind']=='r04.receipt_consumed'
                  and json.loads(e['data_json'])['data']['receipt_id']==r.receipt_id]
        if len(consumed)!=1 or events.index(consumed[0])>=events.index(event):raise ValueError('CONSUMPTION_COMMIT_ORDER')
        event_key='r04.consumed_event:'+digest([r.hash_scope,meta['platform'],meta['conversation_hash'],meta['event_id']])
        if json.loads(store.one('core_meta',event_key)['value_json'])!={'receipt_id':r.receipt_id}:raise ValueError('PERSISTENT_REPLAY_FENCE')
        # Alias recorded by existing CoreSink, not a testing list/boolean.
        alias_key='observer.event:'+digest([r.hash_scope,meta['platform'],meta['conversation_hash'],meta['event_id']])
        if json.loads(store.one('core_meta',alias_key)['value_json'])['result']['observation_id']!=event['event_id']:
            raise ValueError('PERSISTENT_DEDUP_ALIAS')
        counts={t:len(store.all(t)) for t in ('actions','attempts','grants','budgets','strategies')}
        if any(counts.values()) or core['zero_execution_counts']!=counts or core['barrier_result']!='SHADOW_BLOCKED':raise ValueError('SHADOW_BARRIER')
        z=report['noncore_zero']
        if type(z) is not dict or set(z)!=ZERO_KEYS or any(type(x) is not int or x!=0 for x in z.values()):missing.append('NONCORE_ZERO_EVIDENCE')
        if missing:return {'status':'INCOMPLETE','missing':missing,'host_binding':'UNVERIFIED'}
        if type(ledger.trust) is FixtureTrustStore:
            return {'status':'SIMULATED_REAL_SHADOW_PROOF_PASS','missing':[], 'host_binding':'UNVERIFIED',
                    'real_dispatcher_traversal':'NOT_VERIFIED','E12':'NOT_RUN'}
        # Authorization proves scope, NOT dispatcher traversal/registry/unload/zero drift.
        # A second, independent reviewed runtime evidence pin is mandatory.
        binding=report['binding_evidence_digest']
        if (r.review_provenance is not Provenance.ASTRBOT_REAL_MESSAGE
            or type(binding) is not str or REAL_RUNTIME_PROOF_PINS.get(digest(report))!=binding):
            return {'status':'UNKNOWN','missing':['INDEPENDENT_REAL_RUNTIME_PROOF'], 'host_binding':'UNVERIFIED'}
        return {'status':'REAL_MESSAGE_SHADOW_PROOF_COMPLETE','missing':[],'host_binding':'VERIFIED'}
    except BaseException as exc:
        # Fixed trusted error codes only, never stringify foreign exceptions.
        codes={'REPORT_SCHEMA','CORE_RECORD_MISSING_OR_TAMPERED','EVENT_EVIDENCE_LINK','EVIDENCE_CONTENT_LINK',
               'SOURCE_TIME_LINK','CANDIDATE_LINK','SHADOW_PLAN_DECISION_LINK','IDENTITY_LINK',
               'CONSUMPTION_COMMIT_ORDER','PERSISTENT_REPLAY_FENCE','PERSISTENT_DEDUP_ALIAS','SHADOW_BARRIER'}
        code=exc.args[0] if type(exc) is ValueError and len(exc.args)==1 and type(exc.args[0]) is str and exc.args[0] in codes else 'PERSISTENT_PROOF_READBACK'
        # No exception/input repr to logs, including hostile user objects.
        return {'status':'INCOMPLETE','missing':[code], 'host_binding':'UNVERIFIED'}


def mark_verified(report,ledger):
    verdict=verify_first_real_message_shadow(report,ledger)
    allowed=('SIMULATED_REAL_SHADOW_PROOF_PASS' if type(ledger.trust) is FixtureTrustStore
             else 'REAL_MESSAGE_SHADOW_PROOF_COMPLETE')
    if verdict['status']!=allowed:raise ValueError('PROOF_NOT_COMPLETE')
    r,v=ledger.record(report['receipt_id'])
    if v['state']!='CONSUMED':raise ValueError('RECEIPT_TERMINAL')
    v.update(state='VERIFIED',verified_proof_digest=digest(report),verification_domain=ledger.trust.domain)
    with ledger.store.transaction('r04.proof_verified',{'receipt_id':r.receipt_id,'domain':ledger.trust.domain}) as tx:
        ledger._write(tx,r,v)
    return verdict
