"""Actual owned TCP HTTP/WS/reverse-WS peers. No real QQ account or native code."""
import asyncio
import hashlib
import hmac
import json
import socket
import threading
from contextlib import contextmanager
import pytest
from aiohttp import web, ClientSession, WSMsgType
from nana_core.contracts import CoreError
from nana_core.nanalink.onebot import OneBotAdapter
from nana_core.nanalink.sidecar import SessionConfig, SidecarConfig, OneBotSidecar
from nana_core.life.secret_binding import MemorySecretResolver
from nana_core.life.platform_bridge import OneBotHTTPTransport
from nana_core.life.platform_runtime import SecretReference


def message(mid=1,text='hello',sender=43,target=43):
    return dict(post_type='message',self_id=42,time=1,message_id=mid,message_type='private',user_id=sender,
                sender={'user_id':sender},target_id=target,message=[{'type':'text','data':{'text':text}}])


@contextmanager
def network(*,mode='websocket'):
    """Independent loop thread keeps original synchronous Core on its owner."""
    loop=asyncio.new_event_loop()
    ready=threading.Event()
    state={'sent':[],'reads':0,'logins':0,'connections':0,'lose_ack':False,'messages':{'1':message()}}
    token='FIXTURE_ONLY_UPSTREAM_NOT_A_REAL_SECRET'
    coretoken='FIXTURE_ONLY_CORE_NOT_A_REAL_SECRET'
    resolver=MemorySecretResolver()
    resolver.bind('upstream.test',token)
    resolver.bind('core.test',coretoken)
    holders={}

    async def operation(action,params):
        if action=='get_login_info':state['logins']+=1;return {'user_id':42}
        if action=='get_msg':state['reads']+=1;return state['messages'].get(str(params['message_id']),{})
        if action in {'send_private_msg','send_group_msg'}:
            mid=100+len(state['sent'])
            state['sent'].append(params)
            state['messages'][str(mid)]=message(mid,params['message'][0]['data']['text'],42,params.get('user_id',43))
            return {'message_id':mid}
        raise AssertionError(action)

    async def upstream(request):
        assert request.headers.get('Authorization')=='Bearer '+token
        ws=web.WebSocketResponse()
        await ws.prepare(request)
        state['connections']+=1
        state['ws']=ws
        async for msg in ws:
            if msg.type!=WSMsgType.TEXT:continue
            req=json.loads(msg.data)
            data=await operation(req['action'],req['params'])
            if req['action'].startswith('send_') and state['lose_ack']:
                await ws.close();break
            await ws.send_json(dict(status='ok',retcode=0,data=data,echo=req['echo']))
        return ws

    async def upstream_http(request):
        data=await operation(request.match_info['action'],await request.json())
        return web.json_response(dict(status='ok',retcode=0,data=data))

    async def start():
        app=web.Application()
        app.router.add_get('/ws',upstream)
        app.router.add_post('/{action}',upstream_http)
        runner=web.AppRunner(app,access_log=None)
        await runner.setup()
        site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
        port=site._server.sockets[0].getsockname()[1]
        endpoint=('ws' if mode=='websocket' else 'http')+'://127.0.0.1:'+str(port)+('/ws' if mode=='websocket' else '')
        cfg=SessionConfig(alias='primary',account_id='42',mode=mode,endpoint=endpoint,port=18790,
              upstream_secret_ref='upstream.test',core_api_secret_ref='core.test',allow_send=True)
        sidecar=OneBotSidecar(SidecarConfig(sessions=(cfg,)),resolver)
        adapter=sidecar.adapters['primary'];adapter.timeout=0.5
        await adapter.connect()
        facade=web.AppRunner(sidecar.app(cfg),access_log=None);await facade.setup()
        front=web.TCPSite(facade,'127.0.0.1',0);await front.start()
        fp=front._server.sockets[0].getsockname()[1]
        holders.update(sidecar=sidecar,facade=facade,runner=runner,endpoint='http://127.0.0.1:'+str(fp),adapter=adapter)
        ready.set()
    def serve():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start())
        loop.run_forever()
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    assert ready.wait(5),'owned network did not start'
    try:yield holders,state,resolver,loop
    finally:
        async def close():
            await holders['sidecar'].close()
            await holders['facade'].cleanup();await holders['runner'].cleanup()
        asyncio.run_coroutine_threadsafe(close(),loop).result(5)
        loop.call_soon_threadsafe(loop.stop);thread.join(5);loop.close();resolver.clear()


