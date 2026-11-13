"""Original C's unretained focus reaches the actual wire, not an audit transcript."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.memory import MemoryService
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from .test_provider_subject_seedless import bare,event
from .test_provider_subject_preview import inputs
from .conftest import initialize


@pytest.mark.parametrize('interest',['color','rhythm'])
def test_actual_original_focus_changes_its_private_question_without_retaining_focus_text(tmp_path,interest):
    focus='PRIVATE_FOCUS_CANARY_'+interest;received=[]
    def propose(request):
        actual=request.media_input()['subject_cognition'];received.append(actual)
        selected=actual.get('task','').rsplit('_',1)[-1]
        selected=selected if selected in {'color','rhythm'} else None
        identity=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC original focus candidate',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='SYNTHETIC private association',proposed_operations=('DRAFT',) if selected else ('WAIT',),
            private_question={'topic':'own-'+selected,'question':'SYNTHETIC A new question about '+selected} if selected else None))
    with provider_harness(proposer=propose) as (transport,state),bare(tmp_path,VirtualClock()) as r:
        policy=ContextPolicy(policy_id='focus-private',allowed_scopes=('own-scope',),readable_privacy=('PROJECT',))
        session=CognitionSession(r,transport,policy)
        source=event(r,'focus').model_copy(update={'text':focus,'task_class':'own.research'})
        cycle=r.subject.cognize(source,model=session.subject_port(privacy_class='PROJECT',budget=CognitionBudget(input_tokens=32768)),authority=r.authority,policy=policy)
        assert cycle.judgment.stance=='REFLECT' and state['calls']==1 and len(received)==1
        assert received[0]['task']==focus and received[0]['task_class']=='own.research'
        assert [v.topic for _,v in candidates(r.store,'own-scope',('PROJECT',))]==['own-'+interest]
        assert not r.store.db.execute('SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),?)>0',(focus,)).fetchone()
        assert not r.store.db.execute('SELECT 1 FROM events WHERE instr(data_json,?)>0',(focus,)).fetchone()
        assert not r.store.all('goals') and not r.store.all('actions') and not session._volatile_inputs


def focus_options(options,task='PRIVATE_FOCUS_CANARY_bound'):
    from nana_core.continuity.world_loop.cognition import subject_focus_inputs
    frame=options['subject_frame']
    return {**options,**subject_focus_inputs(frame.subject_event_id,'PROJECT',task,'own.research')}


def test_focus_is_in_complete_wire_budget_preview_and_native_messages_but_not_saved_request(tmp_path):
    from tests.world_loop.test_model_framing import bind,exact_fixture
    from nana_core.continuity.world_loop.anthropic import AnthropicJSONTransport
    home=tmp_path/'home';initialize(home);requests=[]
    def propose(request):
        requests.append(request);identity=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC focused wait',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='SYNTHETIC wait',proposed_operations=('WAIT',)))
    with provider_harness(proposer=propose) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();mid,options=inputs(app);options=focus_options(options);options['budget']=CognitionBudget(input_tokens=65536)
        bind(transport);session=CognitionSession(app.runtime,transport,app.policy)
        snapshot=app.runtime.store.snapshot();writes=app.runtime.store.db.total_changes
        first=session.preview('original-focus','SELF',(mid,),**options)
        assert app.runtime.store.snapshot()==snapshot and app.runtime.store.db.total_changes==writes and not session._volatile_inputs
        # Both the private focus and its full protocol framing affect admission.
        longer=focus_options(options,'PRIVATE_FOCUS_CANARY_bound'+'x'*512)
        assert session.preview('longer-focus','SELF',(mid,),**longer)['token_accounting']['input_tokens']>first['token_accounting']['input_tokens']
        rid=session.prepare('original-focus','SELF',(mid,),**options)
        saved=session.records.read(app.runtime.store.one('cognitive_requests',rid)['record_id'])['payload']['request']
        assert 'PRIVATE_FOCUS_CANARY' not in json.dumps(saved)
        options['volatile_input']['subject_cognition']['task']='PRIVATE_MUTATED_AFTER_PREPARE'
        assert session.execute(rid)['state']=='PROPOSED' and state['calls']==1
        # The harness reconstructs the actual wire request, including volatile focus.
        actual=requests[0];assert actual.media_input()['subject_cognition']['task']=='PRIVATE_FOCUS_CANARY_bound'
        assert exact_fixture(json.loads(transport.request_body(actual)))==first['token_accounting']['input_tokens']
        native=AnthropicJSONTransport(transport.endpoint,transport.model_id,provider_id=transport.provider_id,harness=True)
        native_body=json.loads(native.request_body(actual))
        assert json.loads(native_body['messages'][0]['content'])['role_input']['subject_cognition']['task']=='PRIVATE_FOCUS_CANARY_bound'
        assert 'response_format' not in native_body and 'system' in native_body


@pytest.mark.parametrize('when',['owner-cache-lost','withdrawn'])
def test_expired_or_retired_focus_is_cleared_without_dispatch_or_replay(tmp_path,when):
    home=tmp_path/'home';initialize(home)
    with provider_harness() as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();mid,options=inputs(app);options=focus_options(options);session=CognitionSession(app.runtime,transport,app.policy)
        rid=session.prepare('focus-no-replay','SELF',(mid,),**options)
        if when=='owner-cache-lost':session=CognitionSession(app.runtime,transport,app.policy)
        else:MemoryService(app.runtime.store,app.runtime.authority).forget(mid,app.runtime.authority)
        result=session.execute(rid)
        assert result['state']=='STALE' and state['calls']==0 and not session._volatile_inputs
        assert session.execute(rid)['replayed'] and state['calls']==0


@pytest.mark.parametrize('fault',['missing','event','privacy','oversized','extra'])
def test_focus_body_cannot_cross_its_original_c_binding(tmp_path,fault):
    home=tmp_path/'home';initialize(home)
    with provider_harness() as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();mid,options=inputs(app);options=focus_options(options)
        actual=options['volatile_input']['subject_cognition']
        if fault=='missing':options['volatile_input']=None
        if fault=='event':actual['subject_event_id']='other-event'
        if fault=='privacy':actual['privacy_class']='PERSONAL'
        if fault=='oversized':actual['task']='x'*4097
        if fault=='extra':actual['external_authority']=True
        with pytest.raises(CoreError,match='SUBJECT_FOCUS_BINDING_INVALID'):
            CognitionSession(app.runtime,transport,app.policy).prepare('wrong-focus','SELF',(mid,),**options)
        assert not app.runtime.store.all('cognitive_requests') and state['calls']==0
