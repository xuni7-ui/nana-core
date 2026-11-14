"""One actual owned Core, WS QQ and HTTP Bilibili under the same SDK envelope."""
import asyncio
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


def test_actual_original_core_two_platforms_common_contract_restart_and_duplicate(tmp_path):
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
            assert qr.outcome==br.outcome==Outcome.CONFIRMED_SUCCESS
            assert qr.action_id and br.action_id and qr.external_delivery and br.external_delivery
            assert len(qq_state['sent'])==bili_state['posts']==1 and len(calls)==4
            assert qa.workflow.store is ba.workflow.store is app.runtime.store
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();qa,ba=adapters(app,grant=False)
            assert app.runtime.identity_id==identity
            assert qa.receive_event(envelope(qa,'1')).outcome==Outcome.CONFIRMED_SUCCESS
            assert ba.receive_event(envelope(ba,'9','7','PUBLIC')).outcome==Outcome.CONFIRMED_SUCCESS
            assert len(qq_state['sent'])==bili_state['posts']==1 and len(calls)==4
            assert tables==[r[0] for r in app.runtime.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]


def test_feed_enters_original_surface_without_a_second_subject_or_send(tmp_path):
    home=tmp_path/'home';initialize(home);cfg=load_config(home)
    binding=SurfaceBinding(binding_id='public.feed',platform='web.feed',surface='web.feed',adapter='web.feed',permitted_privacy=('PUBLIC',))
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(binding,)}),expected_revision=cfg.revision)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();adapter=FeedAdapter('https://example.org/rss',authorized=True)
        event=adapter.parse(b'<rss><channel><item><guid>x</guid><title>A sourced public observation</title></item></channel></rss>')[0]
        bridge=FeedCoreBridge(app,adapter,binding.binding_id)
        identity=app.runtime.identity_id
        result=bridge.receive(event)
        assert not result['external_delivery'] and app.runtime.identity_id==identity
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('cognitive_requests')
        app.runtime.clock.advance(1000)
        repeated=bridge.receive(event)
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
        from nana_core.continuity.memory import MemoryService
        MemoryService(app.runtime.store).forget(result['source_memory_id'], app.runtime.authority)
        import pytest
        with pytest.raises(CoreError):bridge.receive(event)
        assert not app.runtime.store.all('actions')


def test_original_core_ws_unknown_survives_restart_without_extra_send_or_model(tmp_path):
    from tests.living_release_v4.test_platform_runtime import initialize_channel
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
                identity=app.runtime.identity_id
            with LifeApplication(home,clock=clock,router=router) as app:
                app.pause()
                transport=OneBotHTTPTransport(net['endpoint'],'42',authorized=True,realm='SYNTHETIC_LOOPBACK',
                                             credential=SecretReference(resolver,'core.test'))
                adapter=qq_adapter(QQReplyWorkflow(app,channel,transport));asyncio.run(adapter.connect())
                assert adapter.receive_event(envelope(adapter,'1')).outcome==Outcome.UNKNOWN
                assert len(state['sent'])==1 and len(calls)==2 and app.runtime.identity_id==identity
