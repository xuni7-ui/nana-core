"""One actual owned Core, WS QQ and HTTP Bilibili under the same SDK envelope."""
import asyncio
import pytest
from nana_core.contracts import GrantSpec, CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config, update_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.platform_runtime import QQChannelBinding, QQReplyWorkflow, SecretReference
from nana_core.life.bilibili_runtime import BilibiliChannelBinding, BilibiliReplyWorkflow
from nana_core.life.platform_bridge import OneBotHTTPTransport
from nana_core.presence.authority import VirtualClock
from nana_core.nanalink.contracts import Account, Event, Outcome
from nana_core.nanalink.adapters import qq_adapter,bilibili_adapter
from nana_core.nanalink.feed import FeedAdapter, FeedCoreBridge
from tests.person_self.conftest import initialize
from tests.independent_life.test_dialogue import relay
from tests.living_release_v4.test_platform_runtime import equip
from tests.living_release_v4.test_bilibili_runtime import equipped
from tests.living_release_v4.bilibili_loopback import counterpart as bili_counterpart
from tests.nanalink.test_onebot_network import network


def envelope(adapter,mid,peer='43',privacy='PROJECT'):
    return Event(account=adapter.account,event_id=mid,message_id=mid,kind='message.created',
                 sender_id='43',conversation_id=peer,conversation_kind='private' if adapter.account.platform=='qq' else 'channel',
                 observed_at_us=1,privacy=privacy,origin='SYNTHETIC_LOOPBACK',raw_sha256='a'*64,raw_reference='fixture:'+mid)


