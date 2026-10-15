"""Trusted negative-only governance, AFTER committed subject judgment.

OperatorAuthority is trusted application construction, never a model capability.
Source roots are typed metadata in the existing journal, never ordinary Memory.
"""
import json,re
from typing import Literal
from pydantic import Field,model_validator
from ...contracts import DTO,CoreError
from ...actions import OperatorAuthority
from ...storage import canonical,digest
from ..records import RecordService
from .contracts import RealizationTarget
from .history import record_disposition

class ManagerConstraint(DTO):
    domain: Literal['SYNTHETIC_CONTROLLER'] = 'SYNTHETIC_CONTROLLER'
    constraint_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    revision: int = Field(ge=1,le=256)
    issuer: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    source_reference: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    identity_id: str
    scope: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    restriction: Literal['DENY'] = 'DENY'
    targets: tuple[RealizationTarget,...] = Field(min_length=1,max_length=16)
    effective_from_us: int = Field(ge=0)
    expires_at_us: int = Field(ge=0)
    reason_code: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,63}$')
    revoked: bool = False
    supersedes_digest: str | None = None

    @model_validator(mode='after')
    def finite(self):
        if self.expires_at_us<=self.effective_from_us:raise ValueError('finite constraint required')
        if len(set(x.model_dump_json() for x in self.targets))!=len(self.targets):raise ValueError('duplicate target')
        return self

class ConstraintOutcome(DTO):
    record_id: str
    cycle_id: str
    intention_id: str
    intention_revision: int
    scope: str
    stage: Literal['MANAGER'] = 'MANAGER'
    result: Literal['PASS','BLOCK','UNKNOWN']
    target: RealizationTarget
    constraint_refs: tuple[str,...]
    reason_codes: tuple[str,...]
    snapshot: str
    runtime_epoch: int
    at_us: int
    valid_until_us: int
    action_id: str | None = None
    actual_effect: Literal['NONE','UNKNOWN','VERIFIED_EFFECT'] = 'NONE'
    # Minimal governance provenance; no resource operands or controller secrets.
    constraint_views: tuple['ConstraintDescriptor',...] = ()

class ConstraintDescriptor(DTO):
    constraint_id: str
    revision: int
    source_event_id: str
    scope: str
    effective_from_us: int
    expires_at_us: int
    reason_code: str

def _required(store):
    if store.schema_target<9:raise CoreError('AUTONOMY_SCHEMA_REQUIRED')

def _event_body(store,row):
    body=json.loads(row['data_json'])['data']
    if body.get('digest')!=digest(json.loads(store.artifact(row['artifact_id']))):raise CoreError('GOVERNANCE_SOURCE_CORRUPT')
    return ManagerConstraint.model_validate_json(store.artifact(row['artifact_id']))

def snapshot(store):
    _required(store)
    registry=store.one('core_meta','governance.registry')
    if not registry:return None,()
    ids=json.loads(registry['value_json'])
    if type(ids) is not list or len(ids)>64:raise CoreError('GOVERNANCE_REGISTRY_CORRUPT')
    roots=[]
    now=store.clock.utc_now_us()
    for cid in sorted(ids):
        row=store.db.execute("SELECT * FROM events WHERE kind='governance.constraint_revision' AND json_extract(data_json,'$.data.target_id')=? ORDER BY seq DESC LIMIT 1",(cid,)).fetchone()
        if not row:raise CoreError('GOVERNANCE_SOURCE_MISSING')
        constraint=_event_body(store,row)
        if constraint.identity_id!=store.identity['identity_id']:raise CoreError('GOVERNANCE_IDENTITY_MISMATCH')
        active=not constraint.revoked and constraint.effective_from_us<=now<constraint.expires_at_us
        roots.append((row['event_id'],constraint,active))
    return digest([(r,c.model_dump(mode='json'),a) for r,c,a in roots]),tuple(roots)

