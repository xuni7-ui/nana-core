import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.bilibili_runtime import BilibiliChannelBinding
from nana_core.presence.authority import VirtualClock
from nana_core.nanalink.contracts import Account
from nana_core.nanalink.bilibili_dynamic import normalize_dynamic
from nana_core.nanalink.private_source import PrivateDynamicBridge
from tests.person_self.conftest import initialize


def test_private_observation_original_memory_duplicate_restart_and_withdrawal(tmp_path):
    home=tmp_path/'home';initialize(home);cfg=load_config(home);clock=VirtualClock()
    binding=SurfaceBinding(binding_id='bili.private',platform='bilibili.account',adapter='bilibili.account',surface='chat.direct',
        mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PERSONAL',),allow_personal_retention=True,
        personal_retention_consent_ref='consent.fixture')
    channel=BilibiliChannelBinding(channel_id='bili',binding_id=binding.binding_id,account_id=42,target_id=43,sender_id=43,
        cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,private_read_authorized=True)
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(binding,),
        'bilibili_channels':(channel,)}),expected_revision=cfg.revision)
    account=Account(platform='bilibili',adapter_id='bilibili.account',account_id='42')
    row={'id_str':'123','type':'DYNAMIC_TYPE_AV','modules':{'module_author':{'mid':43,'pub_ts':1},
        'module_dynamic':{'desc':{'text':'Synthetic private observation'},'major':{}}}}
    event=normalize_dynamic(account,row,now_us=clock.utc_now_us(),origin='SYNTHETIC_LOOPBACK')
    with LifeApplication(home,clock=clock) as app:
        app.pause();bridge=PrivateDynamicBridge(app,'bili');identity=app.runtime.identity_id
        result=bridge.receive(event);mid=result['memory_id']
        assert result['state']=='SOURCE_QUEUED_NOT_JUDGED'
        from nana_core.continuity.memory import MemoryService
        saved=MemoryService(app.runtime.store).read(mid)
        assert saved['privacy_class']=='PERSONAL' and saved['source_provenance']['domain']=='CONSENTED_PLATFORM'
        assert bridge.receive(event)['memory_id']==mid
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('cognitive_requests')
    with LifeApplication(home,clock=clock) as app:
        app.pause();bridge=PrivateDynamicBridge(app,'bili')
        assert app.runtime.identity_id==identity and bridge.receive(event)['memory_id']==mid
        assert bridge.withdraw(event)
        with pytest.raises(CoreError):bridge.receive(event)


def test_forged_private_source_cannot_bypass_authority(tmp_path):
    home=tmp_path/'home';initialize(home)
    app=LifeApplication(home)
    from nana_core.continuity.contracts import Provenance,EvidenceInput
    from nana_core.continuity.memory import MemoryService
    p=Provenance(domain='CONSENTED_PLATFORM',source_namespace='recorded.platform.bilibili.dynamic',
                 source_reference='dynamic:fixture',source_kind='DIRECT_OBSERVATION')
    c=EvidenceInput(provenance=p,retention_consent_ref='consent.fixture',text='fixture',privacy_class='PERSONAL',observed_time_us=0)
    with pytest.raises(CoreError,match='PLATFORM_OBSERVATION_NOT_AUTHORIZED'):
        MemoryService(app.runtime.store).capture(c)
    app.close()


def test_owned_http_pump_budget_dedupe_and_no_social_send(tmp_path):
    from tests.living_release_v4.test_bilibili_runtime import equipped
    from tests.living_release_v4.bilibili_loopback import counterpart
    from tests.nanalink.test_bilibili_notifications import notification_front
    from nana_core.nanalink.private_source import poll_dynamics
    home=tmp_path/'home';initialize(home);cfg=load_config(home);clock=VirtualClock()
    binding=SurfaceBinding(binding_id='bili.private',platform='bilibili.account',adapter='bilibili.account',surface='chat.direct',
       mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PERSONAL',),allow_personal_retention=True,personal_retention_consent_ref='consent.fixture')
    channel=BilibiliChannelBinding(channel_id='bili',binding_id=binding.binding_id,account_id=42,target_id=43,sender_id=43,
       cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,private_read_authorized=True)
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(binding,),
        'bilibili_channels':(channel,)}),expected_revision=cfg.revision)
    row={'id_str':'123','type':'DYNAMIC_TYPE_AV','modules':{'module_author':{'mid':43,'pub_ts':1},
        'module_dynamic':{'desc':{'text':'Synthetic event'},'major':{}}}}
    with counterpart() as (upstream, state), notification_front(upstream.endpoint) as (url, front), LifeApplication(home,clock=clock) as app:
        app.pause();front['dynamic']=[row];workflow=equipped(app,channel,url,grant=False)
        result=poll_dynamics(workflow)
        assert result['observations']==1 and result['model_calls']==0
        assert poll_dynamics(workflow)['state']=='ALREADY_POLLED_NO_RETRY'
        assert len(front['requests'])==2 and state['posts']==0
        assert app.runtime.store.db.execute("SELECT count(*) FROM memories WHERE privacy_class='PERSONAL'").fetchone()[0]==1


def test_revoked_retention_withdraws_original_memory_after_restart(tmp_path):
    from nana_core.continuity.memory import MemoryService
    home=tmp_path/'home';initialize(home);cfg=load_config(home);clock=VirtualClock()
    b=SurfaceBinding(binding_id='bili.private',platform='bilibili.account',adapter='bilibili.account',surface='chat.direct',
        mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PERSONAL',),allow_personal_retention=True,
        personal_retention_consent_ref='consent.fixture')
    c=BilibiliChannelBinding(channel_id='bili',binding_id=b.binding_id,account_id=42,target_id=43,sender_id=43,
        cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,private_read_authorized=True)
    cfg=cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(b,),'bilibili_channels':(c,)})
    update_config(home,cfg,expected_revision=cfg.revision-1)
    account=Account(platform='bilibili',adapter_id='bilibili.account',account_id='42')
    row={'id_str':'123','modules':{'module_author':{'mid':43,'pub_ts':1},'module_dynamic':{'desc':{'text':'fixture'}}}}
    event=normalize_dynamic(account,row,now_us=clock.utc_now_us(),origin='SYNTHETIC_LOOPBACK')
    with LifeApplication(home,clock=clock) as app:
        app.pause();mid=PrivateDynamicBridge(app,'bili').receive(event)['memory_id']
    updated=cfg.model_copy(update={'revision':cfg.revision+1,'bilibili_channels':(c.model_copy(update={'private_read_authorized':False}),)})
    update_config(home,updated,expected_revision=cfg.revision)
    with LifeApplication(home,clock=clock) as app:
        with pytest.raises(CoreError):MemoryService(app.runtime.store).read(mid)
        assert app.runtime.store.one('memories',mid)['lifecycle']=='DELETED'