@pytest.mark.parametrize('preexisting', [False, True])
def test_actual_original_core_two_platforms_common_contract_restart_and_duplicate(tmp_path,monkeypatch,preexisting):
    home=tmp_path/'home';initialize(home);cfg=load_config(home);clock=VirtualClock()
    bindings=(SurfaceBinding(binding_id='qq.primary',platform='qq.onebot',surface='chat.direct',adapter='qq.onebot',
                             mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PROJECT',)),
              SurfaceBinding(binding_id='bili.primary',platform='bilibili.account',surface='chat.direct',adapter='bilibili.account',
                             mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PUBLIC',)))
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':bindings}),expected_revision=cfg.revision)
    with network() as (net,qq_state,resolver,_),bili_counterpart() as (opener,bili_state),relay(home,'CHAT') as (router,calls):
        qc=QQChannelBinding(channel_id='primary',binding_id='qq.primary',endpoint=net['endpoint'],account_id='42',sender_id='43',
                            target_id='43',enabled=True,read_authorized=True,send_authorized=True)
        bc=BilibiliChannelBinding(channel_id='primary',binding_id='bili.primary',kind='comment',account_id=42,sender_id=43,
                            target_id=7,cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,send_authorized=True)
        bili_state['comments']=[{'rpid':9,'root':0,'member':{'mid':43},'content':{'message':'Independent SDK public event'}}]
        if preexisting:
            bili_state['comments'].append({'rpid':99,'root':9,'parent':9,'member':{'mid':42},
                                           'content':{'message':'A deliberately synthetic language response'}})
        def adapters(app,grant=True):
            if grant:
                q=equip(app,qc,net['endpoint']);q.transport.credential=SecretReference(resolver,'core.test')
            else:
                t=OneBotHTTPTransport(net['endpoint'],'42',authorized=True,realm='SYNTHETIC_LOOPBACK',credential=SecretReference(resolver,'core.test'))
                q=QQReplyWorkflow(app,qc,t)
            b=equipped(app,bc,opener.endpoint,grant=False)
            if grant:
                b.realization.kernel.grant(GrantSpec(capabilities=('bilibili.comment.send','bilibili.action.verify'),resources=(b.resource,),
                        not_before_us=clock.utc_now_us(),expires_at_us=clock.utc_now_us()+100000000),app.runtime.authority)
            qa,ba=qq_adapter(q),bilibili_adapter(b)
            asyncio.run(qa.connect());asyncio.run(ba.connect())
            return qa,ba
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();qa,ba=adapters(app);identity=app.runtime.identity_id
            tables=[r[0] for r in app.runtime.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            qr=qa.receive_event(envelope(qa,'1'));br=ba.receive_event(envelope(ba,'9','7','PUBLIC'))
            assert qr.outcome==Outcome.CONFIRMED_SUCCESS
            assert br.outcome==(Outcome.CANCELLED if preexisting else Outcome.CONFIRMED_SUCCESS)
            assert qr.action_id and br.action_id and qr.external_delivery and br.external_delivery is not preexisting
            assert len(qq_state['sent'])==1 and bili_state['posts']==(0 if preexisting else 1) and len(calls)==4
            assert qa.workflow.store is ba.workflow.store is app.runtime.store
            from types import SimpleNamespace
            from nana_core.nanalink.core_bridge import CoreBridge,ChannelRoute
            configured=SimpleNamespace(runtime=app.runtime,config=SimpleNamespace(qq_channels=(qc,),bilibili_channels=(bc,)))
            bridge=CoreBridge(SimpleNamespace(app=configured),[
                ChannelRoute(qa.account.key,'primary','43','43','PROJECT','private'),
                ChannelRoute(ba.account.key,'primary','7','43','PUBLIC','channel')])
            assert bridge.receipt(qr.action_id).outcome==Outcome.CONFIRMED_SUCCESS
            assert bridge.receipt(br.action_id).outcome==(Outcome.CANCELLED if preexisting else Outcome.CONFIRMED_SUCCESS)
            owner=SimpleNamespace(app=configured,qq=lambda *args:None,bilibili=lambda channel,mid:{'delivery':'SUCCEEDED','action_id':br.action_id,'external_delivery':True})
            direct=CoreBridge(owner,[ChannelRoute(ba.account.key,'primary','7','43','PUBLIC','channel')])
            assert direct.receive(envelope(ba,'9','7','PUBLIC')).outcome==(Outcome.CANCELLED if preexisting else Outcome.CONFIRMED_SUCCESS)
            wrong_qc=qc.model_copy(update={'account_id':'99'})
            wrong_qa=Account(platform='qq',adapter_id='qq.onebot',account_id='99')
            wrong_bc=bc.model_copy(update={'account_id':99})
            wrong_ba=Account(platform='bilibili',adapter_id='bilibili.account',account_id='99')
            wrong_config=SimpleNamespace(runtime=app.runtime,config=SimpleNamespace(qq_channels=(wrong_qc,),bilibili_channels=(wrong_bc,)))
            wrong_bridge=CoreBridge(SimpleNamespace(app=wrong_config),[
                ChannelRoute(wrong_qa.key,'primary','43','43','PROJECT','private'),
                ChannelRoute(wrong_ba.key,'primary','7','43','PUBLIC','channel')])
            assert wrong_bridge.receipt(qr.action_id).outcome==Outcome.UNKNOWN
            assert wrong_bridge.receipt(br.action_id).outcome==Outcome.UNKNOWN
            import pytest
            unbound=CoreBridge(SimpleNamespace(app=configured),[])
            with pytest.raises(CoreError,match='NANALINK_RECEIPT_NOT_FOUND'):unbound.receipt(qr.action_id)
            other_session=CoreBridge(SimpleNamespace(app=configured),[
                ChannelRoute(qa.account.key,'primary','99','43','PROJECT','private'),
                ChannelRoute(ba.account.key,'primary','8','43','PUBLIC','channel')])
            with pytest.raises(CoreError,match='NANALINK_RECEIPT_NOT_FOUND'):other_session.receipt(qr.action_id)
            with pytest.raises(CoreError,match='NANALINK_RECEIPT_NOT_FOUND'):other_session.receipt(br.action_id)
            other_privacy=CoreBridge(SimpleNamespace(app=configured),[
                ChannelRoute(qa.account.key,'primary','43','43','PERSONAL','private'),
                ChannelRoute(ba.account.key,'primary','7','43','PROJECT','channel')])
            with pytest.raises(CoreError,match='NANALINK_RECEIPT_NOT_FOUND'):other_privacy.receipt(qr.action_id)
            with pytest.raises(CoreError,match='NANALINK_RECEIPT_NOT_FOUND'):other_privacy.receipt(br.action_id)
            store=app.runtime.store;original_one=store.one;action=original_one('actions',qr.action_id)
            with monkeypatch.context() as patch:
                patch.setattr(store,'one',lambda table,key: {**action,'body_json':'{}'} if table=='actions' and key==qr.action_id else original_one(table,key))
                assert bridge.receipt(qr.action_id).outcome==Outcome.UNKNOWN
            with monkeypatch.context() as patch:
                patch.setattr(store,'one',lambda table,key: {**action,'capability':'world.compute'} if table=='actions' and key==qr.action_id else original_one(table,key))
                with pytest.raises(CoreError,match='NANALINK_RECEIPT_NOT_FOUND'):bridge.receipt(qr.action_id)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();qa,ba=adapters(app,grant=False)
            assert app.runtime.identity_id==identity
            assert qa.receive_event(envelope(qa,'1')).outcome==Outcome.CONFIRMED_SUCCESS
            assert ba.receive_event(envelope(ba,'9','7','PUBLIC')).outcome==(Outcome.CANCELLED if preexisting else Outcome.CONFIRMED_SUCCESS)
            assert len(qq_state['sent'])==1 and bili_state['posts']==(0 if preexisting else 1) and len(calls)==4
            assert tables==[r[0] for r in app.runtime.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            import json
            from nana_core.continuity.records import RecordService
            configured=SimpleNamespace(runtime=app.runtime,config=SimpleNamespace(qq_channels=(qc,),bilibili_channels=(bc,)))
            bridge=CoreBridge(SimpleNamespace(app=configured),[ChannelRoute(qa.account.key,'primary','43','43','PROJECT','private')])
            action=app.runtime.store.one('actions',qr.action_id)
            verification=app.runtime.store.event(json.loads(action['body_json'])['verification_event_id'])
            record=app.runtime.store.db.execute('SELECT record_id FROM continuity_records WHERE payload_artifact_id=?',(verification['artifact_id'],)).fetchone()[0]
            support=RecordService(app.runtime.store).support(record)
            assert support
            app.forget(support[0])
            assert bridge.receipt(qr.action_id).outcome==Outcome.UNKNOWN
            bili_action=app.runtime.store.one('actions',br.action_id)
            bili_event=app.runtime.store.event(json.loads(bili_action['body_json'])['verification_event_id'])
            bili_record=app.runtime.store.db.execute('SELECT record_id FROM continuity_records WHERE payload_artifact_id=?',(bili_event['artifact_id'],)).fetchone()[0]
            bili_support=RecordService(app.runtime.store).support(bili_record)
            assert bili_support
            app.forget(bili_support[0])
            with monkeypatch.context() as patch:
                patch.setattr(ba.workflow,'receive',lambda _: {'delivery':'SUCCEEDED','action_id':br.action_id,'external_delivery':True})
                assert ba.receive_event(envelope(ba,'9','7','PUBLIC')).outcome==Outcome.UNKNOWN
            assert len(qq_state['sent'])==1 and bili_state['posts']==(0 if preexisting else 1)


def test_feed_enters_original_surface_without_a_second_subject_or_send(tmp_path):
    home=tmp_path/'home';initialize(home);cfg=load_config(home)
    binding=SurfaceBinding(binding_id='public.feed',platform='web.feed',surface='web.feed',adapter='web.feed',permitted_privacy=('PUBLIC',))
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(binding,)}),expected_revision=cfg.revision)
    clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();adapter=FeedAdapter('https://example.org/rss',authorized=True)
        event=adapter.parse(b'<rss><channel><item><guid>x</guid><title>A sourced public observation</title></item></channel></rss>')[0]
        bridge=FeedCoreBridge(app,adapter,binding.binding_id)
        identity=app.runtime.identity_id
        result=bridge.receive(event)
        assert not result['external_delivery'] and app.runtime.identity_id==identity
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('cognitive_requests')
        clock.advance(1000)
        repeated=bridge.receive(event.model_copy(update={'observed_at_us':event.observed_at_us+1000}))
        assert repeated['queue_id']==result['queue_id']
        row=app.runtime.store.db.execute('SELECT * FROM runtime_queue WHERE queue_id=?',(result['queue_id'],)).fetchone()
        assert row['event_type']=='WORLD_EVENT'
        from nana_core.continuity.records import RecordService
        source=RecordService(app.runtime.store).read(row['record_id'])
        assert source['payload']['input']['origin']=='SELF_WAKE'
        assert source['payload']['input']['interaction_signal'] is None
        assert source['payload']['input']['text'] is None
        app.runtime.step()
        assert not app.runtime.store.all('subject_cycles')  # Paused original C is not forced awake.
        app.forget(result['source_memory_id'])
        import pytest
        with pytest.raises(CoreError):bridge.receive(event)
        assert not app.runtime.store.all('actions')


def test_feed_bridge_rechecks_host_binding_and_adapter_authorization(tmp_path):
    import pytest
    home=tmp_path/'home';initialize(home);cfg=load_config(home)
    binding=SurfaceBinding(binding_id='public.feed',platform='web.feed',surface='web.feed',adapter='web.feed',permitted_privacy=('PUBLIC',))
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(binding,)}),expected_revision=cfg.revision)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();adapter=FeedAdapter('https://example.org/rss',authorized=True)
        event=adapter.parse(b'<rss><channel><item><guid>x</guid><title>source</title></item></channel></rss>')[0]
        bridge=FeedCoreBridge(app,adapter,binding.binding_id)
        adapter.authorized=False
        with pytest.raises(CoreError,match='FEED_SOURCE_BINDING_MISMATCH'):bridge.receive(event)
        adapter.authorized='false'
        with pytest.raises(CoreError,match='FEED_SOURCE_BINDING_MISMATCH'):bridge.receive(event)
        adapter.authorized=True
        cfg=load_config(home)
        disabled=binding.model_copy(update={'enabled':False})
        update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(disabled,)}),expected_revision=cfg.revision)
        before=len(app.runtime.store.all('memories'))
        with pytest.raises(CoreError,match='FEED_PUBLIC_SURFACE_REQUIRED'):bridge.receive(event)
        assert len(app.runtime.store.all('memories'))==before
        assert not app.runtime.store.all('runtime_queue')


