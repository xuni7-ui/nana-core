"""Reviewed, store-bound, single-use observation permission. NOT a Core Grant.

Production trust is SOURCE PINNED and empty. Fixtures have a different class and
persist a different domain; they cannot promote proof or be opened by real CLI.
Only the existing Store writer/transaction/core_meta/event log is used.
"""
from enum import StrEnum
from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import uuid4
import json
import re
from types import MappingProxyType
from pydantic import BaseModel, ConfigDict, Field, model_validator
from tools.nana_host_shadow.safety import canonical, digest

REAL_SOURCE = 'astrbot_on_decorating_result'
SKEW_SECONDS = 2
MAX_WINDOW_SECONDS = 600
PRODUCTION_REVIEW_PINS = MappingProxyType({})  # reviewed receipt digest -> authorization digest; NEVER configuration

class Provenance(StrEnum):
    FIXTURE = 'FIXTURE'
    LOCAL_SYNTHETIC = 'LOCAL_SYNTHETIC'
    ASTRBOT_LIFECYCLE = 'ASTRBOT_LIFECYCLE'
    ASTRBOT_REAL_MESSAGE = 'ASTRBOT_REAL_MESSAGE'

class ReceiptState(StrEnum):
    CREATED='CREATED'
    REVIEWED='REVIEWED'
    ARMED='ARMED'
    CONSUMED='CONSUMED'
    VERIFIED='VERIFIED'
    EXPIRED='EXPIRED'
    DISARMED='DISARMED'
    REJECTED='REJECTED'
    CORRUPT='CORRUPT'
    UNKNOWN='UNKNOWN'


def utc(value):
    if type(value) is not str or len(value)>40: raise ValueError('RECEIPT_TIME_INVALID')
    dt=datetime.fromisoformat(value)
    if dt.tzinfo is None or dt.utcoffset()!=timedelta(0): raise ValueError('RECEIPT_UTC_REQUIRED')
    if dt.isoformat()!=value: raise ValueError('RECEIPT_CANONICAL_UTC_REQUIRED')
    return dt

class OneShotReceipt(BaseModel):
    model_config=ConfigDict(strict=True,extra='forbid',frozen=True)
    receipt_id: str = Field(pattern=r'^r04-[0-9a-f]{32}$',max_length=36)
    schema_version: Literal[1] = 1
    purpose: Literal['one-shot metadata-only result-path Shadow'] = 'one-shot metadata-only result-path Shadow'
    issued_at: str = Field(max_length=40)
    expires_at: str = Field(max_length=40)
    platform_scope: str = Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_.-]{0,47}$',max_length=48)
    conversation_hash: str = Field(pattern=r'^[0-9a-f]{64}$',max_length=64)
    sender_hash: str = Field(pattern=r'^[0-9a-f]{64}$',max_length=64)
    event_type_scope: str = Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_.-]{0,47}$',max_length=48)
    event_source: Literal['astrbot_on_decorating_result'] = REAL_SOURCE
    max_uses: Literal[1] = 1
    authorization_class: Literal['FIRST_REAL_MESSAGE_SHADOW'] = 'FIRST_REAL_MESSAGE_SHADOW'
    review_provenance: Provenance
    review_receipt_digest: str = Field(pattern=r'^[0-9a-f]{64}$',max_length=64)
    store_binding: str = Field(pattern=r'^[0-9a-f]{64}$',max_length=64)
    hash_scope: str = Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_.-]{0,47}$',max_length=48)

    @model_validator(mode='before')
    @classmethod
    def exact_types(cls, values):
        if type(values) is not dict: raise ValueError('RECEIPT_OBJECT_REQUIRED')
        for key in ('schema_version','max_uses'):
            if key in values and type(values[key]) is not int: raise ValueError('RECEIPT_INTEGER_REQUIRED')
        return values

    @model_validator(mode='after')
    def temporal_contract(self):
        start,end=utc(self.issued_at),utc(self.expires_at)
        if not 0 < (end-start).total_seconds() <= MAX_WINDOW_SECONDS: raise ValueError('RECEIPT_WINDOW_INVALID')
        from .sanitize import FORBIDDEN_VALUE
        if any(FORBIDDEN_VALUE.search(v) for v in (self.platform_scope,self.event_type_scope,self.hash_scope)):
            raise ValueError('RECEIPT_LABEL_INVALID')
        return self

    def authorization(self):
        return self.model_dump(mode='json',exclude={'review_receipt_digest'})

    def canonical(self):
        return canonical(self.model_dump(mode='json'))

    @property
    def authorization_digest(self): return digest(self.authorization())
    @property
    def receipt_digest(self): return digest(self.model_dump(mode='json'))


