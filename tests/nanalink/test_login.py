"""Synthetic login providers and actual owned BFF/vault; no platform requests."""
from types import SimpleNamespace
import pytest
from nana_core.contracts import CoreError
from nana_core.nanalink.login import LoginBroker, BilibiliQRProvider
from nana_core.life.provider_vault import DurableSecretResolver
from nana_core.life.secret_binding import MemorySecretResolver
from nana_core.life.config import load_config
from tests.first_life_android_v2.test_http_integration import running, http, login, base  # noqa: F401
from tests.nanalink.test_console_setup import body

COOKIE='SESSDATA=FIXTURE_ONLY_SESSION_NOT_REAL;DedeUserID=42;bili_jct=FIXTUREONLYCSRF00000000000000'
CSRF='FIXTUREONLYCSRF00000000000000'


class Fake:
    account='42'
    def __init__(self):self.credentials=None;self.calls=0
    def begin(self):return 'https://passport.bilibili.com/fixture-login-only'
    def poll(self):self.calls+=1;self.credentials=COOKIE,CSRF;return 'IDENTITY_VERIFIED',self.account
    def clear(self):self.credentials=None


def test_qr_broker_expiry_identity_owner_rate_and_atomic_commit(tmp_path):
    now=[0];broker=LoginBroker(provider_factory=Fake,clock=lambda:now[0]);owner=('host',1,'WEB',None)
    result=broker.begin(owner,'bili');key=result['session_id']
    assert result['qr_svg'].startswith('<?xml') and COOKIE not in str(result)
    with pytest.raises(CoreError):broker.session(key,('other',1,'WEB',None))
    assert broker.poll(key,owner,42)['state']=='WAITING_SCAN'
    now[0]=3
    assert broker.poll(key,owner,42)['state']=='IDENTITY_VERIFIED'
    provider=broker.session(key,owner)['provider']
    vault=DurableSecretResolver(tmp_path/'vault',initialize=True)
    c=SimpleNamespace(channel_id='bili',account_id=42,cookie_ref='bili.cookie',csrf_ref='bili.csrf')
    before=vault.metadata()['revision']
    assert broker.commit(key,owner,c,vault,before)['state']=='BOUND_IN_HOST_VAULT'
    assert vault.metadata()['revision']==before+1 and provider.credentials is None
    assert vault.available(c.cookie_ref) and vault.available(c.csrf_ref)
    assert COOKIE.encode() not in (tmp_path/'vault/vault.json').read_bytes()
    result=broker.begin(owner,'bili');now[0]+=181
    with pytest.raises(CoreError):broker.session(result['session_id'],owner)
    vault.clear()


def test_mismatch_and_cas_leave_no_partial_credentials(tmp_path):
    now=[0];broker=LoginBroker(provider_factory=Fake,clock=lambda:now[0]);owner=('host',1,'WEB',None)
    key=broker.begin(owner,'bili')['session_id'];now[0]=3
    with pytest.raises(CoreError):broker.poll(key,owner,43)
    assert broker.session(key,owner)['provider'].credentials is None
    broker.cancel(key,owner)
    key=broker.begin(owner,'bili')['session_id'];now[0]+=3;broker.poll(key,owner,42)
    vault=DurableSecretResolver(tmp_path/'vault',initialize=True);rev=vault.metadata()['revision']
    vault.bind('unrelated','FIXTURE_ONLY_OTHER_NOT_REAL',expected_revision=rev)
    c=SimpleNamespace(channel_id='bili',account_id=42,cookie_ref='bili.cookie',csrf_ref='bili.csrf')
    with pytest.raises(CoreError):broker.commit(key,owner,c,vault,rev)
    assert not vault.available(c.cookie_ref) and not vault.available(c.csrf_ref)
    with pytest.raises(CoreError):vault.bind_many({'bili.cookie':COOKIE,'bad reference':CSRF},expected_revision=rev+1)
    assert not vault.available(c.cookie_ref);vault.clear()
    memory=MemorySecretResolver()
    with pytest.raises(CoreError):memory.bind_many({'bili.cookie':COOKIE,'bili.csrf':'invalid value'})
    assert not memory.available('bili.cookie')


def test_real_bff_explicit_host_consent_csrf_disabled_channels_and_vault(running,tmp_path):
    server,service=running;headers=login(server,service);service.allow_provider_configuration=True
    http(server,'platform/setup','POST',body(service,'login.setup','bilibili.account','comment'),headers)
    channel=load_config(service.supervisor.home).bilibili_channels[0]
    def req(action,key=None,consent=True):
        return {**base(service,'qr.'+action), 'action':action,'channel_id':channel.channel_id,
                'session_id':key,'configuration_revision':load_config(service.supervisor.home).revision,
                'expected_vault_revision':service.credential_resolver.metadata()['revision'] if service.credential_resolver else None,
                'consent':consent}
    assert http(server,'platform/login','POST',req('BEGIN'),headers)[0]==403
    service.allow_platform_login=True
    service.credential_resolver=DurableSecretResolver(tmp_path/'vault',initialize=True)
    now=[0];service.platform_login=LoginBroker(provider_factory=Fake,clock=lambda:now[0])
    assert http(server,'platform/login','POST',req('BEGIN',consent=False),headers)[0]==409
    assert http(server,'platform/login','POST',req('BEGIN'),{k:v for k,v in headers.items() if k!='X-Nana-CSRF'})[0]==403
    result=http(server,'platform/login','POST',req('BEGIN'),headers)[1]['data'];key=result['session_id']
    now[0]=3
    assert http(server,'platform/login','POST',req('POLL',key),headers)[1]['data']['state']=='IDENTITY_VERIFIED'
    result=http(server,'platform/login','POST',req('COMMIT',key),headers)[1]['data']
    assert result['state']=='BOUND_IN_HOST_VAULT' and result['enabled'] is False
    assert not load_config(service.supervisor.home).bilibili_channels[0].enabled
    assert COOKIE not in str(service.ledger.document.read()) and COOKIE not in str(result)
    service.credential_resolver.clear()


def test_fixed_public_provider_parses_codes_cookies_and_verified_profile(monkeypatch):
    provider=BilibiliQRProvider();provider.key='fixture'
    calls=[]
    def owned_get(url,**kw):
        calls.append(url)
        if url.startswith('https://passport.bilibili.com/'):
            return {'code':0},['SESSDATA=FIXTURE_ONLY_SESSION_NOT_REAL; Path=/','DedeUserID=42; Path=/',f'bili_jct={CSRF}; Path=/']
        return {'isLogin':True,'mid':42},[]
    monkeypatch.setattr(provider,'_get',owned_get)
    assert provider.poll()==('IDENTITY_VERIFIED','42') and provider.credentials[1]==CSRF
    assert len(calls)==2


def test_missing_optional_qr_support_does_not_start_an_external_login(monkeypatch):
    import builtins
    original_import = builtins.__import__
    calls = []
    class ExternalLogin:
        def begin(self):
            calls.append('external_login_request')
            return 'https://passport.bilibili.com/fixture'
        def clear(self):
            pass
    def without_qr(name, *args, **kwargs):
        if name == 'qrcode' or name.startswith('qrcode.'):
            raise ImportError('SYNTHETIC_OPTIONAL_DEPENDENCY_ABSENT')
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', without_qr)
    broker = LoginBroker(provider_factory=ExternalLogin)
    with pytest.raises(CoreError, match='NANALINK_LOGIN_QR_DEPENDENCY_UNAVAILABLE'):
        broker.begin(('fixture', 1, 'WEB', None), 'bili')
    assert calls == [] and broker.sessions == {}
