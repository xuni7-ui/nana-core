import asyncio
import json
import pytest
from tools.nana_astrbot_shadow.sanitize import MetadataSanitizer
from tools.nana_astrbot_shadow.observer import ShadowObserver, ProbePermit

PROBE='nana-probe-development-v1'
def sanitizer():
    return MetadataSanitizer(scope='dev-observer-v1',hash_key=b'D'*32,probe_ids=frozenset({PROBE}))
def event(**kw):
    return dict(platform='fixture',type='message',event_id='synthetic-event',timestamp='2026-10-11T10:00:00+08:00',
        sender_id='synthetic-person',conversation_id='synthetic-conversation',event_source='operator_probe',synthetic=True,probe_id=PROBE,**kw)

class SecretRepr:
    def __repr__(self): raise AssertionError('repr must not be called')
    def __str__(self): raise AssertionError('str must not be called')
    def __getattribute__(self,k): raise AssertionError('getattr must not be called')

@pytest.mark.parametrize('factory', [lambda: SecretRepr(), lambda: b'private-body', lambda: {'content':'synthetic-private-canary'}, lambda: 'X'*1_000_000])
def test_unknown_fields_never_inspected(factory):
    payload=factory()
    e=event(content=payload,body=payload,attachments=payload,token=payload)
    before=dict(e); result=sanitizer().sanitize(e)
    assert result.status=='ACCEPT' and e==before
    text=json.dumps(result.metadata.public())
    assert 'synthetic-private-canary' not in text and 'synthetic-person' not in text
    assert set(result.metadata.public())=={'platform','type','event_id','timestamp','sender_hash','conversation_hash','event_source','synthetic','probe_id'}

@pytest.mark.parametrize('key,value', [('event_id',None),('sender_id','OBJECT'),('platform','sk-fake-development-canary'),('timestamp','bad'),('timestamp','2026-10-11'),('synthetic',1),('probe_id','foreign')])
def test_bad_inputs_fail_closed(key,value):
    e=event();e[key]=SecretRepr() if value=='OBJECT' else value
    assert sanitizer().sanitize(e).metadata is None

def test_unknown_objects_null_unicode_time_and_hash_scope():
    s=sanitizer(); assert s.sanitize(SecretRepr()).metadata is None
    e=event();e['sender_id']=e['conversation_id']='合成身份'; e['timestamp']=None; e['platform']=None
    m=s.sanitize(e).metadata
    assert m.timestamp is None and m.platform is None and m.sender_hash!=m.conversation_hash
    assert s.sanitize(event()).metadata.timestamp=='2026-10-11T02:00:00+00:00'
    assert MetadataSanitizer(scope='other',hash_key=b'D'*32,probe_ids=frozenset({PROBE})).sanitize(e).metadata.sender_hash!=m.sender_hash
    assert s.sanitize({**event(),'sender_id': {'nested': 'private'}}).metadata is None

class Sink:
    def accept(self,m): return {'barrier_result':'SHADOW_BLOCKED'}
    def close(self): pass

def test_observer_never_returns_reply_even_failure_and_logger_failure():
    async def run():
        o=ShadowObserver(sanitizer(),Sink(),logger=lambda code: (_ for _ in ()).throw(RuntimeError('synthetic-secret')))
        permit=o.issue_local_permit(PROBE)
        assert await o.callback(event(),permit=ProbePermit(PROBE)) is None
        assert o.last_result['status']=='DROP_UNAUTHORIZED_PROBE'
        assert await o.callback(event(),permit=permit) is None
        assert o.last_result['status']=='RECORDED'
        assert await o.callback(SecretRepr(),permit=permit) is None
        assert o.last_result['status'].startswith('DROP')
        o.sanitizer.sanitize=lambda _: (_ for _ in ()).throw(ValueError('synthetic-private-canary'))
        assert await o.callback(event(),permit=permit) is None and o.last_result=={'status':'DROP_SHADOW_FAILURE'}
        await o.close()
    asyncio.run(run())
