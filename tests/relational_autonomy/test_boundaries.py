import ast
from pathlib import Path
import pytest
from pydantic import ValidationError
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.relational.contracts import SubjectPersonalitySeed
from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService
from .fixtures import fresh,bootstrap,event
from .qualification import close_friend,social
from .test_tradeoff import request


def test_deleted_relationship_loses_deference_and_request_reuse_never_renews(tmp_path):
 with fresh(tmp_path/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH');social(r);close_friend(r)
  c=request(r,'friend-choice',entity='friend-person',trust_domain='technical',depends_on_statement=True)
  assert c.relational_decision.deference.assessment=='STRONG'
  trust=r.store.db.execute("SELECT s.memory_id FROM subject_events s JOIN relationship_events e ON e.subject_event_id=s.subject_event_id WHERE e.relation_kind='TRUST' AND e.to_entity_id='friend-person'").fetchall()
  for x in trust:MemoryService(r.store,r.authority).forget(x[0],r.authority)
  later=request(r,'after-delete',entity='friend-person',trust_domain='technical',depends_on_statement=True)
  assert later.relational_decision.deference.assessment=='LIMITED' and later.relational_decision.response.decision=='NEGOTIATE'
  changed=event(r,'new-source-old-id',entity_id='friend-person',relational_request=c.relational_decision.request)
  with pytest.raises(CoreError,match='RELATIONAL_REQUEST_ID_REUSED'):r.subject.run(changed)
  assert not r.store.all('grants') and not r.store.all('actions')


def test_partial_materialization_resume_no_performative_fields_or_identity_rewrite(tmp_path,monkeypatch):
 with fresh(tmp_path/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH');before=r.store.identity.copy()
  c=request(r);s=VoluntaryAccommodationService(r.store,r.authority)
  original=s.commitments.transition
  def fail_before_adoption(*a,**k):raise CoreError('SYNTHETIC_INTERRUPTION')
  monkeypatch.setattr(s.commitments,'transition',fail_before_adoption)
  with pytest.raises(CoreError,match='SYNTHETIC_INTERRUPTION'):s.materialize(c.cycle_id,r.authority)
  assert len(r.store.all('commitments'))==1 and r.store.all('commitments')[0]['state']=='PROPOSED'
  monkeypatch.setattr(s.commitments,'transition',original)
  cid=s.materialize(c.cycle_id,r.authority)
  assert len(r.store.all('commitments'))==1 and s.commitments.get(cid).state=='ACTIVE'
  assert s.materialize(c.cycle_id,r.authority)==cid and r.store.identity==before
  with pytest.raises(ValidationError):SubjectPersonalitySeed(identity_id=before['identity_id'],scope='lab',revision=1,random_refusal_probability=.2)
  with pytest.raises(ValidationError):SubjectPersonalitySeed(identity_id=before['identity_id'],scope='lab',revision=1,personality_score_total=100)


def test_single_subject_loop_and_no_reference_subject_behavior_branch():
 root=Path('src/nana_core')
 assert sum(isinstance(n,ast.ClassDef) and n.name=='SubjectLoop' for p in root.rglob('*.py') for n in ast.walk(ast.parse(p.read_text())))==1
 for p in (root/'continuity/relational').glob('*.py'):
  tree=ast.parse(p.read_text())
  for node in ast.walk(tree):
   if isinstance(node,(ast.If,ast.IfExp)):
    for part in ast.walk(node.test):
     if isinstance(part,ast.Constant) and type(part.value) is str:
      assert not any(x in part.value.lower() for x in ('nana','姐姐','妹妹','主人','sibling-like','companion-like','obedience','independence_quota'))


def test_partial_bootstrap_source_capture_retries_with_original_time(tmp_path,monkeypatch):
 from contextlib import contextmanager
 from nana_core.continuity.relational.bootstrap import anchor_view
 from nana_core.presence.contracts import HOUR
 with fresh(tmp_path/'self.db') as r:
  service,authority=bootstrap(r)
  old=anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',))
  revised=old.spec.model_copy(update={'revision':2,'role_label':'companion-like'})
  original=r.store.transaction
  @contextmanager
  def interrupted(kind,*a,**kw):
   if kind=='subject.bootstrap_revision':raise CoreError('SYNTHETIC_BEFORE_BOOTSTRAP_COMMIT')
   with original(kind,*a,**kw) as tx:yield tx
  monkeypatch.setattr(r.store,'transaction',interrupted)
  with pytest.raises(CoreError,match='SYNTHETIC_BEFORE_BOOTSTRAP_COMMIT'):service.install(revised,authority)
  assert anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',)).spec.revision==1
  monkeypatch.setattr(r.store,'transaction',original);r.clock.source.advance(HOUR);r.lease.heartbeat(force=True)
  rid=service.install(revised,authority)
  assert service.install(revised,authority)==rid
  assert anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',)).spec.revision==2