def test_original_core_ws_unknown_survives_restart_without_extra_send_or_model(tmp_path):
    from tests.living_release_v4.test_platform_runtime import initialize_channel
    from types import SimpleNamespace
    from nana_core.nanalink.core_bridge import CoreBridge,ChannelRoute
    home=tmp_path/'home';clock=VirtualClock()
    with network() as (net,state,resolver,_):
        channel=initialize_channel(home,net['endpoint'])
        state['lose_ack']=True
        with relay(home,'CHAT') as (router,calls):
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause();flow=equip(app,channel,net['endpoint'])
                flow.transport.credential=SecretReference(resolver,'core.test')
                adapter=qq_adapter(flow);asyncio.run(adapter.connect())
                result=adapter.receive_event(envelope(adapter,'1'))
                assert result.outcome==Outcome.UNKNOWN and not result.external_delivery
                assert result.action_id
                configured=SimpleNamespace(runtime=app.runtime,config=SimpleNamespace(qq_channels=(channel,),bilibili_channels=()))
                bridge=CoreBridge(SimpleNamespace(app=configured),[ChannelRoute(adapter.account.key,channel.channel_id,'43','43','PROJECT','private')])
                assert bridge.receipt(result.action_id).outcome==Outcome.UNKNOWN
                identity=app.runtime.identity_id
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause()
                transport=OneBotHTTPTransport(net['endpoint'],'42',authorized=True,realm='SYNTHETIC_LOOPBACK',
                                             credential=SecretReference(resolver,'core.test'))
                adapter=qq_adapter(QQReplyWorkflow(app,channel,transport));asyncio.run(adapter.connect())
                assert adapter.receive_event(envelope(adapter,'1')).outcome==Outcome.UNKNOWN
                configured=SimpleNamespace(runtime=app.runtime,config=SimpleNamespace(qq_channels=(channel,),bilibili_channels=()))
                bridge=CoreBridge(SimpleNamespace(app=configured),[ChannelRoute(adapter.account.key,channel.channel_id,'43','43','PROJECT','private')])
                assert bridge.receipt(result.action_id).outcome==Outcome.UNKNOWN
                assert len(state['sent'])==1 and len(calls)==2 and app.runtime.identity_id==identity


