"""HTTP parent review receipt, original C; followup still uses owned IPC here.

This does not qualify concurrent HTTP/Web admission, enabled only in fixture.
"""
import threading
import pytest
from .test_message_sequence_http import sequence_api
from .test_http_integration import login,http,base
from .test_continuous_inputs import launch,message,wait_pending


def test_deferred_parent_is_verified_review_without_speech_and_replays_only_its_receipt(tmp_path):
    release=threading.Event();blocked=threading.Event();threads=[];parent={}
    with sequence_api(tmp_path,coalesce_continuations=True) as (server,service,calls):
        control=service.fixture_owner['control'];factory=control.app.router.factory;original=factory.create
        def create(*args):
            port=original(*args);exchange=port.exchange
            def once(request):
                if request.cognitive_role=='INTERPRET' and not blocked.is_set():
                    blocked.set();assert release.wait(4)
                return exchange(request)
            port.exchange=once;return port
        factory.create=create;headers=login(server,service)
        body={**base(service,'deferred-parent'),'text':'SYNTHETIC original thought',
              'thread_id':'same-recipient','privacy_class':'PROJECT','require_model':True}
        def send():parent['response']=http(server,'messages','POST',body,headers)
        thread=threading.Thread(target=send,daemon=True);thread.start();threads.append(thread)
        try:
            assert blocked.wait(3)
            child,done,t2=launch(service.supervisor.home,message('deferred-child','SYNTHETIC added thought',thread_id='same-recipient'))
            threads.append(t2);wait_pending(control,1);release.set()
            thread.join(5);assert not thread.is_alive() and done.wait(5)
            code,envelope,_=parent['response'];receipt=envelope['data']
            assert code==200 and receipt['state']=='VERIFIED',envelope
            result=receipt['result']
            assert result['state']=='SHADOW_INPUT_REVIEWED_NO_REPLY' and result['text'] is None
            assert result['render_state']=='DEFERRED_TO_CONTINUATION' and result['respond_to_memory_ids']==[]
            assert result['external_delivery'] is False and result['completion_kind']=='SUBJECT_REVIEW_NOT_SOCIAL_DELIVERY'
            from nana_core.life.presentation import display
            assert display({'dialogue':result})=='本条已审阅，未单独生成回复。'
            followup=child['response']['result']
            assert followup['respond_to_memory_ids']==[result['message_memory_id'],followup['message_memory_id']]
            assert followup['reply_response_id']==followup['cycle_id'] and len(calls)==3
            saved=http(server,'receipts/'+body['idempotency_key'],headers=headers)[1]['data']
            assert saved['state']=='VERIFIED' and saved['result']==result
            assert http(server,'messages','POST',body,headers)[1]['data']['result']==result
            assert len(calls)==3
        finally:
            release.set()
            for thread in threads:thread.join(5)


@pytest.mark.parametrize('change',[{'text':'SYNTHETIC falsely presented speech'},{'raw_body_persisted':True},
    {'respond_to_memory_ids':['memory.synthetic']},{'message_memory_id':None},{'drop_text':True}])
def test_deferred_receipt_never_promotes_malformed_or_spoken_result(tmp_path,monkeypatch,change):
    import nana_core.life.live_api.bridge as bridge
    with sequence_api(tmp_path) as (server,service,calls):
        row={'state':'SHADOW_INPUT_REVIEWED_NO_REPLY','render_state':'DEFERRED_TO_CONTINUATION',
             'text':None,'message_memory_id':'memory.synthetic','respond_to_memory_ids':[],
             'raw_body_persisted':False,'exchange_record_id':None,**change}
        if row.pop('drop_text',False):row.pop('text')
        monkeypatch.setattr(bridge,'core_request',lambda *args,**kwargs:{'ok':True,'result':row})
        headers=login(server,service)
        body={**base(service,'invalid-deferred'),'text':'SYNTHETIC input','privacy_class':'PROJECT'}
        code,result,_=http(server,'messages','POST',body,headers)
        assert code==200 and result['data']['state']=='UNKNOWN'
        assert not result['data']['result'] and not calls


@pytest.mark.parametrize('empty',[None,'','   '])
def test_empty_model_draft_is_an_explicit_resource_result_not_invented_offline_speech(tmp_path,empty):
    from nana_core.life.application import LifeApplication
    from tests.first_life_android_v2.test_supervisor import owned
    from tests.first_life_android_v2.test_continuous_inputs import setup
    from tests.independent_life.test_dialogue import relay
    home,_,_=owned(tmp_path);setup(home)
    with relay(home,'CHAT',renderer=lambda request:empty) as (router,calls),LifeApplication(home,router=router) as app:
        app.pause();reply=app.chat('SYNTHETIC input with empty renderer',privacy='PROJECT',message_id='empty-draft')
        assert len(calls)==2 and reply['render_state']=='PROVIDER_EMPTY_DRAFT',reply
        assert reply['text']=='这次模型没有返回可用的回复。'
        assert reply['reply_response_id'] is None and reply['route'] is None
        assert reply['respond_to_memory_ids']==[reply['message_memory_id']]
        assert not app.runtime.store.all('actions')
