"""HTTP -> original ledger/UDS/owner/C -> loopback provider, no paid model."""
from contextlib import contextmanager
from types import SimpleNamespace
import shutil,threading
import pytest
from nana_core.life.live_api.auth import AuthService
from nana_core.life.live_api.bridge import GatewayService
from nana_core.life.live_api.contracts import Role
from nana_core.life.live_api.server import ApiServer
from tests.first_life_android_v2.test_supervisor import owned
from tests.first_life_android_v2.test_continuous_inputs import setup,running_owner
from tests.first_life_android_v2.test_http_integration import http,login,base,ORIGIN,PW
from tests.independent_life.test_dialogue import relay


@contextmanager
def sequence_api(tmp_path,roles=tuple(Role)):
    home,binding,_=owned(tmp_path);setup(home)
    with relay(home,'CHAT') as (router,calls),running_owner(home,router) as owner:
        shutil.copyfile(home/'test-providers.json',home/'providers.json')
        supervisor=SimpleNamespace(home=home,binding=binding,provider_live_authorized=False,
            status=lambda:{'owner_epoch':owner['control'].app.runtime.lease.epoch,'process_ready':True,'source_commit':'a'*40},
            verify_binding=lambda:None)
        service=GatewayService(supervisor,AuthService(tmp_path/'auth.json',password=PW,roles=roles),tmp_path/'gateway')
        server=ApiServer(('127.0.0.1',0),service,public_origin=ORIGIN)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:yield server,service,calls
        finally:server.shutdown();thread.join(3);server.server_close()


def body(service,key='sequence'):
    return {**base(service,key),'thread_id':'same-recipient','privacy_class':'PROJECT','require_model':True,
        'messages':[{'client_message_id':'part-'+str(i),'text':'SYNTHETIC sequence input '+str(i)} for i in range(3)]}


def test_actual_http_sequence_has_original_receipt_sources_and_idempotency(tmp_path):
    with sequence_api(tmp_path) as (server,service,calls):
        headers=login(server,service)
        bootstrap=http(server,'bootstrap',headers=headers)[1]
        assert bootstrap['capabilities']['conversation_sequence'] is True
        request=body(service)
        code,value,_=http(server,'messages/sequence','POST',request,headers)
        assert code==200 and value['data']['state']=='VERIFIED',value
        result=value['data']['result'];assert result['coalesced'] and len(result['results'])==3
        rows=result['results'];assert [r['client_message_id'] for r in rows]==['part-0','part-1','part-2']
        mids=[r['message_memory_id'] for r in rows]
        assert rows[-1]['respond_to_memory_ids']==mids and rows[0]['respond_to_memory_ids']==[]
        assert rows[-1]['text']=='A deliberately synthetic language response'
        assert len(calls)==4 and all(r['external_delivery'] is False for r in rows)
        assert http(server,'messages/sequence','POST',request,headers)[1]['data']['state']=='VERIFIED'
        assert len(calls)==4
        assert http(server,'receipts/sequence',headers=headers)[1]['data']['result']['results'][-1]['text']==rows[-1]['text']
        assert 'SYNTHETIC sequence input' not in service.ledger.document.path.read_text()


def test_lost_sequence_completion_stays_unknown_and_never_redispatches(tmp_path,monkeypatch):
    from nana_core.life.live_api import bridge
    original=bridge.core_request;dispatches=[]
    def lost(home,value,**kwargs):
        result=original(home,value,**kwargs)
        if value.get('operation')=='surface-sequence':dispatches.append(value);raise OSError('SYNTHETIC lost ACK')
        return result
    with sequence_api(tmp_path) as (server,service,calls):
        headers=login(server,service);http(server,'bootstrap',headers=headers)
        monkeypatch.setattr(bridge,'core_request',lost)
        request=body(service)
        assert http(server,'messages/sequence','POST',request,headers)[1]['data']['state']=='UNKNOWN'
        assert http(server,'receipts/sequence',headers=headers)[1]['data']['state']=='UNKNOWN'
        history=http(server,'conversation/history',headers=headers)[1]['data']
        assert history['pending_receipts']==[{'receipt_id':'sequence','state':'UNKNOWN'}]
        assert not history['items']
        assert http(server,'messages/sequence','POST',request,headers)[1]['data']['state']=='UNKNOWN'
        assert len(dispatches)==1 and len(calls)==4


@pytest.mark.parametrize('change,expected',[('private',403),('duplicate',400),('wire-bound',413),('csrf',403)])
def test_sequence_rejects_invalid_admission_without_core_effects(tmp_path,change,expected):
    with sequence_api(tmp_path) as (server,service,calls):
        headers=login(server,service);http(server,'bootstrap',headers=headers);request=body(service)
        if change=='private':request['privacy_class']='PERSONAL'
        elif change=='duplicate':request['messages'][1]['client_message_id']='part-0'
        elif change=='wire-bound':request['messages']=request['messages'][:2];[m.update(text='月'*2048) for m in request['messages']]
        elif change=='csrf':headers.pop('X-Nana-CSRF')
        assert http(server,'messages/sequence','POST',request,headers)[0]==expected
        assert not calls and service.ledger.revision==0


def test_old_core_status_does_not_advertise_or_dispatch_sequences(tmp_path,monkeypatch):
    from nana_core.life.live_api import bridge
    original=bridge.core_request;dispatches=[]
    def old_status(home,value,**kwargs):
        result=original(home,value,**kwargs)
        if value=={'operation':'view','view':'status'}:
            result['result'].pop('conversation_sequence',None)
        if value.get('operation')=='surface-sequence':dispatches.append(value)
        return result
    with sequence_api(tmp_path) as (server,service,calls):
        monkeypatch.setattr(bridge,'core_request',old_status)
        headers=login(server,service)
        assert http(server,'bootstrap',headers=headers)[1]['capabilities']['conversation_sequence'] is False
        code,response,_=http(server,'messages/sequence','POST',body(service),headers)
        assert code==200 and response['data']['state']=='REJECTED'
        assert response['data']['error']=='CONVERSATION_SEQUENCE_UNAVAILABLE'
        assert response['data']['dispatch_happened'] is False and not dispatches and not calls


def test_reader_does_not_acquire_conversation_write_permission(tmp_path):
    with sequence_api(tmp_path,roles=(Role.READER,)) as (server,service,calls):
        headers=login(server,service)
        assert http(server,'messages/sequence','POST',body(service),headers)[0]==403
        assert not calls and service.ledger.revision==0


def test_withdrawal_withholds_the_whole_multi_source_cached_reply(tmp_path):
    from nana_core.life.control import request
    with sequence_api(tmp_path) as (server,service,calls):
        headers=login(server,service);http(server,'bootstrap',headers=headers)
        saved=http(server,'messages/sequence','POST',body(service),headers)[1]['data']
        assert saved['state']=='VERIFIED'
        mid=saved['result']['results'][0]['message_memory_id']
        assert request(service.supervisor.home,{'operation':'forget','memory_id':mid})['ok']
        receipt=http(server,'receipts/sequence',headers=headers)[1]['data']
        assert receipt['state']=='VERIFIED' and receipt['result']=={'state':'BODY_WITHHELD_SOURCE_CHANGED'}
        assert 'A deliberately synthetic language response' not in str(receipt) and len(calls)==4
