"""D-045 scoped exception, backed by committed single-use receipt; no real pins.

Raw AstrBot objects NEVER enter this module. The old synthetic callback and
sanitizer keep their gates unchanged. Real handling uses two additional gates.
"""
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from .sanitize import Metadata, MetadataSanitizer, LABEL, FORBIDDEN_VALUE, SanitizeResult
from .observer import ShadowObserver, _consume_exception
from .core_sink import MetadataCoreSink
from .one_shot import ReceiptLedger, ProductionTrustStore, REAL_SOURCE, utc
from tools.nana_host_shadow.safety import digest

@dataclass(frozen=True,slots=True)
class OneShotPermit:
    receipt_id: str
    receipt_digest: str
    metadata_digest: str
    store_binding: str
    trust_domain: str

class OneShotSanitizer(MetadataSanitizer):
    def __init__(self,*,scope,hash_key,receipt_id):
        super().__init__(scope=scope,hash_key=hash_key,probe_ids=frozenset({'nana-probe-'+receipt_id}))
        self.receipt_id=receipt_id
        self.__permits={}
        self.__outputs={}
        self.__issued=False

    def project(self,raw):
        if type(raw) is not dict or len(raw)>64: raise ValueError('DROP_METADATA_SHAPE')
        # Only allowlist lookups; never serialize/traverse unknown values.
        if raw.get('event_source')!=REAL_SOURCE or raw.get('synthetic') is not False or raw.get('probe_id') not in ('',None):
            raise ValueError('DROP_REAL_SOURCE')
        def label(name):
            v=raw.get(name)
            if type(v) is not str or not LABEL.fullmatch(v) or FORBIDDEN_VALUE.search(v):raise ValueError('DROP_REAL_LABEL')
            return v
        stamp=utc(raw.get('timestamp')).isoformat()
        return Metadata(label('platform'),label('type'),self.scoped_hash('event_id',raw.get('event_id')),stamp,
            self.scoped_hash('conversation_id',raw.get('conversation_id')),self.scoped_hash('sender_id',raw.get('sender_id')),
            REAL_SOURCE,False,'nana-probe-'+self.receipt_id)

    def project_public(self,raw):
        # Already scoped-hashed metadata crosses IPC, never raw host IDs/body.
        from .bridge_wire import validate_metadata
        m=validate_metadata(raw,self.receipt_id)
        return Metadata(**m)

    def issue_consumed_permit(self,ledger,metadata):
        if type(ledger) is not ReceiptLedger:raise ValueError('DROP_LEDGER_TYPE')
        r,v=ledger.record(self.receipt_id)
        if self.__issued:raise ValueError('DROP_ALREADY_ISSUED_PERMIT')
        if (v['state']!='CONSUMED' or v['uses']!=1 or v['core'] is not None
            or not ledger._review_valid(r,v['review']) or v['matched_metadata']!=metadata.public()
            or r.hash_scope!=self.scope or r.store_binding!=ledger.binding): raise ValueError('DROP_UNCONSUMED_PERMIT')
        p=OneShotPermit(r.receipt_id,r.receipt_digest,digest(metadata.public()),ledger.binding,ledger.trust.domain)
        self.__issued=True
        self.__permits[id(p)]=p
        return p

    def sanitize_real(self,metadata,*,permit):
        if (type(permit) is not OneShotPermit or self.__permits.pop(id(permit),None) is not permit
            or type(metadata) is not Metadata or permit.metadata_digest!=digest(metadata.public())):
            return SanitizeResult('DROP_ONE_SHOT_PERMIT')
        self.__outputs[id(metadata)]=metadata
        return SanitizeResult('ACCEPT',metadata)

    def validate_output(self,metadata):
        if type(metadata) is Metadata and metadata.synthetic is False:
            if self.__outputs.get(id(metadata)) is not metadata:raise ValueError('DROP_REAL_SANITIZER_SCOPE')
            return metadata
        return super().validate_output(metadata)

    def forget(self,metadata): self.__outputs.pop(id(metadata),None)

