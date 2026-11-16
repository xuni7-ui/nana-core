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
        with pytest.raises(CoreError,match='PLATFORM_OBSERVATION_NOT_AUTHORIZED'):
            bridge.receive(event.model_copy(update={'origin':'AUTHENTICATED_PLATFORM'}))
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
    home=tmp_path/'home';initialize(home);cfg=load_config(home);clock=VirtualClock(now_us=1_791_590_699_000_000)
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
        front['dynamic']=[{**row,'modules':{**row['modules'],'module_dynamic':{'desc':{'text':'changed synthetic event'}}}}, {**row,'id_str':'124'}]
        clock.advance(2_000_000)
        changed=poll_dynamics(workflow)
        assert changed['changed_withdrawn']==1 and changed['observations']==1
        assert app.runtime.store.db.execute("SELECT count(*) FROM memories WHERE privacy_class='PERSONAL' AND lifecycle='ACTIVE'").fetchone()[0]==1
        assert state['posts']==0


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


def test_private_platform_source_recalled_in_qq_and_phone_and_withdrawn(tmp_path):
    from tests.nanalink.test_onebot_network import network
    from tests.independent_life.test_dialogue import relay
    from tests.living_release_v4.test_platform_runtime import equip
    from nana_core.life.platform_runtime import QQChannelBinding, SecretReference
    import time
    home=tmp_path/'home';initialize(home);cfg=load_config(home);clock=VirtualClock(now_us=time.time_ns()//1000)
    bili=SurfaceBinding(binding_id='bili.private',platform='bilibili.account',adapter='bilibili.account',surface='chat.direct',
       mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PERSONAL',),allow_personal_retention=True,personal_retention_consent_ref='consent.fixture')
    qq=SurfaceBinding(binding_id='qq.private',platform='qq.onebot',adapter='qq.onebot',surface='chat.direct',
       mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PERSONAL',))
    mobile=SurfaceBinding(binding_id='nana.space',platform='nana.space',adapter='nana-space.gateway',surface='chat.direct',permitted_privacy=('PERSONAL','PROJECT','PUBLIC'))
    channel=BilibiliChannelBinding(channel_id='bili',binding_id=bili.binding_id,account_id=42,target_id=43,sender_id=43,
       cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,private_read_authorized=True)
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(bili,qq,mobile),'bilibili_channels':(channel,)}),expected_revision=cfg.revision)
    account=Account(platform='bilibili',adapter_id='bilibili.account',account_id='42')
    item={'id_str':'123','modules':{'module_author':{'mid':7654321,'pub_ts':1},'module_dynamic':{'desc':{'text':'Synthetic ORCHID video observation'}}}}
    event=normalize_dynamic(account,item,now_us=clock.utc_now_us(),origin='SYNTHETIC_LOOPBACK')
    with network() as (net,state,resolver,loop),relay(home,'CHAT',recall_query_terms=('ORCHID',)) as (router,calls),LifeApplication(home,clock=clock,router=router) as app:
        app.pause();bridge=PrivateDynamicBridge(app,'bili');mid=bridge.receive(event)['memory_id'];identity=app.runtime.identity_id
        qc=QQChannelBinding(channel_id='qq',binding_id=qq.binding_id,endpoint=net['endpoint'],account_id='42',sender_id='43',target_id='43',
                            enabled=True,read_authorized=True,send_authorized=True,private_read_authorized=True,privacy_class='PERSONAL')
        workflow=equip(app,qc,net['endpoint']);workflow.transport.credential=SecretReference(resolver,'core.test')
        delivery=workflow.receive('1')
        assert delivery['delivery']=='SUCCEEDED' and delivery['external_delivery']
        assert len(state['sent'])==1
        assert mid in calls[-1]['source_context_refs']
        assert 'PRIVATE_PLATFORM_OBSERVATION_NOT_USER_INSTRUCTION' in str(calls[-1])
        assert '7654321' in str(calls[-1])
        # Same live owner/Store: real Nana Space HTTP and UDS, fixture transport.
        import threading, time
        from types import SimpleNamespace
        from nana_core.life.control import ControlServer
        from nana_core.life.live_api.supervisor import existing_identity
        from nana_core.life.live_api.contracts import Binding, Role
        from nana_core.life.live_api.auth import AuthService
        from nana_core.life.live_api.bridge import GatewayService
        from nana_core.life.live_api.server import ApiServer
        from tests.first_life_android_v2.test_http_integration import http,login,base,ORIGIN,PW
        _,lineage,_=existing_identity(home)
        binding=Binding(subject_id=identity,lineage_binding=lineage,privacy=('PUBLIC','PROJECT','PERSONAL'))
        epoch=app.runtime.lease.epoch
        supervisor=SimpleNamespace(home=home,binding=binding,provider_live_authorized=False,
            status=lambda:{'owner_epoch':epoch,'process_ready':True,'source_commit':'a'*40},verify_binding=lambda:None)
        service=GatewayService(supervisor,AuthService(tmp_path/'auth.json',password=PW,roles=tuple(Role)),tmp_path/'gateway')
        server=ApiServer(('127.0.0.1',0),service,public_origin=ORIGIN)
        server_thread=threading.Thread(target=server.serve_forever,daemon=True);server_thread.start()
        result={};done=threading.Event()
        def phone():
            try:
                headers=login(server,service)
                result['value']=http(server,'messages','POST',{**base(service,'phone-fixture'),
                    'text':'ORCHID synthetic phone follow-up','privacy_class':'PERSONAL'},headers)
            finally:
                done.set()
        try:
            with ControlServer(app) as control:
                thread=threading.Thread(target=phone,daemon=True);thread.start();deadline=time.monotonic()+10
                while not done.is_set() and time.monotonic()<deadline:
                    control.poll();time.sleep(.005)
                thread.join(1)
                assert done.is_set() and result['value'][1]['data']['state']=='VERIFIED',result
            assert mid in calls[-1]['source_context_refs'] and app.runtime.identity_id==identity
        finally:
            server.shutdown();server_thread.join(3);server.server_close()
        app.chat('ORCHID project context',privacy='PROJECT',message_id='project-fixture')
        assert mid not in calls[-1]['source_context_refs']
        bridge.withdraw(event)
        app.chat('ORCHID after withdrawal',privacy='PERSONAL',message_id='phone-withdrawn')
        assert mid not in calls[-1]['source_context_refs']