class GovernanceController:
    def __init__(self,store,authority):
        _required(store)
        if not isinstance(authority,OperatorAuthority) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,96}',authority.principal):
            raise CoreError('GOVERNANCE_CONTROLLER_REQUIRED')
        self.store,self._authority=store,authority

    def _auth(self,authority):
        if authority is not self._authority:raise CoreError('UNAUTHENTICATED_GOVERNANCE_CONTROLLER')

    def initialize(self,authority):
        self._auth(authority)
        if self.store.one('core_meta','governance.registry'):return
        with self.store.transaction('governance.initialized',{'issuer':authority.principal}) as tx:
            tx.put('core_meta',{'key':'governance.registry','value_json':'[]'})

    def install(self,constraint:ManagerConstraint,authority):
        self._auth(authority)
        if not isinstance(constraint,ManagerConstraint):raise CoreError('TYPED_NEGATIVE_CONSTRAINT_REQUIRED')
        constraint=ManagerConstraint.model_validate_json(constraint.model_dump_json())
        if constraint.issuer!=authority.principal or constraint.identity_id!=self.store.identity['identity_id']:
            raise CoreError('GOVERNANCE_SOURCE_MISMATCH')
        self.initialize(authority)
        previous=self.store.db.execute("SELECT * FROM events WHERE kind='governance.constraint_revision' AND json_extract(data_json,'$.data.target_id')=? ORDER BY seq DESC LIMIT 1",(constraint.constraint_id,)).fetchone()
        old=_event_body(self.store,previous) if previous else None
        if old and constraint==old:return previous['event_id']
        if constraint.revision!=(old.revision+1 if old else 1) or constraint.supersedes_digest!=(digest(old.model_dump(mode='json')) if old else None):
            raise CoreError('STALE_GOVERNANCE_REVISION')
        if old and (constraint.scope, constraint.issuer)!=(old.scope,old.issuer):raise CoreError('GOVERNANCE_SCOPE_COLLISION')
        ids=json.loads(self.store.one('core_meta','governance.registry')['value_json'])
        if constraint.constraint_id not in ids:ids.append(constraint.constraint_id)
        if len(ids)>64:raise CoreError('GOVERNANCE_CAPACITY_REQUIRES_REVIEW')
        data={'target_id':constraint.constraint_id,'revision':constraint.revision,'digest':digest(constraint.model_dump(mode='json'))}
        with self.store.transaction('governance.constraint_revision',data,source_namespace='governance.controller',source_key=constraint.constraint_id+':'+str(constraint.revision)) as tx:
            tx.payload_id=tx.artifact(constraint.model_dump_json().encode())
            tx.put('core_meta',{'key':'governance.registry','value_json':canonical(sorted(ids))})
        return tx.event_id

    def revoke(self,constraint_id,*,expected_revision,authority):
        self._auth(authority)
        row=self.store.db.execute("SELECT * FROM events WHERE kind='governance.constraint_revision' AND json_extract(data_json,'$.data.target_id')=? ORDER BY seq DESC LIMIT 1",(constraint_id,)).fetchone()
        if not row:raise CoreError('CONSTRAINT_MISSING')
        old=_event_body(self.store,row)
        if old.revoked or old.revision!=expected_revision:raise CoreError('STALE_GOVERNANCE_REVISION')
        return self.install(old.model_copy(update={'revoked':True,'revision':old.revision+1,'supersedes_digest':digest(old.model_dump(mode='json'))}),authority)

def manager_views(store,*,scope,privacy_classes,limit=16):
    if store.schema_target<9:return ()
    records=RecordService(store);out=[]
    for raw in store.db.execute("SELECT * FROM continuity_records WHERE record_kind='CONSTRAINT_OUTCOME' AND scope=? AND lifecycle='ACTIVE' ORDER BY created_at_us DESC,rowid DESC LIMIT ?",(scope,min(limit,64))):
        r=dict(raw)
        if r['privacy_class'] not in privacy_classes or not records.current_support(r['record_id']):continue
        body=records.read(r['record_id'])['payload']
        if body['result'] not in {'BLOCK','UNKNOWN'}:continue
        # Definition body, issuer config and resource operands never leave the gate.
        out.append({'record_id':r['record_id'],'intention_id':body['intention_id'],'intention_revision':body['intention_revision'],
            'constraint_refs':tuple(body['constraint_refs']),'reason_codes':tuple(body['reason_codes']),
            'scope':scope,'stage':'MANAGER','result':body['result'],'at_us':body['at_us'],'valid_until_us':body['valid_until_us'],
            'action_id':body['action_id'],'actual_effect':body['actual_effect'],'constraints':tuple(body.get('constraint_views',()))})
    return tuple(out)

