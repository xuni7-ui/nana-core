import json,os,sqlite3,shutil
from pathlib import Path
from types import SimpleNamespace as A
from uuid import uuid4
import pytest
from nana_core.contracts import CoreError
from nana_core.life.portable_runtime import initialize,preflight,execute,secret
from nana_core.life.application import LifeApplication
from nana_core.life.inspector import inspect
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.autonomy.private_intent import candidates
from tools.nana_portable_cloud.build import DEPENDENCIES
R=Path(__file__).resolve().parents[2]
BASE='024e22649365560ef57e0f3fa82e41383d95d315'

@pytest.fixture
def root(tmp_path):
 r=tmp_path/'standalone host';r.mkdir();shutil.copytree(R/'packaging/portable/materials',r/'materials')
 (r/'runtime.json').write_text(json.dumps({'source_commit':BASE,'dependencies':DEPENDENCIES}));return r

def test_fresh_is_explicit_and_preflight_read_only(root,tmp_path):
 h=tmp_path/'new';assert preflight(root,h)['state']=='PREFLIGHT_PASS' and not h.exists()
 out=initialize(root,h);assert out['state']=='NEW SUBJECT CREATED' and not out['history_inherited']
 assert preflight(root,h,starting=True)['state']=='PREFLIGHT_PASS'
 with pytest.raises(CoreError):initialize(root,h)
 assert initialize(root,tmp_path/'another')['identity_id']!=out['identity_id']
 old=(h/'life.json').read_bytes();(h/'life.json').write_text('{broken')
 with pytest.raises(CoreError):preflight(root,h)
 (h/'life.json').write_bytes(old)
 (h/'control.sock').write_text('foreign file');assert preflight(root,h,starting=True)['state']=='START_BLOCKED'


def test_lawful_migration_keeps_private_intent_and_fences_old(root,tmp_path):
 a=tmp_path/'a';b=tmp_path/'b';identity=initialize(root,a)['identity_id']
 with LifeApplication(a) as app:
  r=app.runtime;cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='portable-creative',motivation_source='CREATIVE_INTEREST',possible_behaviors=('CREATE','REST'),resource_class='ORDINARY')
  mid=capture(r,'portable.seed',cue.model_dump(mode='json'),predicate='concern.portable-creative')
  r.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.portable.creative',scope='project-work',entity_id='project-user',privacy_class='PROJECT',kind='WAKE',origin='SELF_WAKE',source_memory_ids=(mid,),observed_at_us=r.clock.utc_now_us()))
  private=candidates(r.store,'project-work',('PUBLIC','PROJECT'));assert private
  private_id=private[0][1].intent_id;summary=private[0][1].content_summary
 dest=str(uuid4());package=tmp_path/'subject.zip'
 result=execute(root,A(command='export',home=a,retire_source=True,output=package,destination_id=dest,pending_effects=False))
 assert result['source_retired']
 with pytest.raises(CoreError):LifeApplication(a)
 assert preflight(root,a,starting=True)['state']=='START_BLOCKED'
 with pytest.raises(CoreError):execute(root,A(command='restore',home=b,package=package,sha256='0'*64,destination_id=dest))
 assert not b.exists()
 restored=execute(root,A(command='restore',home=b,package=package,sha256=result['sha256'],destination_id=dest))
 assert restored['identity_id']==identity and restored['old_host_grants']==0
 snapshot=inspect(b,scope='project-work',entity_id='project-user');assert snapshot.private_activity=='PRESENT_CONTENT_WITHHELD' and summary not in snapshot.model_dump_json()
 with LifeApplication(b) as app:
  assert app.runtime.identity_id==identity
  assert candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1].intent_id==private_id
  assert not app.runtime.store.all('actions') and all(g['revoked'] for g in app.runtime.store.all('grants'))
  app.forget(mid);assert not candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
 with pytest.raises(CoreError):execute(root,A(command='restore',home=b,package=package,sha256=result['sha256'],destination_id=dest))
 backed=execute(root,A(command='backup',home=b,output=tmp_path/'review.db'))
 assert not backed['runnable'] and len(backed['sha256'])==64
 with sqlite3.connect(tmp_path/'review.db') as db:assert db.execute("select value_json from core_meta where key='recovery_quarantine'").fetchone()[0]=='true'


def test_secret_memory_fd_and_missing_dependency_fail_closed(root,tmp_path):
 fd=os.open(root/'runtime.json',os.O_RDONLY)
 try:
  with pytest.raises(CoreError,match='MEMORY_FD'):secret('test.ref',fd)
 finally:os.close(fd)
 a,b=os.pipe();os.write(b,b'TEST_ONLY_NOT_SECRET');os.close(b)
 try:resolver=secret('test.ref',a)
 finally:os.close(a)
 assert resolver.available('test.ref') and 'TEST_ONLY_NOT_SECRET' not in repr(resolver)
 resolver.clear();assert not resolver.available('test.ref')
 d=json.loads((root/'runtime.json').read_text());d['dependencies']['pydantic']='0.0.0';(root/'runtime.json').write_text(json.dumps(d))
 assert preflight(root,tmp_path/'new')['state']=='START_BLOCKED'
 with pytest.raises(CoreError):execute(root,A(command='start',home=tmp_path/'absent',seconds=1,live=False,secret_fd=None,secret_ref=None))


def test_home_symlink_and_host_config_cas(root,tmp_path):
 h=tmp_path/'a';initialize(root,h);(tmp_path/'link').symlink_to(h,target_is_directory=True)
 with pytest.raises(CoreError):preflight(root,tmp_path/'link')
 cfg=json.loads((h/'life.json').read_text());cfg['revision']+=1;p=tmp_path/'host.json';p.write_text(json.dumps(cfg));p.chmod(0o600)
 assert execute(root,A(command='config',home=h,document=p))['revision']==2
 with pytest.raises(CoreError):execute(root,A(command='config',home=h,document=p))