def test_config_revocation_closes_source_before_next_original_memory_read(tmp_path):
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
        next_cfg=cfg.model_copy(update={'revision':cfg.revision+1,'bilibili_channels':(c.model_copy(update={'private_read_authorized':False}),)})
        with app.runtime.store.transaction('fixture.source_config_change'):
            update_config(home,next_cfg,expected_revision=cfg.revision)
            with pytest.raises(CoreError,match='PLATFORM_SOURCE_REVOCATION_PENDING_SAFE_POINT'):
                MemoryService(app.runtime.store).read(mid)
        # No platform-refresh or restart: the original privacy safe point detects
        # the changed host config before revealing the now-revoked source.
        with pytest.raises(CoreError):MemoryService(app.runtime.store).read(mid)
        assert app.runtime.store.one('memories',mid)['lifecycle']=='DELETED'


def test_dynamic_read_rejects_account_credential_rotation_before_network():
    from nana_core.life.bilibili_account import BilibiliAccountPolicy, BilibiliAccountTransport
    from nana_core.life.secret_binding import MemorySecretResolver
    from tests.living_release_v4.bilibili_loopback import counterpart
    from tests.nanalink.test_bilibili_notifications import notification_front
    secrets = MemorySecretResolver()
    secrets.bind('test.cookie', 'FIXTURE_COOKIE_ACCOUNT_42')
    with counterpart() as (upstream, _), notification_front(upstream.endpoint) as (url, front):
        transport = BilibiliAccountTransport(secrets, cookie_ref='test.cookie', csrf_ref='test.csrf',
            policy=BilibiliAccountPolicy(42, read_authorized=True), realm='SYNTHETIC_LOOPBACK', loopback_endpoint=url)
        assert transport.account()['account_id'] == 42
        secrets.bind('test.cookie', 'FIXTURE_COOKIE_DIFFERENT_ACCOUNT')
        with pytest.raises(CoreError, match='BILIBILI_ACCOUNT_BINDING_MISMATCH'):
            transport.dynamic_rows()
        assert len(front['requests']) == 1
        secrets.bind('test.cookie', 'FIXTURE_COOKIE_ACCOUNT_42')
        transport.account()
        assert transport.dynamic_rows() == []
        with pytest.raises(CoreError, match='BILIBILI_ACCOUNT_BINDING_MISMATCH'):
            transport.dynamic_rows()
        assert len(front['requests']) == 3
    secrets.clear()


