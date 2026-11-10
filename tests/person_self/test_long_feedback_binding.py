import hashlib
import json
import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.lived_language import LanguageSample, LanguageService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_dialogue import relay
from .conftest import initialize


@pytest.mark.parametrize('reply', ['SYNTHETIC '+('long explanation. '*180), '🌙'*3000], ids=['ascii','unicode'])
def test_long_feedback_binds_full_source_without_copying_body_into_legacy_sample(tmp_path, reply):
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',renderer=lambda _:reply,stream_fixture={}) as (router,requests), LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();app.response_sink=lambda _:None
        turn=app.chat('SYNTHETIC retained discussion',privacy='PROJECT',retain_shared_life=True)
        assert turn['text']==reply
        exchange=turn['exchange_record_id']
        sample=LanguageSample(sample_id='synthetic.long-review',review_target=exchange,mode='CASUAL',
            context='SYNTHETIC whole-response review',candidate_response='DEPENDENT_RECORD_BODY',
            human_judgment='REJECTED',reason_tags=('TOO_VERBOSE',),provenance='USER_PROVIDED_REVIEW',
            observed_at_us=app.runtime.clock.utc_now_us())
        sha=hashlib.sha256(reply.encode()).hexdigest()
        service=LanguageService(app.runtime.store,app.runtime.authority)
        args=dict(scope=app.runtime.config.scopes[0],entity_id=app.runtime.config.entity_id,privacy='PROJECT',
            authority=app.runtime.authority,exchange_record_id=exchange,response_sha256=sha)
        rid=service.record(sample,**args)
        assert service.record(sample,**args)==rid
        stored=RecordService(app.runtime.store).read(rid)['payload']
        assert stored['sample']['candidate_response']=='DEPENDENT_RECORD_BODY'
        assert stored['response_sha256']==sha
        assert reply not in str(stored)
        (tmp_path/'legacy-sample.json').write_text(json.dumps(stored['sample']))
        assert LanguageSample.model_validate_json(json.dumps(stored['sample'])).candidate_response=='DEPENDENT_RECORD_BODY'
        from nana_core.continuity.lived_language import context
        projected=context(app.runtime.store,scope=args['scope'],privacy=('PROJECT',),mode='CASUAL')
        assert projected['examples'][0]['candidate_response']==reply[:384]
        assert projected['examples'][0]['candidate_response_truncated'] is True
        with pytest.raises(CoreError,match='TURN_MISMATCH'):
            service.record(sample.model_copy(update={'sample_id':'synthetic.wrong-long-review'}),
                **{**args,'response_sha256':'0'*64})
        MemoryService(app.runtime.store,app.runtime.authority).forget(turn['message_memory_id'],app.runtime.authority)
        assert not RecordService(app.runtime.store).current_support(rid)
        assert len(requests)==2 and not app.runtime.store.all('actions')
