import hashlib
import json
import time
import pytest

from nana_core.life.application import LifeApplication
from nana_core.life.live_api import bridge
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_dialogue import relay
from .test_http_integration import running, http, login, base


def test_feedback_json_tag_arrays_keep_strict_consent_and_legacy_wire_shape():
    from nana_core.life.live_api.contracts import LanguageFeedbackRequest
    body={'client_request_id':'review','idempotency_key':'review','expected_revision':0,
        'run_generation':'a'*32,'owner_epoch':1,'exchange_record_id':'exchange','consent':True,
        'sample':{'sample_id':'review','review_target':'exchange','mode':'CASUAL','context':'synthetic',
            'candidate_response':'SYNTHETIC short reply','human_judgment':'REJECTED',
            'reason_tags':['TOO_VERBOSE'],'provenance':'USER_PROVIDED_REVIEW','observed_at_us':0}}
    parsed=LanguageFeedbackRequest.model_validate_json(json.dumps(body))
    assert parsed.sample.reason_tags==('TOO_VERBOSE',)
    assert 'response_sha256' not in parsed.model_dump(mode='json')
    for value in (False,1,'true',None):
        with pytest.raises(ValueError):LanguageFeedbackRequest.model_validate_json(json.dumps({**body,'consent':value}))


@pytest.mark.parametrize('reply', ['SYNTHETIC '+('long explanation. '*180),'🌙'*3000], ids=['ascii','unicode'])
@pytest.mark.parametrize('lost_ack',[False,True])
def test_long_reply_feedback_uses_original_exchange_hash_and_verify_only(running,monkeypatch,reply,lost_ack):
    server,service=running;headers=login(server,service)
    identity=service.binding.subject_id
    service.supervisor.stop()
    from nana_core.life.config import load_config,update_config
    config=load_config(service.supervisor.home)
    update_config(service.supervisor.home,config.model_copy(update={'revision':config.revision+1,
        'provider_calls_per_day':2,'provider_calls_per_hour':2,'per_provider_calls_per_day':2,
        'provider_total_calls_limit':2}),expected_revision=config.revision)
    with relay(service.supervisor.home,'CHAT',renderer=lambda _:reply,stream_fixture={}) as (router,requests):
        with LifeApplication(service.supervisor.home,clock=VirtualClock(time.time_ns()//1000),router=router) as app:
            app.pause();app.response_sink=lambda _:None
            turn=app.chat('SYNTHETIC explicit retained long reply',privacy='PROJECT',retain_shared_life=True)
            assert app.runtime.identity_id==identity and turn['text']==reply
    service.supervisor.start()
    sample={'sample_id':'synthetic.long-http-review','review_target':turn['exchange_record_id'],'mode':'CASUAL',
        'context':'SYNTHETIC long reply review','candidate_response':'DEPENDENT_RECORD_BODY',
        'human_judgment':'REJECTED','reason_tags':['TOO_VERBOSE'],'provenance':'USER_PROVIDED_REVIEW',
        'observed_at_us':time.time_ns()//1000}
    body={**base(service,'long-review'),'exchange_record_id':turn['exchange_record_id'],
        'sample':sample,'consent':True,'response_sha256':hashlib.sha256(reply.encode()).hexdigest()}
    old=bridge.core_request;calls=[]
    def request(home,value,**kwargs):
        response=old(home,value,**kwargs)
        if value.get('operation')=='language-feedback':
            calls.append(value)
            if lost_ack:raise OSError('SYNTHETIC lost ACK after original commit')
        return response
    monkeypatch.setattr(bridge,'core_request',request)
    code,saved,_=http(server,'conversation/feedback','POST',body,headers)
    assert code==200 and saved['data']['state']==('UNKNOWN' if lost_ack else 'VERIFIED'),saved
    checked=http(server,'receipts/long-review',headers=headers)[1]['data']
    assert checked['state']=='VERIFIED' and not checked['result']['delivery_proven'],checked
    assert len(calls)==1 and calls[0]['sample']['candidate_response']=='DEPENDENT_RECORD_BODY'
    assert reply not in str(calls[0])
    assert http(server,'conversation/feedback','POST',body,headers)[1]['data']['state']=='VERIFIED'
    assert len(calls)==1
    wrong={**body,**base(service,'wrong-long-review'),'response_sha256':'0'*64}
    rejected=http(server,'conversation/feedback','POST',wrong,headers)[1]['data']
    assert rejected['state']=='REJECTED' and not rejected['dispatch_happened'] and len(calls)==1
    assert len(requests)==2