def test_bilibili_video_capabilities_follow_original_installed_consumer(monkeypatch):
    from types import SimpleNamespace
    from nana_core.life.bilibili import BilibiliLoopbackOpener
    from nana_core.nanalink.adapters import BilibiliEventsAdapter, bilibili_adapter
    channel = SimpleNamespace(account_id=42, enabled=True, read_authorized=True,
                              private_read_authorized=True, send_authorized=False)
    app = SimpleNamespace(bilibili_life=None, config=SimpleNamespace(bilibili_life=None))
    workflow = SimpleNamespace(channel=channel, app=app)
    adapter = bilibili_adapter(workflow)
    events = BilibiliEventsAdapter(workflow)
    def availability(obj):
        return {c.name: c.available for c in obj.capabilities()}
    assert all(not availability(adapter)[key] for key in ('video.metadata', 'video.subtitles', 'video.frames'))
    cfg = SimpleNamespace(enabled=True, read_authorized=True, visual_samples=True, activation=None)
    transport = SimpleNamespace(origin='SYNTHETIC_FIXTURE', authorized=True,
                                opener=BilibiliLoopbackOpener('http://127.0.0.1:12345'))
    app.bilibili_life = SimpleNamespace(config=cfg, transport=transport)
    app.config.bilibili_life = cfg
    assert all(availability(adapter)[key] for key in ('video.metadata', 'video.subtitles', 'video.frames'))
    assert availability(events)['video.frames']
    from importlib import util
    with monkeypatch.context() as patch:
        patch.setattr(util, 'find_spec', lambda name: None)
        assert not availability(adapter)['video.frames']
        assert next(c.reason for c in adapter.capabilities() if c.name == 'video.frames') == 'FRAME_DECODER_UNAVAILABLE'
    cfg.read_authorized = False
    assert not availability(adapter)['video.metadata'] and not availability(events)['video.frames']
    cfg.read_authorized = True
    app.config.bilibili_life = None
    assert not availability(adapter)['video.metadata']
    app.config.bilibili_life = cfg
    transport.origin = 'REAL_PLATFORM_HTTP'
    assert not availability(adapter)['video.metadata']


