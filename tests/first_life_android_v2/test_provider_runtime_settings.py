"""Authenticated original host settings, no model/key/network operations."""
import pytest
from nana_core.continuity.provider_config import ProviderConfigService,ProviderConfigurationAuthority,ProviderProfile,ProviderCommand
from nana_core.life.config import load_config
from nana_core.life.live_api import provider_settings
from .test_http_integration import running,http,login,base


def configure_profile(service):
    authority=ProviderConfigurationAuthority()
    settings=ProviderConfigService(service.supervisor.home/'providers.json',authority)
    document=settings.initialize(authority)
    return settings.update(ProviderCommand(operation='UPSERT_PROVIDER',expected_revision=document.revision,
        provider=ProviderProfile(provider_profile_id='provider.runtime',display_name='SYNTHETIC runtime provider',
            protocol='OPENAI_COMPATIBLE_CHAT',base_url='https://provider.example/v1',locality='REMOTE',
            permitted_privacy=('PUBLIC','PROJECT'),default_timeout_ms=120000,default_cost_ceiling=1000)),authority)


def request_body(service,key='runtime-settings'):
    config=load_config(service.supervisor.home)
    return {**base(service,key),'provider_profile_id':'provider.runtime','profile_revision':1,
        'configuration_revision':config.revision,'calls_per_day':6,'calls_per_hour':4,
        'per_provider_calls_per_day':6,'output_tokens':1024,'context_tokens':8192,
        'per_call_reserved_cost_micro':500,'consent':True}


def test_runtime_settings_explicit_host_opt_in_cas_and_same_receipt(running):
    server,service=running;configure_profile(service);headers=login(server,service)
    service.allow_provider_configuration=True;service.allow_provider_runtime_budget=True
    before=load_config(service.supervisor.home);identity=service.binding.subject_id
    code,status,_=http(server,'providers/runtime',headers=headers)
    assert code==200 and status['data']['configuration_revision']==before.revision,status
    assert status['data']['network_calls']==0 and status['data']['can_configure'] is True
    body=request_body(service)
    code,response,_=http(server,'providers/runtime','POST',body,headers)
    assert code==200 and response['data']['state']=='VERIFIED',response
    result=response['data']['result']
    assert result['network_calls']==0 and result['runtime_applied'] is False and result['restart_required'] is True
    assert result['subject_history_changed'] is False and result['provider_host']=='provider.example'
    saved=load_config(service.supervisor.home)
    assert saved.revision==before.revision+1 and saved.provider_hosts==(*before.provider_hosts,'provider.example')
    assert saved.provider_calls_per_day==6 and saved.provider_calls_per_hour==4 and saved.per_provider_calls_per_day==6
    assert saved.provider_cost_ceiling_micro==500 and saved.provider_timeout_ms==before.provider_timeout_ms
    assert saved.provider_total_calls_limit==before.provider_total_calls_limit
    assert saved.provider_total_reserved_cost_micro==before.provider_total_reserved_cost_micro
    assert set(saved.remote_privacy)==set(before.remote_privacy)|{'PUBLIC','PROJECT'}
    assert service.binding.subject_id==identity
    repeated=http(server,'providers/runtime','POST',body,headers)[1]
    assert repeated['data']['state']=='VERIFIED' and load_config(service.supervisor.home).revision==saved.revision
    stale={**body,**base(service,'stale-runtime')}
    denied=http(server,'providers/runtime','POST',stale,headers)[1]['data']
    assert denied['state']=='REJECTED' and denied['dispatch_happened'] is False
    assert load_config(service.supervisor.home).revision==saved.revision


@pytest.mark.parametrize('condition',['opt-in-disabled','launch-not-authorized','consent-false','consent-number'])
def test_runtime_settings_does_not_inherit_permission_from_profile_edit(running,condition):
    server,service=running;configure_profile(service);headers=login(server,service)
    service.allow_provider_configuration=True
    service.allow_provider_runtime_budget=condition!='opt-in-disabled'
    if condition=='launch-not-authorized':service.supervisor.provider_live_authorized=False
    before=load_config(service.supervisor.home)
    body=request_body(service)
    if condition=='consent-false':body['consent']=False
    if condition=='consent-number':body['consent']=1
    code,_,_=http(server,'providers/runtime','POST',body,headers)
    assert code==(400 if condition.startswith('consent') else 403)
    assert load_config(service.supervisor.home)==before


def test_runtime_settings_lost_result_after_commit_remains_unknown_without_rewrite(running,monkeypatch):
    server,service=running;configure_profile(service);headers=login(server,service)
    service.allow_provider_configuration=True;service.allow_provider_runtime_budget=True
    original=provider_settings.update_config;calls=[]
    def lost(*args,**kwargs):
        calls.append(1);original(*args,**kwargs)
        raise OSError('SYNTHETIC lost local completion after settings replacement')
    monkeypatch.setattr(provider_settings,'update_config',lost)
    body=request_body(service);before=load_config(service.supervisor.home)
    code,response,_=http(server,'providers/runtime','POST',body,headers)
    assert code==200 and response['data']['state']=='UNKNOWN',response
    assert load_config(service.supervisor.home).revision==before.revision+1 and len(calls)==1
    checked=http(server,'receipts/'+body['client_request_id'],headers=headers)[1]['data']
    assert checked['state']=='UNKNOWN'
    assert http(server,'providers/runtime','POST',body,headers)[1]['data']['state']=='UNKNOWN'
    assert len(calls)==1


def test_runtime_settings_keeps_host_admin_and_csrf_checks(running,tmp_path):
    from nana_core.life.live_api.auth import AuthService
    from nana_core.life.live_api.contracts import Role
    from .test_http_integration import PW
    server,service=running;configure_profile(service);headers=login(server,service)
    service.allow_provider_configuration=True;service.allow_provider_runtime_budget=True
    before=load_config(service.supervisor.home)
    no_csrf={k:v for k,v in headers.items() if k!='X-Nana-CSRF'}
    assert http(server,'providers/runtime','POST',request_body(service),no_csrf)[0]==403
    service.auth=AuthService(tmp_path/'reader-auth.json',password=PW,roles=(Role.READER,Role.CONVERSATION))
    headers=login(server,service)
    assert http(server,'providers/runtime',headers=headers)[0]==403
    assert http(server,'providers/runtime','POST',request_body(service),headers)[0]==403
    assert load_config(service.supervisor.home)==before


def test_host_runtime_budget_flag_defaults_off_and_is_absent_from_legacy_serialization(running,tmp_path):
    from nana_core.life.live_api.__main__ import HostConfiguration
    _,service=running
    config=HostConfiguration(home=str(service.supervisor.home),host_state=str(tmp_path/'host'),
        binding=service.binding,releases=tuple(service.supervisor.releases.values()),
        active_release='qualified',public_origin='https://space.test',web_root=str(tmp_path))
    assert config.allow_provider_runtime_budget is False
    assert 'allow_provider_runtime_budget' not in config.model_dump(mode='json')
    assert config.model_copy(update={'allow_provider_runtime_budget':True}).model_dump(mode='json')['allow_provider_runtime_budget'] is True
