"""Unprivileged OneBot compatibility sidecar for the existing Core HTTP port.

Per-account loopback listeners isolate tokens and sessions. No raw message disk
cache, no native injection, no Core DB, no model, no automatic social retry.
"""
import asyncio
import hashlib
import hmac
import re
import time
from typing import Literal
from pydantic import Field, model_validator
from ..contracts import DTO, CoreError
from .contracts import Outcome, OperationReceipt
from .onebot import OneBotAdapter, decode
from .transport import EventTransport


class ForwardRoute(DTO):
    channel_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    sender_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')
    conversation_kind: Literal['private', 'group']
    conversation_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')
    # Host grants metadata forwarding only. Existing Core authorizes content
    # reads and any eventual effect separately; this does not mint consent.


class SessionConfig(DTO):
    alias: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,31}$')
    account_id: str = Field(pattern=r'^[0-9]{1,20}$')
    backend: Literal['onebot', 'official'] = 'onebot'
    native_bot_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    ingress_secret_ref: str | None = Field(default=None, pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    mode: Literal['websocket', 'reverse-websocket', 'http']
    endpoint: str | None = Field(default=None, max_length=256, repr=False)
    port: int = Field(ge=1024, le=65535)
    upstream_secret_ref: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    core_api_secret_ref: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    forward_secret_ref: str | None = Field(default=None, pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    core_origin: str | None = Field(default=None, max_length=256, repr=False)
    allow_send: bool = False
    routes: tuple[ForwardRoute, ...] = Field(default=(), max_length=16)

    @model_validator(mode='after')
    def endpoints(self):
        from .onebot import safe_endpoint
        if self.backend == 'official':
            if self.mode != 'http' or not self.native_bot_id or not self.ingress_secret_ref:
                raise ValueError('official session needs bot identity, HTTP and a separate ingress credential')
            if self.ingress_secret_ref in {self.upstream_secret_ref, self.core_api_secret_ref}:
                raise ValueError('official ingress credential must be isolated')
            if self.endpoint not in {None, 'https://api.sgroup.qq.com'}:
                raise ValueError('fixed official API required')
        elif self.mode != 'reverse-websocket':
            safe_endpoint(self.endpoint, schemes=('ws', 'wss') if self.mode == 'websocket' else ('http', 'https'))
        if self.routes:
            if not self.forward_secret_ref or not self.core_origin:
                raise ValueError('forward destination and credential reference required')
            safe_endpoint(self.core_origin, schemes=('http', 'https'))
        if self.backend == 'onebot' and any(not re.fullmatch(r'[0-9]{1,20}', v) for r in self.routes for v in (r.sender_id, r.conversation_id)):
            raise ValueError('OneBot numeric route IDs required')
        coords = [(r.sender_id, r.conversation_kind, r.conversation_id) for r in self.routes]
        if len(set(coords)) != len(coords):
            raise ValueError('duplicate route')
        if self.upstream_secret_ref == self.core_api_secret_ref:
            raise ValueError('upstream and Core API tokens must be isolated')
        return self


class SidecarConfig(DTO):
    schema_version: Literal[1] = 1
    sessions: tuple[SessionConfig, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode='after')
    def unique_sessions(self):
        if len({(s.backend, s.account_id) for s in self.sessions}) != len(self.sessions):
            raise ValueError('duplicate backend account')
        for field in ('alias', 'port', 'core_api_secret_ref'):
            if len({getattr(s, field) for s in self.sessions}) != len(self.sessions):
                raise ValueError('each account needs isolated alias, port and credential')
        return self


class OneBotSidecar:
    def __init__(self, config, resolver, *, management_state=None, catalogs=None):
        self.config, self.resolver = config, resolver
        self.adapters = {}
        self.official_sessions = {}
        def build(c):
            if c.backend == 'official':
                from .official import OfficialQQAdapter
                return OfficialQQAdapter(c.account_id, bot_id=c.native_bot_id,
                    token=lambda c=c: self.official_token(c), allow_send=c.allow_send)
            return OneBotAdapter(c.account_id, mode=c.mode, endpoint=c.endpoint,
                    token=lambda c=c: self.secret(c.upstream_secret_ref), allow_send=c.allow_send)
        self.adapters = {c.alias:build(c) for c in config.sessions}
        from .management import AdapterManagement
        approved = catalogs if catalogs is not None else {
            c.alias:{self.adapters[c.alias].manifest.version:lambda c=c:build(c)} for c in config.sessions}
        self.management = AdapterManagement(self.adapters, approved, state_path=management_state)
        self.adapters = {c.alias:self.management.adapter(c.alias) for c in config.sessions}
        self.transport = EventTransport(capacity=64, per_account=16, dedupe=512)
        self.tasks, self.runners = [], []
        self.last = {}
        self.stopped = asyncio.Event()

    def official_token(self, config):
        value = self.official_sessions.get(config.alias)
        if value is None or value[1] <= time.time():
            raise CoreError('QQ_OFFICIAL_HOST_SESSION_EXPIRED')
        return value[0]

    def secret(self, reference):
        if not self.resolver.available(reference):
            raise CoreError('NANALINK_CREDENTIAL_UNAVAILABLE')
        credential = self.resolver.resolve(reference)
        try:
            value = credential.reveal_for_header()
            if not isinstance(value, str) or len(value) < 24 or any(c in value for c in '\r\n'):
                raise CoreError('NANALINK_CREDENTIAL_INVALID')
            return value
        finally:
            credential.clear()

    def authenticated(self, request, reference):
        try:
            return hmac.compare_digest(request.headers.get('Authorization', ''), 'Bearer ' + self.secret(reference))
        except CoreError:
            return False

    def app(self, config):
        from aiohttp import web
        from .management import AdapterHandle
        adapter = AdapterHandle(self, config.alias)

        @web.middleware
        async def errors(request, handler):
            try:
                return await handler(request)
            except CoreError as exc:
                # All post-dispatch uncertainty is an HTTP error; the existing
                # Core retains its original UNKNOWN and performs no auto-retry.
                return web.json_response({'status': 'failed', 'retcode': 1500,
                    'error': exc.code, 'data': {}, 'no_retry': True}, status=502)
            except web.HTTPException:
                raise
            except (ValueError, TypeError, KeyError):
                return web.json_response({'error': 'NANALINK_INVALID_REQUEST'}, status=400)
            except Exception:
                return web.json_response({'error': 'NANALINK_COMPLETION_UNKNOWN_NO_RETRY'}, status=502)

        app = web.Application(client_max_size=262144, middlewares=[errors])

        async def rpc(request):
            if not self.authenticated(request, config.core_api_secret_ref):
                raise web.HTTPForbidden()
            action = request.match_info['action']
            # Only actions used by the EXISTING QQ port can enter this facade.
            if action not in {'get_login_info', 'get_msg', 'send_private_msg', 'send_group_msg'}:
                raise web.HTTPNotFound()
            if not self.management.enabled(config.alias):
                raise CoreError('NANALINK_ADAPTER_DISABLED')
            params = decode(await request.read())
            if action == 'get_login_info' and params:
                raise web.HTTPBadRequest()
            if action == 'get_msg' and (set(params) != {'message_id'} or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}' if config.backend=='official' else r'-?[0-9]{1,20}', str(params['message_id']))):
                raise web.HTTPBadRequest()
            if action.startswith('send_'):
                group = action == 'send_group_msg'
                allowed = {'group_id' if group else 'user_id', 'message', 'echo'}
                if set(params) - allowed or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}' if config.backend=='official' else r'[0-9]{1,20}', str(params.get('group_id' if group else 'user_id'))):
                    raise web.HTTPBadRequest()
                message = params.get('message')
                if (type(message) is not list or len(message) not in (1, 2) or type(message[0]) is not dict
                        or set(message[0]) != {'type', 'data'} or message[0]['type'] != 'text'
                        or type(message[0]['data']) is not dict or set(message[0]['data']) != {'text'}
                        or type(message[0]['data']['text']) is not str or not 1 <= len(message[0]['data']['text']) <= 2048):
                    raise web.HTTPBadRequest()
                if len(message) == 2:
                    import base64, binascii
                    image = message[1]
                    if (config.backend != 'onebot' or type(image) is not dict or set(image) != {'type', 'data'}
                            or image['type'] != 'image' or type(image['data']) is not dict
                            or set(image['data']) != {'file'} or type(image['data']['file']) is not str
                            or not image['data']['file'].startswith('base64://')
                            or len(image['data']['file']) > 10933):
                        raise web.HTTPBadRequest()
                    try:
                        content = base64.b64decode(image['data']['file'][9:], validate=True)
                    except (ValueError, binascii.Error):
                        raise web.HTTPBadRequest() from None
                    if not 1 <= len(content) <= 8192:
                        raise web.HTTPBadRequest()
            result = await adapter.rpc(action, params)
            return web.json_response({'status': 'ok', 'retcode': 0, 'data': result})

        async def reverse(request):
            if not self.authenticated(request, config.upstream_secret_ref) or request.headers.get('X-Self-ID') != config.account_id:
                raise web.HTTPForbidden()
            if config.mode != 'reverse-websocket' or adapter.ws is not None and not adapter.ws.closed:
                raise web.HTTPConflict()
            ws = web.WebSocketResponse(heartbeat=20, max_msg_size=262144)
            await ws.prepare(request)
            await adapter.attach(ws)
            return ws

        async def events(request):
            if config.backend != 'onebot':
                raise web.HTTPNotFound()
            raw = await request.read()
            # OneBot v11 HTTP-POST signature is SHA1; Nana Core metadata handoff
            # remains the existing SHA256 protocol. Neither is a user role.
            signature = request.headers.get('X-Signature', '')
            expected = 'sha1=' + hmac.new(self.secret(config.upstream_secret_ref).encode(), raw, hashlib.sha1).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise web.HTTPForbidden()
            state = adapter.offer(decode(raw)) if self.management.enabled(config.alias) else 'CANCELLED'
            return web.json_response({'state': state, 'delivery_confirmed': False}, status=429 if state == 'BACKPRESSURE' else 202)

        async def official_events(request):
            if config.backend != 'official':
                raise web.HTTPNotFound()
            raw = await request.read()
            expected = 'sha256=' + hmac.new(self.secret(config.ingress_secret_ref).encode(), raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(request.headers.get('X-Nana-Signature', ''), expected):
                raise web.HTTPForbidden()
            state = adapter.offer(decode(raw)) if self.management.enabled(config.alias) else 'CANCELLED'
            return web.json_response({'state': state, 'external_delivery': False}, status=429 if state=='BACKPRESSURE' else 202)

        async def official_session(request):
            if config.backend != 'official':
                raise web.HTTPNotFound()
            raw = await request.read()
            expected = 'sha256=' + hmac.new(self.secret(config.ingress_secret_ref).encode(), raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(request.headers.get('X-Nana-Signature', ''), expected):
                raise web.HTTPForbidden()
            body = decode(raw)
            token, expires = body.get('access_token'), body.get('expires_at')
            if (set(body) != {'application_id', 'bot_id', 'access_token', 'expires_at'}
                    or body['application_id'] != config.account_id or body['bot_id'] != config.native_bot_id
                    or type(token) is not str or not 24 <= len(token) <= 4096
                    or any(ord(c) < 33 or ord(c) > 126 for c in token)
                    or type(expires) is not int or not time.time() < expires <= time.time() + 7200):
                raise web.HTTPBadRequest()
            previous = self.official_sessions.get(config.alias)
            if previous is not None and (expires < previous[1] or expires == previous[1] and token != previous[0]):
                raise web.HTTPConflict()
            self.official_sessions[config.alias] = (token, expires)
            return web.json_response({'state': 'HOST_SESSION_ACCEPTED', 'external_delivery': False})

        async def status(request):
            if not self.authenticated(request, config.core_api_secret_ref):
                raise web.HTTPForbidden()
            return web.json_response({'schema_version': 1, 'platform': 'qq',
                'adapter_id': adapter.manifest.adapter_id, 'account_key': adapter.account.key, 'version': adapter.manifest.version,
                'health': adapter.health().model_dump(), 'capabilities': [c.model_dump() for c in adapter.capabilities()],
                'pending_events': adapter.events.qsize(), 'metrics': dict(adapter.metrics),
                'last_forward': self.last.get(config.alias), 'raw_body_persisted': False,
                'external_delivery': False})

        async def manage(request):
            if not self.authenticated(request, config.core_api_secret_ref):
                raise web.HTTPForbidden()
            if request.method == 'GET':
                return web.json_response(self.management.view(config.alias))
            body = decode(await request.read())
            if (set(body) != {'operation','version','revision'} or type(body['revision']) is not int
                    or type(body['operation']) is not str or body['version'] is not None and type(body['version']) is not str):
                raise web.HTTPBadRequest()
            # Do not silently discard accepted input at an offline version switch.
            if body['operation'] in {'INSTALL','UPGRADE','ROLLBACK','UNINSTALL'} and (
                    not adapter.events.empty() or self.transport.counts.get(adapter.account.key,0)):
                raise CoreError('NANALINK_DRAIN_INPUT_BEFORE_PACKAGE_CHANGE')
            result = await self.management.command(config.alias,body['operation'],body['version'],body['revision'])
            self.adapters[config.alias] = self.management.adapter(config.alias)
            if body['operation'] == 'DISABLE' and not self.management.enabled(config.alias):
                cancelled = len(self.transport.cancel_account(adapter.account.key))
                while not adapter.events.empty():
                    adapter.events.get_nowait()
                    cancelled += 1
                result['cancelled_queued_events'] = cancelled
            return web.json_response(result)

        app.router.add_get('/nanalink/manage', manage)
        app.router.add_post('/nanalink/manage', manage)
        app.router.add_post('/{action:get_login_info|get_msg|send_private_msg|send_group_msg}', rpc)
        app.router.add_get('/reversews', reverse)
        app.router.add_post('/events', events)
        app.router.add_post('/official/events', official_events)
        app.router.add_post('/official/session', official_session)
        app.router.add_get('/nanalink/status', status)
        return app

    async def _maintain(self, config):
        while not self.stopped.is_set():
            adapter = self.adapters[config.alias]
            if self.management.enabled(config.alias) and adapter.session is None:
                try:
                    await adapter.connect()
                except Exception:
                    self.last[config.alias] = {"state": "CONNECT_FAILED", "no_retry": True}
            await asyncio.sleep(2)

    async def _receive(self, config):
        while not self.stopped.is_set():
            if not self.management.enabled(config.alias):
                await asyncio.sleep(0.1)
                continue
            adapter = self.adapters[config.alias]
            try:
                event = await asyncio.wait_for(adapter.receive(), 1)
            except TimeoutError:
                continue
            if not self.management.enabled(config.alias):
                self.last[config.alias] = {'state':'CANCELLED_BEFORE_CORE_FORWARD','no_retry':True}
                continue
            # Forward only exact host-bound source metadata. Unbound groups or
            # peers never spend a Core cognition call merely by arriving.
            matches = [r for r in config.routes if (r.sender_id, r.conversation_kind, r.conversation_id)
                       == (event.sender_id, event.conversation_kind, event.conversation_id)]
            if event.kind != 'message.created' or len(matches) != 1:
                continue
            state = self.transport.offer(event)
            if state == 'BACKPRESSURE':
                self.last[config.alias] = {'state': 'BACKPRESSURE', 'no_retry': True}
                # Bounded backpressure is visible. Never hide loss as delivery.

    async def _forward(self, event):
        from ..life.platform_forward import forward
        config = next(c for c in self.config.sessions if self.adapters[c.alias].account == event.account)
        if not self.management.enabled(config.alias):
            self.last[config.alias] = {'state': 'CANCELLED_BEFORE_CORE_FORWARD', 'no_retry': True}
            return OperationReceipt(operation_id=event.key, outcome=Outcome.CANCELLED,
                                    reason='ADAPTER_DISABLED_BEFORE_CORE_FORWARD')
        route = next(r for r in config.routes if (r.sender_id, r.conversation_kind, r.conversation_id)
                     == (event.sender_id, event.conversation_kind, event.conversation_id))
        result = await asyncio.to_thread(forward, config.core_origin, 'qq', route.channel_id,
                                         event.message_id, self.resolver, config.forward_secret_ref, backend=config.backend)
        self.last[config.alias] = result
        return OperationReceipt(operation_id=event.key, outcome=Outcome.UNKNOWN,
                                reason='CORE_METADATA_QUEUED_NOT_DELIVERY' if result['state'] in
                                {'QUEUED_NOT_JUDGED', 'ALREADY_QUEUED_NOT_DELIVERED'} else 'CORE_METADATA_ACK_UNKNOWN_NO_RETRY')

    async def _drain(self):
        while not self.stopped.is_set():
            if self.transport.size:
                await self.transport.drain_once(self._forward)
            else:
                await asyncio.sleep(0.05)

    async def start(self):
        from aiohttp import web
        try:
            for config in self.config.sessions:
                runner = web.AppRunner(self.app(config), access_log=None, shutdown_timeout=2)
                await runner.setup()
                self.runners.append(runner)
                await web.TCPSite(runner, '127.0.0.1', config.port).start()
                self.tasks.append(asyncio.create_task(self._receive(config)))
                self.tasks.append(asyncio.create_task(self._maintain(config)))
            self.tasks.append(asyncio.create_task(self._drain()))
        except BaseException:
            await self.close()
            raise

    async def close(self):
        self.official_sessions.clear()
        self.stopped.set()
        self.transport.close()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await asyncio.gather(*(a.shutdown() for a in self.adapters.values()), return_exceptions=True)
        for runner in self.runners:
            await runner.cleanup()