class ManagerConstraintGate:
    def __init__(self,store):_required(store);self.store,self.records=store,RecordService(store)

    def _cycle(self,intention):
        row=self.store.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=?',(intention['subject_event_id'],)).fetchone()
        body=self.records.read(row['record_id'])['payload']
        if not self.records.current_support(row['record_id']):raise CoreError('INTENTION_SUPPORT_RETIRED')
        return dict(row),body

    def read(self,record_id):
        return ConstraintOutcome.model_validate_json(canonical({'record_id':record_id,**self.records.read(record_id)['payload']}))

    def gate(self,intention_id,*,expected_revision):
        i=self.store.one('subject_intentions',intention_id)
        if not i:raise CoreError('INTENTION_MISSING')
        if i['state'] in {'MANAGER_BLOCKED','MANAGER_UNKNOWN'}:
            old=self.store.db.execute("SELECT * FROM events WHERE kind='governance.outcome' AND json_extract(data_json,'$.data.target_id')=? ORDER BY seq DESC LIMIT 1",(intention_id,)).fetchone()
            return self.read(json.loads(old['data_json'])['data']['record_id'])
        if i['state']!='PENDING' or i['revision']!=expected_revision or i['expires_at_us']<=self.store.clock.utc_now_us():raise CoreError('STALE_INTENTION_REVISION')
        cycle,body=self._cycle(i)
        if not body.get('evaluation') or body['evaluation']['normative']!='ENDORSED' or not body.get('realization_target'):raise CoreError('SUBJECT_DID_NOT_ENDORSE_TARGET')
        target=RealizationTarget.model_validate_json(canonical(body['realization_target']))
        try:token,roots=snapshot(self.store)
        except (CoreError,ValueError,KeyError,TypeError):token,roots=None,()
        epoch=getattr(getattr(self.store,'_runtime_guard',None),'__self__',None)
        epoch=epoch.epoch if epoch else 0
        now=self.store.clock.utc_now_us()
        high=self.store.one('core_meta','governance.clock')
        rollback=high and now<json.loads(high['value_json'])
        veto=[(ref,c) for ref,c,active in roots if active and c.scope==i['scope'] and target in c.targets]
        result='UNKNOWN' if token is None or rollback else 'BLOCK' if veto else 'PASS'
        snapshot_id=token or 'UNINITIALIZED'
        key=digest([intention_id,expected_revision,snapshot_id,epoch,now//30_000_000])
        old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='governance.outcome' AND source_key=?",(key,)).fetchone()
        if old:return self.read(json.loads(old[0])['data']['record_id'])
        action=self.store.db.execute('SELECT * FROM actions WHERE effect_slot=?',('subject:'+intention_id,)).fetchone()
        actual='UNKNOWN' if action and action['state'] in {'DISPATCHING','PENDING_VERIFY','UNKNOWN','FAILED_EFFECT'} else 'VERIFIED_EFFECT' if action and action['state']=='SUCCEEDED' else 'NONE'
        data={'target_id':intention_id}
        with self.store.transaction('governance.outcome',data,source_namespace='governance.outcome',source_key=key) as tx:
            payload=dict(cycle_id=cycle['cycle_id'],intention_id=intention_id,intention_revision=expected_revision,scope=i['scope'],
                stage='MANAGER',result=result,target=target.model_dump(mode='json'),constraint_refs=tuple(r for r,c in veto),
                reason_codes=tuple(c.reason_code for r,c in veto) or ('NEGATIVE_ONLY_NO_VETO',) if result=='PASS' else tuple(c.reason_code for r,c in veto) or ('GOVERNANCE_UNAVAILABLE',),
                snapshot=snapshot_id,runtime_epoch=epoch,at_us=now,valid_until_us=min([now+30_000_000]+[c.expires_at_us for r,c in veto]),
                action_id=action['action_id'] if action else None,actual_effect=actual,
                constraint_views=tuple(ConstraintDescriptor(constraint_id=c.constraint_id,revision=c.revision,source_event_id=r,
                    scope=c.scope,effective_from_us=c.effective_from_us,expires_at_us=c.expires_at_us,reason_code=c.reason_code).model_dump(mode='json') for r,c in veto))
            rid=self.records.create(tx,kind='CONSTRAINT_OUTCOME',scope=i['scope'],payload=payload,records=(i['record_id'],),target_id=intention_id)
            data['record_id']=rid
            record_disposition(self.store,tx,cycle_id=cycle['cycle_id'],intention_id=intention_id,intention_revision=expected_revision,
                scope=i['scope'],parent_record=rid,stage='MANAGER',code='REALIZATION_ELIGIBLE' if result=='PASS' else 'MANAGER_'+('BLOCKED' if result=='BLOCK' else 'UNKNOWN'),
                normative='ENDORSED',wanted=body['evaluation']['wanted'],reason_refs=tuple(r for r,c in veto))
            if result!='PASS':
                tx.update('subject_intentions',intention_id,state='MANAGER_BLOCKED' if result=='BLOCK' else 'MANAGER_UNKNOWN',revision=i['revision']+1)
                for c in self.store.db.execute('SELECT * FROM subject_goal_candidates WHERE intention_id=?',(intention_id,)).fetchall():
                    tx.update('subject_goal_candidates',c['candidate_id'],state='WITHDRAWN')
            tx.put('core_meta',{'key':'governance.clock','value_json':canonical(max(now,json.loads(high['value_json']) if high else 0))})
        return self.read(rid)

    def require_current(self,outcome):
        if not isinstance(outcome,ConstraintOutcome) or self.read(outcome.record_id)!=outcome:raise CoreError('GOVERNANCE_OUTCOME_TAMPERED')
        if outcome.result!='PASS':raise CoreError('INTENTION_BLOCKED_MANAGER')
        i=self.store.one('subject_intentions',outcome.intention_id)
        epoch=getattr(getattr(self.store,'_runtime_guard',None),'__self__',None)
        epoch=epoch.epoch if epoch else 0
        token,roots=snapshot(self.store)
        now=self.store.clock.utc_now_us()
        if (not i or i['state']!='PENDING' or i['revision']!=outcome.intention_revision or now>=min(i['expires_at_us'],outcome.valid_until_us)
            or now<outcome.at_us or token!=outcome.snapshot or epoch!=outcome.runtime_epoch):raise CoreError('STALE_MANAGER_PASS')
        cycle,body=self._cycle(i)
        if body.get('realization_target')!=outcome.target.model_dump(mode='json'):raise CoreError('GOVERNANCE_TARGET_MISMATCH')
