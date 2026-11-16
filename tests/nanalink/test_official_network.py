"""Owned HTTP official-shaped peer; no QQ account/login/external message."""
import asyncio
import hashlib
import hmac
import json
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from aiohttp import web, ClientSession
from nana_core.contracts import CoreError, GrantSpec
from nana_core.nanalink.official_host import OfficialHostBridge, gateway_message
from nana_core.nanalink.sidecar import SessionConfig, SidecarConfig, OneBotSidecar
from nana_core.life.secret_binding import MemorySecretResolver
from nana_core.life.platform_runtime import QQChannelBinding, QQReplyWorkflow, SecretReference
from nana_core.life.official_transport import OfficialQQHTTPTransport

TOKEN='FIXTURE_ONLY_OFFICIAL_NOT_A_REAL_TOKEN'
KEY='FIXTURE_ONLY_INGRESS_NOT_A_REAL_SECRET'
CORE='FIXTURE_ONLY_CORE_NOT_A_REAL_SECRET'


def event(mid='native:message-1', *, group=False):
    return {'application_id':'42','type':'GROUP_AT_MESSAGE_CREATE' if group else 'C2C_MESSAGE_CREATE',
            'data':{'id':mid,'content':'An original official-shaped event','timestamp':1,
                    'author':{'member_openid' if group else 'user_openid':'opaque_sender'},
                    **({'group_openid':'opaque_group'} if group else {})}}


@contextmanager
def network():
    loop=asyncio.new_event_loop();ready=threading.Event();net={}
    state={'sent':[],'bot':'bot_42','lose_ack':False,'logins':0}
    resolver=MemorySecretResolver();resolver.bind('core',CORE);resolver.bind('ingress',KEY)
    async def get_me(request):
        assert request.headers['Authorization']=='QQBot '+TOKEN
        assert request.headers['X-Union-Appid']=='42'
        state['logins']+=1
        return web.json_response({'id':state['bot']})
    async def send(request):
        body=await request.json();state['sent'].append((request.path,body))
        if state['lose_ack']:
            request.transport.close()
            return web.Response()
        if state.get('empty_ack'):
            return web.json_response({})
        return web.json_response({'id':'ack:native-'+str(len(state['sent']))})
    async def start():
        app=web.Application();app.router.add_get('/users/@me',get_me)
        app.router.add_post('/v2/{kind}/{peer}/messages',send)
        runner=web.AppRunner(app,access_log=None);await runner.setup()
        site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
        origin='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
        cfg=SessionConfig(alias='official',account_id='42',backend='official',mode='http',native_bot_id='bot_42',
             ingress_secret_ref='ingress',upstream_secret_ref='unused.host.session',core_api_secret_ref='core',port=18790,allow_send=True)
        sidecar=OneBotSidecar(SidecarConfig(sessions=(cfg,)),resolver)
        adapter=sidecar.adapters['official']
        adapter.endpoint=origin;adapter.realm='SYNTHETIC_LOOPBACK'
        # An authenticated host session is required before connect; not a vault token.
        sidecar.official_sessions['official']=(TOKEN,int(time.time())+600)
        await adapter.connect()
        facade=web.AppRunner(sidecar.app(cfg),access_log=None);await facade.setup()
        front=web.TCPSite(facade,'127.0.0.1',0);await front.start()
        net.update(adapter=adapter,sidecar=sidecar,runner=runner,facade=facade,
                   endpoint='http://127.0.0.1:'+str(front._server.sockets[0].getsockname()[1]))
        ready.set()
    def serve():
        asyncio.set_event_loop(loop);loop.run_until_complete(start());loop.run_forever()
    thread=threading.Thread(target=serve,daemon=True);thread.start();assert ready.wait(5)
    try:yield net,state,resolver,loop
    finally:
        async def close():
            await net['sidecar'].close();await net['facade'].cleanup();await net['runner'].cleanup()
        asyncio.run_coroutine_threadsafe(close(),loop).result(5)
        loop.call_soon_threadsafe(loop.stop);thread.join(5);loop.close();resolver.clear()


