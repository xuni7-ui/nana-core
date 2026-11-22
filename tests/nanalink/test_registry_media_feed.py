import asyncio
from dataclasses import replace
import pytest
from nana_core.contracts import CoreError
from nana_core.nanalink.sdk import AdapterRegistry, AdapterManifest
from nana_core.nanalink.contracts import Outcome
from nana_core.nanalink.feed import FeedAdapter
from nana_core.nanalink.media import MediaCache


@pytest.mark.parametrize('authorized', ['false', 1, None])
def test_feed_requires_explicit_boolean_read_authorization(authorized):
    adapter=FeedAdapter('https://example.org/rss',authorized=authorized)
    assert not adapter.capabilities()[0].available
    with pytest.raises(CoreError,match='FEED_READ_NOT_AUTHORIZED'):
        asyncio.run(adapter.connect())


@pytest.mark.parametrize('invalid', ['false', 1, None])
def test_media_source_validator_requires_explicit_boolean_true(tmp_path, invalid):
    state={'value':True}
    cache=MediaCache(tmp_path/'media',source_current=lambda _:state['value'],max_bytes=16,item_bytes=8,max_items=2)
    try:
        handle=cache.put((b'image',),source_ref='source')
        state['value']=invalid
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.read(handle)
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.resolve(source_ref='source',sha256=handle.sha256)
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.put((b'image',),source_ref='source')
    finally:
        cache.close()


def test_media_observed_withdrawal_cannot_be_undone_by_later_callback(tmp_path):
    active={'old':True,'other':True,'new':True}
    cache=MediaCache(tmp_path/'media',source_current=lambda ref:active[ref],max_bytes=16,item_bytes=8,max_items=2)
    try:
        old=cache.put((b'image',),source_ref='old')
        other=cache.put((b'image',),source_ref='other')
        active['old']=False
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.read(old)
        active['old']=True
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.read(old)
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.put((b'image',),source_ref='old')
        assert cache.read(other)==b'image'
        fresh=cache.put((b'image',),source_ref='new')
        assert cache.read(fresh)==b'image'
        active['other']=False
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.read(other)
        assert cache.read(fresh)==b'image'
        active['new']=False
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.read(fresh)
        assert cache.total==0 and list((tmp_path/'media').iterdir())==[]
    finally:
        cache.close()
    with pytest.raises(CoreError,match='MEDIA_CACHE_CLOSED'):cache.put((b'image',),source_ref='new')


def test_media_source_callback_error_retires_admitted_reference(tmp_path):
    state={'fail':False}
    def current(_):
        if state['fail']:raise RuntimeError('synthetic source lookup failure')
        return True
    cache=MediaCache(tmp_path/'media',source_current=current,max_bytes=16,item_bytes=8,max_items=1)
    try:
        handle=cache.put((b'image',),source_ref='source')
        state['fail']=True
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.read(handle)
        state['fail']=False
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.read(handle)
        assert cache.total==0
    finally:
        cache.close()


def test_media_withdrawal_during_initial_ingest_stays_retired(tmp_path):
    state={'current':True}
    cache=MediaCache(tmp_path/'media',source_current=lambda _:state['current'],max_bytes=16,item_bytes=8,max_items=1)
    def chunks():
        yield b'image'
        state['current']=False
    try:
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.put(chunks(),source_ref='source')
        assert cache.total==0 and list((tmp_path/'media').iterdir())==[]
        state['current']=True
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.put((b'image',),source_ref='source')
    finally:
        cache.close()


def test_media_retirement_budget_fails_closed(tmp_path):
    state={'current':True}
    cache=MediaCache(tmp_path/'media',source_current=lambda _:state['current'],max_bytes=16,item_bytes=8,max_items=1)
    try:
        for n in range(65):
            state['current']=True
            handle=cache.put((b'x',),source_ref=f'source.{n}')
            state['current']=False
            with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.read(handle)
        state['current']=True
        with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):cache.put((b'x',),source_ref='new')
        assert cache.total==0
    finally:
        cache.close()


