"""Finite admitted response survives access expiry; new requests and revocation do not."""
import http.client as http_client
import json
import pytest
from nana_core.life.live_api.auth import AuthService
from nana_core.life.live_api.contracts import ApiError, Role
from nana_core.life.live_api.server import PREFIX
from tests.first_life_android_v2.test_http_integration import PW, login, http, base
from tests.first_life_android_v2.test_message_sequence_http import sequence_api, body


def test_response_permit_is_finite_scoped_and_does_not_renew_access(tmp_path):
    now=[0.0]
    auth=AuthService(tmp_path/'auth.json',password=PW,roles=tuple(Role),clock=lambda:now[0])
    token,csrf=auth.login(PW)
    permit=auth.admit_response(token,'WEB',csrf=csrf,timeout=1230)
    other,_=auth.login(PW)
    now[0]=601
    with pytest.raises(ApiError,match='SESSION_REVOKED'):auth.authorize(token,'WEB')
    assert auth.authorize(token,'WEB',response=permit,csrf=csrf,mutating=True).principal_id=='host.web'
    with pytest.raises(ApiError,match='SESSION_REVOKED'):auth.authorize(other,'WEB',response=permit)
    with pytest.raises(ApiError,match='CSRF_DENIED'):auth.authorize(token,'WEB',response=permit,csrf='wrong',mutating=True)
    with pytest.raises(ApiError,match='SESSION_REVOKED'):auth.admit_response(token,'WEB',csrf=csrf,timeout=1230)
    now[0]=1230
    with pytest.raises(ApiError,match='SESSION_REVOKED'):auth.authorize(token,'WEB',response=permit)
    auth.end_response(permit)
    assert not auth.responses


@pytest.mark.parametrize('change',['logout','roles','generation','release','device'])
def test_response_permit_never_overrides_live_revocation(tmp_path,change):
    now=[0.0]
    auth=AuthService(tmp_path/'auth.json',password=PW,roles=tuple(Role),clock=lambda:now[0])
    token,csrf=auth.login(PW)
    admin=auth.authorize(token,'WEB')
    kind='WEB'
    if change=='device':
        device,refresh=auth.login_device(PW,'SYNTHETIC phone')
        token=auth.native_session(device,refresh);kind='NATIVE'
    permit=auth.admit_response(token,kind,csrf=csrf,timeout=1230)
    now[0]=601
    if change=='logout':auth.logout(token)
    elif change=='roles':auth.roles=(Role.READER,)
    elif change=='generation':auth.generation+=1
    elif change=='release':auth.end_response(permit)
    elif change=='device':auth.revoke(admin,device)
    with pytest.raises(ApiError,match='SESSION_REVOKED'):auth.authorize(token,kind,response=permit)
    auth.end_response(permit)


def test_expired_session_pruning_keeps_only_an_active_bounded_response(tmp_path):
    now=[0.0]
    auth=AuthService(tmp_path/'auth.json',password=PW,clock=lambda:now[0])
    token,csrf=auth.login(PW)
    permit=auth.admit_response(token,'WEB',csrf=csrf,timeout=1230)
    principal=auth.authorize(token,'WEB')
    for _ in range(63):auth._session(principal)
    now[0]=601
    auth._session(principal)  # original 64-session pruning path
    assert len(auth.sessions)==2
    assert auth.authorize(token,'WEB',response=permit)==principal
    auth.end_response(permit)
    with pytest.raises(ApiError,match='SESSION_REVOKED'):auth.authorize(token,'WEB',response=permit)
    assert not auth.responses


