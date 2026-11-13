"""No old experience is needed to consider a provider resource or a new thought."""
import json
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.cognition import CognitiveProposal,AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.presence import NanaRuntime
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import RuntimeConfig


def bare(tmp_path,clock):
    path=tmp_path/'bare'/'self.db';authority=OperatorAuthority()
    with ContinuityStore(path,clock,schema_target=13) as store:
        IdentityService(store,authority);MemoryService(store).entity('counterparty','PERSON')
    return NanaRuntime(path,RuntimeConfig(schema_target=13,scopes=('own-scope',),entity_id='counterparty',privacy_classes=('PROJECT',)),clock=clock)


def event(r,key='seedless'):
    return SubjectInput(source_key='synthetic.provider.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='counterparty',scope='own-scope',
        privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us())


def test_seedless_provider_can_form_a_private_question_from_its_own_real_consideration(tmp_path):
    clock=VirtualClock();runtime=bare(tmp_path,clock);received=[]
    def propose(request):
        received.append(request);identity=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC internal candidate',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='PRIVATE_SEEDLESS_REASON',proposed_operations=('DRAFT',),
            private_question={'topic':'own-seedless-interest','question':'PRIVATE_SEEDLESS_QUESTION'}))
    with provider_harness(proposer=propose) as (transport,state),runtime as r:
        assert not r.store.all('memories') and not r.store.all('continuity_records')
        policy=ContextPolicy(policy_id='seedless-provider',allowed_scopes=('own-scope',),readable_privacy=('PROJECT',))
        session=CognitionSession(r,transport,policy);source=event(r);identity=r.identity_id
        cycle=r.subject.cognize(source,model=session.subject_port(privacy_class='PROJECT',budget=CognitionBudget(input_tokens=32768)),authority=r.authority,policy=policy)
        assert cycle.judgment.stance=='REFLECT' and state['calls']==1
        values=candidates(r.store,'own-scope',('PROJECT',));assert len(values)==1 and values[0][1].content_summary=='PRIVATE_SEEDLESS_QUESTION'
        roots=[MemoryService(r.store).read(row['memory_id']) for row in r.store.all('memories')]
        assert len(roots)==1 and roots[0]['source_provenance']['source_namespace']=='recorded.subject.provider-consideration'
        from nana_core.continuity.contracts import SELF_PROVIDER_CONSIDERATION_TEXT
        assert roots[0]['text']==SELF_PROVIDER_CONSIDERATION_TEXT and roots[0]['entity_id']==identity
        assert roots[0]['source_provenance']['domain']=='SELF_COGNITION' and roots[0]['importance']==roots[0]['significance']==0
        assert 'PRIVATE_SEEDLESS_' not in roots[0]['text'] and len(r.store.all('cognitive_requests'))==1
        assert not r.store.all('runtime_cognition_calls') and not r.store.all('actions') and not r.subject.pending('own-scope')
        root=roots[0]['memory_id'];cycle_id=cycle.cycle_id;path=r.store.path;config=r.config
    with NanaRuntime(path,config,clock=clock) as r:
        assert r.identity_id==identity and r.subject.result(r.store.one('subject_cycles',cycle_id)).judgment.stance=='REFLECT'
        MemoryService(r.store,r.authority).forget(root,r.authority)
        assert not candidates(r.store,'own-scope',('PROJECT',))
        assert not r.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'PRIVATE_SEEDLESS_QUESTION')>0").fetchone()
        with pytest.raises(CoreError,match='SUBJECT_RATIONALE_RETIRED'):r.subject.run(source)
    assert len(received)==1


@pytest.mark.parametrize('provider',[False,True],ids=['fixture-transient','provider-audit-only'])
def test_seedless_passing_thought_is_not_saved_as_thought_or_goal(tmp_path,provider):
    runtime=bare(tmp_path,VirtualClock());policy=ContextPolicy(policy_id='transient-seedless',allowed_scopes=('own-scope',),readable_privacy=('PROJECT',))
    def propose(request):
        identity=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='PRIVATE_TRANSIENT_REASON',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='PRIVATE_TRANSIENT_REASON',
            proposed_operations=('DRAFT',),passing_thought='PRIVATE_TRANSIENT_ASSOCIATION'))
    with provider_harness(proposer=propose) as (transport,state),runtime as r:
        class Passing:
            descriptor='synthetic-passing-only'
            def propose(self,request):
                value=json.loads(AnalyticalFixturePort().propose(request));value['passing_thought']='PRIVATE_TRANSIENT_ASSOCIATION'
                return json.dumps(value)
        model=CognitionSession(r,transport,policy).subject_port(privacy_class='PROJECT') if provider else Passing()
        r.subject.cognize(event(r),model=model,authority=r.authority,policy=policy)
        assert state['calls']==int(provider) and len(r.store.all('memories'))==int(provider)
        assert not candidates(r.store,'own-scope',('PROJECT',)) and not r.store.all('goals')
        assert not r.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'PRIVATE_TRANSIENT_ASSOCIATION')>0").fetchone()


