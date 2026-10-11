"""C-level neutral dispatch rehearsal, explicitly not AstrBot binding evidence."""
import asyncio
from datetime import datetime,timezone
import json
from tools.nana_host_shadow.safety import digest,checked_path,private_file
from .binding import RegistryLifecycle
from .sanitize import MetadataSanitizer
from .core_sink import MetadataCoreSink
from .observer import ShadowObserver
from .proof import BindingRecorder,verify,verify_core_links

class DevelopmentRegistry:
    def __init__(self):self._callbacks={}
    def register(self,key,callback):self._callbacks[key]=callback
    def unregister(self,key):self._callbacks.pop(key,None)
    def contains(self,key):return key in self._callbacks
    def fingerprint(self):return digest(sorted(self._callbacks))
    async def local_dispatch(self,key,event,permit):
        return await self._callbacks[key](event,permit=permit)

def run(directory):
    directory=checked_path(directory,directory=True,missing=True)
    if not directory.exists():directory.mkdir(mode=0o700)
    metadata={'platform':'fixture','type':'synthetic','event_id':'synthetic-binding-event-v1',
        'event_source':'operator_probe','synthetic':True,'probe_id':'nana-probe-binding-v1',
        'timestamp':'2026-10-11T02:00:00+00:00','sender_id':'synthetic-operator','conversation_id':'synthetic-local'}
    # Fixture-only public hash seed. Real ingress must supply its own private
    # scoped key; no real IDs enter this development harness.
    sanitizer=MetadataSanitizer(scope='fixture-binding-v1',hash_key=b'D'*32,probe_ids=frozenset({metadata['probe_id']}))
    sanitized=sanitizer.sanitize(metadata).metadata
    registration_id=digest(['fixture-registration',metadata['probe_id']])
    from pathlib import Path
    callback_fingerprint=digest(Path(__file__).with_name('observer.py').read_bytes())
    recorder=BindingRecorder(registration_id,callback_fingerprint)
    async def session():
        registry=DevelopmentRegistry();lifecycle=RegistryLifecycle(registry,registration_id)
        observer=ShadowObserver(sanitizer,MetadataCoreSink(directory,sanitizer),timeout=2.)
        recorder.add('registry_before',lifecycle.registry_probe())
        try:
            recorder.add('registry_after_register',lifecycle.register(observer.callback))
            dispatch={'probe_id':sanitized.probe_id,'event_id':sanitized.event_id,'event_timestamp':sanitized.timestamp,'event_source':sanitized.event_source}
            recorder.add('dispatch',{**dispatch,'synthetic':True,'external_delivery':False})
            permit=observer.issue_local_permit(metadata['probe_id'])
            assert await registry.local_dispatch(registration_id,metadata,permit) is None
            if observer.last_result['status']!='RECORDED':raise ValueError('HARNESS_CORE_UNAVAILABLE')
            receipt=observer.last_result['core']
            recorder.add('callback',{**dispatch,'observer_received_at':datetime.now(timezone.utc).isoformat()})
            recorder.add('core',{k:receipt[k] for k in ('core_evidence_id','observation_id','goal_candidate_id','shadow_plan_id','shadow_decision_id','metadata_hash')})
            assert await registry.local_dispatch(registration_id,metadata,permit) is None
            if observer.last_result['status']!='RECORDED':raise ValueError('HARNESS_DEDUP_UNAVAILABLE')
            duplicate=observer.last_result['core']
            recorder.add('dedup',{k:duplicate[k] for k in ('dedup_result','observation_id')})
            recorder.add('barrier',{k:duplicate[k] for k in ('barrier_result','zero_execution_counts')})
        finally:
            try:after=lifecycle.unregister()
            finally:await observer.close()
        recorder.add('registry_after_unregister',after)
        return receipt
    receipt=asyncio.run(session());proof=recorder.export()
    from nana_core.storage import Store
    with Store(directory/'observer-shadow.db') as audit_store:
        links=verify_core_links(proof,audit_store)
    if not links['core_links_verified']:raise ValueError('INDEPENDENT_CORE_LINKS_FAILED')
    report={'scope':'DEVELOPMENT_ENGINEERING_C_ONLY','host_binding':'UNVERIFIED','proof':proof,'verification':links,
        'identity_id':receipt['identity_id'],'identity_revision':receipt['identity_revision'],
        'production_modifications':0,'production_calls':0,'external_messages':0,'private_records_read':0,'real_model_calls':0,
        'observer_removed':True,'store_closed':True,'E12':'NOT_RUN'}
    private_file(directory/'binding_proof.json',report,replace=(directory/'binding_proof.json').exists())
    return report
