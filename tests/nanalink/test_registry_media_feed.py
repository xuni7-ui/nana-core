import asyncio
from dataclasses import replace
import pytest
from nana_core.contracts import CoreError
from nana_core.nanalink.sdk import AdapterRegistry, AdapterManifest
from nana_core.nanalink.contracts import Outcome
from nana_core.nanalink.feed import FeedAdapter
from nana_core.nanalink.media import MediaCache


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
