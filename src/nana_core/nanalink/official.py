"""QQ official v2 adapter using authenticated host sessions and one-shot HTTP.

AstrBot/botpy keep gateway/login ownership. Their higher-level send helpers may
retry, so this independent transport uses the documented REST routes once. No
third-party implementation or native component is copied. Native IDs stay opaque.
"""
import asyncio
import hashlib
import json
import re
import time
from aiohttp import ClientError
from collections import OrderedDict
from datetime import datetime
from .contracts import Account, Capability, Event, Segment
from .onebot import OneBotAdapter, decode, safe_endpoint
from .sdk import AdapterManifest
from ..contracts import CoreError

OPAQUE_ID = r'[A-Za-z0-9._:-]{1,128}'


class OfficialQQAdapter(OneBotAdapter):
    manifest = AdapterManifest(adapter_id='qq.official', version='1.0.0', platforms=('qq',),
                                license='Nana original; external AstrBot/botpy separately licensed')

    def __init__(self, account_id, *, bot_id, token, allow_send=False, endpoint='https://api.sgroup.qq.com',
                 realm='AUTHENTICATED_PLATFORM', capacity=32, timeout=5):
        if not re.fullmatch(OPAQUE_ID, bot_id):
            raise CoreError('QQ_OFFICIAL_BOT_ID_REQUIRED')
        safe_endpoint(endpoint, schemes=('https', 'http'))
        if endpoint != 'https://api.sgroup.qq.com' and realm != 'SYNTHETIC_LOOPBACK':
            raise CoreError('QQ_OFFICIAL_FIXED_API_REQUIRED')
        super().__init__(account_id, mode='http', endpoint=endpoint, token=token, allow_send=allow_send,
                         capacity=capacity, timeout=timeout)
        self.account = Account(platform='qq', account_id=str(account_id), adapter_id='qq.official')
        self.bot_id, self.realm = bot_id, realm
        self.cache, self.reply_ids = OrderedDict(), {}
        self.verified_token = None

    def _headers(self):
        value = self.token() if callable(self.token) else self.token
        if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in value):
            raise CoreError('QQ_OFFICIAL_TOKEN_UNAVAILABLE')
        return {'Authorization': 'QQBot ' + value, 'X-Union-Appid': self.account.account_id}

    async def _api(self, method, path, payload=None):
        if self.session is None or self.closed:
            raise CoreError('QQ_OFFICIAL_SESSION_UNAVAILABLE')
        if path != '/users/@me' and not re.fullmatch(r'/v2/(?:users|groups)/[A-Za-z0-9_-]{1,128}/messages', path):
            raise CoreError('QQ_OFFICIAL_ROUTE_DENIED')
        self.metrics['rpc'] += 1
        self.metrics['writes'] += method == 'POST'
        headers = self._headers()
        fingerprint = hashlib.sha256(headers['Authorization'].encode()).hexdigest()
        if method == 'GET':
            self.verified_token = None
        if method == 'POST':
            if fingerprint != self.verified_token:
                raise CoreError('QQ_OFFICIAL_CREDENTIAL_CHANGED')
            self.verified_token = None
        try:
            async with self.session.request(method, self.endpoint + path, json=payload,
                                            headers=headers, allow_redirects=False) as response:
                if response.status not in {200, 201, 202}:
                    raise CoreError('QQ_OFFICIAL_REJECTED_NO_RETRY')
                raw = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    raw.extend(chunk)
                    if len(raw) > 262144:
                        raise CoreError('ONEBOT_FRAME_BOUND')
                value = decode(bytes(raw))
                if path == "/users/@me" and value.get("id") == self.bot_id:
                    self.verified_token = fingerprint
                return value
        except (OSError, TimeoutError, ClientError):
            self.metrics['unknown'] += 1
            raise CoreError('QQ_OFFICIAL_COMPLETION_UNKNOWN_NO_RETRY') from None
        except CoreError:
            if method == 'POST':
                self.metrics['unknown'] += 1
            raise
        except asyncio.CancelledError:
            self.metrics['unknown'] += 1
            raise

    async def _account(self):
        value = await self._api('GET', '/users/@me')
        if value.get('id') != self.bot_id:
            self._health = self._health.model_copy(update={'login': 'REQUIRED', 'error': 'ACCOUNT_MISMATCH'})
            raise CoreError('QQ_OFFICIAL_ACCOUNT_MISMATCH')
        self._health = self._health.model_copy(update={'connection': 'CONNECTED', 'login': 'AUTHENTICATED',
                                                     'compatibility': 'QQ_OFFICIAL_V2', 'error': None})
        return {'user_id': self.account.account_id}

    def health(self):
        value = super().health()
        if value.connection in {'CONNECTED','DEGRADED'}:
            try:
                self._headers()  # Local host session snapshot, never a network/login call.
            except CoreError:
                return value.model_copy(update={'connection':'DEGRADED','login':'REQUIRED','error':'HOST_SESSION_EXPIRED'})
        return value

    def capabilities(self):
        ready = self.health().login == 'AUTHENTICATED'
        return (Capability(name='message.receive', available=ready),
                Capability(name='message.text.send.via_core', available=ready and self.allow_send),
                Capability(name='delivery.independent_readback', available=False, reason='C2C_GROUP_API_NOT_AVAILABLE'),
                Capability(name='media.reference', available=True),
                Capability(name='message.image.send.via_core', available=False, reason='ORIGINAL_MEDIA_ACTION_NOT_WIRED'),
                Capability(name='message.face.send.via_core', available=False, reason='ORIGINAL_MEDIA_ACTION_NOT_WIRED'),
                Capability(name='login.external_session', available=True),
                Capability(name='message.edit', available=False, reason='PLATFORM_UNSUPPORTED'))

    def offer(self, row):
        # Called only after the sidecar verifies the dedicated host ingress HMAC.
        if type(row) is not dict or str(row.get('application_id')) != self.account.account_id:
            raise CoreError('QQ_OFFICIAL_APPLICATION_MISMATCH')
        typ = row.get('type')
        if typ not in {'C2C_MESSAGE_CREATE', 'GROUP_AT_MESSAGE_CREATE', 'GROUP_MESSAGE_CREATE'}:
            return 'UNSUPPORTED'
        mid, data = row.get('id'), row.get('data')
        if type(data) is not dict:
            raise CoreError('QQ_OFFICIAL_EVENT_INVALID')
        mid = data.get('id') or mid
        kind = 'private' if typ == 'C2C_MESSAGE_CREATE' else 'group'
        author = data.get('author')
        sender = author.get('user_openid') if kind == 'private' and type(author) is dict else (
                 author.get('member_openid') if type(author) is dict else None)
        peer = sender if kind == 'private' else data.get('group_openid')
        if any(type(v) is not str or not re.fullmatch(OPAQUE_ID, v) for v in (mid, sender, peer)):
            raise CoreError('QQ_OFFICIAL_NATIVE_ID_INVALID')
        if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', v) for v in (sender, peer)):
            raise CoreError('QQ_OFFICIAL_PEER_INVALID')
        text = data.get('content', '')
        if type(text) is not str or not 1 <= len(text) <= 2048:
            raise CoreError('QQ_OFFICIAL_CONTENT_BOUND')
        ts = data.get('timestamp')
        try:
            if type(ts) is int and ts >= 0:
                occurred = ts * 1000000
            else:
                parsed = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    raise ValueError()
                occurred = int(parsed.timestamp() * 1000000)
                if occurred < 0:
                    raise ValueError()
        except (ValueError, AttributeError, TypeError):
            raise CoreError('QQ_OFFICIAL_EVENT_TIME_INVALID') from None
        raw = json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
        if len(raw) > 262144:
            raise CoreError('QQ_OFFICIAL_EVENT_BOUND')
        sha = hashlib.sha256(raw).hexdigest()
        event = Event(account=self.account, event_id=mid, message_id=mid, kind='message.created',
                sender_id=sender, conversation_id=peer, conversation_kind=kind,
                occurred_at_us=occurred, observed_at_us=time.time_ns() // 1000,
                privacy='PERSONAL', origin=self.realm, segments=(Segment(kind='text', text=text),),
                raw_sha256=sha, raw_reference='qq.official:' + mid)
        if mid in self.cache:
            if self.cache[mid][0] != sha:
                raise CoreError('QQ_OFFICIAL_EVENT_COLLISION')
            return 'DUPLICATE'
        try:
            self.events.put_nowait(event)
        except asyncio.QueueFull:
            self.metrics['backpressure'] += 1
            return 'BACKPRESSURE'
        # Native message content remains volatile; no second memory authority.
        native = {'message_id': mid, 'sender': {'user_id': sender}, 'message_type': kind,
                  'group_id': peer if kind == 'group' else None, 'target_id': peer,
                  'time': occurred // 1000000, 'message': [{'type': 'text', 'data': {'text': text}}]}
        self.cache[mid] = (sha, native)
        self.reply_ids[kind, peer] = mid
        while len(self.cache) > 256:
            old, (_, body) = self.cache.popitem(last=False)
            dest = body['message_type'], body['target_id']
            if self.reply_ids.get(dest) == old:
                del self.reply_ids[dest]
        self._health = self._health.model_copy(update={'receive': 'HEALTHY', 'last_event_us': event.observed_at_us})
        return 'QUEUED'

    async def rpc(self, action, params, **kwargs):
        if action == 'get_login_info' and not params:
            return await self._account()
        if self._health.login != 'AUTHENTICATED':
            raise CoreError('QQ_OFFICIAL_LOGIN_REQUIRED')
        if action == 'get_msg':
            value = self.cache.get(str(params.get('message_id')))
            if value is None:
                raise CoreError('QQ_OFFICIAL_MESSAGE_NOT_IN_VOLATILE_CAPTURE')
            return value[1]
        if action not in {'send_private_msg', 'send_group_msg'} or not self.allow_send:
            raise CoreError('QQ_OFFICIAL_SEND_NOT_AUTHORIZED')
        kind = 'private' if action == 'send_private_msg' else 'group'
        peer = params.get('user_id' if kind == 'private' else 'group_id')
        if type(peer) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', peer):
            raise CoreError('QQ_OFFICIAL_PEER_INVALID')
        message = params.get('message')
        if (type(message) is not list or len(message) != 1 or type(message[0]) is not dict
                or set(message[0]) != {'type', 'data'} or message[0]['type'] != 'text'
                or type(message[0]['data']) is not dict or set(message[0]['data']) != {'text'}
                or type(message[0]['data']['text']) is not str or not 1 <= len(message[0]['data']['text']) <= 2048):
            raise CoreError('QQ_OFFICIAL_TEXT_REQUIRED')
        text = message[0]['data']['text']
        payload = {'content': text, 'msg_type': 0}
        reply_id = self.reply_ids.get((kind, peer))
        if reply_id:
            payload.update(msg_id=reply_id, msg_seq=1)
        result = await self._api('POST', '/v2/' + ('users' if kind == 'private' else 'groups') + '/' + peer + '/messages', payload)
        mid = result.get('id')
        if type(mid) is not str or not re.fullmatch(OPAQUE_ID, mid):
            self.metrics['unknown'] += 1
            raise CoreError('QQ_OFFICIAL_ACK_UNKNOWN_NO_RETRY')
        # Never create a fake get_msg row from this ACK. Original Verify remains
        # INCONCLUSIVE for official C2C/group scenes without a readback API.
        return {'message_id': mid, 'platform_ack': True}
