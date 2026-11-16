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
    state={'sent':[],'reads':0,'logins':0,'connections':0,'lose_ack':False,'image_readback':False,'messages':{'1':message()}}
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
            if state['image_readback']:
                state['messages'][str(mid)]['message'] = params['message']
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
            if req['action'] == 'get_msg' and state.get('hold_read'):
                state['read_started'].set()
                await state['release_read'].wait()
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
        assert net['adapter'].metrics['unknown']==1


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


@pytest.mark.parametrize('mode', ['websocket', 'http'])
def test_owned_sidecar_transports_bounded_inline_image_without_claiming_verified_delivery(mode):
    import base64
    with network(mode=mode) as (net, state, resolver, loop):
        transport = OneBotHTTPTransport(net['endpoint'], '42', credential=SecretReference(resolver, 'core.test'),
                                        authorized=True, realm='SYNTHETIC_LOOPBACK')
        data = b'owned synthetic image bytes'
        receipt = transport.send_image('private', '43', 'picture', data, hashlib.sha256(data).hexdigest(), 'image-key')
        assert len(state['sent']) == 1
        assert state['sent'][0]['message'][1]['data']['file'] == 'base64://' + base64.b64encode(data).decode()
        assert transport.verify_receipt(receipt).verdict == 'INCONCLUSIVE'
        async def reject():
            async with ClientSession() as client:
                msg = [{'type':'text','data':{'text':'x'}}, {'type':'image','data':{'file':'https://example.invalid/a'}}]
                async with client.post(net['endpoint']+'/send_private_msg', json={'user_id':43,'message':msg},
                                       headers={'Authorization':'Bearer FIXTURE_ONLY_CORE_NOT_A_REAL_SECRET'}) as response:
                    assert response.status == 400
        asyncio.run_coroutine_threadsafe(reject(), loop).result(3)
        assert len(state['sent']) == 1


def test_one_bad_event_does_not_disconnect_account_or_lose_following_event():
    with network() as (net, state, resolver, loop):
        async def inject_and_receive():
            await state['ws'].send_str('{malformed-json')
            await state['ws'].send_json({**message(2), 'message': [{'type': 'text', 'data': {'text': 99}}]})
            await state['ws'].send_json(message(3, 'after malformed'))
            return await asyncio.wait_for(net['adapter'].receive(), 3)
        got = asyncio.run_coroutine_threadsafe(inject_and_receive(), loop).result(5)
        assert got.message_id == '3' and got.segments[0].text == 'after malformed'
        assert net['adapter'].metrics['invalid_events'] == 2
        assert net['adapter'].health().connection == 'CONNECTED'
        assert state['connections'] == 1 and not state['sent']
        bound = OneBotHTTPTransport(net['endpoint'], '42', credential=SecretReference(resolver, 'core.test'),
                                    authorized=True, realm='SYNTHETIC_LOOPBACK')
        assert bound.account() == {'account_id': '42'}


def test_wrong_account_event_closes_old_socket_before_recovery():
    with network() as (net, state, resolver, loop):
        async def inject_and_wait():
            first = state['ws']
            await first.send_json({**message(2), 'self_id': 99})
            for _ in range(60):
                if state['connections'] >= 2 and first.closed and net['adapter'].health().login == 'AUTHENTICATED':
                    return
                await asyncio.sleep(.05)
            raise AssertionError('old account socket was not retired and replaced')
        asyncio.run_coroutine_threadsafe(inject_and_wait(), loop).result(5)
        assert net['adapter'].metrics['invalid_events'] == 0
        assert net['adapter'].events.empty() and not state['sent']


def test_bad_event_during_pending_rpc_preserves_correlated_response():
    with network() as (net, state, resolver, loop):
        async def exercise():
            state['hold_read'] = True
            state['read_started'], state['release_read'] = asyncio.Event(), asyncio.Event()
            request = asyncio.create_task(net['adapter'].rpc('get_msg', {'message_id': 1}))
            await asyncio.wait_for(state['read_started'].wait(), 2)
            await state['ws'].send_str('{bad-event')
            await state['ws'].send_json(message(4, 'after bad event'))
            state['release_read'].set()
            response = await asyncio.wait_for(request, 2)
            event = await asyncio.wait_for(net['adapter'].receive(), 2)
            return response, event
        response, event = asyncio.run_coroutine_threadsafe(exercise(), loop).result(5)
        assert response['message_id'] == 1 and event.message_id == '4'
        assert net['adapter'].metrics['invalid_events'] == 1 and state['connections'] == 1
        assert not state['sent'] and net['adapter'].health().login == 'AUTHENTICATED'