def test_dynamic_pump_does_not_attribute_rotated_account_or_retry(tmp_path):
    from tests.living_release_v4.test_bilibili_runtime import equipped
    from tests.living_release_v4.bilibili_loopback import counterpart
    from tests.nanalink.test_bilibili_notifications import notification_front
    from nana_core.nanalink.private_source import poll_dynamics
    home = tmp_path / 'home'; initialize(home); cfg = load_config(home); clock = VirtualClock(now_us=1_791_590_699_000_000)
    binding = SurfaceBinding(binding_id='bili.private', platform='bilibili.account', adapter='bilibili.account',
        surface='chat.direct', mode='PLATFORM_ADAPTER_NO_SEND', permitted_privacy=('PERSONAL',),
        allow_personal_retention=True, personal_retention_consent_ref='consent.fixture')
    channel = BilibiliChannelBinding(channel_id='bili', binding_id=binding.binding_id, account_id=42, target_id=43,
        sender_id=43, cookie_ref='test.cookie', csrf_ref='test.csrf', enabled=True, read_authorized=True, private_read_authorized=True)
    update_config(home, cfg.model_copy(update={'revision':cfg.revision+1, 'surface_bindings':(binding,),
        'bilibili_channels':(channel,)}), expected_revision=cfg.revision)
    with counterpart() as (upstream, state), notification_front(upstream.endpoint) as (url, front), LifeApplication(home, clock=clock) as app:
        app.pause(); workflow = equipped(app, channel, url, grant=False)
        transport = workflow.transport
        original = transport._BilibiliAccountTransport__resolver
        class RotatingResolver:
            calls = 0
            def resolve(self, ref):
                if ref == 'test.cookie':
                    self.calls += 1
                    if self.calls == 2:
                        original.bind(ref, 'FIXTURE_ROTATED_DIFFERENT_ACCOUNT')
                return original.resolve(ref)
        transport._BilibiliAccountTransport__resolver = RotatingResolver()
        with pytest.raises(CoreError, match='BILIBILI_ACCOUNT_BINDING_MISMATCH'):
            poll_dynamics(workflow)
        assert len(front['requests']) == 1 and state['posts'] == 0
        assert not app.runtime.store.db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace='recorded.platform.bilibili.dynamic'").fetchone()
        assert poll_dynamics(workflow)['state'] == 'ALREADY_POLLED_NO_RETRY'
        assert len(front['requests']) == 1


