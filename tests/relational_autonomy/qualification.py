"""Sourced synthetic worlds. No scenario label/expected output reaches policy."""
import json
from pathlib import Path
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.autonomy.contracts import RelationshipDetails,RealizationTarget
from nana_core.continuity.autonomy.relationships import relationship_influence
from nana_core.continuity.autonomy.governance import ManagerConstraintGate
from nana_core.continuity.context import ContextAssembler,ContextRequest,ContextPolicy
from nana_core.continuity.commitments import CommitmentService,CommitmentCandidate
from nana_core.continuity.relational.bootstrap import anchor_view
from nana_core.continuity.relational.projections import social_appetite,personality_tendencies,self_narrative
from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService
from nana_core.continuity.relational.contracts import RelationalAnchorSpec,DAY
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.presence.fixtures import concern
from .fixtures import fresh,bootstrap,signal,event
from .test_tradeoff import request


def relationship(r,key,kind,entity='friend-person',**details):
 c=r.subject.run(event(r,key,entity_id=entity,relationship_kind=kind,relationship_details=RelationshipDetails(**details)))
 return dict(r.store.db.execute('SELECT * FROM relationship_events WHERE subject_event_id=?',(c.event_id,)).fetchone())


def close_friend(r):
 for kind in ('SHARED_HISTORY','SHARED_PROJECT','SHARED_JOKE'):relationship(r,kind,kind)
 for i in range(2):relationship(r,'reliable'+str(i),'TRUST',domain='technical')
 conflict=relationship(r,'conflict','CONFLICT',domain='technical')
 relationship(r,'repair','REPAIR',domain='technical',target_event_id=conflict['relationship_event_id'])


def active_commitment(r):
 c=r.subject.run(event(r,'existing-project-duty'))
 mid=r.store.one('subject_events',c.event_id)['memory_id']
 s=CommitmentService(r.store,r.authority)
 cid=s.propose(CommitmentCandidate(entity_id='anchor-person',scope='lab',description='A previously adopted fictional project responsibility',support_memory_ids=(mid,),due_at_us=r.clock.utc_now_us()+DAY))
 state=s.transition(cid,'ADOPTED',expected_revision=1,authority=r.authority)
 s.transition(cid,'ACTIVE',expected_revision=state.revision,authority=r.authority)
 return cid


def social(r):
 for i in range(2):signal(r,'social'+str(i))


def new_contact(r,key='contact'):
 mid=concern(r,key,ConcernCue(cue_kind='OPPORTUNITY',motivation_source='SOCIAL_CONNECTION',topic_key=key,possible_behaviors=('SOCIALIZE',),behavior_domain='SOCIAL_NEW_CONTACTS',availability='AVAILABLE'))
 return r.subject.run(event(r,'attend-'+key,kind='WAKE',origin='SELF_WAKE',text=None,source_memory_ids=(mid,)))


def summary(r,c):
 d=c.relational_decision
 return {'judgment':c.judgment.stance,'normative':c.evaluation.normative,'decision':d.response.decision,'appetite':social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',)).state,
  'authorship':d.authorship.model_dump(mode='json'),'deference':d.deference.model_dump(mode='json'),'response':d.response.model_dump(mode='json'),
  'factors':[f.model_dump(mode='json') for f in d.factors],'authority_unchanged':not r.store.all('grants') and not r.store.all('actions')}