def transport(net,resolver):
    return OfficialQQHTTPTransport(net['endpoint'],'42',credential=SecretReference(resolver,'core'),
                                   authorized=True,realm='SYNTHETIC_LOOPBACK')


@pytest.mark.parametrize('group',[False,True])
def test_native_ids_capture_and_ack_never_fabricates_readback(group):
    with network() as (net,state,resolver,loop):
        async def ingress():
            adapter=net['adapter'];row=event(group=group)
            assert adapter.offer(row)=='QUEUED'
            assert adapter.offer(row)=='DUPLICATE'
            e=await adapter.receive()
            assert e.account.adapter_id=='qq.official' and e.sender_id=='opaque_sender'
            assert e.origin=='SYNTHETIC_LOOPBACK' and e.privacy=='PERSONAL'
        asyncio.run_coroutine_threadsafe(ingress(),loop).result(3)
        t=transport(net,resolver)
        assert t.get_message('native:message-1')['sender']['user_id']=='opaque_sender'
        r=t.send('group' if group else 'private','opaque_group' if group else 'opaque_sender','owned response','key')
        assert len(state['sent'])==1 and state['sent'][0][1]['msg_id']=='native:message-1'
        assert t.verify_receipt(r).verdict=='INCONCLUSIVE'
        assert r['message_id'] not in net['adapter'].cache
        assert not next(c.available for c in net['adapter'].capabilities() if c.name=='delivery.independent_readback')


def test_loss_account_change_invalid_text_no_retry_or_fallback():
    with network() as (net,state,resolver,loop):
        t=transport(net,resolver)
        with pytest.raises(CoreError):t.send('private','opaque_sender','x'*2049,'key')
        assert not state['sent']
        state['bot']='other_bot'
        with pytest.raises(CoreError):t.send('private','opaque_sender','x','key')
        assert not state['sent']
        state['bot']='bot_42';state['lose_ack']=True
        with pytest.raises(CoreError):t.send('private','opaque_sender','ambiguous','key')
        assert len(state['sent'])==1
        async def malformed():
            with pytest.raises(CoreError):await net['adapter'].rpc('send_private_msg',{'user_id':'opaque_sender','message':[]})
        asyncio.run_coroutine_threadsafe(malformed(),loop).result(3)
        assert len(state['sent'])==1


def test_hmac_host_session_and_exclusive_route_no_fallthrough():
    with network() as (net,state,resolver,loop):
        async def run():
            stopped=[]
            bridge=OfficialHostBridge(net['endpoint'],'42','bot_42',KEY,routes=(('opaque_sender','private','opaque_sender'),),
                                      enabled=True,read_authorized=True)
            async with ClientSession(trust_env=False) as session:
                assert (await session.post(net['endpoint']+'/official/events',json=event())).status==403
                assert (await session.post(net['endpoint']+'/events',json=event())).status==404
                assert await bridge.forward(session,event(),token=TOKEN,expires_at=int(time.time())+700,
                        stop_legacy=lambda:stopped.append(True))=='QUEUED_NOT_DELIVERED'
                assert stopped==[True]
                data=await (await session.get(net['endpoint']+'/nanalink/status',headers={'Authorization':'Bearer '+CORE})).json()
                assert TOKEN not in json.dumps(data) and data['adapter_id']=='qq.official'
                invalid=OfficialHostBridge(net['endpoint'],'42','bot_42','FIXTURE_WRONG_SIGNATURE_SECRET',routes=bridge.routes,
                                           enabled=True,read_authorized=True)
                with pytest.raises(CoreError):await invalid.forward(session,event('another'),token=TOKEN,
                     expires_at=int(time.time())+700,stop_legacy=lambda:stopped.append(True))
                assert stopped==[True,True]  # Even lost handoff cannot start another responder.
                disabled=OfficialHostBridge(net['endpoint'],'42','bot_42',KEY,routes=bridge.routes)
                assert await disabled.forward(session,event(),token=TOKEN,expires_at=0,
                     stop_legacy=lambda:stopped.append(True))=='NOT_SELECTED'
                raw=json.dumps({**event(),'application_id':'99'}).encode()
                signature='sha256='+hmac.new(KEY.encode(),raw,hashlib.sha256).hexdigest()
                assert (await session.post(net['endpoint']+'/official/events',data=raw,headers={'X-Nana-Signature':signature})).status==502
                assert len(stopped)==2 and not state['sent']
        asyncio.run_coroutine_threadsafe(run(),loop).result(5)


