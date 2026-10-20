"""One-call controlled PROJECT source qualification; no credential discovery.

Default caller uses synthetic loopback. A real transport requires an explicit
separately authorized host binding. This module never constructs credentials.
"""
import json
from pathlib import Path
from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.storage import canonical,digest
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget
from nana_core.continuity.world_loop.world import WorldModel,SourcedClaim
from nana_core.continuity.world_loop.attention import ConcernService
from nana_core.continuity.subject import SubjectInput


def run(root,transport,*,allow_real_provider=False):
    if transport.remote and not allow_real_provider:raise CoreError('NEW_PAID_QUALIFICATION_AUTHORIZATION_REQUIRED')
    root=Path(root)
    if root.exists():raise CoreError('FRESH_QUALIFICATION_ROOT_REQUIRED')
    root.mkdir(parents=True)
    # Owned project file, no personal information or user device capture.
    path=root/'project-source.json'
    path.write_text(canonical({'resource_state':'a controlled project note needs review','opportunities':[{'topic':'project-note','motive':'CURIOSITY','value':'HIGH','possible_behaviors':['EXPLORE','WATCH']}]}))
    raw=path.read_bytes();clock=Clock();db=root/'subject.db'
    policy=ContextPolicy(policy_id='closure-controlled-project',allowed_scopes=('world',),readable_privacy=('PUBLIC','PROJECT'),remote_privacy=('PUBLIC','PROJECT'))
    with open_runtime(db,clock,wall=True) as r:
        m=MemoryService(r.store);records=r.subject.records
        text=raw.decode();eid=m.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT',source_namespace='recorded.project.foundation-closure',source_reference='owned-note',source_kind='DIRECT_OBSERVATION'),text=text,privacy_class='PROJECT',observed_time_us=clock.utc_now_us()))
        mid=m.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text))
        session=CognitionSession(r,transport,policy)
        cid=session.prepare('closure-one-new-request','INTERPRET',(mid,),budget=CognitionBudget(timeout_ms=15000,cost_ceiling_micro=50000))
        outcome=session.execute(cid)
        result={'execution':'REAL_PROVIDER' if transport.remote else 'SYNTHETIC_LOOPBACK','request_id':cid,'state':outcome['state'],'source_sha256':digest(raw),'identity_id':r.identity_id,'max_new_calls':1,'retry':0,'fallback':0}
        if outcome['state']!='PROPOSED':return result
        reply=session.proposal(outcome['record_id'])
        # Accepted strict text semantics become a model belief, never raw fact.
        claim=SourcedClaim(entity_id='device',predicate='project.semantic',kind='MODEL_BELIEF',value=reply.proposal.interpretation,valid_from_us=clock.utc_now_us(),confidence=reply.proposal.confidence)
        body=canonical({'world_claim':claim.model_dump(mode='json'),'request_id':cid,'request_digest':reply.request_digest,'provider_id':reply.provider_id,'model_id':reply.model_id})
        de=m.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT',source_namespace='recorded.project.foundation-closure.semantic',source_reference=cid,source_kind='MODEL_DERIVATION'),text=body,privacy_class='PROJECT',observed_time_us=clock.utc_now_us()))
        derived=m.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.SEMANTIC,epistemic_kind='INFERENCE',source_evidence_id=de,text=body,derived_from=(mid,)))
        world=WorldModel(r.store,scopes=('world',),privacy_classes=('PROJECT',));world.ingest(derived)
        concerns=ConcernService(r,resources=('synthetic://project/note',));ids=concerns.offer(outcome['record_id'])
        event=concerns.opportunity()
        if event is None:result.update(state='PARTIAL_NO_ELIGIBLE_CONCERN');return result
        cycle=r.subject.run(event.input)
        result.update(world_before=world.view('device','project.semantic').state,concern_ids=ids,judgment_before=cycle.judgment.stance,intention_before=cycle.intention.kind,source_kind=m.read(derived)['source_provenance']['source_kind'])
        # Actual withdrawal, not a log assertion: change the owned source and erase
        # the old observation. It cannot continue supporting world/concern/C.
        path.write_text(canonical({'resource_state':'withdrawn by controlled source owner'}))
        m=MemoryService(r.store,r.authority);m.forget(mid,r.authority)
        assert concerns.opportunity() is None
        after=r.subject.run(SubjectInput(source_key='development.closure.withdrawn-wake',domain='DEVELOPMENT_MATERIAL',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',privacy_class='PROJECT',observed_at_us=clock.utc_now_us()))
        result.update(world_after=world.view('device','project.semantic').state,intention_after=after.intention.kind,provider_id=reply.provider_id,model_id=reply.model_id,usage=reply.usage,billing=reply.billing,http=reply.http_observation.model_dump(mode='json') if reply.http_observation else None)
        assert result['world_before']=='SUPPORTED_BELIEF' and result['world_after']=='UNKNOWN' and after.intention.kind=='NO_ACTION'
        assert not r.store.all('grants') and not r.store.all('actions') and not r.store.all('goals')
        identity=r.identity_id
    with open_runtime(db,clock,wall=True) as r:
        session=CognitionSession(r,transport,policy)
        assert session.execute(cid)['replayed']
        assert r.identity_id==identity
        result.update(restart_identity=True,no_duplicate_dispatch=True,new_grants=0,new_actions=0,new_goals=0,qualified_scope='CONTROLLED_TEXT_SOURCE_INTEGRATION_NOT_HUMAN_NATURALNESS')
    return result
