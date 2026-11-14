import pytest
from nana_core.life.config import load_config
from tests.first_life_android_v2.test_http_integration import running, http, login, base


def body(service,key,method='qq.onebot',kind='private'):
    return {**base(service,key),'method':method,'kind':kind,'account_id':'42','peer_id':'43','sender_id':'43',
            'configuration_revision':load_config(service.supervisor.home).revision}


def test_phone_setup_actual_http_cas_disabled_no_account_calls(running):
    server,service=running
    headers=login(server,service)
    service.allow_provider_configuration=True
    request=body(service,'setup.qq')
    code,value,_=http(server,'platform/setup','POST',request,headers)
    assert code==200 and value['data']['state']=='VERIFIED',value
    result=value['data']['result']
    assert result['network_calls']==0 and result['enabled'] is False
    config=load_config(service.supervisor.home)
    channel=config.qq_channels[0]
    assert not channel.enabled and not channel.read_authorized and not channel.send_authorized
    assert channel.activation is None and channel.privacy_class=='PERSONAL' and not channel.private_read_authorized
    assert config.surface_bindings[-1].allow_personal_retention is False
    again=http(server,'platform/setup','POST',request,headers)[1]
    assert again['data']['receipt_id']==value['data']['receipt_id']
    assert load_config(service.supervisor.home).revision==config.revision
    status=http(server,'platform/status',headers=headers)[1]['data']
    assert status['configuration_revision']==config.revision
    assert any(c['channel_id']==channel.channel_id and c['state']=='PENDING_OWNER_RESTART' for c in status['channels'])
    stale={**request,**base(service,'setup.stale')}
    assert http(server,'platform/setup','POST',stale,headers)[1]['data']['state']=='REJECTED'
    switch={**base(service,'switch.denied'),'platform':'qq','channel_id':channel.channel_id,'enabled':True,
            'configuration_revision':config.revision}
    assert http(server,'platform/commands','POST',switch,headers)[1]['data']['error']=='PLATFORM_READ_NOT_AUTHORIZED'


def test_setup_bili_and_csrf_role_host_optin(running):
    server,service=running
    headers=login(server,service)
    request=body(service,'setup.bili','bilibili.account','comment')
    assert http(server,'platform/setup','POST',request,headers)[0]==403
    service.allow_provider_configuration=True
    assert http(server,'platform/setup','POST',request,{k:v for k,v in headers.items() if k!='X-Nana-CSRF'})[0]==403
    result=http(server,'platform/setup','POST',request,headers)[1]
    assert result['data']['state']=='VERIFIED',result
    channel=load_config(service.supervisor.home).bilibili_channels[0]
    assert channel.kind=='comment' and not channel.send_authorized and not channel.read_authorized
    assert channel.cookie_ref.startswith('nanalink.bili.cookie.')


def test_config_write_ack_loss_is_unknown_and_not_replayed(running,monkeypatch):
    import nana_core.life.live_api.platform_setup as module
    server,service=running;headers=login(server,service)
    service.allow_provider_configuration=True
    real=module.update_config
    def lose(*args,**kw):real(*args,**kw);raise OSError('fixture loss after durable config')
    monkeypatch.setattr(module,'update_config',lose)
    request=body(service,'setup.lost')
    result=http(server,'platform/setup','POST',request,headers)[1]
    assert result['data']['state']=='UNKNOWN'
    rev=load_config(service.supervisor.home).revision
    assert http(server,'platform/setup','POST',request,headers)[1]['data']['state']=='UNKNOWN'
    assert load_config(service.supervisor.home).revision==rev