def test_media_retirement_unlink_failure_remains_tracked_for_cleanup(tmp_path, monkeypatch):
    from pathlib import Path
    state={'current':True}
    cache=MediaCache(tmp_path/'media',source_current=lambda _:state['current'],max_bytes=16,item_bytes=8,max_items=1)
    handle=cache.put((b'x',),source_ref='source')
    target=cache.items[handle.sha256][0]
    original=Path.unlink
    def fail_unlink(path,*args,**kwargs):
        if path==target:raise OSError('synthetic unlink failure')
        return original(path,*args,**kwargs)
    state['current']=False
    with monkeypatch.context() as patch:
        patch.setattr(Path,'unlink',fail_unlink)
        with pytest.raises(OSError):cache.read(handle)
    assert handle.sha256 in cache.items and target.exists()
    cache.close()
    assert not target.exists()


def test_media_eviction_unlink_failure_preserves_existing_entry(tmp_path, monkeypatch):
    from pathlib import Path
    cache=MediaCache(tmp_path/'media',source_current=lambda _:True,max_bytes=8,item_bytes=8,max_items=1)
    old=cache.put((b'old',),source_ref='old')
    target=cache.items[old.sha256][0]
    original=Path.unlink
    def fail_unlink(path,*args,**kwargs):
        if path==target:raise OSError('synthetic unlink failure')
        return original(path,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path,'unlink',fail_unlink)
        with pytest.raises(OSError):cache.put((b'new',),source_ref='new')
    assert cache.read(old)==b'old' and list((tmp_path/'media').iterdir())==[target]
    cache.close()


def test_real_feed_reads_rss_atom_no_model_and_no_send():
    async def run():
        payload=b'<rss><channel><item><guid>a</guid><title>hello</title><link>https://example.org/a</link></item></channel></rss>'
        calls=[]
        async def fetch(url,limit):calls.append(url);return payload
        a=FeedAdapter('https://example.org/rss',authorized=True,fetch=fetch)
        await a.connect()
        e=await a.receive()
        assert e.kind=='feed.item' and e.privacy=='PUBLIC' and e.segments[1].reference=='https://example.org/a'
        assert await a.receive() is None and len(calls)==1
        assert a.parse(payload)==[]
        atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>b</id><title>atom</title><link href="https://example.org/b"/></entry></feed>'
        assert a.parse(atom)[0].segments[0].text=='atom'
        assert (await a.send(None)).outcome==Outcome.UNSUPPORTED
        await a.shutdown()
    asyncio.run(run())


def test_feed_blocks_dtd_oversize_and_missing_stable_id():
    a=FeedAdapter('https://example.org/rss',authorized=True,max_bytes=1024)
    for raw in [b'<!DOCTYPE rss><rss/>',b'<rss>'+b' '*1024+b'</rss>',b'<notfeed/>']:
        with pytest.raises(CoreError):a.parse(raw)
    assert a.parse(b'<rss><channel><item><title>no stable id</title></item></channel></rss>')==[]


def test_registry_failure_isolated_offline_upgrade_rollback():
    class Broken(FeedAdapter):
        async def connect(self):raise OSError('fake credential in exception must never escape status')
    async def run():
        registry=AdapterRegistry(limit=2)
        good=FeedAdapter('https://example.org/a',authorized=True,fetch=lambda *a:None)
        bad=Broken('https://example.org/b',authorized=True)
        g,b=registry.install(good),registry.install(bad)
        assert await registry.enable(g) and not await registry.enable(b)
        assert registry.slots[g].enabled and registry.view()[1]['error']=='CONNECT_FAILED'
        candidate=FeedAdapter('https://example.org/a',authorized=True)
        candidate.manifest=AdapterManifest(adapter_id='web.feed',version='1.1.0',platforms=('webfeed',),license='original')
        with pytest.raises(CoreError):await registry.replace(g,candidate)
        await registry.disable(g)
        await registry.replace(g,candidate)
        assert registry.view()[0]['rollback_available']
        await registry.rollback(g)
        assert registry.slots[g].adapter is good
        await registry.uninstall(b)
        await registry.shutdown()
    asyncio.run(run())


