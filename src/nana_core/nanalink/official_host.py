"""Opt-in authenticated host handoff, no bot/agent/send or credential persistence.

AstrBot integration supplies its existing botpy token object and raw gateway
message to this independent public-interface shim. No high-level send helper is
used. Host owns token refresh and exclusive routing; HTTP is never retried.
"""
import hashlib
import hmac
import json
import time
from .onebot import safe_endpoint
from ..contracts import CoreError


def gateway_message(application_id, raw):
    """Whitelist fields from botpy C2C/Group objects, never serialize a session."""
    group = getattr(raw, 'group_openid', None)
    author = getattr(raw, 'author', None)
    field = 'member_openid' if group else 'user_openid'
    sender = getattr(author, field, None)
    data = {'id': getattr(raw, 'id', None), 'content': getattr(raw, 'content', ''),
            'timestamp': getattr(raw, 'timestamp', None), 'author': {field: sender}}
    if group:
        data['group_openid'] = group
    # datetime objects are deliberately not converted by repr(). botpy contract
    # provides an ISO string; incompatible versions fail closed at the sidecar.
    return {'application_id': application_id, 'type': 'GROUP_AT_MESSAGE_CREATE' if group else 'C2C_MESSAGE_CREATE',
            'data': data}


class OfficialHostBridge:
    def __init__(self, origin, application_id, bot_id, signing_key, *, routes, enabled=False, read_authorized=False):
        safe_endpoint(origin, schemes=('https', 'http'))
        from urllib.parse import urlsplit
        url = urlsplit(origin)
        if url.path not in {'', '/'} or len(routes) > 16:
            raise ValueError('origin/routes bound')
        self.origin, self.application_id, self.bot_id = origin.rstrip('/'), application_id, bot_id
        self.signing_key, self.routes = signing_key, frozenset(routes)
        self.enabled, self.read_authorized = enabled, read_authorized

    async def _post(self, session, path, body):
        raw = json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        if len(raw) > 262144:
            raise CoreError('QQ_OFFICIAL_HOST_PAYLOAD_BOUND')
        key = self.signing_key() if callable(self.signing_key) else self.signing_key
        if not isinstance(key, str) or len(key) < 24:
            raise CoreError('QQ_OFFICIAL_HOST_CREDENTIAL_REQUIRED')
        signature = 'sha256=' + hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()
        async with session.post(self.origin + path, data=raw, headers={
            'Content-Type': 'application/json', 'X-Nana-Signature': signature}, allow_redirects=False, timeout=5) as reply:
            if reply.status not in {200, 202}:
                raise CoreError('QQ_OFFICIAL_HOST_HANDOFF_NOT_CONFIRMED_NO_RETRY')
            return await reply.content.read(4097)

    def matches(self, row):
        data = row.get('data') or {}
        group = data.get('group_openid')
        author = data.get('author') or {}
        sender = author.get('member_openid' if group else 'user_openid')
        return (self.enabled and self.read_authorized and row.get('application_id') == self.application_id
                and (sender, 'group' if group else 'private', group or sender) in self.routes)

    async def forward(self, session, row, *, token, expires_at, stop_legacy):
        if not self.matches(row):
            return 'NOT_SELECTED'
        # Once selected, fail/UNKNOWN must not fall through to a second responder.
        stop_legacy()
        if type(expires_at) is not int or not time.time() < expires_at <= time.time() + 7200:
            raise CoreError('QQ_OFFICIAL_HOST_SESSION_EXPIRED')
        await self._post(session, '/official/session', {'application_id': self.application_id,
                         'bot_id': self.bot_id, 'access_token': token, 'expires_at': expires_at})
        await self._post(session, '/official/events', row)
        return 'QUEUED_NOT_DELIVERED'
