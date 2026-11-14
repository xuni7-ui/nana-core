"""Independent OneBot v11 HTTP/WS/reverse-WS connector, no native addon.

Only connection recovery is retried. An RPC that might have left the process
becomes UNKNOWN on timeout/disconnect and is NEVER replayed after reconnect.
"""
import asyncio
import hashlib
import json
import re
import time
from collections import OrderedDict
from urllib.parse import urlsplit
from .contracts import Account, Capability, Event, OperationReceipt, Outcome, Segment, SessionHealth
from .sdk import AdapterManifest
from ..contracts import CoreError
from ..continuity.privacy import _json_object

ACTIONS = frozenset({'get_login_info', 'get_msg', 'send_private_msg', 'send_group_msg', 'get_version_info', 'get_status'})
WRITES = frozenset({'send_private_msg', 'send_group_msg'})


def safe_endpoint(value, *, schemes=('https', 'wss', 'http', 'ws')):
    try:
        u = urlsplit(value)
        if (u.scheme not in schemes or not u.hostname or u.username is not None or u.password is not None
                or u.query or u.fragment or any(c in value for c in '\r\n\\')
                or (u.scheme in {'http', 'ws'} and u.hostname not in {'127.0.0.1', '::1'})
                or u.port is not None and not 1 <= u.port <= 65535):
            raise ValueError()
        return value
    except (ValueError, TypeError):
        raise CoreError('NANALINK_SAFE_ENDPOINT_REQUIRED') from None


def decode(raw):
    if len(raw.encode() if isinstance(raw, str) else raw) > 262144:
        raise CoreError('ONEBOT_FRAME_BOUND')
    try:
        value = json.loads(raw, object_pairs_hook=_json_object)
        if type(value) is not dict:
            raise ValueError()
        return value
    except (ValueError, UnicodeError):
        raise CoreError('ONEBOT_INVALID_FRAME') from None


def normalize(account, row, *, origin='AUTHENTICATED_PLATFORM', now_us=None):
    """No nickname merging, string CQ execution, URL fetch or silent truncation."""
    if str(row.get('self_id')) != account.account_id:
        raise CoreError('ONEBOT_ACCOUNT_BINDING_CHANGED')
    raw = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > 262144:
        raise CoreError('ONEBOT_FRAME_BOUND')
    post = row.get('post_type')
    if post == 'meta_event':
        return None
    kind = row.get('message_type')
    sender = row.get('user_id')
    if post == 'message' and kind in {'private', 'group'}:
        mid = str(row.get('message_id'))
        if not re.fullmatch(r'-?[0-9]{1,20}', mid):
            raise CoreError('ONEBOT_MESSAGE_ID_INVALID')
        event_kind, event_id = 'message.created', mid
    elif post == 'notice':
        notice = str(row.get('notice_type', 'unknown'))
        if not re.fullmatch(r'[a-z_]{1,64}', notice):
            raise CoreError('ONEBOT_NOTICE_INVALID')
        event_kind = {'group_recall': 'message.recalled', 'friend_recall': 'message.recalled'}.get(notice, 'notice.' + notice)
        # Stable raw digest dedupes notices with no platform event ID. Time and
        # operator remain in raw digest; two different recalls never collapse.
        event_id = hashlib.sha256(raw).hexdigest()
        mid = str(row['message_id']) if row.get('message_id') is not None else None
        kind = 'group' if row.get('group_id') is not None else 'private'
    else:
        return None
    peer = row.get('group_id') if kind == 'group' else sender
    if not re.fullmatch(r'[0-9]{1,20}', str(peer)) or not re.fullmatch(r'[0-9]{1,20}', str(sender)):
        raise CoreError('ONEBOT_PEER_METADATA_REQUIRED')
    ts = row.get('time')
    if type(ts) is not int or ts < 0:
        raise CoreError('ONEBOT_EVENT_TIME_REQUIRED')
    segments, parent = [], None
    message = row.get('message', [])
    if isinstance(message, str):
        # Keep the original CQ string opaque. It is not authoritative Core text.
        if len(message) > 2048:
            raise CoreError('ONEBOT_TEXT_BOUND')
        segments.append(Segment(kind='text', text=message))
    elif type(message) is list and len(message) <= 64:
        for part in message:
            if type(part) is not dict or type(part.get('data')) is not dict:
                raise CoreError('ONEBOT_SEGMENT_INVALID')
            typ, data = part.get('type'), part['data']
            if not isinstance(typ, str) or not re.fullmatch(r'[a-z][a-z0-9._-]{0,63}', typ):
                raise CoreError('ONEBOT_SEGMENT_INVALID')
            if typ == 'text':
                segments.append(Segment(kind=typ, text=data.get('text')))
            else:
                ref = data.get('id', data.get('file', data.get('url')))
                segments.append(Segment(kind=typ, reference=str(ref)[:512] if ref is not None else None))
                if typ == 'reply':
                    parent = str(data.get('id', ''))[:128]
    else:
        raise CoreError('ONEBOT_SEGMENT_BOUND')
    return Event(account=account, event_id=event_id, kind=event_kind, conversation_id=str(peer),
                 conversation_kind=kind, sender_id=str(sender), message_id=mid, parent_id=parent,
                 occurred_at_us=ts * 1000000, observed_at_us=now_us if now_us is not None else time.time_ns() // 1000,
                 privacy='PERSONAL', origin=origin, segments=tuple(segments),
                 raw_sha256=hashlib.sha256(raw).hexdigest(), raw_reference='onebot:' + str(mid or event_id))


