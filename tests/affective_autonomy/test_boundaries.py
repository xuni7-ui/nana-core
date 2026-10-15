"""Highest-risk invariants, each exercises the actual mutation boundary."""
import ast,json
from pathlib import Path
import pytest
from pydantic import ValidationError
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.subject import SubjectLoop
from nana_core.continuity.autonomy.contracts import DisclosureRequest,PositiveRequest,RelationshipDetails
from nana_core.continuity.autonomy.governance import manager_views,snapshot
from nana_core.continuity.memory import MemoryService
from .life import fresh,equip,propose,rule,cycle,inp,TARGET,familiar,influence


def test_model_cannot_mint_governance_or_commit_judgment(tmp_path):
 with fresh(tmp_path/'self.db') as r:
  realizer,ctrl=equip(r);seed=propose(r)
  r.subject.transition_intention(seed.intention_id,expected_revision=1,state='DROPPED')
  mid=r.store.db.execute("SELECT memory_id FROM memories WHERE predicate_key='concern.open.work'").fetchone()[0]
  event=inp(r,'model-input',source_memory_ids=(mid,),realization_target=TARGET)
  revision=r.subject.revision
  class Forged:
   descriptor='synthetic-forged-proposal'
   def propose(self,envelope):
    body=json.loads(AnalyticalFixturePort().propose(envelope));body['manager_constraint']={'restriction':'DENY'};body['judgment']='ENDORSED'
    return json.dumps(body)
  with pytest.raises(ValidationError):r.subject.cognize(event,model=Forged(),authority=r.authority,policy=ContextPolicy(policy_id='local',allowed_scopes=('lab',),readable_privacy=('PERSONAL',)))
  assert r.subject.revision==revision and snapshot(r.store)[1]==()
  class OperatorRace:
   descriptor='synthetic-operator-race'
   def propose(self,envelope):
    # Trusted application fault injection, not a service supplied to ModelPort.
    ctrl.install(rule(r),r.authority)
    return AnalyticalFixturePort().propose(envelope)
  accepted=r.subject.cognize(event,model=OperatorRace(),authority=r.authority,policy=ContextPolicy(policy_id='local',allowed_scopes=('lab',),readable_privacy=('PERSONAL',)))
  assert accepted.evaluation.normative=='ENDORSED'
  gate,aid=realizer.propose(accepted.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
  assert gate.result=='BLOCK' and aid is None
  view=manager_views(r.store,scope='lab',privacy_classes=('PERSONAL',))[0]
  assert view['constraints'][0]['revision']==1 and view['constraints'][0]['expires_at_us']>view['at_us']
  assert 'synthetic://ordinary/work' not in json.dumps(view)
  with pytest.raises(CoreError,match='UNAUTHENTICATED'):ctrl.revoke('negative-a',expected_revision=1,authority=OperatorAuthority())


def test_toctou_at_action_transaction_and_tampered_pass(tmp_path,monkeypatch):
 with fresh(tmp_path/'self.db') as r:
  realizer,ctrl=equip(r);c=propose(r)
  passed=realizer.gate.gate(c.intention_id,expected_revision=1)
  with pytest.raises(CoreError,match='TAMPERED'):realizer.gate.require_current(passed.model_copy(update={'valid_until_us':passed.valid_until_us+10000000}))
  original=realizer.kernel._valid_args
  def between(*args):
   ctrl.install(rule(r),r.authority)
   return original(*args)
  monkeypatch.setattr(realizer.kernel,'_valid_args',between)
  out,aid=realizer.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
  assert out.result=='BLOCK' and aid is None and not r.store.all('actions')
  assert not r.store.all('attempts')


def test_hard_resource_class_cannot_be_relabelled_or_erase_desire(tmp_path):
 with fresh(tmp_path/'self.db') as r:
  realizer,ctrl=equip(r)
  c=propose(r,resource_class='PASSWORD')
  assert c.evaluation.wanted and c.evaluation.normative=='ENDORSED'
  assert c.realization_target.resource_class=='PASSWORD'
  with pytest.raises(CoreError,match='RESOURCE_HARD_DENY'):realizer.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
  assert not r.store.all('actions')


def test_new_private_input_erases_without_revoking_governance(tmp_path):
 with fresh(tmp_path/'self.db') as r:
  realizer,ctrl=equip(r);ctrl.install(rule(r),r.authority)
  familiar(r);before=influence(r)
  canary='SYNTHETIC-PRIVATE-REQUEST-CONTENT'
  request=cycle(r,'private-request',positive_request=PositiveRequest(task_class='REMINDER',description=canary))
  for row in r.store.all('runtime_queue'):assert canary not in row['metadata_json']
  sources=r.store.db.execute('SELECT memory_id FROM subject_events').fetchall()
  mem=MemoryService(r.store,r.authority)
  for row in sources:
   if row['memory_id'] and r.store.one('memories',row['memory_id'])['lifecycle']!='DELETED':mem.forget(row['memory_id'],r.authority)
  after=influence(r)
  assert after.familiarity.assessment=='UNKNOWN' and not after.source_record_ids and before.source_record_ids
  assert snapshot(r.store)[1][0][1].constraint_id=='negative-a'
  for row in r.store.all('artifacts'):
   assert row['payload'] is None or canary.encode() not in row['payload']
  ignored=cycle(r,'no-retention',text=canary,retention='DO_NOT_REMEMBER',positive_request=PositiveRequest(task_class='REMINDER',description=canary))
  assert ignored.intention.kind=='NO_ACTION'
  assert canary not in json.dumps(r.store.snapshot(),default=str)


def test_hidden_counterevidence_never_inflates_projection(tmp_path):
 with fresh(tmp_path/'self.db') as r:
  familiar(r)
  wide=SubjectLoop(r.store,scopes=('lab',),privacy_classes=('PERSONAL','SECRET'))
  wide.run(inp(r,'hidden-breach',privacy_class='SECRET',text='SYNTHETIC-SECRET-BREACH',relationship_kind='CONFLICT',relationship_details=RelationshipDetails(domain='project',trust_breach=True)))
  view=influence(r)
  assert view.familiarity.coverage=='PARTIAL'
  assert next(x for x in view.trust if x.domain=='project').assessment=='UNKNOWN'
  assert 'SYNTHETIC-SECRET-BREACH' not in view.model_dump_json()


def test_no_identity_specific_branch_or_second_subject_coordinator():
 root=Path('src/nana_core')
 loops=[p for p in root.rglob('*.py') for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.ClassDef) and n.name=='SubjectLoop']
 assert len(loops)==1
 for path in (root/'continuity'/'autonomy').glob('*.py'):
  source=path.read_text();tree=ast.parse(source)
  for node in ast.walk(tree):
   if isinstance(node,(ast.If,ast.IfExp,ast.Match)):
    condition=node.subject if isinstance(node,ast.Match) else node.test
    for item in ast.walk(condition):
     if isinstance(item,ast.Constant) and type(item.value) is str:
      assert not any(x in item.value.lower() for x in ('nana','姐姐','奈奈','sister_override','user_is_special'))