@pytest.mark.parametrize('route',['messages','messages/sequence','messages/stream'])
@pytest.mark.parametrize('change',['expiry','logout','roles'])
def test_real_http_core_completion_after_access_expiry_or_revocation(tmp_path,monkeypatch,route,change):
    from nana_core.life.live_api import bridge
    original=bridge.core_request
    now=[0.0]
    with sequence_api(tmp_path) as (server,service,calls):
        service.auth.clock=lambda:now[0]
        headers=login(server,service)
        http(server,'bootstrap',headers=headers)
        token=headers['Cookie'].split('=',1)[1].split(';',1)[0]
        def advance(home,command,**kwargs):
            if command.get('operation') in {'surface','surface-sequence','surface-stream'}:
                now[0]=601
                if change=='logout':service.auth.logout(token)
                if change=='roles':service.auth.roles=(Role.READER,)
            return original(home,command,**kwargs)
        monkeypatch.setattr(bridge,'core_request',advance)
        request=body(service) if route.endswith('sequence') else {
            **base(service,'single'),'text':'SYNTHETIC bounded response',
            'privacy_class':'PROJECT','require_model':True}
        if route.endswith('stream'):
            connection=http_client.HTTPConnection(*server.server_address,timeout=10)
            connection.request('POST',PREFIX+'/'+route,json.dumps(request),
                {'Host':'space.test','Content-Type':'application/json',**headers})
            response=connection.getresponse();frames=[json.loads(line) for line in response.read().splitlines()]
            connection.close()
            if change=='expiry':
                assert response.status==200 and frames[-1]['event']=='receipt',frames
                result=frames[-1]['data']['data']
            else:
                assert response.status==401 or frames[-1].get('code')=='SESSION_REVOKED',frames
                assert 'A deliberately synthetic language response' not in str(frames)
        else:
            code,value,_=http(server,route,'POST',request,headers)
            if change=='expiry':assert code==200,value;result=value['data']
            else:assert code==401 and value['code']=='SESSION_REVOKED',value
        if change=='expiry':
            assert result['state']=='VERIFIED',result
            assert 'A deliberately synthetic language response' in str(result)
        assert len(calls)==(4 if route.endswith('sequence') else 2)
        assert http(server,'bootstrap',headers=headers)[0]==401
        assert not service.auth.responses


@pytest.mark.parametrize('change',['expiry','logout'])
def test_real_sse_prefix_and_remaining_frames_recheck_bounded_response(tmp_path,monkeypatch,change):
    import threading
    from nana_core.life.live_api import bridge
    original=bridge.core_request
    release=threading.Event();release.set()
    now=[0.0];prefixes=[]
    response_text='SYNTHETIC original long response '+('source-bound continuation. '*220)
    with sequence_api(tmp_path,stream_fixture={'release':release},renderer=lambda _:response_text) as (server,service,calls):
        service.auth.clock=lambda:now[0]
        headers=login(server,service)
        token=headers['Cookie'].split('=',1)[1].split(';',1)[0]
        def during(home,command,**kwargs):
            if command.get('operation')=='surface-stream':
                progress=kwargs['progress']
                def emit(value):
                    progress(value)
                    if value.get('text') and not prefixes:
                        prefixes.append(value['text']);now[0]=601
                        if change=='logout':service.auth.logout(token)
                kwargs['progress']=emit
            return original(home,command,**kwargs)
        monkeypatch.setattr(bridge,'core_request',during)
        request={**base(service,'prefix'),'text':'SYNTHETIC finite live stream',
            'privacy_class':'PROJECT','require_model':True}
        connection=http_client.HTTPConnection(*server.server_address,timeout=10)
        connection.request('POST',PREFIX+'/messages/stream',json.dumps(request),
            {'Host':'space.test','Content-Type':'application/json',**headers})
        response=connection.getresponse();frames=[json.loads(line) for line in response.read().splitlines()]
        connection.close()
        assert response.status==200 and prefixes and len(calls)==2
        assert len(prefixes[0]) < len(response_text), 'must revoke after a partial prefix'
        assert frames[-1]['event']==('receipt' if change=='expiry' else 'error'),frames
        if change=='expiry':
            assert frames[-1]['data']['data']['state']=='VERIFIED'
            assert frames[-1]['data']['data']['result']['text']==response_text
        else:
            assert frames[-1]['code']=='SESSION_REVOKED'
            assert response_text not in str(frames)
            assert not any(f['event']=='receipt' for f in frames)
            # Revocation stops delivery; the independent original Core can
            # still finish. Preserve its verified receipt, never fake UNKNOWN.
            assert service.ledger.entry('prefix')['receipt']['state']=='VERIFIED'
            fresh=login(server,service)
            restored=http(server,'receipts/prefix',headers=fresh)[1]['data']
            assert restored['state']=='VERIFIED' and restored['result']['text']==response_text
            assert len(calls)==2
        assert http(server,'bootstrap',headers=headers)[0]==401
        assert not service.auth.responses
