"""Owned HTTP -> existing provider ledger -> original C; no real provider calls."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.project_work.service import capture
from .conftest import initialize


def event_for(app,key='provider-subject'):
    r=app.runtime
    cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CREATIVE_INTEREST',topic_key='private-creation',possible_behaviors=('CREATE','REST'))
    mid=capture(r,key,cue.model_dump(mode='json'),predicate='concern.'+key)
    return mid,SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.'+key,kind='WAKE',origin='SELF_WAKE',
        entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))


def candidate(request,**changes):
    context=json.loads(request.context_json);identity=context['manifest']
    body=dict(identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],
        interpretation='PRIVATE_CANDIDATE_REASON_CANARY',proposed_operations=('DRAFT',),preferred_behavior='REST')
    body.update(changes)
    return StructuredProposal(interpretation='PRIVATE_ROOT_REASON_CANARY',source_refs=(),subject_cognition=CognitiveProposal(**body))


def test_provider_resource_uses_original_ledger_then_c_chooses_without_private_candidate_log(tmp_path):
    home=tmp_path/'home';initialize(home);requests=[]
    def propose(request):
        requests.append(request)
        context=json.loads(request.context_json);identity=context['manifest']
        return StructuredProposal(interpretation='PRIVATE_ROOT_REASON_CANARY',source_refs=(),
            subject_cognition=CognitiveProposal(identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],
                interpretation='PRIVATE_CANDIDATE_REASON_CANARY',proposed_operations=('DRAFT',),preferred_behavior='REST',
                passing_thought='PRIVATE_PASSING_ASSOCIATION_CANARY'))
    with provider_harness(proposer=propose) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime
        cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CREATIVE_INTEREST',topic_key='private-creation',possible_behaviors=('CREATE','REST'))
        mid=capture(r,'provider-subject-opportunity',cue.model_dump(mode='json'),predicate='concern.provider-subject')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.provider-subject',kind='WAKE',origin='SELF_WAKE',
            entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        session=CognitionSession(r,transport,app.policy,max_calls_per_day=24)
        cycle=r.subject.cognize(event,model=session.subject_port(privacy_class='PROJECT',budget=CognitionBudget(input_tokens=32768)),authority=r.authority,policy=app.policy)
        assert cycle.intention.behavior=='REST' and cycle.intention.kind=='NO_ACTION'
        assert r.subject.cognize(event,model=session.subject_port(privacy_class='PROJECT'),authority=r.authority,policy=app.policy).cycle_id==cycle.cycle_id
        assert state['calls']==1 and len(requests)==1
        assert len(r.store.all('cognitive_requests'))==1 and not r.store.all('runtime_cognition_calls')
        row=r.store.all('cognitive_requests')[0];assert row['state']=='PROPOSED' and row['reserved_bytes']>0
        support=r.store.db.execute("SELECT r.record_kind FROM record_dependencies d JOIN continuity_records r ON r.record_id=d.parent_id WHERE d.record_id=? AND d.parent_kind='RECORD'",(cycle.record_id,)).fetchall()
        assert 'COGNITION_PROPOSAL' in {item[0] for item in support}
        assert requests[0].cognitive_role=='SELF' and 'subject_cognition' in requests[0].expected_schema['required']
        assert not r.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'PRIVATE_CANDIDATE_REASON_CANARY')>0 OR instr(CAST(payload AS TEXT),'PRIVATE_PASSING_ASSOCIATION_CANARY')>0 OR instr(CAST(payload AS TEXT),'PRIVATE_ROOT_REASON_CANARY')>0").fetchone()
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')


@pytest.mark.parametrize('change',['new-source','withdraw','foreground'])
def test_resource_audit_does_not_hide_new_sources_withdrawal_or_foreground_preemption(tmp_path,change):
    from nana_core.presence.contracts import RuntimeEvent,Cause
    home=tmp_path/'home';initialize(home)
    with provider_harness(proposer=candidate,delay=.1) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,event=event_for(app)
        before=len(r.store.all('subject_cycles'));changed=[]
        def control():
            if changed:return
            changed.append(True)
            if change=='new-source':capture(r,'independent-new-observation',{'SYNTHETIC':'a new independent occurrence'})
            elif change=='withdraw':app.forget(mid)
            else:
                incoming=event.model_copy(update={'source_key':'development.new-foreground','kind':'INTERACTION','origin':'USER'})
                r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=incoming,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=r.clock.utc_now_us()))
        r.control_progress=control
        session=CognitionSession(r,transport,app.policy)
        code='PREEMPTED_NO_AUTOMATIC_RETRY' if change=='foreground' else 'STALE_CONTEXT'
        with pytest.raises(CoreError,match=code):r.subject.cognize(event,model=session.subject_port(privacy_class='PROJECT'),authority=r.authority,policy=app.policy)
        assert changed and state['calls']==1 and len(r.store.all('subject_cycles'))==before
        if change=='foreground':assert r.store.all('cognitive_requests')[0]['state']=='UNKNOWN' and r.queue.has_reactive()
        assert not r.store.all('actions') and not r.store.all('goals')


def test_timeout_remains_unknown_and_same_request_never_redispatches(tmp_path):
    home=tmp_path/'home';initialize(home)
    with provider_harness(proposer=candidate,delay=.15) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,event=event_for(app);session=CognitionSession(r,transport,app.policy)
        port=session.subject_port(privacy_class='PROJECT',budget=CognitionBudget(timeout_ms=50,cost_ceiling_micro=1))
        with pytest.raises(CoreError,match='PROVIDER_TIMEOUT_BILLING_UNKNOWN'):r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
        saved=dict(r.store.all('cognitive_requests')[0]);assert saved['state']=='UNKNOWN' and saved['reserved_cost_micro']==1 and saved['actual_cost_micro'] is None
        with pytest.raises(CoreError,match='SUBJECT_COGNITION_UNKNOWN'):r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
        assert state['calls']==1 and dict(r.store.all('cognitive_requests')[0])==saved
        assert not r.store.all('runtime_cognition_calls') and not r.store.all('subject_cycles')


def test_private_question_is_retained_only_by_original_c_and_withdraws_with_its_source(tmp_path):
    from nana_core.continuity.autonomy.private_intent import candidates
    home=tmp_path/'home';initialize(home)
    question='PRIVATE_PROVIDER_QUESTION_CANARY'
    def propose(request):
        return candidate(request,preferred_behavior=None,private_question={'topic':'private-creation','question':question})
    with provider_harness(proposer=propose) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,event=event_for(app);session=CognitionSession(r,transport,app.policy)
        cycle=r.subject.cognize(event,model=session.subject_port(privacy_class='PROJECT'),authority=r.authority,policy=app.policy)
        private=[(rid,value) for rid,value in candidates(r.store,'project-work',('PROJECT',)) if value.category=='PRIVATE_QUESTION']
        assert cycle.judgment.stance=='REFLECT' and len(private)==1
        assert question in private[0][1].content_summary
        for row in r.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind IN ('COGNITION_REQUEST','COGNITION_PROPOSAL') AND lifecycle='ACTIVE'"):
            assert question not in json.dumps(session.records.read(row[0])['payload'])
        app.forget(mid)
        assert not candidates(r.store,'project-work',('PROJECT',)) and not session.records.current_support(private[0][0])
        assert not r.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),?)>0",(question,)).fetchone()
        assert state['calls']==1


@pytest.mark.parametrize('changes,code',[
    ({'identity_id':'another-subject'},'MODEL_IDENTITY_MISMATCH'),
    ({'memory_refs':('forged-memory',)},'UNSUPPORTED_COGNITIVE_REFERENCE'),
    ({'preferred_behavior':'SOCIALIZE'},'UNSUPPORTED_COGNITIVE_BEHAVIOR'),
    ({'private_question':{'topic':'private-creation','question':'SYNTHETIC hypothesis','related_private_record_ids':('forged-private',)}},'UNSUPPORTED_PRIVATE_QUESTION_REFERENCE'),
])
def test_provider_candidate_cannot_forge_original_c_identity_or_references(tmp_path,changes,code):
    home=tmp_path/'home';initialize(home)
    with provider_harness(proposer=lambda request:candidate(request,**changes)) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,event=event_for(app);session=CognitionSession(r,transport,app.policy)
        with pytest.raises(CoreError,match=code):r.subject.cognize(event,model=session.subject_port(privacy_class='PROJECT'),authority=r.authority,policy=app.policy)
        assert r.store.all('cognitive_requests')[0]['state']=='REJECTED' and state['calls']==1
        assert not r.store.all('subject_cycles') and not r.store.all('actions')


def test_inner_candidate_is_not_advertised_or_accepted_in_other_resource_roles(tmp_path):
    from nana_core.continuity.world_loop.cognition import proposal_schema
    home=tmp_path/'home';initialize(home)
    assert 'subject_cognition' not in proposal_schema()['properties']
    with provider_harness(proposer=candidate) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,event=event_for(app);session=CognitionSession(r,transport,app.policy)
        request=session.prepare('not-inner','INTERPRET',(mid,))
        result=session.execute(request)
        assert result['state']=='REJECTED' and result['error_code']=='SUBJECT_COGNITION_ROLE_REQUIRED' and state['calls']==1
        assert not r.store.all('subject_cycles')


def test_subject_request_privacy_ceiling_applies_to_the_original_frame_before_dispatch(tmp_path):
    from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
    from nana_core.continuity.memory import MemoryService
    home=tmp_path/'home';initialize(home)
    with provider_harness(proposer=candidate) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;memory=MemoryService(r.store,r.authority)
        eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.subject-private',source_reference='private-source',source_kind='DIRECT_OBSERVATION'),
            text='SYNTHETIC_PRIVATE_SOURCE',privacy_class='PERSONAL',observed_time_us=r.clock.utc_now_us()))
        mid=memory.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text='SYNTHETIC_PRIVATE_SOURCE'))
        event=SubjectInput(domain='SYNTHETIC_ONLY',source_key='synthetic.private-resource',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
            privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        session=CognitionSession(r,transport,app.policy)
        with pytest.raises(CoreError,match='CONTEXT_REQUIRED_SOURCE_DENIED'):
            r.subject.cognize(event,model=session.subject_port(privacy_class='PROJECT'),authority=r.authority,policy=app.policy)
        assert state['calls']==0 and not r.store.all('cognitive_requests')


@pytest.mark.parametrize('overflow',[False,True])
def test_self_resource_keeps_complete_request_framing_counter_and_overflow_gate(tmp_path,overflow):
    from tests.world_loop.test_model_framing import bind,exact_fixture
    from nana_core.continuity.world_loop.cognition import CognitionRequest
    from nana_core.storage import canonical
    home=tmp_path/'home';initialize(home)
    with provider_harness(proposer=candidate) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,event=event_for(app)
        bind(transport,(lambda body:70000) if overflow else exact_fixture)
        session=CognitionSession(r,transport,app.policy)
        port=session.subject_port(privacy_class='PROJECT',budget=CognitionBudget(input_tokens=65536))
        if overflow:
            with pytest.raises(CoreError,match='INSUFFICIENT_CONTEXT_BUDGET'):r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
            assert state['calls']==0 and not r.store.all('cognitive_requests')
        else:
            assert r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy).intention.behavior=='REST'
            payload=session.records.read(r.store.all('cognitive_requests')[0]['record_id'])['payload']
            request=CognitionRequest.model_validate_json(canonical(payload['request']))
            assert payload['token_accounting']['input_tokens']==exact_fixture(json.loads(transport.request_body(request)))
            assert payload['token_accounting']['input_tokens']+request.budget.output_tokens<=request.budget.input_tokens
            assert state['calls']==1


def test_withdrawal_between_acceptance_and_take_clears_private_candidate_cache(tmp_path,monkeypatch):
    home=tmp_path/'home';initialize(home)
    with provider_harness(proposer=candidate) as (transport,state),LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;mid,event=event_for(app);session=CognitionSession(r,transport,app.policy)
        take=session.take_subject_candidate
        def withdraw(record_id):
            assert session._volatile_subject
            app.forget(mid)
            return take(record_id)
        monkeypatch.setattr(session,'take_subject_candidate',withdraw)
        with pytest.raises(CoreError,match='RECORD_UNAVAILABLE'):
            r.subject.cognize(event,model=session.subject_port(privacy_class='PROJECT'),authority=r.authority,policy=app.policy)
        assert not session._volatile_subject and not r.store.all('subject_cycles') and state['calls']==1