def test_bilibili_notification_capability_requires_private_read_and_enabled_channel():
    from types import SimpleNamespace
    from nana_core.nanalink.adapters import bilibili_adapter
    channel = SimpleNamespace(account_id=42, enabled=True, read_authorized=True,
                              private_read_authorized=False, send_authorized=False)
    app = SimpleNamespace(bilibili_life=None, config=SimpleNamespace(bilibili_life=None))
    adapter = bilibili_adapter(SimpleNamespace(channel=channel, app=app))
    def notice():
        return next(c for c in adapter.capabilities() if c.name == 'notification.reply')
    assert not notice().available
    channel.private_read_authorized = True
    assert notice().available
    channel.enabled = False
    assert not notice().available


def test_bilibili_message_capabilities_respect_channel_and_dm_read_policy():
    from types import SimpleNamespace
    from nana_core.nanalink.adapters import bilibili_adapter
    channel = SimpleNamespace(account_id=42, kind='dm', enabled=True, read_authorized=True,
                              private_read_authorized=False, send_authorized=True)
    app = SimpleNamespace(bilibili_life=None, config=SimpleNamespace(bilibili_life=None))
    adapter = bilibili_adapter(SimpleNamespace(channel=channel, app=app))
    def capabilities():
        return {c.name:c.available for c in adapter.capabilities()}
    assert not capabilities()['message.receive']
    assert not capabilities()['message.text.send'] and not capabilities()['message.readback']
    assert all(c.reason=='PRIVATE_READ_OR_CHANNEL_DISABLED' for c in adapter.capabilities()
               if c.name in {'message.receive','message.text.send','message.readback'})
    channel.private_read_authorized = True
    assert capabilities()['message.receive'] and capabilities()['message.text.send'] and capabilities()['message.readback']
    channel.enabled = False
    assert not capabilities()['message.receive'] and not capabilities()['message.text.send'] and not capabilities()['message.readback']
    channel.enabled = True; channel.read_authorized = False
    assert not capabilities()['message.receive'] and not capabilities()['message.text.send'] and not capabilities()['message.readback']
    channel.kind='comment'; channel.read_authorized=True; channel.private_read_authorized=False
    assert capabilities()['message.receive'] and capabilities()['message.text.send'] and capabilities()['message.readback']


def test_qq_capabilities_follow_current_channel_authorizations():
    from types import SimpleNamespace
    from nana_core.nanalink.adapters import qq_adapter
    channel = SimpleNamespace(account_id='42', backend='onebot', enabled=True, read_authorized=True,
                              private_read_authorized=False, privacy_class='PERSONAL', send_authorized=True)
    adapter = qq_adapter(SimpleNamespace(channel=channel))
    def capabilities():
        return {c.name:c.available for c in adapter.capabilities()}
    assert not capabilities()['message.receive']
    channel.private_read_authorized = True
    assert capabilities()['message.receive'] and capabilities()['message.text.send']
    channel.enabled = False
    assert not capabilities()['message.receive'] and not capabilities()['message.text.send']
    channel.enabled = True; channel.read_authorized = False
    assert not capabilities()['message.receive'] and not capabilities()['message.text.send']