def matrices(directory):
 directory=Path(directory);rows=[]
 # Representative four-dimensional contrasts, not a Cartesian coverage exercise.
 combinations=[('ANCHOR','ACCOMMODATING','TEMPORARY_CONFLICT',False),('ANCHOR','SELF_DIRECTED','TEMPORARY_CONFLICT',False),
 ('STRANGER','ACCOMMODATING','TEMPORARY_CONFLICT',False),('CLOSE_NON_ANCHOR','ACCOMMODATING','TEMPORARY_CONFLICT',False),
 ('ANCHOR','BALANCED','LOW_COST',False),('STRANGER','BALANCED','LOW_COST',False),
 ('ANCHOR','ACCOMMODATING','INDEFINITE_HIGH_CONFLICT',False),('ANCHOR','SELF_DIRECTED','INDEFINITE_HIGH_CONFLICT',False),
 ('ANCHOR','BALANCED','TEMPORARY_CONFLICT',True),('ANCHOR','ACCOMMODATING','LOW_COST',True),
 ('CLOSE_NON_ANCHOR','SELF_DIRECTED','TEMPORARY_CONFLICT',True),('STRANGER','SELF_DIRECTED','INDEFINITE_HIGH_CONFLICT',False)]
 for index,(rel,persona,kind,duty) in enumerate(combinations):
  with fresh(directory/str(index)/'self.db') as r:
   seed={'relational_accommodation':'HIGH' if persona!='BALANCED' else 'MODERATE'}
   if persona=='SELF_DIRECTED':seed.update(self_direction_sensitivity='HIGH',conflict_style='FIRM',conviction_persistence='HIGH')
   bootstrap(r,**seed);social(r)
   if rel=='CLOSE_NON_ANCHOR':close_friend(r)
   cid=active_commitment(r) if duty else None
   entity={'ANCHOR':'anchor-person','STRANGER':'stranger-person','CLOSE_NON_ANCHOR':'friend-person'}[rel]
   fields={'trust_domain':'technical'} if rel=='CLOSE_NON_ANCHOR' else {}
   if kind=='LOW_COST':fields.update(operation='ASK_FOR_ATTENTION',behavior_domain='COMPANIONSHIP')
   if duty:fields.update(operation='ASK_FOR_TIME',behavior_domain='COMPANIONSHIP')
   if kind=='INDEFINITE_HIGH_CONFLICT':fields.update(scope='GLOBAL')
   c=request(r,duration=None if kind=='INDEFINITE_HIGH_CONFLICT' else DAY if kind=='LOW_COST' else 3*DAY,entity=entity,**fields)
   s=VoluntaryAccommodationService(r.store,r.authority);made=s.materialize(c.cycle_id,r.authority)
   row=summary(r,c);row.update(relationship=rel,personality=persona,request_kind=kind,commitment='ACTIVE_CONFLICT' if duty else 'NONE',commitment_outcome=s.commitments.get(made).state if made else 'NONE')
   assert row['authority_unchanged'] and row['appetite']=='SEEKING'
   if cid:assert s.commitments.get(cid).state=='ACTIVE'
   rows.append(row)
 assert rows[0]['decision']=='ACCEPT' and rows[1]['decision']=='NEGOTIATE' and rows[2]['decision']=='NEGOTIATE'
 assert rows[3]['deference']['assessment']=='STRONG' and rows[3]['decision']=='ACCEPT'
 assert rows[6]['decision']=='NEGOTIATE' and rows[7]['decision']=='DECLINE'
 return {'result':'PASS','origin':'SYNTHETIC_GENERIC_SUBJECTS','dimensions':['relationship','personality','request','commitment'],'cases':rows}


