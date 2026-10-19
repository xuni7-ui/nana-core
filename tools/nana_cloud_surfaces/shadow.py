"""Pure development adapters into the one application's SurfaceObservation.

No network, account, history import, platform pump, Store or authority. Bilibili
reuses the existing pure event-source normalization (not its fetch/pump/brain).
Real traffic is deliberately rejected until a separate capture authorization.
"""
from nana_core.contracts import CoreError
from nana_core.storage import digest
from nana_core.life.surfaces import SurfaceObservation


def _fixture(payload):
    if type(payload) is not dict or payload.get('synthetic') is not True:
        raise CoreError('CLOUD_ONLY_EXPLICIT_SYNTHETIC_PLATFORM_FIXTURE')


def qq(payload,*,topic='daily'):
    _fixture(payload)
    if set(payload)!={'synthetic','event_id','conversation_id','sender_id','text'}:
        raise CoreError('CLOUD_QQ_FIXTURE_FIELDS')
    if any(type(payload[k]) is not str or not 1<=len(payload[k])<=96 for k in ('event_id','conversation_id','sender_id')):
        raise CoreError('CLOUD_QQ_FIXTURE_ID')
    return SurfaceObservation(binding_id='qq.shadow',event_id='qq:'+digest([payload['conversation_id'],payload['event_id']])[:48],
        thread_id='qq:'+digest(payload['conversation_id'])[:48],topic=topic,text=payload['text'],privacy_class='PROJECT')


def bilibili(payload,*,topic='daily'):
    _fixture(payload)
    if set(payload)!={'synthetic','channel','item'} or payload['channel'] not in {'reply','at'}:
        raise CoreError('CLOUD_BILI_FIXTURE_FIELDS')
    # This module's imports have no account/credential side effects. Do not import
    # bili_event_pump, bili_agent or fetch_channel: they own legacy execution.
    from bili_agent.bili_event_source import normalize
    event=normalize(payload['channel'],payload['item'])
    if not event:raise CoreError('CLOUD_BILI_SOURCE_ID_REQUIRED')
    return SurfaceObservation(binding_id='bili.shadow',event_id=event['eid'],
        thread_id=event['bvid'],topic=topic,text=event['message'],privacy_class='PUBLIC')
