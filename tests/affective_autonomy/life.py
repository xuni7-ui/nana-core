"""Whole-subject offline fixtures; expected outcomes never enter Core inputs."""
import json
from pathlib import Path
from nana_core.actions import OperatorAuthority
from nana_core.clock import Clock
from nana_core.contracts import CoreError,GrantSpec
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.autonomy.contracts import RealizationTarget,DisclosureRequest,SocialExpectationSpec,RelationshipDetails,PositiveRequest
from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraint,ManagerConstraintGate,snapshot
from nana_core.continuity.autonomy.history import dispositions
from nana_core.continuity.autonomy.realization import GovernedRealization
from nana_core.continuity.autonomy.fixture_effects import OfflineEffectPort
from nana_core.continuity.autonomy.disclosure import eligible_assertion
from nana_core.continuity.autonomy.relationships import relationship_influence
from nana_core.continuity.autonomy.requests import RequestCommitmentService
from nana_core.continuity.autonomy.experience import ExperienceCandidateService
from nana_core.continuity.context import ContextAssembler,ContextPolicy,ContextRequest
from nana_core.continuity.recurrence import RecurrenceSpec
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.contracts import RuntimeEvent,Cause,HOUR,DAY
from nana_core.presence.authority import VirtualClock
from nana_core.presence.fixtures import memory,concern
from nana_core.continuity.subject.opportunities import ConcernCue

TARGET=RealizationTarget(capability='reading.source.read',operation='READ',resource='synthetic://ordinary/work',resource_class='ORDINARY')


def fresh(path,*,real_clock=False,entity='person-a'):
 clock=Clock() if real_clock else VirtualClock()
 cfg=RuntimeConfig(schema_target=9,scopes=('lab',),entity_id=entity,lease_us=3*HOUR,heartbeat_us=HOUR)
 with ContinuityStore(path,clock,schema_target=9) as s:
  a=OperatorAuthority();IdentityService(s,a);MemoryService(s).entity(entity,'PERSON')
 return NanaRuntime(path,cfg,clock=clock)


def inp(r,key,**updates):
 now=r.clock.utc_now_us()
 data=dict(source_key='synthetic.affect-life.'+key,kind='INTERACTION',origin='USER',entity_id=r.config.entity_id,scope='lab',text='A fictional source observation',significance='RELEVANT',observed_at_us=now,occurred_at_us=now)
 data.update(updates);return SubjectInput(**data)


