"""Explicit account login capability; bounded RAM tickets, original host vault.

No polling daemon, Core Grant, account event reading, messages or new memory.
All network occurs only after an authenticated user invokes the opt-in flow.
"""
import io
import json
import secrets
import time
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie
from ..contracts import CoreError
from ..life.platform_bridge import NoRedirect
from ..life.live_api.platform_credentials import normalized


class BilibiliQRProvider:
    def __init__(self):
        self.key = None
        self.credentials = None

    def _get(self, url, *, cookie=None):
        headers = {'User-Agent': 'NanaLink/1.0 explicit-account-login'}
        if cookie:
            headers['Cookie'] = cookie
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(urllib.request.Request(url, headers=headers), timeout=5) as reply:
            raw = reply.read(65537)
            if len(raw) > 65536 or reply.status != 200:
                raise CoreError('NANALINK_LOGIN_RESPONSE_BOUND')
            value = json.loads(raw)
            if type(value) is not dict or value.get('code') != 0 or type(value.get('data')) is not dict:
                raise CoreError('NANALINK_LOGIN_PLATFORM_REJECTED')
            return value['data'], reply.headers.get_all('Set-Cookie') or []

    def begin(self):
        data, _ = self._get('https://passport.bilibili.com/x/passport-login/web/qrcode/generate')
        self.key = data.get('qrcode_key')
        url = data.get('url')
        if (type(self.key) is not str or not 1 <= len(self.key) <= 128 or type(url) is not str
                or len(url) > 2048 or not url.startswith('https://passport.bilibili.com/')):
            raise CoreError('NANALINK_LOGIN_QR_INVALID')
        return url

    def poll(self):
        if not self.key:
            raise CoreError('NANALINK_LOGIN_SESSION_EXPIRED')
        data, cookies = self._get('https://passport.bilibili.com/x/passport-login/web/qrcode/poll?' +
                                 urllib.parse.urlencode({'qrcode_key': self.key}))
        code = data.get('code')
        if code in {86101, 86090, 86038}:
            return {86101:'WAITING_SCAN',86090:'WAITING_CONFIRMATION',86038:'EXPIRED'}[code], None
        if code != 0:
            raise CoreError('NANALINK_LOGIN_PLATFORM_REJECTED')
        jar = SimpleCookie()
        for value in cookies:
            jar.load(value)
        values = {key: item.value for key,item in jar.items()}
        if not {'SESSDATA','bili_jct','DedeUserID'} <= values.keys():
            raise CoreError('NANALINK_LOGIN_SESSION_INCOMPLETE')
        cookie = normalized(';'.join(key+'='+value for key,value in values.items()), 'COOKIE')
        csrf = normalized(values['bili_jct'], 'CSRF')
        if len(cookie) > 4096:
            raise CoreError('NANALINK_LOGIN_SESSION_BOUND')
        profile, _ = self._get('https://api.bilibili.com/x/web-interface/nav', cookie=cookie)
        account = str(profile.get('mid'))
        if profile.get('isLogin') is not True or account != values['DedeUserID']:
            raise CoreError('NANALINK_LOGIN_IDENTITY_MISMATCH')
        self.credentials = cookie, csrf
        return 'IDENTITY_VERIFIED', account

    def clear(self):
        self.key = self.credentials = None


def qr_svg(url):
    import qrcode
    import qrcode.image.svg
    qr = qrcode.QRCode(box_size=5, border=4)
    qr.add_data(url);qr.make(fit=True)
    output = io.BytesIO()
    qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(output)
    return output.getvalue().decode('utf-8')


class LoginBroker:
    def __init__(self, *, provider_factory=BilibiliQRProvider, clock=time.monotonic):
        self.provider_factory, self.clock = provider_factory, clock
        self.sessions = {}

    def _prune(self):
        for key, value in tuple(self.sessions.items()):
            if value['expires'] <= self.clock():
                value['provider'].clear();del self.sessions[key]

    def begin(self, owner, channel):
        self._prune()
        if len(self.sessions) >= 4 or any(v['owner']==owner for v in self.sessions.values()):
            raise CoreError('NANALINK_LOGIN_SESSION_CAPACITY_CANCEL_PREVIOUS')
        provider = self.provider_factory()
        try:
            url = provider.begin()
            svg = qr_svg(url)
        except Exception:
            provider.clear()
            raise CoreError('NANALINK_LOGIN_START_NOT_CONFIRMED_NO_RETRY') from None
        key = secrets.token_urlsafe(24)
        self.sessions[key] = {'provider': provider, 'owner': owner, 'channel': channel,
                  'expires': self.clock()+180, 'next_poll': self.clock()+2,
                  'state': 'WAITING_SCAN', 'account': None}
        return {'session_id':key,'state':'WAITING_SCAN','expires_in':180,'qr_svg':svg,
                'credential_exposed':False,'external_delivery':False}

    def session(self, key, owner):
        self._prune()
        value = self.sessions.get(key)
        if value is None or value['owner'] != owner:
            raise CoreError('NANALINK_LOGIN_SESSION_UNAVAILABLE')
        return value

    def poll(self, key, owner, expected_account):
        value = self.session(key, owner)
        if value['state'] in {'ACCOUNT_MISMATCH','EXPIRED'}:
            return {'state':value['state']}
        if value['state'] == 'IDENTITY_VERIFIED':
            return {'state': value['state'], 'account_label':'账号尾号 '+value['account'][-4:]}
        if value['next_poll'] > self.clock():
            return {'state':value['state'],'retry_after':2}
        value['next_poll'] = self.clock()+2
        try:
            state, account = value['provider'].poll()
            if state == 'IDENTITY_VERIFIED' and account != str(expected_account):
                value['provider'].clear();value['state']='ACCOUNT_MISMATCH'
                raise CoreError('NANALINK_LOGIN_ACCOUNT_MISMATCH')
            value['state'], value['account'] = state, account
            if state == 'EXPIRED':
                value['provider'].clear()
            return {'state':state,'account_label':'账号尾号 '+account[-4:] if account else None}
        except CoreError:
            raise
        except Exception:
            raise CoreError('NANALINK_LOGIN_POLL_UNKNOWN_NO_AUTORETRY') from None

    def cancel(self, key, owner):
        value = self.session(key, owner)
        value['provider'].clear();del self.sessions[key]
        return {'state':'CANCELLED','credential_exposed':False}

    def commit(self, key, owner, channel, resolver, expected_revision):
        value = self.session(key, owner)
        if value['channel'] != channel.channel_id or value['state'] != 'IDENTITY_VERIFIED' or value['account'] != str(channel.account_id):
            raise CoreError('NANALINK_LOGIN_IDENTITY_UNVERIFIED')
        cookie, csrf = value['provider'].credentials
        try:
            kwargs = {'expected_revision':expected_revision} if resolver.persistent else {}
            resolver.bind_many({channel.cookie_ref:cookie, channel.csrf_ref:csrf}, **kwargs)
        finally:
            # CAS failure or lost publish ACK requires a fresh explicit flow;
            # never keep credentials for an automatic retry or partial pair.
            value['provider'].clear();del self.sessions[key]
        return {'state':'BOUND_IN_HOST_VAULT' if resolver.persistent else 'BOUND_IN_HOST_MEMORY',
                'credential_exposed':False,'grants_created':False,'restart_required':True,
                'enabled':False,'send_authorized':False}