def test_cancelled_manager_action_disclosure_preserves_block_and_erasure(tmp_path):
 with fresh(tmp_path/'self.db') as r:
  realizer,ctrl=equip(r);c=propose(r)
  _,aid=realizer.propose(c.intention_id,expected_revision=1,args={'source_id':TARGET.resource})
  ctrl.install(rule(r),r.authority)
  assert realizer.dispatch(c.intention_id,aid,expected_revision=1)=='INTENTION_BLOCKED_MANAGER'
  d=cycle(r,'after-block',disclosure_request=DisclosureRequest(topic='work',action_id=aid))
  assert d.disclosure.phase=='MANAGER_BLOCKED'
  assert d.disclosure.source_record_ids and not d.disclosure.delivery_authority
  mid=r.store.db.execute("SELECT memory_id FROM memories WHERE predicate_key='concern.open.work'").fetchone()[0]
  MemoryService(r.store,r.authority).forget(mid,r.authority)
  with pytest.raises(CoreError,match='RECORD_UNAVAILABLE|DISCLOSURE_SUPPORT_RETIRED'):
   r.subject.run(inp(r,'after-erasure',disclosure_request=DisclosureRequest(topic='work',action_id=aid)))
  assert snapshot(r.store)[1][0][1].constraint_id=='negative-a'