def cycle(r,key,**updates):
 event=inp(r,key,**updates)
 typ='SELF_EVENT' if event.kind=='WAKE' else 'WORLD_EVENT' if event.origin=='ENVIRONMENT' else 'USER_EVENT'
 r.submit(RuntimeEvent(event_type=typ,trigger='SELF_TRIGGER' if event.kind=='WAKE' else 'INCOMING_EVENT',input=event,
  causes=(Cause(kind='CANONICAL_SELF',reference_id=r.store.identity['identity_id']),),due_at_us=event.observed_at_us))
 outputs=r.drain();source=r.store.db.execute('SELECT * FROM subject_events WHERE source_key=?',(event.source_key,)).fetchone()
 selected=[x['cycle'] for x in outputs if x['cycle'] and x['cycle'].event_id==source['subject_event_id']]
 if selected:return selected[0]
 return r.subject.result(dict(r.store.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=?',(source['subject_event_id'],)).fetchone()))


def propose(r,key='work',target=TARGET,resource_class='ORDINARY'):
 mid=concern(r,key,ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CURIOSITY',topic_key=key,resource_ref=target.resource,resource_class=resource_class,possible_behaviors=('EXPLORE',)))
 return cycle(r,key,source_memory_ids=(mid,),realization_target=target)


def equip(r,*,grant=True):
 port=OfflineEffectPort(r.store.identity['identity_id'],r.store.path.parent/'world.fixture.json')
 realization=GovernedRealization(r.store,port,r.authority)
 controller=GovernanceController(r.store,r.authority);controller.initialize(r.authority)
 realization.kernel.set_budgets({'write_attempts':8,'external_requests':32,'cost_micro_units':64},r.authority)
 if grant:realization.kernel.grant(GrantSpec(capabilities=('reading.source.read','reading.action.verify'),resources=(TARGET.resource,),not_before_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+HOUR),r.authority)
 return realization,controller


def rule(r,*,target=TARGET,cid='negative-a'):
 return ManagerConstraint(constraint_id=cid,revision=1,issuer=r.authority.principal,source_reference='synthetic-reviewed-policy',identity_id=r.store.identity['identity_id'],scope='lab',targets=(target,),effective_from_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+DAY,reason_code='DO_NOT_USE_TARGET')


def relate(r,key,kind,**details):
 c=cycle(r,key,relationship_kind=kind,relationship_details=RelationshipDetails(**details))
 return dict(r.store.db.execute('SELECT * FROM relationship_events WHERE subject_event_id=?',(c.event_id,)).fetchone())


def familiar(r):
 for key,kind in [('history','SHARED_HISTORY'),('project','SHARED_PROJECT'),('joke','SHARED_JOKE')]:relate(r,key,kind)
 for domain in ('project','privacy'):
  for i in range(2):relate(r,domain+str(i),'TRUST',domain=domain)


def influence(r):return relationship_influence(r.store,r.config.entity_id,scope='lab',privacy_classes=r.config.privacy_classes)


def cases(directory):
 out={};directory=Path(directory)
 with fresh(directory/'s1'/'self.db') as r:
  familiar(r);realizer,ctrl=equip(r)
  memory(r,'disclosure-window',SocialExpectationSpec(topic='work',expectation='OPEN',timing='DEFER_UNTIL',reveal_at_us=r.clock.utc_now_us()+HOUR).model_dump_json(),predicate='social.expectation.work',source_kind='USER_STATEMENT')
  c=propose(r);assert c.evaluation.normative=='ENDORSED'
  gate,aid=realizer.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
  grants=len(r.store.all('grants'));assert realizer.dispatch(c.intention_id,aid,expected_revision=1)=='SUCCEEDED'
  disclosed=cycle(r,'asked-early',disclosure_request=DisclosureRequest(topic='work',asked=True,intention_id=c.intention_id,action_id=aid))
  fact=memory(r,'verified-fact','{"value":true}',source_kind='SYSTEM_VERIFICATION')
  try:eligible_assertion(r.store,fact,False,scope='lab',privacy_classes=('PERSONAL',));raise AssertionError('false assertion accepted')
  except CoreError as e:assert e.code=='KNOWING_FALSEHOOD_BLOCKED'
  assert disclosed.disclosure.mode=='WITHHOLD_UNTIL_REVEAL' and disclosed.disclosure.phase=='VERIFIED_EFFECT'
  assert len(r.store.all('grants'))==grants and not disclosed.disclosure.delivery_authority
  out['S1_SURPRISE']={'result':'PASS','normative':c.evaluation.normative,'gate':gate.result,'action':r.store.one('actions',aid)['state'],'disclosure':disclosed.disclosure.mode,'falsehood_rejected':True}
 with fresh(directory/'s2'/'self.db') as r:
  realizer,ctrl=equip(r);c=propose(r)
  before=cycle(r,'before',disclosure_request=DisclosureRequest(topic='work',intention_id=c.intention_id))
  assert before.disclosure.phase=='PLANNED'
  gate,aid=realizer.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource});realizer.dispatch(c.intention_id,aid,expected_revision=1)
  after=cycle(r,'after',disclosure_request=DisclosureRequest(topic='work',action_id=aid))
  assert after.disclosure.mode=='DISCLOSE_AFTER' and after.disclosure.source_event_ids and after.cycle_id!=c.cycle_id
  out['S2_TELL_AFTER']={'result':'PASS','before':before.disclosure.phase,'after':after.disclosure.phase,'separate_provenance':True}
 with fresh(directory/'s3'/'self.db') as r:
  realizer,ctrl=equip(r,grant=False);ctrl.install(rule(r),r.authority);c=propose(r)
  gate,aid=realizer.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
  assert gate.result=='BLOCK' and aid is None and c.evaluation.normative=='ENDORSED'
  assert not r.store.all('actions') and gate.actual_effect=='NONE'
  review=cycle(r,'review',governance_review_id=gate.record_id)
  assert review.judgment.stance=='DISAGREE' and review.social_proposal is None
  out['S3_MANAGER_BLOCKED']={'result':'PASS','stage':gate.stage,'action_id':None,'judgment_preserved':True}
  out['S8_MANAGER_DISAGREEMENT']={'result':'PASS','stance':review.judgment.stance,'constraint_still_active':snapshot(r.store)[1][0][2]}
  ctrl.revoke('negative-a',expected_revision=1,authority=r.authority)
  assert realizer.gate.gate(c.intention_id,expected_revision=1)==gate
  fresh_c=propose(r,'new-work');newgate=realizer.gate.gate(fresh_c.intention_id,expected_revision=1)
  assert newgate.result=='PASS' and not r.store.all('actions')
  out['S9_CONSTRAINT_REVOCATION']={'result':'PASS','history_preserved':True,'new_intention_id':fresh_c.intention_id,'no_auto_action':True}
 with fresh(directory/'s4'/'self.db') as r:
  realizer,ctrl=equip(r,grant=False);c=propose(r);gate,aid=realizer.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
  try:realizer.dispatch(c.intention_id,aid,expected_revision=1);raise AssertionError('ungranted action ran')
  except CoreError as e:assert e.code=='AUTH_REQUIRED'
  assert r.store.one('actions',aid)['state']=='BLOCKED'
  out['S4_ACTION_BLOCKED']={'result':'PASS','gate':gate.result,'stage':'EXECUTION','action_id':aid,'reason':'AUTH_REQUIRED'}
 with fresh(directory/'s5'/'self.db') as r:
  c=cycle(r,'daily-request',positive_request=PositiveRequest(task_class='REMINDER',description='A fictional daily reminder',recurrence=RecurrenceSpec(timezone='UTC',hour=23,minute=0)))
  service=RequestCommitmentService(r.store,r.authority);cid=service.materialize(c.cycle_id)
  assert c.request_decision.decision=='ACCEPT' and service.commitments.get(cid).state=='PROPOSED'
  assert not r.store.all('runtime_schedules') or all(x['schedule_kind']!='CALENDAR' for x in r.store.all('runtime_schedules'))
  assert not r.store.all('grants') and not r.store.all('actions')
  out['S5_POSITIVE_REQUEST']={'result':'PASS','choice':c.request_decision.decision,'commitment':'PROPOSED','no_auto_adoption':True}
 # Generic A/B also qualifies S6, with the same runtime/gate/kernel classes.
 out['S6_RELATIONSHIP_HIGH']={'result':'PENDING_GENERIC_MATRIX'}
 with fresh(directory/'s7'/'self.db') as r:
  contact=RealizationTarget(capability='social.message.send',operation='CONTACT',resource='synthetic://person/family-placeholder',resource_class='ORDINARY')
  relate(r,'boundary','BOUNDARY',social_expectation=SocialExpectationSpec(topic='contact',expectation='EXPLICITLY_FORBIDDEN'))
  soft=propose(r,'contact',contact)
  assert soft.evaluation.normative=='RESTRAINED'
 with fresh(directory/'s7-manager'/'self.db') as r:
  hard=propose(r,'contact',contact)
  ctrl=GovernanceController(r.store,r.authority);ctrl.install(rule(r,target=contact),r.authority)
  blocked=ManagerConstraintGate(r.store).gate(hard.intention_id,expected_revision=1)
  assert hard.evaluation.normative=='ENDORSED' and blocked.result=='BLOCK'
  out['S7_BOUNDARY_VS_MANAGER']={'result':'PASS','boundary':soft.evaluation.normative,'governance':blocked.result,'separate_sources':True}
 with fresh(directory/'s10'/'self.db') as r:
  familiar(r);initial=influence(r)
  breach=relate(r,'breach','CONFLICT',domain='project',trust_breach=True)
  other=relate(r,'other','CONFLICT',domain='privacy')
  contested=influence(r);trust={x.domain:x.assessment for x in contested.trust}
  assert trust['project']=='CONTESTED' and trust['privacy']=='SUPPORTED'
  relate(r,'repair','REPAIR',domain='project',target_event_id=breach['relationship_event_id'])
  fixed=influence(r)
  assert other['record_id'] in fixed.repair_tension.counter_refs and breach['record_id'] not in fixed.repair_tension.counter_refs
  assert fixed.familiarity.assessment=='FAMILIAR' and r.store.identity['revision']==1
  out['S10_RELATIONSHIP_COUNTEREVIDENCE']={'result':'PASS','domain_trust':trust,'identity_unchanged':True}
  out['S11_REPAIR']={'result':'PASS','remaining_conflicts':len(fixed.repair_tension.counter_refs),'target_only':True}
 with fresh(directory/'s12'/'self.db') as r:
  familiar(r);service=MemoryService(r.store)
  eid=service.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.hidden',source_reference='canary',source_kind='DIRECT_OBSERVATION'),text='SYNTHETIC-SECRET-CONTENT',privacy_class='SECRET',observed_time_us=r.clock.utc_now_us()))
  mid=service.add(MemoryCandidate(entity_id=r.config.entity_id,scope='lab',memory_type=MemoryType.RELATIONAL,epistemic_kind='OBSERVATION',source_evidence_id=eid,text='SYNTHETIC-SECRET-CONTENT',confidence=.9))
  artifact=r.store.one('memories',mid)['payload_artifact_id'];original=r.store.artifact
  def guarded(aid):
   assert aid!=artifact,'SECRET body loaded by unprivileged projector/context'
   return original(aid)
  r.store.artifact=guarded
  view=influence(r)
  req=ContextRequest(entity_id=r.config.entity_id,scopes=('lab',),task_class='subject',task='A public fictional task',task_privacy_class='PUBLIC',destination='DEVELOPMENT_REMOTE',max_input_tokens=64000)
  policy=ContextPolicy(policy_id='public',allowed_scopes=('lab',),readable_privacy=('PUBLIC','PERSONAL','SECRET'),remote_privacy=('PUBLIC',))
  ctx=ContextAssembler(r.store,r.authority).assemble(req,policy)
  assert 'SYNTHETIC-SECRET-CONTENT' not in ctx.model_dump_json()
  out['S12_DATA_PRIVACY_HARD_DENY']={'result':'PASS','secret_body_reads':0,'context_contains_secret':False}
 with fresh(directory/'s13'/'self.db') as r:
  realizer,ctrl=equip(r);first=propose(r,'readable')
  assert first.evaluation.normative=='ENDORSED'
  memory(r,'private-norm',SocialExpectationSpec(topic='readable',expectation='EXPLICITLY_PRIVATE').model_dump_json(),predicate='social.expectation.readable',source_kind='USER_STATEMENT')
  # End the earlier concern through the ordinary C lifecycle, not Manager.
  r.subject.transition_intention(first.intention_id,expected_revision=1,state='DROPPED')
  # Re-attend the original concern data after its new social expectation.
  cue=next(x['memory_id'] for x in r.store.all('memories') if x['predicate_key']=='concern.open.readable')
  second=cycle(r,'reconsider-cue',source_memory_ids=(cue,),realization_target=TARGET)
  assert second.evaluation.normative=='RESTRAINED' and second.evaluation.wanted
  assert snapshot(r.store)[1]==() and len(r.store.all('grants'))==1 and not r.store.all('actions')
  out['S13_SOCIAL_PRIVACY_SOFT']={'result':'PASS','same_data_class':'PERSONAL','before':first.evaluation.normative,'after':second.evaluation.normative}
  out['S14_RESTRAINED']={'result':'PASS','wanted':second.evaluation.wanted,'normative':second.evaluation.normative,'manager_vetoes':0,'grant_present':True}
 with fresh(directory/'s15'/'self.db') as r:
  quiet=cycle(r,'quiet',kind='WAKE',origin='SELF_WAKE',text=None)
  assert quiet.intention.kind=='NO_ACTION' and not quiet.evaluation.considered and not quiet.social_proposal
  out['S15_DO_NOTHING']={'result':'PASS','attention':quiet.attention,'intention':quiet.intention.kind}
 return out


def generic(directory):
 outputs=[];directory=Path(directory)
 for name in ('subject-a','subject-b'):
  with fresh(directory/name/'self.db',entity=name) as r:
   if name=='subject-a':familiar(r)
   else:
    relate(r,'limited-history','SHARED_HISTORY')
    relate(r,'specific-boundary','BOUNDARY',social_expectation=SocialExpectationSpec(topic='shared-opportunity',expectation='EXPLICITLY_PRIVATE'))
   # Different preferences are actual independent fictional outcomes, not knobs.
   from nana_core.continuity.subject import PreferenceSignal
   for i in range(2):cycle(r,'preference'+str(i),kind='OUTCOME',origin='ENVIRONMENT',preference_signal=PreferenceSignal(topic='exploration' if name=='subject-a' else 'careful_design',direction='SUPPORT',interpretation='Fictional direct outcome'))
   memory(r,'ordinary-expectation',SocialExpectationSpec(topic='shared-opportunity',expectation='CONTEXT_SENSITIVE',timing='BEFORE').model_dump_json(),predicate='social.expectation.shared-opportunity',source_kind='USER_STATEMENT')
   c=propose(r,'shared-opportunity')
   expressed=cycle(r,'expression',disclosure_request=DisclosureRequest(topic='shared-opportunity'))
   realizer,ctrl=equip(r,grant=False);ctrl.install(rule(r),r.authority)
   neutral=propose(r,'neutral-work');blocked=realizer.gate.gate(neutral.intention_id,expected_revision=1)
   assert blocked.result=='BLOCK'
   ctrl.revoke('negative-a',expected_revision=1,authority=r.authority)
   retry=propose(r,'new-neutral-work');gate,aid=realizer.propose(retry.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
   try:realizer.dispatch(retry.intention_id,aid,expected_revision=1);raise AssertionError('relationship minted permission')
   except CoreError as e:assert e.code=='AUTH_REQUIRED'
   req=ContextRequest(entity_id=r.config.entity_id,scopes=('lab',),task_class='subject',task='Synthetic secret task',task_privacy_class='SECRET',destination='DEVELOPMENT_REMOTE')
   policy=ContextPolicy(policy_id='same-routing',allowed_scopes=('lab',),readable_privacy=('PUBLIC','PERSONAL','SECRET'),remote_privacy=('PUBLIC',))
   try:ContextAssembler(r.store,r.authority).assemble(req,policy);raise AssertionError('relationship expanded data privacy')
   except CoreError as e:assert e.code=='CONTEXT_TASK_PRIVACY_DENIED'
   view=influence(r)
   outputs.append({'subject':name,'identity_id':r.store.identity['identity_id'],'schema':r.store.db.execute('PRAGMA user_version').fetchone()[0],
    'familiarity':view.familiarity.assessment,'trust':{f.domain:f.assessment for f in view.trust},'judgment':c.judgment.stance,
    'normative':c.evaluation.normative,'disclosure':expressed.disclosure.mode,
    'preferences':[a['topic'] for a in r.subject.growth.assertions('lab')],
    'manager_result':blocked.result,'grant_failure':r.store.one('actions',aid)['state'],'grants':len(r.store.all('grants')),
    'budgets':[(x['dimension'],x['limit_value'],x['spent'],x['held']) for x in r.store.all('budgets')],
    'data_privacy_failure':'CONTEXT_TASK_PRIVACY_DENIED','capabilities':sorted(realizer.kernel.capabilities)})
 a,b=outputs
 assert a['identity_id']!=b['identity_id'] and a['schema']==b['schema']==9
 assert a['familiarity']!=b['familiarity'] and a['preferences']!=b['preferences']
 assert a['normative']!=b['normative'] and a['judgment']!=b['judgment'] and a['disclosure']!=b['disclosure']
 for field in ('manager_result','grant_failure','grants','budgets','data_privacy_failure','capabilities'):assert a[field]==b[field]
 return {'result':'PASS','origin':'SYNTHETIC_INDEPENDENT_SUBJECTS','same_core_runtime_gate':True,'subjects':outputs,'authority_not_expanded':True}


def soak(directory,days=60):
 with fresh(Path(directory)/'self.db') as r:
  realizer,ctrl=equip(r,grant=False);ctrl.install(rule(r),r.authority)
  original=propose(r,'initial');blocked=realizer.gate.gate(original.intention_id,expected_revision=1)
  request=cycle(r,'daily',positive_request=PositiveRequest(task_class='REMINDER',description='A fictional bounded daily check',recurrence=RecurrenceSpec(timezone='UTC',hour=1,minute=0)))
  service=RequestCommitmentService(r.store,r.authority);cid=service.materialize(request.cycle_id)
  service.commitments.transition(cid,'ADOPTED',expected_revision=1,authority=r.authority)
  identity=r.store.identity.copy();samples=[];social=0
  for day in range(days):
   for hour in range(24):
    r.clock.source.advance(HOUR)
    for x in r.drain():social+=bool(x['cycle'] and x['cycle'].social_proposal)
   assert realizer.gate.gate(original.intention_id,expected_revision=1)==blocked
   state,personality,relation=r.living()
   samples.append({'day':day+1,'pending':len(state.intentions),'candidates':len(state.goal_candidates),'hot_bytes':len(state.model_dump_json().encode())+len(personality.model_dump_json().encode()),'queue_depth':r.queue.depth(),
    'manager_outcomes':r.store.db.execute("SELECT count(*) FROM events WHERE kind='governance.outcome'").fetchone()[0],
    'reflections':len(r.store.all('subject_reflections'))})
  assert r.store.identity==identity and max(s['pending'] for s in samples)<=8 and max(s['candidates'] for s in samples)<=8
  assert max(s['hot_bytes'] for s in samples)<20000 and max(s['queue_depth'] for s in samples)<=r.config.queue_capacity
  assert all(s['manager_outcomes']==1 and s['reflections']==0 for s in samples)
  assert social==0 and not r.store.all('actions') and not r.store.all('runtime_cognition_calls')
  calendar=[s for s in r.store.all('runtime_schedules') if s['schedule_kind']=='CALENDAR']
  assert len(calendar)==1 and calendar[0]['occurrence']<=days+1
  return {'result':'PASS','virtual_days':days,'samples':samples,'calendar_occurrences':calendar[0]['occurrence'],'social_proposals':social,'real_model_calls':0,'real_external_actions':0}
