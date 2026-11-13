"""The original normal D, queue, lease and C drive an owned provider resource."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.autonomy.private_intent import candidates
from tests.first_life_integration.test_private_intent import _private_d_fixture


def proposer(request):
    context=json.loads(request.context_json);identity=context['manifest']
    plans=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE'
        and json.loads(b['data_json'])['category']=='PRIVATE_PLAN']
    return StructuredProposal(interpretation='SYNTHETIC private continuation candidate',subject_cognition=CognitiveProposal(
        identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='SYNTHETIC private research question',
        proposed_operations=('DRAFT',) if plans else ('WAIT',),private_question={
            'topic':'own-composition','question':'SYNTHETIC Could negative space connect the existing compositional interests?'} if plans else None))


def bind(runtime,transport,*,blocked=None,budget=None,previews=None):
    policy=ContextPolicy(policy_id='provider-normal-d',allowed_scopes=('own-scope',),readable_privacy=('PROJECT',))
    session=CognitionSession(runtime,transport,policy,max_calls_per_day=runtime.config.max_calls_per_day)
    budget=budget or CognitionBudget(input_tokens=32768)
    def preview(event,frame):
        if blocked and blocked[0]:raise CoreError('COGNITION_COST_BUDGET')
        if frame is None:return  # Coarse readiness before original source ingress.
        if previews is not None:previews.append(frame.subject_event_id)
        return session.preview('subject-cognition.'+frame.subject_event_id,'SELF',frame.source_memory_ids,
            subject_frame=frame,role_input={'subject_cognition':{'subject_event_id':frame.subject_event_id,'privacy_class':event.privacy_class}},budget=budget)
    runtime.cognition.bind_provider(lambda event:session.subject_port(privacy_class=event.privacy_class,budget=budget),preview)
    return session


def test_normal_d_provider_continues_private_plan_without_fixture_double_charge_or_polling(tmp_path):
    clock=VirtualClock();runtime,rid,plan=_private_d_fixture(tmp_path,clock)
    with provider_harness(proposer=proposer,delay=1.6) as (transport,state),runtime as r:
        identity=r.identity_id;previews=[];bind(r,transport,previews=previews)
        r.refresh_attention();r.step();assert state['calls']==0
        clock.advance(3*SECOND);r.refresh_attention()
        for _ in range(4):r.step()
        assert state['calls']==1 and len(r.store.all('cognitive_requests'))==1 and not r.store.all('runtime_cognition_calls')
        assert len(previews)==1  # Claim does not repeat the same full request preview.
        values=candidates(r.store,'own-scope',('PROJECT',))
        assert {v.category for _,v in values}=={'PRIVATE_PLAN','PRIVATE_QUESTION'}
        assert any('negative space' in v.content_summary for _,v in values)
        for _ in range(3):r.refresh_attention();r.step()
        assert state['calls']==1 and r.identity_id==identity and not r.store.all('actions') and not r.store.all('grants')


def test_queued_private_provider_pause_is_read_only_and_recovers_the_same_opportunity(tmp_path):
    clock=VirtualClock();runtime,rid,plan=_private_d_fixture(tmp_path,clock)
    with provider_harness(proposer=proposer) as (transport,state),runtime as r:
        clock.advance(3*SECOND);r._watch_sources();r.scheduler.due()
        qid=r.store.db.execute('SELECT last_queue_id FROM runtime_schedules WHERE dedupe_key=?',('private-thought.'+rid,)).fetchone()[0]
        blocked=[True];bind(r,transport,blocked=blocked)
        r.step();assert r.store.one('runtime_queue',qid)['state']=='READY'
        writes=r.store.db.total_changes;events=len(r.store.all('events'))
        for _ in range(4):r.refresh_attention();r.step()
        assert r.store.db.total_changes==writes and len(r.store.all('events'))==events
        assert r.store.one('runtime_queue',qid)['attempts']==0 and state['calls']==0
        blocked[0]=False
        assert r.step()['queue_id']==qid and state['calls']==1
        assert r.store.one('runtime_queue',qid)['state']=='DONE' and not r.store.all('runtime_cognition_calls')


def test_provider_foreground_preemption_remains_unknown_without_retrying_after_restart(tmp_path):
    from nana_core.presence import NanaRuntime
    from nana_core.presence.contracts import RuntimeEvent,Cause
    from nana_core.continuity.subject import SubjectInput
    clock=VirtualClock();runtime,rid,plan=_private_d_fixture(tmp_path,clock);config=runtime.config;path=runtime.store.path;identity=runtime.identity_id
    with provider_harness(proposer=proposer,delay=.15) as (transport,state):
        with runtime as r:
            bind(r,transport);incoming=[]
            def control():
                if incoming:return
                event=SubjectInput(source_key='synthetic.provider-d-user',kind='INTERACTION',origin='USER',entity_id='counterparty',scope='own-scope',
                    privacy_class='PROJECT',observed_at_us=clock.utc_now_us(),text='SYNTHETIC foreground interruption',source_memory_ids=plan.source_memory_ids)
                incoming.append(r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=event,causes=(Cause(kind='MEMORY',reference_id=plan.source_memory_ids[0]),),due_at_us=clock.utc_now_us())))
            r.control_progress=control;clock.advance(3*SECOND);r.refresh_attention()
            result=r.step()
            assert result['reason']=='PREEMPTED_NO_AUTOMATIC_RETRY' and result['cycle'] is None
            request=dict(r.store.all('cognitive_requests')[0]);assert request['state']=='UNKNOWN' and state['calls']==1
            assert r.step()['queue_id']==incoming[0]
        with NanaRuntime(path,config,clock=clock) as r:
            bind(r,transport);clock.advance(3*SECOND);r.refresh_attention()
            for _ in range(4):r.step()
            assert state['calls']==1 and r.identity_id==identity
            assert dict(r.store.one('cognitive_requests',request['request_id']))==request
            assert not r.store.all('runtime_cognition_calls') and not r.store.all('actions')


@pytest.mark.parametrize('when',['queued','factory-race'])
def test_provider_private_source_withdrawal_retires_without_network_dispatch(tmp_path,when):
    from nana_core.continuity.memory import MemoryService
    clock=VirtualClock();runtime,rid,plan=_private_d_fixture(tmp_path,clock)
    with provider_harness(proposer=proposer) as (transport,state),runtime as r:
        clock.advance(3*SECOND);r._watch_sources();r.scheduler.due()
        qid=r.store.db.execute('SELECT last_queue_id FROM runtime_schedules WHERE dedupe_key=?',('private-thought.'+rid,)).fetchone()[0]
        session=bind(r,transport)
        def forget():MemoryService(r.store,r.authority).forget(plan.source_memory_ids[0],r.authority)
        if when=='queued':forget()
        else:
            original=r.cognition.provider_factory
            def race(event):forget();return original(event)
            r.cognition.provider_factory=race
        r.step()
        assert r.store.one('runtime_queue',qid)['state']=='IGNORED' and state['calls']==0
        assert not r.store.all('cognitive_requests') and not r.store.all('runtime_cognition_calls')


def test_life_application_explicit_binding_uses_its_actual_route_and_host_limits(tmp_path):
    from nana_core.life.application import LifeApplication
    from tests.independent_life.test_dialogue import relay
    from .conftest import initialize
    from .test_inner_communication import seed
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    def inner(request):
        identity=json.loads(request['context_json'])['manifest']
        return {'interpretation':'SYNTHETIC application-owned resource','subject_cognition':{
            'identity_id':identity['identity_id'],'identity_revision':identity['identity_revision'],
            'interpretation':'SYNTHETIC new private association','proposed_operations':['DRAFT'],
            'private_question':{'topic':'own-curiosity','question':'SYNTHETIC Could this private interest connect to a new creative method?'}}}
    with relay(home,context_limit=32768,subject_builder=inner) as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
        app.pause();seed(app);identity=app.runtime.identity_id
        assert app.runtime.cognition.provider_factory is None
        binding=app.bind_provider_cognition();assert binding['enabled'] and binding['dispatch_happened'] is False and not requests
        app.bind_provider_cognition(False);assert app.runtime.cognition.provider_factory is None and not requests
        app.bind_provider_cognition();app.pause(False);clock.advance(2*SECOND);app.runtime.refresh_attention()
        for _ in range(5):app.runtime.step()
        assert len(requests)==1 and requests[0]['cognitive_role']=='SELF'
        assert requests[0]['budget']['timeout_ms']==app.config.provider_timeout_ms==120000
        assert requests[0]['budget']['input_tokens']<=app.config.provider_context_tokens
        assert len(app.runtime.store.all('cognitive_requests'))==1 and not app.runtime.store.all('runtime_cognition_calls')
        assert any('new creative method' in value.content_summary for _,value in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')))
        assert app.runtime.identity_id==identity and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_normal_provider_d_without_inner_projection_does_not_form_the_same_question(tmp_path,monkeypatch):
    from nana_core.continuity.autonomy import private_intent
    clock=VirtualClock();runtime,rid,plan=_private_d_fixture(tmp_path,clock)
    with provider_harness(proposer=proposer) as (transport,state),runtime as r:
        bind(r,transport)
        monkeypatch.setattr(private_intent,'internal_projection',lambda *args,**kwargs:())
        clock.advance(3*SECOND);r.refresh_attention()
        for _ in range(4):r.step()
        assert state['calls']==1 and len(r.store.all('cognitive_requests'))==1
        values=candidates(r.store,'own-scope',('PROJECT',))
        assert {v.category for _,v in values}=={'PRIVATE_PLAN'} and values[0][1].activity_state=='ACTIVE'
        assert not r.store.all('runtime_cognition_calls') and not r.store.all('actions')
