"""Actual original Core + HTTP: explicit device privacy, never implicit authority."""
import pytest
from nana_core.life.config import load_config, update_config
from nana_core.life.live_api.auth import Principal
from nana_core.life.live_api.contracts import ApiError, Role
from tests.first_life_android_v2.test_http_integration import running as running, http, login, base


def private_host(service, *, retention=True):
    service.supervisor.stop()
    cfg=load_config(service.supervisor.home)
    bindings=tuple(b.model_copy(update={'permitted_privacy':('PUBLIC','PROJECT','PERSONAL'),
        'allow_personal_retention':retention,'personal_retention_consent_ref':'TEST_ONLY_NOT_SECRET_SYNTHETIC_CONSENT' if retention else None})
        if b.binding_id==service.binding.surface_binding_id else b for b in cfg.surface_bindings)
    update_config(service.supervisor.home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':bindings}),expected_revision=cfg.revision)
    service.binding=service.binding.model_copy(update={'privacy':('PUBLIC','PROJECT','PERSONAL')})
    service.supervisor.binding=service.binding
    service.supervisor.start()


def paired(server,service,headers,roles):
    offered=http(server,'devices/offers','POST',{'device_name':'TEST_ONLY_NOT_SECRET_phone','roles':roles},headers)
    assert offered[0]==200,offered
    result=http(server,'device/pairing','POST',{'code':offered[1]['data']['pairing_code'],
        'subject_id':service.binding.subject_id,'device_name':'TEST_ONLY_NOT_SECRET_phone'})[1]
    session=http(server,'session/native','POST',{k:result[k] for k in ('device_id','refresh_token','subject_id')})
    assert session[0]==200,session
    return {'Authorization':'Bearer '+session[1]['access_token']}


def test_personal_actual_core_retention_restart_scoped_read_withdrawal_and_cached_receipt(running):  # noqa: F811
    server,service=running
    headers=login(server,service)
    ordinary=paired(server,service,headers,['READER','CONVERSATION','MANAGER'])
    private_host(service)
    # Host widening cannot widen an already-paired device.
    assert http(server,'bootstrap',headers=ordinary)[1]['privacy_scope']==['PUBLIC','PROJECT']
    assert http(server,'bootstrap',headers=headers)[1]['privacy_scope']==['PUBLIC','PROJECT','PERSONAL']
    msg={**base(service,'personal-one'),'text':'先不聊这个话题','privacy_class':'PERSONAL',
        'retain_shared_life':True,'require_model':True}
    assert http(server,'messages','POST',msg,ordinary)[0]==403
    status,result,_=http(server,'messages','POST',msg,headers)
    assert status==200 and result['data']['state']=='VERIFIED',result
    source=result['data']['result']['message_memory_id']
    private_history=http(server,'conversation/history',headers=headers)[1]
    assert len(private_history['data']['items'])==1
    assert http(server,'conversation/history',headers=ordinary)[1]['data']['items']==[]
    memories=http(server,'views/memories',headers=headers)[1]['data']['memories']
    assert any(m['memory_id']==source and m['privacy_class']=='PERSONAL' for m in memories)
    assert not any(m['memory_id']==source for m in http(server,'views/memories',headers=ordinary)[1]['data']['memories'])
    denied=http(server,'privacy/withdrawal','POST',{**base(service,'private-withdraw-denied'),'operation':'WITHDRAW','target_id':source},ordinary)
    assert denied[0]==403
    service.supervisor.restart()
    assert len(http(server,'conversation/history',headers=headers)[1]['data']['items'])==1
    # A new session under a narrower host role cannot recover cached private text.
    service.auth.roles=tuple(r for r in service.auth.roles if r!=Role.PRIVATE_CONTEXT)
    ordinary_host=login(server,service)
    cached=http(server,'receipts/personal-one',headers=ordinary_host)[1]['data']
    assert cached['result']=={'state':'BODY_WITHHELD_SOURCE_CHANGED'}
    assert http(server,'conversation/history',headers=ordinary_host)[1]['data']['items']==[]
    # Explicit authorization restored for synthetic withdrawal only.
    service.auth.roles=tuple(Role)
    headers=login(server,service)
    forgotten=http(server,'privacy/withdrawal','POST',{**base(service,'personal-withdraw'),'operation':'WITHDRAW','target_id':source},headers)[1]
    assert forgotten['data']['state']=='VERIFIED',forgotten
    assert http(server,'conversation/history',headers=headers)[1]['data']['items']==[]


def test_personal_still_requires_surface_retention_and_provider_privacy(running):  # noqa: F811
    server,service=running
    headers=login(server,service)
    msg={**base(service,'default-denied'),'text':'PROJECT synthetic','privacy_class':'PERSONAL'}
    assert http(server,'messages','POST',msg,headers)[0]==403
    private_host(service,retention=False)
    msg={**base(service,'no-retention'),'text':'先不聊这个话题','privacy_class':'PERSONAL','retain_shared_life':True}
    result=http(server,'messages','POST',msg,headers)[1]['data']
    assert result['state']=='REJECTED' and not result['dispatch_happened']
    assert result['error']=='SURFACE_PERSONAL_RETENTION_NOT_AUTHORIZED'
    model={**base(service,'no-live-private'),'text':'synthetic current state','privacy_class':'PERSONAL','require_model':True}
    result=http(server,'messages','POST',model,headers)[1]['data']
    assert result['state']=='REJECTED' and not result['dispatch_happened']
    assert result['error']!='READY_LOCAL_GATES'
    assert http(server,'messages','POST',{**base(service,'secret-no'),'text':'synthetic','privacy_class':'SECRET'},headers)[0]==400
    principal=Principal('ordinary',(Role.READER,Role.CONVERSATION,Role.HOST_ADMIN),'WEB',None,service.auth.generation)
    from nana_core.life.live_api.contracts import PairOffer
    with pytest.raises(ApiError,match='ROLE_ESCALATION_DENIED'):
        service.auth.offer(principal,PairOffer(device_name='test',roles=(Role.PRIVATE_CONTEXT,)))
    assert 'PERSONAL' not in service.envelope({})['privacy_scope']


def test_private_binding_rejects_old_release_before_healthy_owner_stops(tmp_path):
    from tests.first_life_android_v2.test_supervisor import owned,cleanup
    from tests.living_release_v4.test_supervisor_secret_binding_contract import target_release
    from nana_core.life.live_api.supervisor import Supervisor
    home,binding,current=owned(tmp_path)
    binding=binding.model_copy(update={'privacy':('PUBLIC','PROJECT','PERSONAL')})
    supervisor=Supervisor(home,tmp_path/'host',binding,[current],active_release=current.release_id)
    try:
        supervisor.start();pid=supervisor.child.pid
        target=target_release(tmp_path,contract=2);supervisor.releases[target.release_id]=target
        with pytest.raises(ApiError,match='INCOMPATIBLE_PRIVATE_CONTEXT_CONTRACT'):
            supervisor.change_release(target.release_id,rollback=True)
        assert supervisor.child.pid==pid and supervisor.child.poll() is None
    finally:cleanup(supervisor)