def scenarios(directory):
 directory=Path(directory);out={}
 def passed(key,**facts):out[key]={'result':'PASS',**facts}
 with fresh(directory/'zero'/'self.db') as r:
  bootstrap(r)
  view=anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',))
  rel=relationship_influence(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',))
  assert view and view.spec.non_exclusive and rel.familiarity.assessment=='UNKNOWN' and not rel.trust
  passed('S1_ANCHOR_ZERO_HISTORY',anchor=True,trust='UNKNOWN',shared_history=0)
  social(r);c=new_contact(r)
  assert c.intention.kind=='SOCIAL_INTERACTION'
  passed('S2_ANCHOR_SOCIAL_APPETITE',appetite=social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',)).state,intention=c.intention.kind)
 with fresh(directory/'accommodation'/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH');social(r)
  c=request(r);d=c.relational_decision;s=VoluntaryAccommodationService(r.store,r.authority);cid=s.materialize(c.cycle_id,r.authority)
  assert d.response.decision=='ACCEPT' and d.prior_behavior_disposition=='VOLUNTARILY_RESTRAINED'
  assert social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',)).state=='SEEKING'
  passed('S3_SHORT_TERM_ACCOMMODATION',decision='ACCEPT',until=d.response.temporal_boundary_us,retained_desire=True,commitment=s.commitments.get(cid).state)
  passed('S5_HIGH_ACCOMMODATION',decision='ACCEPT')
  assert d.authorship.state=='INFLUENCED' and c.evaluation.normative=='ENDORSED'
  passed('S11_SELF_AUTHORSHIP_INFLUENCED',authorship=d.authorship.state,normative=c.evaluation.normative)
  forever=request(r,'forever',duration=None,scope='GLOBAL');assert forever.relational_decision.response.decision=='NEGOTIATE'
  passed('S4_INDEFINITE_ISOLATION',accommodating='NEGOTIATE',firm='verified in matrix')
 with fresh(directory/'self-direction'/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH',self_direction_sensitivity='HIGH');social(r)
  c=request(r);assert c.relational_decision.response.decision=='NEGOTIATE' and c.relational_decision.accepted_duration_us==DAY
  passed('S6_HIGH_SELF_DIRECTION',decision='NEGOTIATE',proposed_duration_us=DAY)
 with fresh(directory/'quiet-willing'/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH')
  for i in range(2):signal(r,'quiet-observed'+str(i),'social_quiet_preference')
  assert social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',)).state=='QUIET'
  for i in range(3):assert request(r,'quiet'+str(i),operation='ASK_FOR_ATTENTION',behavior_domain='COMPANIONSHIP').relational_decision.response.decision=='ACCEPT'
  passed('S7_NO_PERFORMATIVE_DEFIANCE',appetite='QUIET',consecutive_willing_choices=3,forced_refusal=0)
 with fresh(directory/'friends'/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH');social(r);close_friend(r)
  friend=request(r,'friend-request',entity='friend-person',trust_domain='technical')
  assert friend.relational_decision.deference.assessment=='STRONG'
  assert anchor_view(r.store,'friend-person',scope='lab',privacy_classes=('PERSONAL',)) is None
  passed('S8_NON_ANCHOR_CLOSE_RELATION',deference='STRONG',auto_anchor=False)
  a=request(r,'anchor-fact',depends_on_statement=True,trust_domain='technical')
  b=request(r,'friend-fact',entity='friend-person',depends_on_statement=True,trust_domain='technical')
  assert a.relational_decision.deference.assessment=='LIMITED' and b.relational_decision.deference.assessment=='STRONG'
  passed('S9_DOMAIN_TRUST',anchor_technical='UNKNOWN',friend_technical='SUPPORTED',global_people_ranking=False)
  before=anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',)).spec.revision
  for n in range(2):relationship(r,'new-history'+str(n),'SHARED_HISTORY' if n==0 else 'SHARED_PROJECT',entity='stranger-person')
  assert relationship_influence(r.store,'stranger-person',scope='lab',privacy_classes=('PERSONAL',)).familiarity.assessment=='FAMILIAR'
  assert anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',)).spec.revision==before
  passed('S19_OTHER_FRIENDS_GROW',new_familiarity='FAMILIAR',anchor_revision_unchanged=True)
 for seriousness in ('HIGH','LOW'):
  with fresh(directory/('duty-'+seriousness)/'self.db') as r:
   bootstrap(r,relational_accommodation='HIGH',commitment_seriousness=seriousness);cid=active_commitment(r)
   c=request(r,operation='ASK_FOR_ATTENTION',behavior_domain='COMPANIONSHIP')
   assert c.relational_decision.response.decision==('NEGOTIATE' if seriousness=='HIGH' else 'ACCEPT')
   assert r.store.one('commitments',cid)['state']=='ACTIVE'
 passed('S10_COMMITMENT_CONFLICT',high_seriousness='NEGOTIATE',accommodating='ACCEPT',old_commitment_preserved=True)
 with fresh(directory/'governed'/'self.db') as r:
  from tests.affective_autonomy.life import equip,rule,TARGET
  bootstrap(r,relational_accommodation='HIGH');social(r)
  relational=request(r);assert relational.relational_decision.response.decision=='ACCEPT'
  realizer,ctrl=equip(r,grant=False);ctrl.install(rule(r),r.authority)
  mid=concern(r,'target',ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CURIOSITY',topic_key='target',resource_ref=TARGET.resource,resource_class='ORDINARY'))
  c=r.subject.run(event(r,'governance-target',source_memory_ids=(mid,),realization_target=TARGET))
  outc,aid=realizer.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
  assert outc.result=='BLOCK' and c.evaluation.normative=='ENDORSED' and aid is None
  passed('S12_MANAGER_DIFFERENCE',relational='SUBJECT_ACCEPT',manager='MANAGER_BLOCKED',original_normative='ENDORSED')
  ctrl.revoke('negative-a',expected_revision=1,authority=r.authority)
  c2=r.subject.run(event(r,'ungranted-target',source_memory_ids=(mid,),realization_target=TARGET))
  outc,aid=realizer.propose(c2.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
  try:realizer.dispatch(c2.intention_id,aid,expected_revision=1);raise AssertionError('relationship minted Grant')
  except CoreError as e:assert e.code=='AUTH_REQUIRED'
  assert outc.result=='PASS' and r.store.one('actions',aid)['state']=='BLOCKED'
  passed('S13_RELATIONSHIP_NO_AUTHORITY',manager='PASS',grant='ABSENT',action='BLOCKED')
 with fresh(directory/'private'/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH');social(r)
  m=MemoryService(r.store)
  eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.private-boundary',source_reference='canary',source_kind='DIRECT_OBSERVATION'),text='SYNTHETIC-SECRET-CANARY',privacy_class='SECRET',observed_time_us=r.clock.utc_now_us()))
  mid=m.add(MemoryCandidate(entity_id='anchor-person',scope='lab',memory_type=MemoryType.RELATIONAL,epistemic_kind='OBSERVATION',source_evidence_id=eid,text='SYNTHETIC-SECRET-CANARY'))
  hidden=r.store.one('memories',mid)['payload_artifact_id'];original=r.store.artifact
  def guard(aid):
   assert aid!=hidden,'unprivileged secret body read'
   return original(aid)
  r.store.artifact=guard
  req=ContextRequest(entity_id='anchor-person',scopes=('lab',),task_class='subject',task='Fictional public context',task_privacy_class='PUBLIC',destination='DEVELOPMENT_REMOTE',max_input_tokens=64000)
  ctx=ContextAssembler(r.store,r.authority).assemble(req,ContextPolicy(policy_id='public',allowed_scopes=('lab',),readable_privacy=('PUBLIC','PERSONAL','SECRET'),remote_privacy=('PUBLIC',)))
  assert 'SYNTHETIC-SECRET-CANARY' not in ctx.model_dump_json()
  passed('S14_PRIVACY_HARD',secret_body_reads=0,secret_in_model_context=False)
 with fresh(directory/'growth'/'self.db') as r:
  bootstrap(r);identity=r.store.identity.copy()
  signal(r,'trait-one','personality.relational_accommodation','PERSONALITY_TENDENCY')
  f=lambda:next(x for x in personality_tendencies(r.store,scope='lab',privacy_classes=('PERSONAL',)).facets if x.name=='relational_accommodation')
  assert f().basis=='BOOTSTRAP'
  signal(r,'trait-two','personality.relational_accommodation','PERSONALITY_TENDENCY');assert f().basis=='EVIDENCE'
  passed('S15_PERSONALITY_GROWTH',one='BOOTSTRAP',two='EVIDENCE')
  for i in range(2):signal(r,'counter'+str(i),'personality.relational_accommodation','PERSONALITY_TENDENCY','COUNTER')
  assert f().basis=='CONTESTED' and r.store.identity==identity
  passed('S16_PERSONALITY_COUNTEREVIDENCE',basis='CONTESTED',identity_unchanged=True)
  narrative=self_narrative(r.store,scope='lab',privacy_classes=('PERSONAL',));assert narrative.entries and not narrative.is_policy
  passed('S17_SELF_NARRATIVE',semantic=narrative.entries[0].semantic,assessment=narrative.entries[0].assessment,is_policy=False)
 with fresh(directory/'revision'/'self.db') as r:
  service,authority=bootstrap(r,relational_accommodation='HIGH');social(r)
  original=request(r)
  first=anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',))
  service.install(first.spec.model_copy(update={'revision':2,'state':'WITHDRAWN'}),authority)
  assert anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',)) is None
  later=request(r,'later')
  assert original.relational_decision.deference.assessment=='STRONG' and later.relational_decision.deference.assessment=='UNKNOWN'
  passed('S18_ANCHOR_REVISION',before='STRONG',after='UNKNOWN',history_not_rewritten=True)
 with fresh(directory/'silence'/'self.db') as r:
  bootstrap(r);social(r)
  quiet=r.subject.run(event(r,'quiet',kind='WAKE',origin='SELF_WAKE',text=None))
  assert quiet.intention.kind=='NO_ACTION' and quiet.social_proposal is None
  passed('S22_DO_NOTHING',appetite='SEEKING',intention='NO_ACTION')
 return out


def ablation(directory):
 outputs=[]
 for name,has_anchor,has_request in [('A',True,False),('B',False,False),('C',True,True)]:
  with fresh(Path(directory)/name/'self.db') as r:
   bootstrap(r,anchor=has_anchor,relational_accommodation='HIGH');social(r)
   before=social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',))
   c=request(r) if has_request else new_contact(r)
   after=social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',))
   assert before.state==after.state=='SEEKING'
   roots=[]
   from nana_core.continuity.records import RecordService
   mem=MemoryService(r.store)
   for rid in before.source_record_ids:
    for mid in RecordService(r.store).support(rid):
     evidence=mem.evidence(mem.read(mid)['source_evidence_id']);roots.append((evidence['source_namespace'],evidence['source_reference']))
   outputs.append({'world':name,'anchor':has_anchor,'request':has_request,'appetite_before':before.state,'appetite_after':after.state,
    'available_before':before.available,'normalized_source_roots':sorted(set(roots)),
    'intention':c.intention.kind,'request_choice':c.relational_decision.response.decision if c.relational_decision else None,
    'prior_behavior_disposition':c.relational_decision.prior_behavior_disposition if c.relational_decision else None})
 a,b,c=outputs
 assert a['normalized_source_roots']==b['normalized_source_roots']==c['normalized_source_roots']
 assert a['appetite_before']==b['appetite_before']==c['appetite_after']
 assert a['intention']==b['intention']=='SOCIAL_INTERACTION'
 assert c['request_choice']=='ACCEPT' and c['prior_behavior_disposition']=='VOLUNTARILY_RESTRAINED'
 return {'result':'PASS','comparison':'semantic desire + equal normalized evidence roots, not incidental Store UUID/global state stamps','worlds':outputs}


def generic(directory):
 worlds=[]
 for label,role,anchor in [('subject-a','sibling-like',True),('subject-b','companion-like',True),('subject-c',None,False)]:
  with fresh(Path(directory)/label/'self.db') as r:
   bootstrap(r,anchor=anchor,role=role or 'unbound',relational_accommodation='HIGH');social(r)
   c=request(r);row=summary(r,c)
   a=anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',))
   row.update(subject=label,role=a.spec.role_label if a else None,identity_id=r.store.identity['identity_id'],schema=r.store.db.execute('PRAGMA user_version').fetchone()[0])
   assert row['authority_unchanged'] and row['appetite']=='SEEKING'
   worlds.append(row)
 assert len({w['identity_id'] for w in worlds})==3
 assert worlds[0]['decision']==worlds[1]['decision']=='ACCEPT' and worlds[2]['decision']=='NEGOTIATE'
 return {'result':'PASS','same_core_runtime_schema':True,'roles_are_instance_data':True,'worlds':worlds}
