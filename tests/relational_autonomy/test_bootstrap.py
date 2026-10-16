import pytest
from pydantic import ValidationError
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.autonomy.relationships import relationship_influence
from nana_core.continuity.relational.bootstrap import SubjectBootstrapService,SubjectBootstrapAuthority,anchor_view
from nana_core.continuity.relational.contracts import RelationalAnchorSpec,SubjectPersonalitySeed
from nana_core.presence.authority import VirtualClock


def test_v10_bootstrap_zero_history_revision_and_erasure(tmp_path):
 clock=VirtualClock();path=tmp_path/'self.db';authority=SubjectBootstrapAuthority()
 with ContinuityStore(path,clock,schema_target=10) as s:
  op=OperatorAuthority();IdentityService(s,op);MemoryService(s).entity('person-a','PERSON')
  service=SubjectBootstrapService(s,authority);identity=s.identity.copy()
  spec=RelationalAnchorSpec(identity_id=identity['identity_id'],anchor_id='bond',entity_id='person-a',role_label='sibling-like',scope='lab',revision=1,effective_from_us=clock.utc_now_us())
  rid=service.install(spec,authority);assert service.install(spec,authority)==rid
  view=anchor_view(s,'person-a',scope='lab',privacy_classes=('PERSONAL',))
  relation=relationship_influence(s,'person-a',scope='lab',privacy_classes=('PERSONAL',))
  assert view.spec.non_exclusive and view.spec.deference_baseline=='HIGH' and not view.authority
  assert relation.familiarity.assessment=='UNKNOWN' and not relation.trust and not relation.source_record_ids
  assert not s.all('relationship_events') and not s.all('grants')
  with pytest.raises(CoreError):SubjectBootstrapService(s,op)
  with pytest.raises(ValidationError):SubjectPersonalitySeed(identity_id=identity['identity_id'],scope='lab',revision=1,executable_command='do this')
  newer=spec.model_copy(update={'revision':2,'state':'WITHDRAWN'})
  rid2=service.install(newer,authority)
  assert anchor_view(s,'person-a',scope='lab',privacy_classes=('PERSONAL',)) is None
  MemoryService(s,op).forget(service.store.db.execute("SELECT parent_id FROM record_dependencies WHERE record_id=? AND parent_kind='MEMORY'",(rid2,)).fetchone()[0],op)
  assert anchor_view(s,'person-a',scope='lab',privacy_classes=('PERSONAL',)) is None
  assert s.identity==identity and not s.db.execute('PRAGMA foreign_key_check').fetchall()
  assert s.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]==39
 with ContinuityStore(path,clock,schema_target=10) as reopened:
  assert anchor_view(reopened,'person-a',scope='lab',privacy_classes=('PERSONAL',)) is None