class OneBotAdapter:
    manifest = AdapterManifest(adapter_id='qq.onebot', version='1.0.0', platforms=('qq',), license='Nana original; external service separately licensed')

    def __init__(self, account_id, *, mode='websocket', endpoint=None, token=None, allow_send=False,
                 capacity=32, timeout=5):
        if mode not in {'websocket', 'reverse-websocket', 'http'} or not re.fullmatch(r'[0-9]{1,20}', str(account_id)):
            raise CoreError('ONEBOT_CONFIGURATION_INVALID')
        if not 1 <= capacity <= 256 or not 0.1 <= timeout <= 15:
            raise ValueError('connector bounds')
        if mode != 'reverse-websocket':
            safe_endpoint(endpoint, schemes=('ws', 'wss') if mode == 'websocket' else ('https', 'http'))
        self.account = Account(platform='qq', account_id=str(account_id), adapter_id='qq.onebot')
        self.mode, self.endpoint, self.token, self.allow_send = mode, endpoint, token, allow_send
        self.timeout = timeout
        self.events = asyncio.Queue(capacity)
        self.pending, self.recent = {}, OrderedDict()
        self._health = SessionHealth()
        self.session = self.ws = self.reader = self.recovery = None
        self.closed = False
        self.echo = 0
        self.metrics = dict(frames=0, duplicates=0, backpressure=0, rpc=0, unknown=0, writes=0)

    def __repr__(self):
        return '<OneBotAdapter account-bound; credentials redacted>'

    def _headers(self):
        token = self.token() if callable(self.token) else self.token
        if not token:
            return {}
        if not isinstance(token, str) or any(c in token for c in '\r\n'):
            raise CoreError('ONEBOT_CREDENTIAL_INVALID')
        return {'Authorization': 'Bearer ' + token}

    def health(self):
        value = self._health
        # A quiet conversation is not proof of a failed receive path. Heartbeat
        # staleness is reported only after a heartbeat was actually observed.
        if value.last_heartbeat_us and time.time_ns() // 1000 - value.last_heartbeat_us > 120000000:
            value = value.model_copy(update={'receive': 'STALE'})
        return value

    def capabilities(self):
        ready = self._health.login == 'AUTHENTICATED'
        return (Capability(name='message.receive', available=ready),
                Capability(name='message.text.send.via_core', available=ready and self.allow_send,
                           reason='' if self.allow_send else 'HOST_SEND_DISABLED'),
                Capability(name='message.readback', available=ready),
                Capability(name='media.reference', available=True),
                Capability(name='login.qr', available=False, reason='EXTERNAL_CLIENT_LOGIN'),
                Capability(name='message.edit', available=False, reason='NOT_IN_MINIMUM_PROTOCOL'))

    async def connect(self):
        import aiohttp
        if self.session is not None:
            return
        self.closed = False
        self._health = self._health.model_copy(update={'connection': 'CONNECTING'})
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout), trust_env=False)
        try:
            if self.mode == 'websocket':
                await self._open_ws()
            elif self.mode == 'http':
                await self._account()
            # Reverse mode waits for an authenticated externally initiated peer.
        except BaseException:
            await self.disconnect()
            raise

    async def _account(self):
        row = await self.rpc('get_login_info', {}, _identity_probe=True)
        if str(row.get('user_id')) != self.account.account_id:
            self._health = self._health.model_copy(update={'login': 'REQUIRED', 'error': 'ACCOUNT_MISMATCH'})
            raise CoreError('ONEBOT_ACCOUNT_BINDING_CHANGED')
        self._health = self._health.model_copy(update={'connection': 'CONNECTED', 'login': 'AUTHENTICATED',
                                                      'compatibility': 'ONEBOT11_MINIMUM', 'error': None})

    async def _open_ws(self):
        self.ws = await self.session.ws_connect(self.endpoint, headers=self._headers(), heartbeat=20,
                                               max_msg_size=262144, autoping=True)
        self.reader = asyncio.create_task(self._read(self.ws))
        try:
            await self._account()
        except BaseException:
            await self.ws.close()
            raise

    async def attach(self, ws):
        """The server must authenticate token + X-Self-ID BEFORE invoking this."""
        if self.mode != 'reverse-websocket' or self.closed or self.ws is not None and not self.ws.closed:
            raise CoreError('ONEBOT_REVERSE_SESSION_CONFLICT')
        self.ws = ws
        self.reader = asyncio.create_task(self._read(ws))
        try:
            await self._account()
            await self.reader
        finally:
            await ws.close()

    async def _read(self, ws):
        import aiohttp
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    value = decode(msg.data)
                    self.metrics['frames'] += 1
                    if 'echo' in value:
                        future = self.pending.get(str(value['echo']))
                        if future and not future.done():
                            future.set_result(value)
                    else:
                        self.offer(value)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break
        except Exception:
            self._health = self._health.model_copy(update={'error': 'INVALID_OR_UNBOUND_EVENT'})
        finally:
            if self.ws is ws:
                self._health = self._health.model_copy(update={'connection': 'DISCONNECTED', 'login': 'UNKNOWN'})
                for future in tuple(self.pending.values()):
                    if not future.done():
                        future.set_exception(CoreError('ONEBOT_COMPLETION_UNKNOWN_NO_RETRY'))
                if not self.closed and self.mode == 'websocket' and self.recovery is None:
                    self.recovery = asyncio.create_task(self._recover())

    async def _recover(self):
        delay = 0.5
        try:
            while not self.closed:
                await asyncio.sleep(delay)
                try:
                    self._health = self._health.model_copy(update={'connection': 'CONNECTING', 'reconnects': self._health.reconnects + 1})
                    await self._open_ws()
                    return
                except Exception:
                    delay = min(delay * 2, 30)
        finally:
            self.recovery = None

    def offer(self, row):
        if str(row.get('self_id')) != self.account.account_id:
            raise CoreError('ONEBOT_ACCOUNT_BINDING_CHANGED')
        if row.get('post_type') == 'meta_event':
            if row.get('meta_event_type') == 'heartbeat':
                self._health = self._health.model_copy(update={'last_heartbeat_us': time.time_ns() // 1000})
                return 'HEARTBEAT'
            return 'META_EVENT'
        event = normalize(self.account, row)
        if event is None:
            return 'UNSUPPORTED'
        if event.key in self.recent:
            if self.recent[event.key] != event.raw_sha256:
                raise CoreError('ONEBOT_EVENT_ID_COLLISION')
            self.metrics['duplicates'] += 1
            return 'DUPLICATE'
        try:
            self.events.put_nowait(event)
        except asyncio.QueueFull:
            self.metrics['backpressure'] += 1
            self._health = self._health.model_copy(update={'receive': 'BACKPRESSURE'})
            return 'BACKPRESSURE'
        self.recent[event.key] = event.raw_sha256
        while len(self.recent) > 512:
            self.recent.popitem(last=False)
        self._health = self._health.model_copy(update={'receive': 'HEALTHY', 'last_event_us': event.observed_at_us})
        return 'QUEUED'

    async def receive(self):
        return await self.events.get()

    async def rpc(self, action, params, *, _identity_probe=False):
        if action not in ACTIONS or type(params) is not dict:
            raise CoreError('ONEBOT_OPERATION_DENIED')
        if action in WRITES and not self.allow_send:
            raise CoreError('ONEBOT_HOST_SEND_DISABLED')
        if action != 'get_login_info' and self._health.login != 'AUTHENTICATED':
            raise CoreError('ONEBOT_ACCOUNT_NOT_VERIFIED')
        if self.closed or self.session is None or len(self.pending) >= 16:
            raise CoreError('ONEBOT_SESSION_UNAVAILABLE')
        if len(json.dumps(params, allow_nan=False).encode()) > 16384:
            raise CoreError('ONEBOT_REQUEST_BOUND')
        self.echo += 1
        echo = str(self.echo)
        self.metrics['rpc'] += 1
        self.metrics['writes'] += action in WRITES
        try:
            if self.mode == 'http':
                async with self.session.post(self.endpoint.rstrip('/') + '/' + action, json=params,
                                             headers=self._headers(), allow_redirects=False) as response:
                    if response.status != 200:
                        raise CoreError('ONEBOT_HTTP_REJECTED_NO_RETRY')
                    raw = await response.content.read(262145)
                    value = decode(raw)
            else:
                if self.ws is None or self.ws.closed:
                    raise CoreError('ONEBOT_SESSION_UNAVAILABLE')
                future = asyncio.get_running_loop().create_future()
                self.pending[echo] = future
                # All echoes live at the envelope level per OneBot v11.
                await self.ws.send_json({'action': action, 'params': params, 'echo': echo})
                value = await asyncio.wait_for(future, self.timeout)
        except (TimeoutError, OSError):
            self.metrics['unknown'] += 1
            raise CoreError('ONEBOT_COMPLETION_UNKNOWN_NO_RETRY') from None
        finally:
            self.pending.pop(echo, None)
        if value.get('status') != 'ok' or type(value.get('retcode')) is not int or value['retcode'] != 0:
            raise CoreError('ONEBOT_REJECTED_NO_RETRY')
        if type(value.get('data')) is not dict:
            raise CoreError('ONEBOT_MALFORMED_RESPONSE_NO_RETRY')
        return value['data']

    async def send(self, invocation):
        # The connector is intentionally not an alternative social action path.
        # Core ports below expose this SDK method with original Kernel proof.
        return OperationReceipt(operation_id=getattr(invocation, 'action_id', 'unbound'),
                                outcome=Outcome.UNSUPPORTED, reason='ORIGINAL_KERNEL_PORT_REQUIRED')

    async def disconnect(self):
        self.closed = True
        current = asyncio.current_task()
        tasks = [t for t in (self.recovery, self.reader) if t and t is not current]
        for task in tasks:
            task.cancel()
        if self.ws is not None:
            await self.ws.close()
        await asyncio.gather(*tasks, return_exceptions=True)
        if self.session is not None:
            await self.session.close()
        self.session = self.ws = self.reader = self.recovery = None
        self._health = self._health.model_copy(update={'connection': 'DISCONNECTED', 'login': 'UNKNOWN'})

    async def shutdown(self):
        await self.disconnect()