def test_private_notification_pages_reject_changed_account_between_pages():
    from nana_core.life.bilibili_account import BilibiliAccountPolicy, BilibiliAccountTransport
    from nana_core.life.secret_binding import MemorySecretResolver
    from tests.living_release_v4.bilibili_loopback import counterpart
    from tests.nanalink.test_bilibili_notifications import notification_front
    secrets = MemorySecretResolver(); secrets.bind('test.cookie', 'FIXTURE_COOKIE_ACCOUNT_42')
    with counterpart() as (upstream, _), notification_front(upstream.endpoint) as (url, front):
        transport = BilibiliAccountTransport(secrets, cookie_ref='test.cookie', csrf_ref='test.csrf',
            policy=BilibiliAccountPolicy(42, read_authorized=True), realm='SYNTHETIC_LOOPBACK', loopback_endpoint=url)
        transport.account()
        assert len(transport.notification_rows('reply')) == 1
        secrets.bind('test.cookie', 'FIXTURE_COOKIE_DIFFERENT_ACCOUNT')
        with pytest.raises(CoreError, match='BILIBILI_ACCOUNT_BINDING_MISMATCH'):
            transport.notification_rows('at')
        assert len(front['requests']) == 2
    secrets.clear()


def test_private_dm_read_rejects_rotated_account_credential_before_network():
    from nana_core.life.bilibili_account import BilibiliAccountPolicy, BilibiliAccountTransport
    from nana_core.life.secret_binding import MemorySecretResolver
    from tests.living_release_v4.bilibili_loopback import counterpart
    secrets = MemorySecretResolver(); secrets.bind('test.cookie', 'FIXTURE_COOKIE_ACCOUNT_42')
    with counterpart() as (upstream, state):
        transport = BilibiliAccountTransport(secrets, cookie_ref='test.cookie', csrf_ref='test.csrf',
            policy=BilibiliAccountPolicy(42, read_authorized=True, permitted_recipients=(43,)),
            realm='SYNTHETIC_LOOPBACK', loopback_endpoint=upstream.endpoint)
        transport.account()
        secrets.bind('test.cookie', 'FIXTURE_COOKIE_DIFFERENT_ACCOUNT')
        with pytest.raises(CoreError, match='BILIBILI_ACCOUNT_BINDING_MISMATCH'):
            transport.messages(43)
        assert len(state['requests']) == 1
        secrets.bind('test.cookie', 'FIXTURE_COOKIE_ACCOUNT_42')
        transport.account()
        assert transport.messages(43) == []
    secrets.clear()


def test_synthetic_bilibili_account_requires_actual_loopback_transport(tmp_path):
    from nana_core.life.bilibili_account import BilibiliAccountPolicy, BilibiliAccountTransport
    from nana_core.life.secret_binding import MemorySecretResolver
    from tests.living_release_v4.test_bilibili_runtime import equipped
    secrets = MemorySecretResolver()
    with pytest.raises(CoreError, match='BILIBILI_LOOPBACK_ORIGIN_REQUIRED'):
        BilibiliAccountTransport(secrets, cookie_ref='test.cookie', csrf_ref='test.csrf',
            policy=BilibiliAccountPolicy(42, read_authorized=True), realm='SYNTHETIC_LOOPBACK')
    home=tmp_path/'home';initialize(home);cfg=load_config(home)
    binding=SurfaceBinding(binding_id='bili.synthetic',platform='bilibili.account',adapter='bilibili.account',surface='chat.comment',
        mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PUBLIC',))
    channel=BilibiliChannelBinding(channel_id='synthetic',binding_id=binding.binding_id,kind='comment',account_id=42,target_id=7,
        sender_id=43,cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,private_read_authorized=True)
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(binding,)}),expected_revision=cfg.revision)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();flow=equipped(app,channel,'http://127.0.0.1:1',grant=False)
        flow._authority()
        flow.transport.opener.endpoint='https://example.org'
        with pytest.raises(CoreError,match='BILIBILI_LITERAL_LOOPBACK_REQUIRED'):
            flow._authority()
        flow.transport.opener=object()
        with pytest.raises(CoreError,match='BILIBILI_SYNTHETIC_LOOPBACK_REQUIRED'):
            flow._authority()
    secrets.clear()
