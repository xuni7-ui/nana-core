import asyncio
import pytest
from nana_core.contracts import CoreError
from nana_core.nanalink.contracts import Account, Event, Segment, OperationReceipt, Outcome
from nana_core.nanalink.transport import EventTransport
from nana_core.nanalink.onebot import normalize, safe_endpoint
from nana_core.nanalink.core_bridge import CoreBridge, ChannelRoute


def event(i='1', *, account='42', thread='43', priority=1):
    return Event(account=Account(platform='qq', adapter_id='qq.onebot', account_id=account),
                 event_id=i, message_id=i, conversation_kind='private', conversation_id=thread,
                 sender_id='43', kind='message.created', observed_at_us=1, privacy='PERSONAL',
                 origin='SYNTHETIC_LOOPBACK', raw_sha256='a'*64, raw_reference='onebot:'+i, priority=priority)


def test_five_outcomes_and_no_false_delivery():
    assert len(Outcome) == 5
    for outcome in Outcome:
        if outcome != Outcome.CONFIRMED_SUCCESS:
            with pytest.raises(ValueError):
                OperationReceipt(operation_id='x', outcome=outcome, reason='TEST', external_delivery=True)
    with pytest.raises(ValueError):
        OperationReceipt(operation_id='x', outcome='UNKNOWN', reason='TEST', retry_allowed=True)


def test_event_account_identity_not_nickname_and_collision():
    a, b = event(), event(account='44')
    assert a.key != b.key
    q = EventTransport(capacity=2, per_account=1, dedupe=2)
    assert q.offer(a) == 'QUEUED'
    assert q.offer(a) == 'DUPLICATE'
    with pytest.raises(CoreError, match='COLLISION'):
        q.offer(a.model_copy(update={'raw_sha256':'b'*64}))
    assert q.offer(event('2')) == 'BACKPRESSURE'
    assert q.offer(b) == 'QUEUED'
    assert q.offer(event('3',account='45')) == 'BACKPRESSURE'


def test_order_priority_failure_isolation_and_unknown_no_requeue():
    async def run():
        q = EventTransport(capacity=8, per_account=4, dedupe=8)
        for e in (event('1',priority=2),event('2',priority=0),event('3',account='44',thread='44',priority=0)):
            q.offer(e)
        order = []
        async def receive(e):
            order.append(e.event_id)
            if e.event_id == '3':raise OSError('fixture')
            return OperationReceipt(operation_id=e.key,outcome=Outcome.UNKNOWN,reason='NO_SEND')
        first = await q.drain_once(receive)
        assert first.outcome == Outcome.UNKNOWN
        while q.size:await q.drain_once(receive)
        assert order == ['3','1','2']
        assert q.size == 0 and q.metrics['dispatched'] == 3
        assert await q.drain_once(receive) is None
        q.offer(event('4'))
        assert q.close()[0].outcome == Outcome.CANCELLED and q.offer(event('5')) == 'CANCELLED'
    asyncio.run(run())


def test_original_core_route_cannot_be_selected_by_text():
    class Runtime:
        def qq(self, channel, mid):
            assert (channel,mid) == ('primary','1')
            return dict(delivery='SUCCEEDED',external_delivery=True,action_id='action1')
        def bilibili(self,*args):raise AssertionError('wrong adapter')
    e=event()
    bridge=CoreBridge(Runtime(),[ChannelRoute(e.account.key,'primary','43','43','PERSONAL','private')])
    assert bridge.receive(e).outcome == Outcome.CONFIRMED_SUCCESS
    with pytest.raises(CoreError):bridge.receive(e.model_copy(update={'sender_id':'99'}))
    assert bridge.receive(e.model_copy(update={'kind':'message.recalled'})).outcome == Outcome.UNSUPPORTED


@pytest.mark.parametrize('value',['http://example.com','ws://example.com','https://u:p@example.com','https://example.com?token=x','https://example.com/#x'])
def test_insecure_or_secret_endpoints_denied(value):
    with pytest.raises(CoreError):safe_endpoint(value)


def test_onebot_semantics_and_unknown_segments_are_preserved():
    a=event().account
    row=dict(self_id=42,post_type='message',message_type='group',group_id=88,user_id=43,time=123,
             message_id=-7,message=[dict(type='text',data={'text':'hi'}),dict(type='reply',data={'id':'6'}),
             dict(type='json',data={'data':'untrusted card'}),dict(type='image',data={'file':'image1'})])
    e=normalize(a,row,now_us=999)
    assert e.message_id=='-7' and e.parent_id=='6' and e.conversation_id=='88'
    assert e.privacy=='PERSONAL' and e.occurred_at_us==123000000
    assert [s.kind for s in e.segments]==['text','reply','json','image']
    assert all(not s.inspected for s in e.segments)
    assert e.raw_sha256 and e.raw_reference=='onebot:-7'
    with pytest.raises(CoreError):normalize(a,{**row,'self_id':99})
    notice=normalize(a,{**row,'post_type':'notice','notice_type':'group_recall','message':[]})
    assert notice.kind=='message.recalled'


def test_lifecycle_does_not_invent_heartbeat_or_healthy_receive():
    from nana_core.nanalink.onebot import OneBotAdapter
    a=OneBotAdapter('42',mode='reverse-websocket')
    assert a.offer({'self_id':42,'post_type':'meta_event','meta_event_type':'lifecycle'})=='META_EVENT'
    assert a.health().last_heartbeat_us is None and a.health().receive=='NOT_OBSERVED'
    assert a.offer({'self_id':42,'post_type':'meta_event','meta_event_type':'heartbeat'})=='HEARTBEAT'
    assert a.health().last_heartbeat_us is not None and a.health().receive=='NOT_OBSERVED'


def test_negative_onebot_id_crosses_existing_owner_metadata_contract(tmp_path):
    from types import SimpleNamespace
    from nana_core.life.control import dispatch
    calls=[]
    app=SimpleNamespace(home=tmp_path,config=SimpleNamespace(min_free_disk_mb=1),
                        platforms=SimpleNamespace(qq=lambda channel,mid:calls.append((channel,mid))))
    dispatch(app,{'operation':'qq-message','channel_id':'primary','message_id':'-7'})
    assert calls==[('primary','-7')]