@pytest.mark.parametrize('mode',['websocket','http'])
def test_facade_original_http_transport_and_independent_readback(mode):
    with network(mode=mode) as (net,state,resolver,loop):
        transport=OneBotHTTPTransport(net['endpoint'],'42',credential=SecretReference(resolver,'core.test'),authorized=True,
                                    realm='SYNTHETIC_LOOPBACK')
        assert transport.account()=={'account_id':'42'}
        assert transport.get_message('1')['sender']['user_id']==43
        receipt=transport.send('private','43','owned send','original-key')
        assert len(state['sent'])==1
        assert transport.verify_receipt(receipt).verdict=='MATCH'
        assert net['adapter'].health().receive=='NOT_OBSERVED'
        async def ingress():
            assert net['adapter'].offer(message())=='QUEUED'
            assert net['adapter'].offer(message())=='DUPLICATE'
            assert (await net['adapter'].receive()).message_id=='1'
        asyncio.run_coroutine_threadsafe(ingress(),loop).result(3)
        assert net['adapter'].health().connection=='CONNECTED'
        assert net['adapter'].health().receive=='HEALTHY'


def test_lost_send_ack_is_unknown_reconnect_never_resends():
    with network() as (net,state,resolver,loop):
        state['lose_ack']=True
        transport=OneBotHTTPTransport(net['endpoint'],'42',credential=SecretReference(resolver,'core.test'),authorized=True)
        with pytest.raises(CoreError,match='NO_RETRY'):
            transport.send('private','43','ambiguous','key1')
        async def wait_reconnect():
            for _ in range(40):
                if state['connections']>=2 and net['adapter'].health().login=='AUTHENTICATED':return
                await asyncio.sleep(.05)
            raise AssertionError('no connection recovery')
        asyncio.run_coroutine_threadsafe(wait_reconnect(),loop).result(4)
        assert len(state['sent'])==1 and state['connections']>=2
        assert net['adapter'].health().reconnects>=1


def test_reverse_ws_auth_account_binding_and_http_signature():
    async def run():
        resolver=MemorySecretResolver();token='FIXTURE_REVERSE_ONLY_NOT_REAL_SECRET'
        resolver.bind('upstream',token);resolver.bind('core','FIXTURE_CORE_ONLY_NOT_REAL_SECRET')
        cfg=SessionConfig(alias='reverse',account_id='42',mode='reverse-websocket',port=18791,
                          upstream_secret_ref='upstream',core_api_secret_ref='core')
        sidecar=OneBotSidecar(SidecarConfig(sessions=(cfg,)),resolver)
        await sidecar.adapters['reverse'].connect()
        runner=web.AppRunner(sidecar.app(cfg),access_log=None);await runner.setup()
        site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
        url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
        try:
            async with ClientSession() as client:
                assert (await client.get(url+'/nanalink/status')).status==403
                with pytest.raises(Exception):await client.ws_connect(url+'/reversews',headers={'X-Self-ID':'42'})
                ws=await client.ws_connect(url+'/reversews',headers={'X-Self-ID':'42','Authorization':'Bearer '+token})
                req=await ws.receive_json()
                assert req['action']=='get_login_info'
                await ws.send_json(dict(status='ok',retcode=0,data={'user_id':42},echo=req['echo']))
                raw=json.dumps(message()).encode()
                async with client.post(url+'/events',data=raw) as response:assert response.status==403
                signature='sha1='+hmac.new(token.encode(),raw,hashlib.sha1).hexdigest()
                async with client.post(url+'/events',data=raw,headers={'X-Signature':signature}) as response:
                    assert response.status==202
                e=await asyncio.wait_for(sidecar.adapters['reverse'].receive(),1)
                assert e.account.account_id=='42'
                with pytest.raises(CoreError):sidecar.adapters['reverse'].offer({**message(),'self_id':44})
                await ws.close()
        finally:
            await sidecar.close();await runner.cleanup();resolver.clear()
    asyncio.run(run())


def test_observer_binds_exact_account_and_redacts_configuration():
    from nana_core.nanalink.console import ObservationBinding, NanaLinkObserver
    with network() as (net,_,resolver,loop):
        observer=NanaLinkObserver((ObservationBinding(platform='qq',account_id='42',channel_id='primary',
                    endpoint=net['endpoint'],credential_ref='core.test'),),resolver)
        result=observer.view()
        assert result['sessions'][0]['health']['connection']=='CONNECTED'
        raw=json.dumps(result)
        assert 'FIXTURE_ONLY' not in raw and net['endpoint'] not in raw and 'core.test' not in raw
        wrong=ObservationBinding(platform='qq',account_id='43',channel_id='wrong',endpoint=net['endpoint'],credential_ref='core.test')
        assert NanaLinkObserver((wrong,),resolver).view()['sessions'][0]['health']['connection']=='DISCONNECTED'