@pytest.mark.parametrize('outcome',['resume','withdraw','restart'])
def test_seedless_normal_d_resource_wait_does_not_reclaim_or_rewrite_and_can_resume(tmp_path,outcome):
    from nana_core.presence.contracts import RuntimeEvent,Cause
    from tests.world_loop.test_model_framing import bind as bind_counter
    from .test_provider_subject_runtime import bind
    clock=VirtualClock();runtime=bare(tmp_path,clock)
    def propose(request):
        identity=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC continuation',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='SYNTHETIC independent choice',proposed_operations=('WAIT',)))
    with provider_harness(proposer=propose) as (transport,state),runtime as r:
        bind_counter(transport,lambda body:70000);bind(r,transport)
        source=event(r,'blocked').model_copy(update={'significance':'HIGH','novelty':'HIGH','uncertainty':'HIGH'})
        qid=r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=source,
            causes=(Cause(kind='CANONICAL_SELF',reference_id=r.identity_id),),due_at_us=clock.utc_now_us()))
        result=r.step()
        assert result['reason']=='INSUFFICIENT_CONTEXT_BUDGET'
        assert r.store.one('runtime_queue',qid)['state']=='DEFERRED' and len(r.store.all('memories'))==1
        assert state['calls']==0 and not r.store.all('cognitive_requests')
        r.refresh_attention();r.step()
        writes=r.store.db.total_changes;events=len(r.store.all('events'));attempts=r.store.one('runtime_queue',qid)['attempts']
        for _ in range(4):r.refresh_attention();r.step()
        assert r.store.db.total_changes==writes and len(r.store.all('events'))==events
        assert r.store.one('runtime_queue',qid)['attempts']==attempts==1
        if outcome=='withdraw':
            root=r.store.all('memories')[0]['memory_id']
            MemoryService(r.store,r.authority).forget(root,r.authority)
            r.step()
            assert r.store.one('runtime_queue',qid)['state']=='IGNORED' and state['calls']==0
            assert not r.store.all('cognitive_requests')
        elif outcome=='restart':
            path=r.store.path;config=r.config;identity=r.identity_id
        else:
            transport.token_counter=None
            assert r.step()['queue_id']==qid and state['calls']==1
            assert r.store.one('runtime_queue',qid)['state']=='DONE' and len(r.store.all('memories'))==1
            assert len(r.store.all('cognitive_requests'))==1 and not r.store.all('runtime_cognition_calls')
    if outcome=='restart':
        # Restart never silently enables paid cognition; the owner must rebind.
        with provider_harness(proposer=propose) as (transport,state),NanaRuntime(path,config,clock=clock) as r:
            assert r.identity_id==identity and r.cognition.provider_factory is None
            bind(r,transport)
            assert r.step()['queue_id']==qid and state['calls']==1
            assert len(r.store.all('memories'))==1 and len(r.store.all('cognitive_requests'))==1
            assert not r.store.all('runtime_cognition_calls')


def test_nonretention_never_creates_provider_consideration_root(tmp_path):
    with provider_harness() as (transport,state),bare(tmp_path,VirtualClock()) as r:
        policy=ContextPolicy(policy_id='seedless-nonretention',allowed_scopes=('own-scope',),readable_privacy=('PROJECT',))
        source=event(r,'nonretention').model_copy(update={'retention':'DO_NOT_REMEMBER'})
        r.subject.cognize(source,model=CognitionSession(r,transport,policy).subject_port(privacy_class='PROJECT'),authority=r.authority,policy=policy)
        assert not r.store.all('memories') and not r.store.all('cognitive_requests') and state['calls']==0
