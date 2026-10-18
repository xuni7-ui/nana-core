"""Offline policy tests do not start displays or read OS pixels."""
import hashlib,io,json
import pytest
from PIL import Image
from pydantic import ValidationError
from nana_core.contracts import CoreError
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.sensors.screen import *
from nana_core.continuity.sensors.contracts import *
from tests.h2_perception.helpers import setup
from tests.world_loop.helpers import fresh

class Backend:
    binding_digest='a'*64
    def __init__(self):self.calls=0;self.size=(32,24);self.compression=0;self.fail=False
    def geometry(self):return self.size
    def capture(self,geometry):
        self.calls+=1
        if self.fail:raise TimeoutError()
        im=Image.new('RGB',self.size,'red');out=io.BytesIO();im.save(out,format='PNG',compress_level=self.compression)
        return out.getvalue(),hashlib.sha256(im.tobytes()).hexdigest()
def port(clock,**kw):
    p=PerceptionSourceProfile(source_profile_id='screen.test',display_name='test',source_kind='SCREEN',modality='IMAGE',adapter_ref='test',resource_ref='test',scope='world',entity_id='observer',**kw)
    b=Backend();return RealScreenPerceptionPort(b,ScreenBackendDescriptor(backend_id='controlled.test'),p,clock,host_enabled=True),b,p

def request(p,clock,key='one'):
    return ObservationRequest(request_id=key,source_profile_id=p.source_profile_id,source_revision=p.revision,requested_modality=p.modality,reason_kind='USER_REQUEST',requested_at_us=clock.utc_now_us(),deadline_us=clock.utc_now_us()+1000000,privacy_class=p.privacy_class,max_capture_bytes=p.max_capture_bytes)

@pytest.mark.parametrize('privacy',['PROJECT','PERSONAL','SECRET'])
def test_real_v1_rejects_nonpublic_before_bytes(privacy):
    with pytest.raises(CoreError,match='SCREEN_SCOPE_DENIED'):port(VirtualClock(),privacy_class=privacy)

def test_default_deny_explicit_backend_scope_and_receipt():
    clock=VirtualClock();p,b,profile=port(clock)
    with pytest.raises(CoreError,match='HOST_DISABLED'):RealScreenPerceptionPort(b,ScreenBackendDescriptor(backend_id='test'),profile,clock)
    with pytest.raises(ValidationError):ScreenBackendDescriptor(backend_id='test',supports_full_desktop=True)
    cap=p.capture(request(profile,clock));cap.verify(profile,clock.utc_now_us())
    assert cap.origin=='REAL_OS_CONTROLLED' and 'data' not in cap.model_dump()
    assert not any(k in cap.model_dump_json() for k in ['window_handle','display_socket','auth_cookie'])
    altered=cap.model_copy(update={'screen_receipt':{**cap.screen_receipt,'source_revision':2}})
    with pytest.raises(CoreError,match='RECEIPT_MISMATCH'):altered.verify(profile,clock.utc_now_us())

def test_session_topology_latch_and_stale_revision_no_bytes():
    clock=VirtualClock();p,b,profile=port(clock);req=request(profile,clock)
    with pytest.raises(CoreError,match='BINDING_STALE'):p.capture(req.model_copy(update={'source_revision':2}))
    b.size=(33,24);assert p.health()=='SCREEN_TOPOLOGY_CHANGED';b.size=(32,24)
    with pytest.raises(CoreError,match='TOPOLOGY_CHANGED'):p.capture(req)
    assert b.calls==0
    p,b,profile=port(clock);b.binding_digest='b'*64
    with pytest.raises(CoreError,match='SESSION_CHANGED'):p.capture(req)
    assert b.calls==0

def test_backend_timeout_unknown_not_retry(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,old,m,a=setup(r,tmp_path);profile=c._source('screen.a');b=Backend();b.fail=True
        real=RealScreenPerceptionPort(b,ScreenBackendDescriptor(backend_id='controlled.test'),profile,r.clock,host_enabled=True)
        resolver=HostPerceptionResolver();resolver.bind('fixture','sample',real);c.resolver=resolver
        req=c.request('screen.a',request_id='unknown');v=c.observe(req)
        assert v['state']=='UNKNOWN' and v['reason']=='SCREEN_CAPTURE_UNKNOWN'
        assert c.observe(req)==v and b.calls==1 and m.calls==0

def test_same_pixels_different_encoding_debounce_and_route_freshness(tmp_path):
    with fresh(tmp_path/'subject/self.db') as r:
        c,old,m,a=setup(r,tmp_path);profile=c._source('screen.a');b=Backend()
        real=RealScreenPerceptionPort(b,ScreenBackendDescriptor(backend_id='controlled.test'),profile,r.clock,host_enabled=True)
        resolver=HostPerceptionResolver();resolver.bind('fixture','sample',real);c.resolver=resolver
        first=c.observe(c.request('screen.a',request_id='one'));assert first['state']=='GROUNDED';r.clock.source.advance(SECOND)
        b.compression=9;second=c.observe(c.request('screen.a',request_id='two'))
        x,y=[json.loads(c.records.memory.read(v['memory_id'])['text']) for v in (first,second)]
        assert x['source_byte_digest']!=y['source_byte_digest'] and x['decoded']['pixel_digest']==y['decoded']['pixel_digest']
        assert second['reason']=='EXACT_DIGEST_DEBOUNCE' and m.calls==1
        r.clock.source.advance(SECOND);c.state['sources']['screen.a']['semantic_route_revision']=-1
        third=c.observe(c.request('screen.a',request_id='three'));assert third['state']=='GROUNDED' and m.calls==2

from nana_core.presence.contracts import SECOND