def test_disconnect_during_recovery_handoff_is_not_lost():
    async def run():
        adapter = OneBotAdapter('42', mode='websocket', endpoint='ws://127.0.0.1:12345')
        reconnected = asyncio.Event()
        calls = []
        async def open_fixture():
            calls.append(1)
            if len(calls) == 1:
                # Reader observed a close while the recovery task was still set.
                adapter._health = adapter._health.model_copy(update={'connection':'DISCONNECTED', 'login':'UNKNOWN'})
            else:
                adapter._health = adapter._health.model_copy(update={'connection':'CONNECTED', 'login':'AUTHENTICATED'})
                reconnected.set()
        adapter._open_ws = open_fixture
        adapter.recovery = asyncio.create_task(adapter._recover())
        try:
            await asyncio.wait_for(reconnected.wait(), 4)
            assert len(calls) == 2 and adapter.health().login == 'AUTHENTICATED'
        finally:
            adapter.closed = True
            if adapter.recovery is not None:
                adapter.recovery.cancel()
                await asyncio.gather(adapter.recovery, return_exceptions=True)
    asyncio.run(run())


def test_account_reply_cannot_mark_a_disconnected_websocket_online():
    from types import SimpleNamespace
    async def run():
        adapter = OneBotAdapter('42', mode='websocket', endpoint='ws://127.0.0.1:12345')
        adapter.ws = SimpleNamespace(closed=False)
        adapter._health = adapter._health.model_copy(update={'connection':'CONNECTING'})
        async def reply_after_close(*args, **kwargs):
            adapter._health = adapter._health.model_copy(update={'connection':'DISCONNECTED', 'login':'UNKNOWN'})
            return {'user_id':42}
        adapter.rpc = reply_after_close
        with pytest.raises(CoreError, match='ONEBOT_SESSION_UNAVAILABLE'):
            await adapter._account()
        assert adapter.health().login != 'AUTHENTICATED'
    asyncio.run(run())


