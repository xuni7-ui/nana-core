"""Deterministic one-shot engineering harness. NOT real AstrBot dispatch."""
import asyncio
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
from uuid import uuid4
from tools.nana_host_shadow.safety import private_file,digest
from .one_shot import OneShotReceipt,Provenance,FixtureTrustStore,review_document
from .one_shot_ingress import OneShotCoreSink,OneShotSanitizer,OneShotObserver
from .one_shot_proof import collect,verify_first_real_message_shadow,ZERO_KEYS,mark_verified


def run(directory):
    directory=Path(directory)
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    rid='r04-'+uuid4().hex
    s=OneShotSanitizer(scope='r04-development',hash_key=b'F'*32,receipt_id=rid)
    sink=OneShotCoreSink(directory,s,rid,trust=FixtureTrustStore())
    l=sink.ledger();now=datetime.now(timezone.utc)
    raw={'platform':'development','type':'DevelopmentEvent','event_id':'synthetic-r04-single-event',
         'timestamp':now.isoformat(),'sender_id':'synthetic-sender','conversation_id':'synthetic-conversation',
         'event_source':'astrbot_on_decorating_result','synthetic':False,'probe_id':''}
    r=OneShotReceipt(receipt_id=rid,issued_at=now.isoformat(),expires_at=(now+timedelta(minutes=5)).isoformat(),
        platform_scope=raw['platform'],sender_hash=s.scoped_hash('sender_id',raw['sender_id']),
        conversation_hash=s.scoped_hash('conversation_id',raw['conversation_id']),event_type_scope=raw['type'],
        review_provenance=Provenance.FIXTURE,review_receipt_digest='0'*64,store_binding=l.binding,hash_scope=s.scope)
    review=review_document(r);r=r.model_copy(update={'review_receipt_digest':digest(review)})
    l.create(r);l.review(rid,review);l.arm(rid);identity=l.store.identity;sink.close()
    sink=OneShotCoreSink(directory,s,rid,trust=FixtureTrustStore());observer=OneShotObserver(s,sink,timeout=2)
    async def execute():
        try:
            await observer.callback_real(raw)
            accepted=observer.last_result
            await observer.callback_real(raw)
            return accepted,observer.last_result
        finally:await observer.close()
    accepted,replay=asyncio.run(execute())
    if accepted['status']!='RECORDED' or replay['status']!='DROP_ONE_SHOT_FAILURE':raise ValueError('HARNESS_ONE_SHOT_FAILED')
    reopened=OneShotCoreSink(directory,s,rid,trust=FixtureTrustStore())
    try:
        l=reopened.ledger()
        if l.store.identity!=identity:raise ValueError('HARNESS_IDENTITY_CHANGED')
        report=collect(l,rid,observer_callback_received=True,sanitizer_accepted=True,noncore_zero={k:0 for k in ZERO_KEYS})
        verdict=mark_verified(report,l)
        if verdict['status']!='SIMULATED_REAL_SHADOW_PROOF_PASS':raise ValueError('HARNESS_PROOF_FAILED')
        private_file(directory/'one_shot_proof.json',report)
        result={'status':verdict['status'],'host_binding':'UNVERIFIED','evidence_origin':'FIXTURE',
                'real_dispatcher_traversal':'NOT_VERIFIED','real_message':'NOT_RUN','E12':'NOT_RUN',
                'receipt_status':l.status(rid),'identity_continuous':True,'replay_blocked':True,
                'core_evidence':accepted['receipt']['core'],'observer_closed':True,'external_execute':False}
        private_file(directory/'one_shot_result.json',result)
        return result
    finally:reopened.close()