class OneShotCoreSink(MetadataCoreSink):
    def __init__(self,directory,sanitizer,receipt_id,*,trust=None,checkpoint=None):
        super().__init__(directory,sanitizer)
        if type(sanitizer) is not OneShotSanitizer or receipt_id!=sanitizer.receipt_id:raise ValueError('ONE_SHOT_SCOPE_REQUIRED')
        self.receipt_id=receipt_id
        self.trust=trust if trust is not None else ProductionTrustStore()
        self.checkpoint=checkpoint

    def ledger(self): return ReceiptLedger(self._open(),self.trust)

    def accept(self,raw):
        return self._accept_metadata(self.sanitizer.project(raw))

    def accept_public(self,raw):
        return self._accept_metadata(self.sanitizer.project_public(raw))

    def _accept_metadata(self,m):
        ledger=self.ledger()
        r,v=ledger.record(self.receipt_id)
        if r.hash_scope!=self.sanitizer.scope:raise ValueError('HASH_SCOPE_MISMATCH')
        if self.checkpoint:self.checkpoint('before_consume')
        ledger.consume(self.receipt_id,m,checkpoint=self.checkpoint)
        if self.checkpoint:self.checkpoint('before_evidence')
        permit=self.sanitizer.issue_consumed_permit(ledger,m)
        try:
            result=self.sanitizer.sanitize_real(m,permit=permit)
            if result.status!='ACCEPT':raise ValueError('D045_SANITIZER_BLOCKED')
            core=super().accept(result.metadata)
            if self.checkpoint:self.checkpoint('after_evidence')
            ledger.complete(self.receipt_id,core)
            return {'barrier_result':'SHADOW_BLOCKED','receipt_id':r.receipt_id,
                    'receipt_digest':r.receipt_digest,'trust_domain':ledger.trust.domain,
                    'source_provenance':r.review_provenance.value,'core':core}
        finally:self.sanitizer.forget(m)

class OneShotObserver(ShadowObserver):
    """Same FIFO worker/deadline/logger/close; never accepts a synthetic permit for real metadata."""
    operator_binding_verified=False

    async def callback_real(self,raw):
        return await self._callback(raw,public=False)

    async def callback_public(self,raw):
        return await self._callback(raw,public=True)

    async def _callback(self,raw,*,public):
        try:
            if not self.active:self._record('DROP_INACTIVE');return None
            # Shape/source check independent of receipt authority; two gates retained.
            (self.sanitizer.project_public if public else self.sanitizer.project)(raw)
            # Drop unknown/nested/body values before worker submission; capture
            # immutable scalar snapshot so caller mutation cannot change matching.
            keys=('platform','type','event_id','timestamp','conversation_hash','sender_hash','event_source','synthetic','probe_id') if public else ('platform','type','event_id','timestamp','conversation_id','sender_id','event_source','synthetic','probe_id')
            raw={k:raw.get(k) for k in keys}
            if self._pending is not None and not self._pending.done():self._record('DROP_BUSY');return None
            self._pending=self._worker.submit(self._sink.accept_public if public else self._sink.accept,raw)
            wrapped=asyncio.wrap_future(self._pending);wrapped.add_done_callback(_consume_exception)
            value=await asyncio.wait_for(asyncio.shield(wrapped),self.timeout)
            if type(value) is not dict or value.get('barrier_result')!='SHADOW_BLOCKED':
                self._record('DROP_CORE_CONTRACT');return None
            self.last_result={'status':'RECORDED','receipt':value}
        except asyncio.CancelledError:self._record('DROP_CANCELLED')
        except TimeoutError:self._record('UNKNOWN_LOCAL_STORE_COMPLETION')
        except BaseException:self._record('DROP_ONE_SHOT_FAILURE')
        return None
