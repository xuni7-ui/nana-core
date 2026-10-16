"""Application-owned initial conditions, isolated from governance and identity.

A declaration proves only that this bootstrap role/seed was installed. It proves
no shared experience, familiarity, trust or command authority.
"""
import json
from ...contracts import CoreError
from ...storage import canonical,digest
from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..memory import MemoryService
from ..records import RecordService
from ..revision import state_token
from .contracts import RelationalAnchorSpec,RelationalAnchorView,SubjectPersonalitySeed

class SubjectBootstrapAuthority:
    """Trusted application construction only. Not an Operator/Manager capability."""
    pass


def latest(store,scope,component):
    if store.schema_target<10:return None
    row=store.db.execute("SELECT * FROM events WHERE kind='subject.bootstrap_revision' AND json_extract(data_json,'$.data.target_id')=? ORDER BY seq DESC LIMIT 1",(component+':'+scope,)).fetchone()
    return dict(row) if row else None


def read_current(store,scope,component,privacy_classes):
    row=latest(store,scope,component)
    if not row:return None
    rid=json.loads(row['data_json'])['data']['record_id'];head=store.one('continuity_records',rid)
    records=RecordService(store)
    if not head or head['scope']!=scope or head['lifecycle']!='ACTIVE' or head['privacy_class'] not in privacy_classes or not records.current_support(rid):return None
    body=records.read(rid)['payload']
    if digest(body)!=json.loads(row['data_json'])['data']['digest']:raise CoreError('BOOTSTRAP_SOURCE_CORRUPT')
    return rid,body


def anchor_view(store,entity_id,*,scope,privacy_classes):
    item=read_current(store,scope,'anchor',privacy_classes)
    if not item:return None
    rid,body=item;spec=RelationalAnchorSpec.model_validate_json(canonical(body))
    now=store.clock.utc_now_us()
    if spec.identity_id!=store.identity['identity_id'] or spec.entity_id!=entity_id or spec.state!='ACTIVE' or now<spec.effective_from_us or (spec.expires_at_us is not None and now>=spec.expires_at_us):return None
    return RelationalAnchorView(spec=spec,source_record_id=rid,as_of_us=now,state_token=state_token(store))


class SubjectBootstrapService:
    def __init__(self,store,authority):
        if store.schema_target<10 or type(authority) is not SubjectBootstrapAuthority:raise CoreError('SUBJECT_BOOTSTRAP_AUTHORITY_REQUIRED')
        self.store,self._authority=store,authority

    def install(self,spec,authority):
        if authority is not self._authority:raise CoreError('UNAUTHENTICATED_SUBJECT_BOOTSTRAP')
        if type(spec) not in {RelationalAnchorSpec,SubjectPersonalitySeed}:raise CoreError('TYPED_BOOTSTRAP_REQUIRED')
        spec=type(spec).model_validate_json(spec.model_dump_json())
        component='anchor' if isinstance(spec,RelationalAnchorSpec) else 'seed'
        if spec.identity_id!=self.store.identity['identity_id']:raise CoreError('BOOTSTRAP_IDENTITY_MISMATCH')
        if isinstance(spec,RelationalAnchorSpec) and (not self.store.one('entities',spec.entity_id) or spec.effective_from_us>self.store.clock.utc_now_us()):raise CoreError('BOOTSTRAP_ENTITY_OR_TIME_INVALID')
        prior=latest(self.store,spec.scope,component)
        previous=json.loads(prior['data_json'])['data'] if prior else None
        body=spec.model_dump(mode='json');sha=digest(body)
        if previous and previous['digest']==sha:
            if not read_current(self.store,spec.scope,component,('PUBLIC','PROJECT','PERSONAL','SECRET')):raise CoreError('BOOTSTRAP_SOURCE_RETIRED')
            return previous['record_id']
        if spec.revision!=(previous['revision']+1 if previous else 1):raise CoreError('STALE_BOOTSTRAP_REVISION')
        # A new explicit declaration can survive erasure of the old declaration;
        # only opaque supersession metadata is inherited, no old private content.
        mem=MemoryService(self.store);now=self.store.clock.utc_now_us();slot=component+':'+spec.scope
        reference=digest([slot,spec.revision])
        captured=self.store.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace='synthetic.subject-bootstrap' AND source_reference=? AND source_revision='1'",(reference,)).fetchone()
        source_time=captured[0] if captured else now
        evidence=mem.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.subject-bootstrap',source_reference=reference,source_kind='USER_STATEMENT'),
            text=canonical(body),privacy_class='PERSONAL',observed_time_us=source_time))
        mid=mem.add(MemoryCandidate(entity_id=self.store.identity['identity_id'],scope=spec.scope,memory_type=MemoryType.SELF,
            epistemic_kind='STATEMENT',source_evidence_id=evidence,text=canonical(body),confidence=1.0))
        data={'target_id':slot,'revision':spec.revision,'digest':sha,'supersedes_record_id':previous['record_id'] if previous else None}
        with self.store.transaction('subject.bootstrap_revision',data,source_namespace='subject.bootstrap',source_key=slot+':'+str(spec.revision)) as tx:
            rid=RecordService(self.store).create(tx,kind='SUBJECT_BOOTSTRAP',scope=spec.scope,payload=body,memories=(mid,),target_id=slot)
            if previous:
                old=self.store.one('continuity_records',previous['record_id'])
                if old and old['lifecycle']=='ACTIVE':tx.update('continuity_records',old['record_id'],lifecycle='SUPERSEDED')
            data['record_id']=rid
        return rid
