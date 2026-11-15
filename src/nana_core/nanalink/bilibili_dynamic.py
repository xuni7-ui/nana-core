"""Bounded Bilibili subscription observations, with no private memory writes.

The caller owns the explicitly authorized account reader and its original
budget. C cannot persist PERSONAL source observations until the original
MemoryService gains an approved platform-source contract.
"""
import re
from ..life.bilibili import plain
from ..storage import digest
from .contracts import Account, Event, Segment


def normalize_dynamic(account, row, *, now_us, origin):
    if type(account) is not Account or account.platform != 'bilibili' or type(row) is not dict:
        return None
    event_id = row.get('id_str')
    if type(event_id) is not str or not re.fullmatch(r'[1-9][0-9]{0,24}', event_id):
        return None
    modules = row.get('modules')
    if type(modules) is not dict:
        return None
    author, content = modules.get('module_author'), modules.get('module_dynamic')
    if type(author) is not dict or type(content) is not dict:
        return None
    mid, published = author.get('mid'), author.get('pub_ts')
    if type(mid) is not int or mid <= 0 or type(published) is not int or not 0 <= published*1000000 <= now_us:
        return None
    desc, major = content.get('desc') or {}, content.get('major') or {}
    if type(desc) is not dict or type(major) is not dict:
        return None
    text = plain(desc.get('text'), 2048)
    archive = major.get('archive') or {}
    parts = []
    if type(archive) is dict and re.fullmatch(r'BV[A-Za-z0-9]{10}',str(archive.get('bvid'))):
        parts.append(Segment(kind='video',reference=archive['bvid']))
        if not text:
            text = plain(archive.get('title'),2048)
    if text:
        parts.insert(0, Segment(kind='text',text=text))
    parts.append(Segment(kind='dynamic',reference='bilibili:dynamic:'+event_id))
    # Stable semantic projection avoids duplicate events from changing counters.
    identity = {'id':event_id,'author_id':mid,'published':published,'type':row.get('type'),
                'segments':[part.model_dump() for part in parts]}
    return Event(account=account,event_id=event_id,kind='dynamic.created',sender_id=str(mid),
                 conversation_id='subscriptions',conversation_kind='feed',occurred_at_us=published*1000000,
                 observed_at_us=now_us,privacy='PERSONAL',origin=origin,segments=tuple(parts),
                 raw_sha256=digest(identity),raw_reference='bilibili:dynamic:'+event_id)
