"""In-process host shadow: persist evidence and draft decisions; never dispatch.

There is deliberately no Runtime, kernel, live port or callable executor member.
Observation text cannot turn draft fields into an Action/Grant/Strategy.
"""
import json
from pydantic import Field
from ..contracts import DTO,CoreError
from ..storage import canonical,digest
from .contracts import RuntimeIntegrationContext, ShadowCapabilityPort
from .astrbot import AstrBotObservationAdapter

class ProposedHostAction(DTO):
    capability: str = Field(min_length=1,max_length=128)
    resource: str = Field(min_length=1,max_length=512)
    reason: str = Field(min_length=1,max_length=512)

class ShadowDecision(DTO):
    interpretation: str = Field(min_length=1,max_length=2048)
    memory_ids: tuple[str,...] = Field(default=(),max_length=32)
    evidence_event_ids: tuple[str,...] = Field(default=(),max_length=32)
    goal_purpose: str | None = Field(default=None,max_length=512)
    planned_actions: tuple[ProposedHostAction,...] = Field(default=(),max_length=6)
    rationale: str = Field(min_length=1,max_length=2048)
    model_descriptor: str = Field(default='engineering-fixture',max_length=128)
    model_kind: str = Field(default='fixture',pattern=r'^(fixture|real_model)$')
    experience_refs: tuple[str,...] = Field(default=(),max_length=16)

class ShadowBridge:
    def __init__(self,store,context):
        self.store=store;self.context=RuntimeIntegrationContext.model_validate(context.model_dump())
        if store.identity['identity_id']!=self.context.expected_identity_id:raise CoreError('SHADOW_IDENTITY_MISMATCH')
        self.adapter=AstrBotObservationAdapter()
    def observe(self,event,decision,revision='1'):
        if event.host_instance!=self.context.host_instance:raise CoreError('SHADOW_HOST_MISMATCH')
        decision=ShadowDecision.model_validate(decision.model_dump())
        if decision.model_kind!='fixture':raise CoreError('REAL_MODEL_SHADOW_REQUIRES_CALL_LEDGER_BINDING')
        eid=self.adapter.ingest(self.store,event)
        for mid in decision.memory_ids:
            memory=self.store.one('memory_items',mid)
            if not memory or self.store.event(memory['created_event_id'])['identity_id']!=self.context.expected_identity_id:
                raise CoreError('SHADOW_MEMORY_UNSUPPORTED')
        for ref in decision.evidence_event_ids:
            evidence=self.store.event(ref)
            if evidence['identity_id']!=self.context.expected_identity_id:raise CoreError('SHADOW_EVIDENCE_IDENTITY')
            if evidence['artifact_id']:self.store.artifact(evidence['artifact_id'])
        for sid in decision.experience_refs:
            s=self.store.one('strategies',sid)
            if not s or s['status']!='ACTIVE':raise CoreError('SHADOW_EXPERIENCE_UNSUPPORTED')
        key='cloud.shadow:'+digest([eid,revision]);prior=self.store.one('memory_items',key)
        body={'type':'SHADOW_DECISION','identity':self.store.identity,'observation_event_id':eid,
            'input_hash':digest(decision.model_dump()),'decision':decision.model_dump(mode='json'),
            'goal_draft':{'purpose':decision.goal_purpose,'acceptance':'NOT_ACCEPTED_FOR_ACTIVATION'} if decision.goal_purpose else None,
            'plan_draft':[a.model_dump() for a in decision.planned_actions],
            'execution_state':'SHADOW_BLOCKED','external_execute':False,'production_budget_consumed':False,
            'source_refs':[{'event_id':eid,'artifact_id':self.store.event(eid)['artifact_id'],'coverage':'FULL'}],
            'assessment':'UNASSESSED','epistemic_kind':'MODEL_INFERENCE','model_semantics_verified':False}
        if prior:
            existing=json.loads(prior['body_json'])
            if existing['input_hash']!=body['input_hash']:raise CoreError('SHADOW_DECISION_COLLISION')
            return existing
        with self.store.transaction('cloud.shadow_decision',{'event_id':eid,'execution':'SHADOW_BLOCKED'}) as tx:
            tx.payload_id=tx.artifact(canonical(body).encode())
            tx.put('memory_items',{'memory_id':key,'kind':'CLAIM','status':'ACTIVE','body_json':canonical(body),'created_event_id':tx.event_id})
        return json.loads(canonical(body))
    def capture_export(self,bundle):
        # A bundle is supplied evidence, not authority or a verified memory.
        if not isinstance(bundle,dict) or bundle.get('schema_version')!=1:raise CoreError('EXPORT_SCHEMA_UNKNOWN')
        unsigned={k:v for k,v in bundle.items() if k!='manifest_hash'}
        if digest(unsigned)!=bundle.get('manifest_hash'):raise CoreError('EXPORT_MANIFEST_MISMATCH')
        from ..contracts import Observation
        observation=Observation(source_namespace='cloud.iris_export',object_id=bundle['manifest_hash'],kind='unrelated',
            raw_text=canonical({'export_bundle':bundle,'assessment':'UNASSESSED','execution_evidence':False}),
            occurred_at=None)
        return self.store.ingest(observation)
    def execute(self,*args,**kwargs):raise CoreError('SHADOW_BLOCKED')


def reconcile(event_id,legacy,core,*,important_evidence=()):
    """Pure comparison, no winner inferred from difference and no Store writes."""
    legacy=ShadowDecision.model_validate(legacy.model_dump());core=ShadowDecision.model_validate(core.model_dump())
    arms={}
    for label,d in [('legacy',legacy),('core',core)]:
        arms[label]={'interpretation':d.interpretation,'memory_retrieval':d.memory_ids,'relevant_evidence':d.evidence_event_ids,
            'goal_proposal':d.goal_purpose,'decision':d.rationale,'planned_actions':[a.model_dump() for a in d.planned_actions],
            'omitted_important_evidence':sorted(set(important_evidence)-set(d.evidence_event_ids)),
            'should_act':bool(d.planned_actions),'model':d.model_descriptor,'experience':d.experience_refs}
    differences=[k for k in arms['core'] if arms['legacy'][k]!=arms['core'][k]]
    return {'event_id':event_id,'same_event':True,'paths':arms,'differences':differences,
        'attribution':{'memory_inputs_differ':legacy.memory_ids!=core.memory_ids,
            'experience_inputs_differ':legacy.experience_refs!=core.experience_refs,
            'model_descriptors_differ':legacy.model_descriptor!=core.model_descriptor,
            'causal_effect':'UNKNOWN unless matched ablation is separately run'},
        'unreasonable_goal':'UNASSESSED; needs evidence-backed rubric/operator review',
        'unsupported_citation_rate':'UNASSESSED; Bridge separately rejects absent refs',
        'winner':None,'external_execution':'SHADOW_BLOCKED','scope':'fixture paths; not real production parity'}

def human_report(report):
    return '\n'.join(['# Shadow reconciliation',f"Event: {report['event_id']}",
        'Execution: SHADOW_BLOCKED','Differences: '+(', '.join(report['differences']) or '(none)'),
        'Attribution describes changed inputs; causal superiority UNKNOWN.','No winner inferred.'])+'\n'