def test_streaming_cache_budget_reuse_and_withdrawal(tmp_path):
    live={'source.a','source.b'}
    cache=MediaCache(tmp_path/'media',source_current=lambda x:x in live,max_bytes=12,item_bytes=8,max_items=2)
    a=cache.put([b'abc',b'def'],source_ref='source.a')
    b=cache.put([b'abcdef'],source_ref='source.b')
    assert cache.total==6 and cache.metrics['reused_bytes']==6
    assert cache.read(a,offset=2,length=3)==b'cde'
    live.remove('source.a')
    with pytest.raises(CoreError):cache.read(a)
    assert cache.read(b)==b'abcdef'
    with pytest.raises(CoreError):cache.read(replace(b,source_ref='forged'))
    with pytest.raises(CoreError):cache.put([b'x'*9],source_ref='source.b')
    assert len(list((tmp_path/'media').iterdir()))==1
    cache.put([b'1234567'],source_ref='source.b')
    with pytest.raises(CoreError):cache.read(b)
    cache.close()
    assert list((tmp_path/'media').iterdir())==[]


def test_explicit_installed_plugin_factory_without_core_change(monkeypatch):
    from nana_core.nanalink.sdk import install_adapter,installed_adapters
    import importlib.metadata
    class Point:
        name='third.feed';value='nana_core.nanalink.feed:FeedAdapter';dist=None
        def load(self):return FeedAdapter
    monkeypatch.setattr(importlib.metadata,'entry_points',lambda **kw:[Point()])
    registry=AdapterRegistry()
    assert installed_adapters()[0]['name']=='third.feed'
    with pytest.raises(CoreError):install_adapter(registry,'third.feed',{},allowed=())
    key=install_adapter(registry,'third.feed',{'url':'https://example.org/feed','authorized':False},allowed=('third.feed',))
    assert registry.slots[key].adapter.account.platform=='webfeed'


def test_c4_packaged_normalizer_is_exact_original_snapshot():
    from tools.nanalink_sync_c4 import generated,TARGET
    assert TARGET.read_text()==generated()


