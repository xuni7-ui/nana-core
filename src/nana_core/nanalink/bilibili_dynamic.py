"""Bounded Bilibili subscription observations, with no private memory writes.

The caller owns the explicitly authorized account reader and its original
budget. This normalizer does not itself persist private observations; the
existing consented-platform bridge performs authorization and source capture.
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
    # A forwarding author is not the original author. Preserve the relation
    # as opaque identifiers only; the nested original is not independently
    # authorized or promoted to an observation by this envelope.
    original = row.get('orig')
    parent_id = None
    if type(original) is dict:
        original_id = original.get('id_str')
        if type(original_id) is str and re.fullmatch(r'[1-9][0-9]{0,24}', original_id) and original_id != event_id:
            parent_id = original_id
            parts.append(Segment(kind='forwarded_dynamic',reference='bilibili:dynamic:'+original_id))
            original_modules = original.get('modules')
            original_author = original_modules.get('module_author') if type(original_modules) is dict else None
            original_mid = original_author.get('mid') if type(original_author) is dict else None
            if type(original_mid) is int and 0 < original_mid <= 2**63-1:
                parts.append(Segment(kind='forwarded_author',reference='bilibili:user:'+str(original_mid)))
    parts.append(Segment(kind='dynamic',reference='bilibili:dynamic:'+event_id))
    # Stable semantic projection avoids duplicate events from changing counters.
    identity = {'id':event_id,'author_id':mid,'published':published,'type':row.get('type'),
                'segments':[part.model_dump() for part in parts]}
    return Event(account=account,event_id=event_id,kind='dynamic.created',sender_id=str(mid),
                 conversation_id='subscriptions',conversation_kind='feed',parent_id=parent_id,occurred_at_us=published*1000000,
                 observed_at_us=now_us,privacy='PERSONAL',origin=origin,segments=tuple(parts),
                 raw_sha256=digest(identity),raw_reference='bilibili:dynamic:'+event_id)
