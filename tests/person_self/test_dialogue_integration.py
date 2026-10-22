import json
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_dialogue import relay
from .conftest import initialize


def test_original_transport_c_role_adoption_both_sides_and_restart(tmp_path):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    p={'kind':'RELATIONSHIP_ROLE','operation':'PROPOSE','value':'sibling','quote':'sibling'}
    with relay(home,'CHAT',conversation_proposal=p) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();identity=app.runtime.identity_id
            a=app.chat('Please use sibling as our relationship label',privacy='PROJECT',retain_shared_life=True,message_id='adopt')
            assert a['render_state']=='UNVERIFIED_MODEL_WORDING',a
            assert a['conversation_decision']['choice']=='ADOPT'
            assert a['raw_body_persisted'] and a['exchange_record_id']
            assert requests[-1]['role_input']['dialogue']['conversation_decision']['choice']=='ADOPT'
        with LifeApplication(home,clock=clock,router=router) as app:
            # A different surface/topic may retrieve the enduring relationship;
            # it is not dependent on remembering the last six user messages.
            p.clear()
            result=app.chat('What role do we use?',topic='later',privacy='PROJECT',retain_shared_life=True,message_id='recall')
            assert result['render_state']=='UNVERIFIED_MODEL_WORDING',result
            context=json.loads(requests[-1]['context_json'])
            person=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='PERSON_SELF')
            assert person['adopted_conventions'][0]['value']=='sibling'
            assert app.runtime.identity_id==identity
            assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_default_transient_history_has_assistant_side_but_not_store(tmp_path):
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();app.chat('PROJECT_TRANSIENT_CANARY',privacy='PROJECT',message_id='first')
        result=app.chat('Please continue',privacy='PROJECT',message_id='second')
        assert result['render_state']=='UNVERIFIED_MODEL_WORDING',result
        turns=requests[-1]['role_input']['dialogue']['recent_turns']
        assert any(t['speaker']=='ASSISTANT' for t in turns)
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'PROJECT_TRANSIENT_CANARY')>0 OR instr(CAST(payload AS TEXT),'A deliberately synthetic language response')>0").fetchone()


def test_withdrawal_removes_retained_exchange_from_restart_context(tmp_path):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with relay(home,'CHAT') as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();first=app.chat('RETAINED_CANARY',privacy='PROJECT',retain_shared_life=True)
            assert first['exchange_record_id']
            app.forget(first['message_memory_id'])
        with LifeApplication(home,clock=clock,router=router) as app:
            later=app.chat('Continue',privacy='PROJECT')
            assert later['render_state']=='UNVERIFIED_MODEL_WORDING',later
            assert 'RETAINED_CANARY' not in requests[-1]['context_json']


def test_unknown_still_no_retry_with_retained_input(tmp_path,monkeypatch):
    from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
    home=tmp_path/'home';initialize(home);calls=[];clock=VirtualClock()
    def timeout(self,request):calls.append(request.request_id);raise TimeoutError()
    monkeypatch.setattr(OpenAIJSONTransport,'exchange',timeout)
    with relay(home,'CHAT') as (router,_):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();app.chat('first',privacy='PROJECT',retain_shared_life=True)
        with LifeApplication(home,clock=clock,router=router) as app:
            app.chat('different',privacy='PROJECT',retain_shared_life=True)
            assert len(calls)==1
            assert app.runtime.store.all('cognitive_requests')[0]['state']=='UNKNOWN'


def test_learned_policy_changes_later_unrelated_render_after_restart(tmp_path):
    from .test_learning import record,activate
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    def render(request):
        context=json.loads(request['context_json'])
        active=any(b['kind']=='LIVED_LANGUAGE' and json.loads(b['data_json'])['policy']['state']=='ACTIVE_BOUNDED_HYPOTHESIS' for b in context['blocks'])
        return 'SYNTHETIC: concise contextual wording' if active else 'SYNTHETIC: First, I will summarize your requirements and propose a trial period.'
    with relay(home,'CHAT',renderer=render) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();before=app.chat('casual synthetic case',privacy='PROJECT')
            assert before['render_state']=='UNVERIFIED_MODEL_WORDING',before
            record(app,1);_,eid=record(app,2);activate(app,eid)
        with LifeApplication(home,clock=clock,router=router) as app:
            after=app.chat('unrelated later case',topic='another',privacy='PROJECT')
            assert after['render_state']=='UNVERIFIED_MODEL_WORDING',after
            assert 'concise contextual' in after['text']
            assert before['text']!=after['text']
            assert len(requests)==4  # loopback only, never a real provider