def test_original_core_official_unknown_restart_one_subject(tmp_path):
    from nana_core.life.application import LifeApplication
    from nana_core.life.config import load_config,update_config
    from nana_core.life.surfaces import SurfaceBinding
    from nana_core.continuity.autonomy.governance import GovernanceController
    from nana_core.presence.authority import VirtualClock
    from tests.person_self.conftest import initialize
    from tests.independent_life.test_dialogue import relay
    home=tmp_path/'home';initialize(home);cfg=load_config(home);clock=VirtualClock()
    binding=SurfaceBinding(binding_id='qq.official',platform='qq.official',adapter='qq.official',surface='chat.direct',
                           mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PROJECT',))
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(binding,)}),expected_revision=cfg.revision)
    with network() as (net,state,resolver,loop),relay(home,'CHAT') as (router,calls):
        async def ingest():net['adapter'].offer(event())
        asyncio.run_coroutine_threadsafe(ingest(),loop).result(3)
        channel=QQChannelBinding(channel_id='official',binding_id=binding.binding_id,backend='official',endpoint=net['endpoint'],
                    account_id='42',sender_id='opaque_sender',target_id='opaque_sender',enabled=True,read_authorized=True,send_authorized=True)
        def flow(app):return QQReplyWorkflow(app,channel,transport(net,resolver))
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();f=flow(app);identity=app.runtime.identity_id
            GovernanceController(app.runtime.store,app.runtime.authority).initialize(app.runtime.authority)
            f.realization.kernel.set_budgets({'external_requests':16,'write_attempts':4,'cost_micro_units':16},app.runtime.authority)
            f.realization.kernel.grant(GrantSpec(capabilities=('world.contact','world.action.verify'),resources=(f.resource,),
                   not_before_us=clock.utc_now_us(),expires_at_us=clock.utc_now_us()+100000000),app.runtime.authority)
            result=f.receive('native:message-1')
            assert result['delivery']=='UNKNOWN' and not result['external_delivery'],result
            assert len(state['sent'])==1 and len(calls)==2
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();f=flow(app)
            assert f.receive('native:message-1')['delivery']=='UNKNOWN'
            assert len(state['sent'])==1 and len(calls)==2 and app.runtime.identity_id==identity


def test_host_native_scalar_extraction_and_default_onebot_wire():
    row=gateway_message('42',SimpleNamespace(id='m',content='x',timestamp='2026-11-14T00:00:00Z',
                                             author=SimpleNamespace(user_openid='opaque_sender')))
    assert row['data']['author']=={'user_openid':'opaque_sender'}
    channel=QQChannelBinding(channel_id='old',binding_id='old',account_id='42',endpoint='http://127.0.0.1:18790',sender_id='43',target_id='43')
    assert 'backend' not in channel.model_dump()
    with pytest.raises(ValueError):QQChannelBinding.model_validate({**channel.model_dump(),'sender_id':'opaque'})


def test_expired_host_session_reports_reauthorization_without_network():
    with network() as (net,state,resolver,loop):
        before=state['logins']
        net['sidecar'].official_sessions['official']=(TOKEN,int(time.time())-1)
        health=net['adapter'].health()
        assert health.connection=='DEGRADED' and health.login=='REQUIRED'
        assert not next(c.available for c in net['adapter'].capabilities() if c.name=='message.text.send.via_core')
        assert state['logins']==before and not state['sent']