def test_http_rpc_reads_chunked_response_without_resending():
    async def run():
        calls = []
        async def operation(request):
            action = request.match_info['action']
            calls.append(action)
            await request.json()
            data = {'user_id': 42} if action == 'get_login_info' else {'message_id': 99}
            raw = json.dumps({'status': 'ok', 'retcode': 0, 'data': data}).encode()
            response = web.StreamResponse()
            await response.prepare(request)
            await response.write(raw[:10])
            await asyncio.sleep(.03)
            await response.write(raw[10:])
            await response.write_eof()
            return response
        app = web.Application(); app.router.add_post('/{action}', operation)
        runner = web.AppRunner(app, access_log=None); await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
        adapter = OneBotAdapter('42', mode='http', endpoint='http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1]), allow_send=True)
        try:
            await adapter.connect()
            result = await adapter.rpc('send_private_msg', {'user_id': 43, 'message': 'fixture'})
            assert result == {'message_id': 99}
            assert calls == ['get_login_info', 'send_private_msg']
            assert adapter.metrics['unknown'] == 0
        finally:
            await adapter.shutdown(); await runner.cleanup()
    asyncio.run(run())


def test_http_oversize_write_response_fails_without_resending():
    async def run():
        calls = []
        async def operation(request):
            action = request.match_info['action']; calls.append(action)
            await request.json()
            if action == 'get_login_info':
                return web.json_response({'status': 'ok', 'retcode': 0, 'data': {'user_id': 42}})
            return web.Response(body=b'x' * 262145)
        app = web.Application(); app.router.add_post('/{action}', operation)
        runner = web.AppRunner(app, access_log=None); await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
        adapter = OneBotAdapter('42', mode='http', endpoint='http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1]), allow_send=True)
        try:
            await adapter.connect()
            with pytest.raises(CoreError, match='ONEBOT_FRAME_BOUND'):
                await adapter.rpc('send_private_msg', {'user_id': 43, 'message': 'fixture'})
            assert calls == ['get_login_info', 'send_private_msg']
            assert adapter.metrics['unknown'] == 1
        finally:
            await adapter.shutdown(); await runner.cleanup()
    asyncio.run(run())


def test_disabled_account_queued_event_is_cancelled_without_blocking_other_account(monkeypatch):
    from nana_core.nanalink.onebot import normalize
    from nana_core.nanalink.sidecar import ForwardRoute
    from nana_core.nanalink.contracts import Outcome
    calls = []
    def fake_forward(*args, **kwargs):
        calls.append(args[2]); return {'state':'QUEUED_NOT_JUDGED'}
    monkeypatch.setattr('nana_core.life.platform_forward.forward', fake_forward)
    async def run():
        route = ForwardRoute(channel_id='target', sender_id='43', conversation_kind='private', conversation_id='43')
        def config(alias, account, port):
            return SessionConfig(alias=alias, account_id=account, mode='http', endpoint='http://127.0.0.1:1', port=port,
                upstream_secret_ref='upstream.'+alias, core_api_secret_ref='core.'+alias,
                forward_secret_ref='forward.'+alias, core_origin='http://127.0.0.1:2', routes=(route,))
        resolver = MemorySecretResolver()
        sidecar = OneBotSidecar(SidecarConfig(sessions=(config('a','42',18790), config('b','44',18791))), resolver)
        first = normalize(sidecar.adapters['a'].account, message(1))
        second = normalize(sidecar.adapters['b'].account, {**message(2), 'self_id':44})
        assert sidecar.transport.offer(first) == 'QUEUED'
        assert sidecar.transport.offer(second) == 'QUEUED'
        await sidecar.management.command('a','DISABLE',None,sidecar.management.state['revision'])
        try:
            result = await sidecar.transport.drain_once(sidecar._forward)
            assert result.outcome == Outcome.CANCELLED and calls == []
            result = await sidecar.transport.drain_once(sidecar._forward)
            assert result.outcome == Outcome.UNKNOWN and calls == ['target']
        finally:
            await sidecar.close(); resolver.clear()
    asyncio.run(run())


def test_http_rpc_limits_inflight_calls_and_releases_capacity():
    async def run():
        release = asyncio.Event(); all_started = asyncio.Event(); count = 0
        async def operation(request):
            nonlocal count
            action = request.match_info['action']; await request.json()
            if action == 'get_login_info':
                account=44 if request.headers.get('Authorization') == 'Bearer synthetic-other' else 42
                return web.json_response({'status':'ok','retcode':0,'data':{'user_id':account}})
            count += 1
            if count == 16:
                all_started.set()
            await release.wait()
            return web.json_response({'status':'ok','retcode':0,'data':{'message_id':1}})
        app=web.Application();app.router.add_post('/{action}',operation)
        runner=web.AppRunner(app,access_log=None);await runner.setup()
        site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
        adapter=OneBotAdapter('42',mode='http',endpoint='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]))
        other=OneBotAdapter('44',mode='http',endpoint=adapter.endpoint,token='synthetic-other')
        tasks=[]
        try:
            await adapter.connect();await other.connect()
            tasks=[asyncio.create_task(adapter.rpc('get_msg',{'message_id':i})) for i in range(16)]
            await asyncio.wait_for(all_started.wait(),3)
            with pytest.raises(CoreError,match='ONEBOT_SESSION_UNAVAILABLE'):
                await asyncio.wait_for(adapter.rpc('get_msg',{'message_id':99}),.3)
            assert count == 16
            assert adapter.metrics['http_inflight'] == 16 and adapter.metrics['http_backpressure'] == 1
            assert await other.rpc('get_login_info',{}) == {'user_id':44}
            assert other.metrics['http_backpressure'] == 0
            tasks[0].cancel()
            with pytest.raises(asyncio.CancelledError):
                await tasks[0]
            tasks.append(asyncio.create_task(adapter.rpc('get_msg',{'message_id':100})))
            for _ in range(100):
                if count == 17: break
                await asyncio.sleep(.01)
            assert count == 17
            release.set()
            assert len(await asyncio.gather(*tasks[1:])) == 16
            assert await adapter.rpc('get_msg',{'message_id':101}) == {'message_id':1}
            assert adapter.metrics['http_inflight'] == 0 and adapter.metrics['http_peak_inflight'] == 16
        finally:
            release.set()
            await asyncio.gather(*tasks,return_exceptions=True)
            await adapter.shutdown();await other.shutdown();await runner.cleanup()
    asyncio.run(run())


def test_status_exposes_http_capacity_metrics_without_credentials():
    with network(mode='http') as (net,state,resolver,loop):
        async def run():
            async with ClientSession() as client:
                headers={'Authorization':'Bearer FIXTURE_ONLY_CORE_NOT_A_REAL_SECRET'}
                response=await client.get(net['endpoint']+'/nanalink/status',headers=headers)
                data=await response.json()
                assert data['metrics']['http_inflight']==0
                assert data['metrics']['http_peak_inflight']>=1
                assert data['metrics']['http_backpressure']==0
                assert 'FIXTURE_ONLY' not in json.dumps(data)
        asyncio.run_coroutine_threadsafe(run(),loop).result(3)