def test_feed_actual_owned_http_conditional_fetch():
    from aiohttp import web
    async def run():
        calls=[]
        async def source(request):
            calls.append(request.headers.get('If-None-Match'))
            if calls[-1]=='"fixture"':return web.Response(status=304)
            return web.Response(body=b'<rss><channel><item><guid>http1</guid><title>Owned HTTP source</title></item></channel></rss>',
                                headers={'ETag':'"fixture"'},content_type='application/rss+xml')
        app=web.Application();app.router.add_get('/rss',source)
        runner=web.AppRunner(app,access_log=None);await runner.setup()
        site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
        adapter=FeedAdapter('http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])+'/rss',authorized=True)
        try:
            await adapter.connect()
            assert (await adapter.receive()).segments[0].text=='Owned HTTP source'
            adapter.next_at=0
            assert await adapter.receive() is None and calls==[None,'"fixture"']
        finally:await adapter.shutdown();await runner.cleanup()
    asyncio.run(run())


def test_feed_large_page_delivers_all_entries_before_committing_validator():
    from aiohttp import web
    async def run():
        calls=[]
        body=('<rss><channel>'+''.join(f'<item><guid>{i}</guid><title>Item {i}</title></item>'
              for i in range(35))+'</channel></rss>').encode()
        async def source(request):
            calls.append(request.headers.get('If-None-Match'))
            if calls[-1]=='"fixture"':
                return web.Response(status=304)
            return web.Response(body=body,headers={'ETag':'"fixture"'})
        app=web.Application();app.router.add_get('/rss',source)
        runner=web.AppRunner(app,access_log=None);await runner.setup()
        site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
        adapter=FeedAdapter('http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])+'/rss',authorized=True)
        try:
            await adapter.connect()
            received=[]
            for _ in range(33):
                received.append((await adapter.receive()).segments[0].text)
            await adapter.disconnect()
            await adapter.connect()
            for _ in range(2):
                received.append((await adapter.receive()).segments[0].text)
            assert received==[f'Item {i}' for i in range(35)] and calls==[None]
            adapter.next_at=0
            assert await adapter.receive() is None and calls==[None,'"fixture"']
        finally:
            await adapter.shutdown();await runner.cleanup()
    asyncio.run(run())


def test_feed_chunked_body_and_validators_commit_only_after_parse():
    from aiohttp import web
    async def run():
        headers = []
        async def source(request):
            headers.append(request.headers.get('If-None-Match'))
            if len(headers) == 1:
                return web.Response(body=b'<rss><broken', headers={'ETag': '"bad"'})
            if len(headers) == 2:
                response = web.StreamResponse(headers={'ETag': '"valid"'})
                await response.prepare(request)
                await response.write(b'<rss><channel>')
                await asyncio.sleep(.03)
                await response.write(b'<item><guid>chunked</guid><title>Complete</title></item></channel></rss>')
                await response.write_eof()
                return response
            if len(headers) == 4:
                return web.Response(body=b'x' * 1025, headers={'ETag': '"oversize"'})
            return web.Response(status=304)
        app = web.Application(); app.router.add_get('/rss', source)
        runner = web.AppRunner(app, access_log=None); await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 0); await site.start()
        adapter = FeedAdapter('http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1]) + '/rss', authorized=True, max_bytes=1024)
        try:
            await adapter.connect()
            with pytest.raises(CoreError):
                await adapter.receive()
            adapter.next_at = 0
            assert (await adapter.receive()).segments[0].text == 'Complete'
            adapter.next_at = 0
            assert await adapter.receive() is None
            adapter.next_at = 0
            with pytest.raises(CoreError):
                await adapter.receive()
            adapter.next_at = 0
            assert await adapter.receive() is None
            assert headers == [None, None, '"valid"', '"valid"', '"valid"']
        finally:
            await adapter.shutdown(); await runner.cleanup()
    asyncio.run(run())


def test_feed_disconnect_preserves_unconsumed_entries_without_replaying_delivered():
    async def run():
        payload = (b'<rss><channel><item><guid>one</guid><title>First</title></item>'
                   b'<item><guid>two</guid><title>Second</title></item></channel></rss>')
        calls = []
        async def fetch(url, limit):
            calls.append(url)
            return payload
        adapter = FeedAdapter('https://example.org/rss', authorized=True, fetch=fetch)
        await adapter.connect()
        assert (await adapter.receive()).segments[0].text == 'First'
        await adapter.disconnect()
        await adapter.connect()
        assert (await adapter.receive()).segments[0].text == 'Second'
        assert len(calls) == 1
        await adapter.shutdown()
    asyncio.run(run())


def test_feed_utf16_preserves_valid_input_and_rejects_dtd():
    adapter = FeedAdapter('https://example.org/rss', authorized=True)
    valid = '<?xml version="1.0" encoding="UTF-16"?><rss><channel><item><guid>valid16</guid><title>Readable</title></item></channel></rss>'.encode('utf-16')
    assert adapter.parse(valid)[0].segments[0].text == 'Readable'
    hostile = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE rss [<!ENTITY x "expanded">]><rss><channel><item><guid>x</guid><title>&x;</title></item></channel></rss>'.encode('utf-16')
    with pytest.raises(CoreError, match='FEED_XML_BOUND_OR_DTD_DENIED'):
        adapter.parse(hostile)


@pytest.mark.parametrize('revoked', [False, 'false'])
def test_streaming_cache_discards_read_if_source_revoked_during_io(tmp_path, revoked):
    state = {'checks': 0, 'revoke_on_second': False}
    def current(_):
        state['checks'] += 1
        return True if not state['revoke_on_second'] or state['checks'] < 2 else revoked
    cache = MediaCache(tmp_path / 'media', source_current=current, max_bytes=16, item_bytes=8, max_items=2)
    handle = cache.put([b'abc'], source_ref='source.a')
    state.update(checks=0, revoke_on_second=True)
    with pytest.raises(CoreError, match='MEDIA_SOURCE_RETIRED'):
        cache.read(handle)
    cache.close()
