import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.surfaces import SurfaceBinding
from tools.nana_cloud_surfaces.shadow import qq,bilibili
from .conftest import initialize


def test_legacy_bili_normalization_and_qq_fixture_share_one_subject(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0,surface_bindings=tuple(SurfaceBinding(binding_id=k,platform=k,surface='chat.direct',adapter='shadow.local') for k in ('qq.shadow','bili.shadow')))
 q={'synthetic':True,'event_id':'one','conversation_id':'project','sender_id':'fixture-user','text':'只是吐槽，接口名很长'}
 b={'synthetic':True,'channel':'reply','item':{'item':{'business_id':1,'source_id':500,'uri':'https://www.bilibili.com/video/BV1Synthetic','source_content':'和你分享公开项目进展'}}}
 with LifeApplication(home) as app:
  app.pause();identity=app.runtime.identity_id
  one=app.surfaces.receive(qq(q,topic='shared'))
  two=app.surfaces.receive(bilibili(b,topic='shared'))
  view=app.surfaces.view('bili.shadow')
  assert view.subject_id==identity and {s.platform for s in view.surfaces}>={'qq.shadow','bili.shadow'}
  assert len(app.runtime.store.all('subject_cycles'))==2
  assert app.surfaces.receive(bilibili(b,topic='shared'))['state']=='ALREADY_REVIEWED_NO_REPLAY'
  assert not one['delivered'] and not two['delivered']
  assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
 with pytest.raises(CoreError,match='EXPLICIT_SYNTHETIC'):qq({**q,'synthetic':False})
 with pytest.raises(CoreError,match='EXPLICIT_SYNTHETIC'):bilibili({**b,'synthetic':False})
 b['item']['item'].pop('source_id')
 with pytest.raises(CoreError,match='SOURCE_ID_REQUIRED'):bilibili(b)
