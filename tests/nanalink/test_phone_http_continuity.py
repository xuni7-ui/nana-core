"""Actual Nana Space HTTP -> original IPC owner with synthetic platform source."""
import shutil
import threading
from types import SimpleNamespace
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.bilibili_runtime import BilibiliChannelBinding
from nana_core.life.live_api.auth import AuthService
from nana_core.life.live_api.bridge import GatewayService
from nana_core.life.live_api.contracts import Role
from nana_core.life.live_api.server import ApiServer
from nana_core.nanalink.contracts import Account
from nana_core.nanalink.bilibili_dynamic import normalize_dynamic
from nana_core.nanalink.private_source import PrivateDynamicBridge
from tests.first_life_android_v2.test_supervisor import owned
from tests.first_life_android_v2.test_continuous_inputs import setup,running_owner
from tests.first_life_android_v2.test_http_integration import http,login,base,ORIGIN,PW
from tests.independent_life.test_dialogue import relay


def test_phone_http_original_owner_receives_private_sourced_continuity(tmp_path):
    home,binding,_=owned(tmp_path);setup(home);binding=binding.model_copy(update={'privacy':('PUBLIC','PROJECT','PERSONAL')})
    cfg=load_config(home)
    mobile=tuple(b.model_copy(update={'permitted_privacy':('PUBLIC','PROJECT','PERSONAL')}) if b.binding_id=='nana.space' else b for b in cfg.surface_bindings)
    bili=SurfaceBinding(binding_id='bili.private',platform='bilibili.account',adapter='bilibili.account',surface='chat.direct',
        mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PERSONAL',),allow_personal_retention=True,personal_retention_consent_ref='consent.fixture')
    channel=BilibiliChannelBinding(channel_id='bili',binding_id=bili.binding_id,account_id=42,target_id=43,sender_id=43,
        cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,private_read_authorized=True)
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(*mobile,bili),'bilibili_channels':(channel,)}),expected_revision=cfg.revision)
    account=Account(platform='bilibili',adapter_id='bilibili.account',account_id='42')
    item={'id_str':'123','modules':{'module_author':{'mid':7654321,'pub_ts':1},'module_dynamic':{'desc':{'text':'Synthetic ORCHID source'}}}}
    with LifeApplication(home) as app:
        app.pause();identity=app.runtime.identity_id
        event=normalize_dynamic(account,item,now_us=app.runtime.clock.utc_now_us(),origin='SYNTHETIC_LOOPBACK')
        mid=PrivateDynamicBridge(app,'bili').receive(event)['memory_id']
    with relay(home,'CHAT',recall_query_terms=('ORCHID',)) as (router,calls),running_owner(home,router) as owner:
        shutil.copyfile(home/'test-providers.json',home/'providers.json')
        supervisor=SimpleNamespace(home=home,binding=binding,provider_live_authorized=False,
            status=lambda:{'owner_epoch':owner['control'].app.runtime.lease.epoch,'process_ready':True,'source_commit':'a'*40},verify_binding=lambda:None)
        service=GatewayService(supervisor,AuthService(tmp_path/'auth.json',password=PW,roles=tuple(Role)),tmp_path/'gateway')
        server=ApiServer(('127.0.0.1',0),service,public_origin=ORIGIN)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            headers=login(server,service)
            result=http(server,'messages','POST',{**base(service,'phone.source'),'text':'Synthetic ORCHID follow-up','privacy_class':'PERSONAL'},headers)
            assert result[0]==200 and result[1]['data']['state']=='VERIFIED',result
            assert calls and mid in calls[-1]['source_context_refs']
            assert 'PRIVATE_PLATFORM_OBSERVATION_NOT_USER_INSTRUCTION' in str(calls[-1])
            assert owner['identity']==identity
            project=http(server,'messages','POST',{**base(service,'phone.project'),'text':'Synthetic ORCHID project follow-up','privacy_class':'PROJECT'},headers)
            assert project[0]==200 and project[1]['data']['state']=='VERIFIED',project
            assert mid not in calls[-1]['source_context_refs']
            from nana_core.life.control import request
            assert request(home,{'operation':'forget','memory_id':mid})['ok']
            after=http(server,'messages','POST',{**base(service,'phone.withdrawn'),'text':'Synthetic ORCHID after withdrawal','privacy_class':'PERSONAL'},headers)
            assert after[0]==200 and after[1]['data']['state']=='VERIFIED',after
            assert mid not in calls[-1]['source_context_refs']
        finally:
            server.shutdown();thread.join(3);server.server_close()
