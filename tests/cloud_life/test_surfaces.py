import json
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.surfaces import SurfaceBinding,SurfaceObservation,recent_sources
from .conftest import initialize

def bindings():return tuple(SurfaceBinding(binding_id=x,platform=x,surface='chat.direct',adapter='shadow.local') for x in ('qq.shadow','bili.shadow','cloud.cli'))
def obs(key,event,text='普通公开项目讨论',**kw):return SurfaceObservation(binding_id=key,event_id=event,text=text,topic='shared',**kw)

def test_cross_surface_restart_preserves_topic_summary_and_deletion(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,surface_bindings=bindings())
 with LifeApplication(home) as app:
  app.pause();identity=app.runtime.identity_id
  one=app.surfaces.receive(obs('qq.shadow','a',approved_summary='The approved project topic is source-backed migration.',summary_authorization='EXPLICIT_PROJECT_SUMMARY'))
  mid=one['summary_memory_ids'][0]
  view=app.surfaces.view('bili.shadow');assert view.subject_id==identity and view.surfaces[0].platform=='qq.shadow'
  assert mid in recent_sources(app,'shared','PROJECT')
  app.surfaces.receive(obs('bili.shadow','b',text='这个话题不要深入了'))
 with LifeApplication(home) as app:
  app.pause();three=app.surfaces.receive(obs('cloud.cli','c',text='继续说点普通话'))
  assert three['mode']=='RESPECT_BOUNDARY' and app.runtime.identity_id==identity
  assert app.surfaces.receive(obs('qq.shadow','a'))['state']=='ALREADY_REVIEWED_NO_REPLAY'
  assert mid in recent_sources(app,'shared','PROJECT')
  app.forget(mid)
  assert not recent_sources(app,'shared','PROJECT')
  assert not app.runtime.store.all('cognitive_requests') and not app.runtime.store.all('grants')
  assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'普通公开项目讨论')>0").fetchone()
  tiers=[app.surfaces.view('cloud.cli',tier=k) for k in ('L0_LIVE','L1_RECENT','L2_DURABLE')]
  assert all(t.subject_id==identity for t in tiers)

def test_shadow_policy_cannot_create_binding_authority_or_private_ingress(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,surface_bindings=bindings())
 with LifeApplication(home) as app:
  with pytest.raises(CoreError,match='SURFACE_DISABLED_OR_UNBOUND'):app.surfaces.receive(obs('qq.other','a'))
  with pytest.raises(CoreError,match='SUMMARY_NOT_AUTHORIZED'):app.surfaces.receive(obs('qq.shadow','b',approved_summary='not authorized'))
  with pytest.raises(ValueError):SurfaceObservation(binding_id='qq.shadow',event_id='c',text='x',privacy_class='SECRET')
  from nana_core.life.control import dispatch
  with pytest.raises(CoreError,match='OPERATION_DENIED'):dispatch(app,{'operation':'grant','resource':'*'})
  with pytest.raises(CoreError):dispatch(app,{'operation':'control','command':'install-plugin'})
  assert not app.runtime.store.all('grants')

def test_surface_cas_disable_survives_restart_without_subject_mutation(tmp_path):
 from nana_core.life.control import dispatch
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,surface_bindings=bindings())
 with LifeApplication(home) as app:
  before=app.runtime.subject.revision
  r=dispatch(app,{'operation':'surface-enabled','binding_id':'qq.shadow','enabled':False,'expected_revision':1})
  assert r['host_config_revision']==2 and app.runtime.subject.revision==before
  with pytest.raises(CoreError,match='REVISION_CONFLICT'):dispatch(app,{'operation':'surface-enabled','binding_id':'qq.shadow','enabled':True,'expected_revision':1})
  with pytest.raises(CoreError,match='DISABLED'):app.surfaces.receive(obs('qq.shadow','one'))
 with LifeApplication(home) as app:
  with pytest.raises(CoreError,match='DISABLED'):app.surfaces.receive(obs('qq.shadow','two'))
  assert app.config.revision==2

def test_surface_event_metadata_collision_is_rejected(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,surface_bindings=bindings())
 with LifeApplication(home) as app:
  app.pause();app.surfaces.receive(obs('qq.shadow','same',thread_id='one'))
  with pytest.raises(CoreError,match='COLLISION'):app.surfaces.receive(obs('qq.shadow','same',thread_id='two'))
