"""Real owned HTTP C.4 pages -> original Core/Kernel, never legacy Agent."""
import asyncio
import json
import threading
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from nana_core.contracts import CoreError,GrantSpec
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.bilibili_runtime import BilibiliChannelBinding
from nana_core.nanalink.adapters import BilibiliEventsAdapter
from nana_core.nanalink.contracts import Outcome
from nana_core.presence.authority import VirtualClock
from tests.person_self.conftest import initialize
from tests.independent_life.test_dialogue import relay
from tests.living_release_v4.test_bilibili_runtime import equipped
from tests.living_release_v4.bilibili_loopback import counterpart


@contextmanager
def notification_front(endpoint):
    state={'requests':[],'fail':False}
    item={'id':1,'reply_time':1,'user':{'mid':43,'nickname':'not an identity'},'item':{'business_id':1,'source_id':9,
        'subject_id':7,'root_id':0,'uri':'https://www.bilibili.com/video/BV1t55v6DE2v','source_content':'public comment'}}
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):self.respond()
        def do_POST(self):self.respond()
        def respond(self):
            state['requests'].append(self.path)
            if self.path.startswith('/x/msgfeed/'):
                if state['fail']:self.send_error(503);return
                raw=json.dumps({'code':0,'data':{'items':[item] if '/reply' in self.path else []}}).encode()
            else:
                data=self.rfile.read(int(self.headers['Content-Length'])) if self.command=='POST' else None
                req=urllib.request.Request(endpoint+self.path,data=data,headers=dict(self.headers.items()),method=self.command)
                with opener.open(req,timeout=3) as response:raw=response.read()
            self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield 'http://127.0.0.1:'+str(server.server_port),state
    finally:server.shutdown();thread.join(2);server.server_close()


def configured(home):
    initialize(home);cfg=load_config(home)
    binding=SurfaceBinding(binding_id='bili.notifications',platform='bilibili.account',surface='chat.comment',adapter='bilibili.account',
                           mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PUBLIC',))
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(binding,)}),expected_revision=cfg.revision)
    return BilibiliChannelBinding(channel_id='notifications',binding_id=binding.binding_id,kind='comment',account_id=42,target_id=7,
           sender_id=43,cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,send_authorized=True,
           private_read_authorized=True)


def test_c4_real_http_pages_then_original_c_reply_and_restart_no_repeat(tmp_path):
    home=tmp_path/'home';channel=configured(home);clock=VirtualClock()
    with counterpart() as (opener,platform),notification_front(opener.endpoint) as (endpoint,state),relay(home,'CHAT') as (router,calls):
        platform['comments']=[{'rpid':9,'root':0,'member':{'mid':43},'content':{'message':'public comment'}}]
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();flow=equipped(app,channel,endpoint,grant=False)
            flow.realization.kernel.grant(GrantSpec(capabilities=('bilibili.comment.send','bilibili.action.verify'),resources=(flow.resource,),
                  not_before_us=clock.utc_now_us(),expires_at_us=clock.utc_now_us()+100000000),app.runtime.authority)
            adapter=BilibiliEventsAdapter(flow);asyncio.run(adapter.connect())
            event=asyncio.run(adapter.receive())
            assert event.kind=='notification.reply' and event.message_id=='9' and event.privacy=='PERSONAL'
            assert not app.runtime.store.all('cognitive_requests') and platform['posts']==0
            assert adapter.receive_event(event).outcome==Outcome.CONFIRMED_SUCCESS
            count=len(state['requests'])
            assert asyncio.run(adapter.receive()) is None and len(state['requests'])==count
            assert len(calls)==2 and platform['posts']==1
            identity=app.runtime.identity_id
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();adapter=BilibiliEventsAdapter(equipped(app,channel,endpoint,grant=False));asyncio.run(adapter.connect())
            assert asyncio.run(adapter.receive()) is None
            assert app.runtime.identity_id==identity and len(state['requests'])==count and len(calls)==2 and platform['posts']==1


def test_c4_read_failure_keeps_original_admission_and_requires_private_scope(tmp_path):
    home=tmp_path/'home';channel=configured(home);clock=VirtualClock()
    with counterpart() as (opener,_),notification_front(opener.endpoint) as (endpoint,state):
        with LifeApplication(home,clock=clock) as app:
            app.pause();flow=equipped(app,channel,endpoint,grant=False)
            denied=BilibiliEventsAdapter(equipped(app,channel.model_copy(update={'private_read_authorized':False}),endpoint,grant=False))
            with pytest.raises(CoreError):asyncio.run(denied.connect())
            assert not state['requests']
            adapter=BilibiliEventsAdapter(flow);asyncio.run(adapter.connect());state['fail']=True
            with pytest.raises(CoreError):asyncio.run(adapter.receive())
            count=len(state['requests']);assert count==2
            assert asyncio.run(adapter.receive()) is None and len(state['requests'])==count
            assert not app.runtime.store.all('cognitive_requests')


def test_original_owner_dispatch_and_existing_bff_worker_are_wired(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from nana_core.life.control import dispatch
    from nana_core.life.live_api.platform_events import PlatformEvents
    import nana_core.life.bilibili_runtime as module
    home=tmp_path/'home';channel=configured(home);clock=VirtualClock()
    with counterpart() as (opener,_),notification_front(opener.endpoint) as (endpoint,state):
        with LifeApplication(home,clock=clock) as app:
            app.pause();flow=equipped(app,channel.model_copy(update={'send_authorized':False}),endpoint,grant=False)
            monkeypatch.setattr(module,'account_workflow',lambda *_:flow)
            service=SimpleNamespace(supervisor=SimpleNamespace(home=home),nanalink_bilibili_sources=('notifications',))
            worker=PlatformEvents(service,{})
            def core_request(home,body,timeout):return {'ok':True,'result':dispatch(app,body)}
            monkeypatch.setattr('nana_core.life.live_api.platform_events.request',core_request)
            result=worker.poll_notification_once()
            assert result['external_delivery'] is False and len(state['requests'])>=3
            count=len(state['requests'])
            assert worker.poll_notification_once() is None and len(state['requests'])==count
            assert not app.runtime.store.all('cognitive_requests')
            assert app.platforms._nanalink_bili_sources