def parse_receipt(raw):
    if type(raw) is not str or len(raw)>4096: raise ValueError('RECEIPT_SIZE_OR_TYPE')
    receipt=OneShotReceipt.model_validate_json(raw)
    if receipt.canonical()!=raw: raise ValueError('RECEIPT_NONCANONICAL')
    return receipt


def review_document(receipt):
    return {'schema_version':1,'authorization_digest':receipt.authorization_digest,
            'store_binding':receipt.store_binding,'receipt_id':receipt.receipt_id,
            'review_provenance':receipt.review_provenance.value}

class ProductionTrustStore:
    __slots__=()
    domain='PRODUCTION'
    def validates(self,receipt,review):
        return (receipt.review_provenance is Provenance.ASTRBOT_REAL_MESSAGE
                and PRODUCTION_REVIEW_PINS.get(digest(review))==receipt.authorization_digest)

class FixtureTrustStore:
    """Development harness only. Cannot authorize any non-FIXTURE receipt."""
    __slots__=()
    domain='FIXTURE'
    def validates(self,receipt,review): return receipt.review_provenance is Provenance.FIXTURE

class ReceiptLedger:
    def __init__(self, store, trust=None):
        self.store=store
        self.trust=trust if trust is not None else ProductionTrustStore()
        if type(self.trust) not in (ProductionTrustStore,FixtureTrustStore): raise ValueError('TRUST_STORE_TYPE_BLOCKED')
        if store.one('core_meta','recovery_quarantine')['value_json']!='false': raise ValueError('RESTORED_STORE_BLOCKED')
        if not store.one('core_meta','cloud.shadow_runtime'): raise ValueError('SHADOW_STORE_REQUIRED')
        row=store.one('core_meta','r04.store_binding')
        if row is None:
            binding=digest([store.identity['identity_id'],uuid4().hex])
            with store.transaction('r04.store_bound') as tx:
                tx.put('core_meta',{'key':'r04.store_binding','value_json':canonical(binding)})
        self.binding=json.loads(store.one('core_meta','r04.store_binding')['value_json'])

    def _key(self, rid):
        if type(rid) is not str or not re.fullmatch(r'r04-[0-9a-f]{32}',rid): raise ValueError('RECEIPT_ID_INVALID')
        return 'r04.receipt:'+rid

    def _load(self,rid):
        row=self.store.one('core_meta',self._key(rid))
        if not row: raise ValueError('RECEIPT_NOT_FOUND')
        record=json.loads(row['value_json'])
        receipt=parse_receipt(record['receipt'])
        if receipt.store_binding!=self.binding or record['receipt_digest']!=receipt.receipt_digest:
            raise ValueError('RECEIPT_CORRUPT_OR_COPIED')
        if record['trust_domain']!=self.trust.domain: raise ValueError('TRUST_DOMAIN_BLOCKED')
        if record['state'] not in set(ReceiptState): raise ValueError('RECEIPT_STATE_CORRUPT')
        if record['uses'] not in (0,1) or (record['state'] in ('CONSUMED','VERIFIED','UNKNOWN') and record['uses']!=1):
            raise ValueError('RECEIPT_USE_CORRUPT')
        return receipt,record

    def _write(self, tx, receipt, record):
        tx.put('core_meta',{'key':self._key(receipt.receipt_id),'value_json':canonical(record)})

    def _now(self):
        # Persistent high water prevents clock rollback from reviving expiry.
        now=self.store.clock.utc_now_us()
        row=self.store.one('core_meta','r04.clock_highwater')
        now=max(now,json.loads(row['value_json']) if row else now)
        with self.store.transaction('r04.clock_observed') as tx:
            tx.put('core_meta',{'key':'r04.clock_highwater','value_json':canonical(now)})
        return datetime.fromtimestamp(now/1_000_000,timezone.utc)

    def create(self,receipt):
        if type(receipt) is not OneShotReceipt: raise ValueError('STRICT_RECEIPT_REQUIRED')
        receipt=parse_receipt(receipt.canonical())
        if receipt.store_binding!=self.binding: raise ValueError('RECEIPT_STORE_MISMATCH')
        if self.store.one('core_meta',self._key(receipt.receipt_id)): raise ValueError('DUPLICATE_RECEIPT_ID')
        record={'receipt':receipt.canonical(),'receipt_digest':receipt.receipt_digest,
                'state':'CREATED','uses':0,'trust_domain':self.trust.domain,'review':None,
                'matched_metadata':None,'consumed_at':None,'core':None}
        with self.store.transaction('r04.receipt_created',{'receipt_id':receipt.receipt_id}) as tx:
            self._write(tx,receipt,record)
        return self.status(receipt.receipt_id)

    def _review_valid(self,receipt,review):
        return (type(review) is dict and review==review_document(receipt)
                and digest(review)==receipt.review_receipt_digest
                and self.trust.validates(receipt,review))

    def review(self,rid,review):
        r,v=self._load(rid)
        if v['state']!='CREATED' or not self._review_valid(r,review): raise ValueError('REVIEW_UNTRUSTED')
        v.update(state='REVIEWED',review=review)
        with self.store.transaction('r04.receipt_reviewed',{'receipt_id':rid,'domain':self.trust.domain}) as tx:self._write(tx,r,v)
        return self.status(rid)

    def _live(self,r,v,now):
        if now>=utc(r.expires_at):
            if v['state'] in ('CREATED','REVIEWED','ARMED'):
                v['state']='EXPIRED'
                with self.store.transaction('r04.receipt_expired',{'receipt_id':r.receipt_id}) as tx:self._write(tx,r,v)
            raise ValueError('RECEIPT_EXPIRED')
        if utc(r.issued_at)>now+timedelta(seconds=SKEW_SECONDS): raise ValueError('RECEIPT_FUTURE_ISSUED')

    def arm(self,rid):
        r,v=self._load(rid)
        if v['state']!='REVIEWED' or not self._review_valid(r,v['review']): raise ValueError('RECEIPT_NOT_REVIEWED')
        self._live(r,v,self._now());v['state']='ARMED'
        with self.store.transaction('r04.receipt_armed',{'receipt_id':rid}) as tx:self._write(tx,r,v)
        return self.status(rid)

    def disarm(self,rid):
        r,v=self._load(rid)
        if v['state'] not in ('CREATED','REVIEWED','ARMED'): raise ValueError('RECEIPT_TERMINAL')
        v['state']='DISARMED'
        with self.store.transaction('r04.receipt_disarmed',{'receipt_id':rid}) as tx:self._write(tx,r,v)
        return self.status(rid)

    def consume(self,rid,metadata, *, checkpoint=None):
        r,v=self._load(rid)
        if v['uses']!=0 or v['state'] in ('CONSUMED','VERIFIED','UNKNOWN'): raise ValueError('ALREADY_CONSUMED')
        if v['state']!='ARMED' or not self._review_valid(r,v['review']): raise ValueError('RECEIPT_NOT_ARMED')
        now=self._now();self._live(r,v,now)
        if (metadata.platform!=r.platform_scope or metadata.type!=r.event_type_scope
            or metadata.sender_hash!=r.sender_hash or metadata.conversation_hash!=r.conversation_hash
            or metadata.event_source!=REAL_SOURCE or metadata.synthetic is not False
            or metadata.probe_id!='nana-probe-'+rid): raise ValueError('RECEIPT_SCOPE_MISMATCH')
        t=utc(metadata.timestamp)
        if not utc(r.issued_at)-timedelta(seconds=SKEW_SECONDS)<=t<utc(r.expires_at): raise ValueError('EVENT_TIME_OUT_OF_SCOPE')
        event_key='r04.consumed_event:'+digest([r.hash_scope,metadata.platform,metadata.conversation_hash,metadata.event_id])
        if self.store.one('core_meta',event_key): raise ValueError('EVENT_REPLAY_BLOCKED')
        with self.store.transaction('r04.receipt_consumed',{'receipt_id':rid,'event_hash':metadata.event_id}) as tx:
            # MATCHED and CONSUMED are one atomic commit, no recoverable reusable MATCHED.
            v.update(state='CONSUMED',uses=1,matched_metadata=metadata.public(),consumed_at=now.isoformat())
            self._write(tx,r,v)
            tx.put('core_meta',{'key':event_key,'value_json':canonical({'receipt_id':rid})})
            if checkpoint: checkpoint('before_consume_commit')
        if checkpoint: checkpoint('after_consume_commit')
        return r,v

    def complete(self,rid,core):
        r,v=self._load(rid)
        if v['state']!='CONSUMED' or v['uses']!=1: raise ValueError('RECEIPT_TERMINAL')
        if core.get('barrier_result')!='SHADOW_BLOCKED':raise ValueError('CORE_BARRIER_REQUIRED')
        v['core']=core
        with self.store.transaction('r04.core_recorded',{'receipt_id':rid}) as tx:self._write(tx,r,v)

    def status(self,rid):
        r,v=self._load(rid)
        # No self-declared VERIFIED, no raw identifier/body.
        return {'receipt_id':rid,'state':v['state'],'uses':v['uses'],'receipt_digest':r.receipt_digest,
                'trust_domain':v['trust_domain'],'review_provenance':r.review_provenance.value,
                'core_recorded':v['core'] is not None}

    def record(self,rid): return self._load(rid)
