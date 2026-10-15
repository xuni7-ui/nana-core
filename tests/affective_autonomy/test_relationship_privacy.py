import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.autonomy.contracts import RelationshipDetails,SocialExpectationSpec,DisclosureRequest
from nana_core.continuity.autonomy.relationships import relationship_influence
from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraintGate
from nana_core.continuity.context import ContextAssembler,ContextPolicy,ContextRequest
from nana_core.continuity.memory import MemoryService
from .conftest import event
from .test_governance import proposed,constraint


def relate(r,key,kind,domain='interaction',**updates):
 details=RelationshipDetails(domain=domain,**updates)
 c=r.subject.run(event(r,key,relationship_kind=kind,relationship_details=details))
 return dict(r.store.db.execute('SELECT * FROM relationship_events WHERE subject_event_id=?',(c.event_id,)).fetchone())

def view(r,privacy=('PERSONAL',)):
 return relationship_influence(r.store,r.config.entity_id,scope='lab',privacy_classes=privacy)

def test_domain_trust_target_repair_boundary_and_deletion(subject):
 r=subject
 relate(r,'shared','SHARED_HISTORY');relate(r,'project','SHARED_PROJECT')
 for domain in ('project','privacy'):
  relate(r,domain+'-1','TRUST',domain);relate(r,domain+'-2','TRUST',domain)
 baseline=view(r);assert baseline.familiarity.assessment=='FAMILIAR'
 assert {x.domain:x.assessment for x in baseline.trust}['project']=='SUPPORTED'
 breach=relate(r,'breach','CONFLICT','project',trust_breach=True)
 conflict=relate(r,'other-conflict','CONFLICT','privacy')
 changed=view(r);assert {x.domain:x.assessment for x in changed.trust}['project']=='CONTESTED'
 assert {x.domain:x.assessment for x in changed.trust}['privacy']=='SUPPORTED'
 relate(r,'repair','REPAIR','project',target_event_id=breach['relationship_event_id'])
 repaired=view(r);assert repaired.repair_tension.assessment=='UNRESOLVED'
 assert {x.domain:x.assessment for x in repaired.trust}['project']=='RECOVERING'
 assert conflict['record_id'] in repaired.repair_tension.counter_refs
 assert breach['record_id'] not in repaired.repair_tension.counter_refs
 src=r.store.one('subject_events',conflict['subject_event_id'])['memory_id']
 MemoryService(r.store,r.authority).forget(src,r.authority)
 after=view(r)
 assert conflict['record_id'] not in after.source_record_ids
 assert r.store.identity['revision']==1


def test_social_boundary_is_not_manager_and_secret_never_enters_context(subject):
 r=subject
 spec=SocialExpectationSpec(topic='private-topic',expectation='EXPLICITLY_PRIVATE',timing='ON_REQUEST')
 relate(r,'boundary','BOUNDARY',social_expectation=spec)
 c=proposed(r,'private-topic')
 assert c.evaluation.normative=='RESTRAINED' and c.evaluation.wanted
 assert not r.store.all('actions')
 ctrl=GovernanceController(r.store,r.authority);ctrl.install(constraint(r),r.authority)
 other=proposed(r,'another-topic')
 assert other.evaluation.normative=='ENDORSED'
 assert ManagerConstraintGate(r.store).gate(other.intention_id,expected_revision=1).result=='BLOCK'
 # Secret source is admitted by an explicitly local controller, then must be
 # unavailable to the normal projector and remote ModelPort destination.
 from nana_core.continuity.subject import SubjectLoop
 wide=SubjectLoop(r.store,scopes=('lab',),privacy_classes=('PERSONAL','SECRET'))
 wide.run(event(r,'secret',privacy_class='SECRET',text='SYNTHETIC-PRIVATE-CANARY',relationship_kind='TRUST'))
 assert not view(r,('PUBLIC',)).source_record_ids
 req=ContextRequest(entity_id=r.config.entity_id,scopes=('lab',),task_class='subject',task='A public fixture question',task_privacy_class='PUBLIC',destination='DEVELOPMENT_REMOTE',max_input_tokens=32000)
 pol=ContextPolicy(policy_id='public-only',allowed_scopes=('lab',),readable_privacy=('PUBLIC','PERSONAL','SECRET'),remote_privacy=('PUBLIC',))
 ctx=ContextAssembler(r.store,r.authority).assemble(req,pol)
 assert 'SYNTHETIC-PRIVATE-CANARY' not in ctx.model_dump_json()
 assert 'DO_NOT_READ_RESOURCE' not in ctx.model_dump_json()
 with pytest.raises(CoreError,match='CONTEXT_TASK_PRIVACY_DENIED'):
  ContextAssembler(r.store,r.authority).assemble(req.model_copy(update={'task_privacy_class':'SECRET'}),pol)