def test_official_chunked_http_ack_is_single_send_and_not_readback():
    from nana_core.nanalink.official import OfficialQQAdapter
    async def run():
        calls = []
        async def respond(request):
            calls.append(request.method)
            body = {'id': 'bot_42'} if request.method == 'GET' else {'id': 'native-ack'}
            if request.method == 'POST':
                await request.json()
            raw = json.dumps(body).encode()
            response = web.StreamResponse(); await response.prepare(request)
            await response.write(raw[:5]); await asyncio.sleep(.03)
            await response.write(raw[5:]); await response.write_eof()
            return response
        app = web.Application()
        app.router.add_get('/users/@me', respond)
        app.router.add_post('/v2/{kind}/{peer}/messages', respond)
        runner = web.AppRunner(app, access_log=None); await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
        adapter = OfficialQQAdapter('42', bot_id='bot_42', token=TOKEN, allow_send=True,
            endpoint='http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1]), realm='SYNTHETIC_LOOPBACK')
        try:
            await adapter.connect()
            result = await adapter.rpc('send_private_msg', {'user_id': 'peer', 'message': [{'type':'text','data':{'text':'fixture'}}]})
            assert result == {'message_id': 'native-ack', 'platform_ack': True}
            assert calls == ['GET', 'POST']
            assert 'native-ack' not in adapter.cache
            assert not next(c.available for c in adapter.capabilities() if c.name == 'delivery.independent_readback')
        finally:
            await adapter.shutdown(); await runner.cleanup()
    asyncio.run(run())


def test_official_disable_drops_captured_private_message_and_reply_anchor():
    with network() as (net,state,resolver,loop):
        async def run():
            adapter=net['adapter']
            assert adapter.offer(event()) == 'QUEUED'
            assert adapter.cache and adapter.reply_ids
            headers={'Authorization':'Bearer '+CORE}
            async with ClientSession() as client:
                url=net['endpoint']+'/nanalink/manage'
                view=await (await client.get(url,headers=headers)).json()
                body={'operation':'DISABLE','version':None,'revision':view['revision']}
                result=await (await client.post(url,headers=headers,json=body)).json()
                assert result['state']=='APPLIED'
                assert not adapter.cache and not adapter.reply_ids and adapter.verified_token is None
                body.update(operation='ENABLE',revision=result['revision'])
                result=await (await client.post(url,headers=headers,json=body)).json()
                assert result['state']=='APPLIED'
                with pytest.raises(CoreError,match='QQ_OFFICIAL_MESSAGE_NOT_IN_VOLATILE_CAPTURE'):
                    await adapter.rpc('get_msg',{'message_id':'native:message-1'})
                assert state['sent'] == []
        asyncio.run_coroutine_threadsafe(run(),loop).result(4)


def test_official_unusable_ack_counts_unknown_without_retry():
    with network() as (net,state,resolver,loop):
        state['empty_ack']=True
        t=transport(net,resolver)
        with pytest.raises(CoreError,match='NO_RETRY'):
            t.send('private','opaque_sender','synthetic','key')
        assert len(state['sent']) == 1
        assert net['adapter'].metrics['unknown'] == 1


def test_official_synthetic_realm_never_targets_real_endpoint():
    from nana_core.nanalink.official import OfficialQQAdapter
    with pytest.raises(CoreError,match='QQ_OFFICIAL_SYNTHETIC_LOOPBACK_REQUIRED'):
        OfficialQQAdapter('42',bot_id='bot_42',token=TOKEN,realm='SYNTHETIC_LOOPBACK')
    adapter=OfficialQQAdapter('42',bot_id='bot_42',token=TOKEN,realm='SYNTHETIC_LOOPBACK',endpoint='http://127.0.0.1:12345')
    async def run():
        adapter.session=object()
        adapter.endpoint='https://api.sgroup.qq.com'
        with pytest.raises(CoreError,match='QQ_OFFICIAL_SYNTHETIC_LOOPBACK_REQUIRED'):
            await adapter._account()
        adapter.session=None
    asyncio.run(run())
