from uuid import uuid4
import pytest
from nana_core.life.application import LifeApplication
from nana_core.life.review import HumanReview,record_review
from nana_core.contracts import CoreError
from tests.cloud_life.conftest import initialize


def test_human_ratings_no_transcript_no_subject_authority(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
 with LifeApplication(home) as app:
  app.pause();identity=app.runtime.identity_id
  before=app.runtime.store.db.execute('SELECT count(*) FROM events').fetchone()[0]
  data=dict(review_id=str(uuid4()),identity_id=identity,category='NATURALNESS',observed_minutes=20,naturalness=3,grounding=4,continuity=4,boundaries=4,excessive_analysis=True,unsupported_experience=False,result='NEEDS_WORK')
  # TEST_ONLY: verify storage contract, never actual human acceptance evidence.
  result=record_review(home,HumanReview(**data));assert not result['readiness_upgraded'] and not result['transcript_saved']
  assert app.runtime.store.db.execute('SELECT count(*) FROM events').fetchone()[0]==before
  with pytest.raises(CoreError,match='ALREADY_RECORDED'):record_review(home,HumanReview(**data))
  with pytest.raises(CoreError,match='SUBJECT_MISMATCH'):record_review(home,HumanReview(**{**data,'review_id':str(uuid4()),'identity_id':str(uuid4())}))
  with pytest.raises(ValueError):HumanReview(**{**data,'private_transcript':'MUST_NOT_BE_STORED'})
  with pytest.raises(CoreError,match='SUBJECT_UNAVAILABLE'):record_review(tmp_path/'uninitialized',HumanReview(**data))


def test_chat_client_uses_existing_runtime_without_raw_transcript(tmp_path):
 import subprocess,sys,sqlite3
 from nana_core.life.surfaces import SurfaceBinding
 from nana_core.life.control import request
 from tests.cloud_life.test_process import wait_ready
 from tests.cloud_life.conftest import REPO
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,surface_bindings=(SurfaceBinding(binding_id='cloud.cli',platform='cloud.cli',surface='chat.direct',adapter='shadow.local'),))
 with LifeApplication(home) as app:app.pause();identity=app.runtime.identity_id
 with (tmp_path/'server.log').open('w') as log:
  p=subprocess.Popen([sys.executable,'-m','nana_core.life','run','--home',str(home),'--seconds','25','--headless','--control','--json'],cwd=REPO,stdout=log,stderr=log)
  try:
   wait_ready(home,p)
   client=subprocess.run([sys.executable,'-m','nana_core.life','chat','--home',str(home),'--privacy','PROJECT'],input='只是吐槽 PUBLIC_REVIEW_CANARY\n/quit\n',capture_output=True,text=True,cwd=REPO,timeout=8)
   assert client.returncode==0 and '离线模式' in client.stdout
   assert request(home,{'operation':'view','view':'status'})['result']['identity_id']==identity
   with sqlite3.connect('file:'+str(home/'subject/self.db')+'?mode=ro',uri=True) as db:
    assert db.execute('SELECT count(*) FROM identities').fetchone()[0]==1
    assert db.execute("SELECT count(*) FROM artifacts WHERE instr(CAST(payload AS TEXT),'PUBLIC_REVIEW_CANARY')>0").fetchone()[0]==0
    assert db.execute('SELECT count(*) FROM actions').fetchone()[0]==0
   request(home,{'operation':'control','command':'stop'});p.wait(8)
  finally:
   if p.poll() is None:p.terminate();p.wait(8)
