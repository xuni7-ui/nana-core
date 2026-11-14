"""Original C-selected qualified methods can inform a task-less private D wake."""
import json
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.learning import ExperienceService,ExperienceInput
from nana_core.continuity.context import ContextPolicy,ContextAssembler,ContextRequest
from nana_core.continuity.cognition import AnalyticalFixturePort,CognitiveProposal
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.autonomy import private_intent
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal,subject_focus_inputs
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.presence import NanaRuntime
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import RuntimeConfig,SECOND
from tests.continuous_self.test_learning import learn_missing_locator


def prepared(tmp_path,clock,*,selected=True):
    path=tmp_path/'private'/'self.db';authority=OperatorAuthority()
    with ContinuityStore(path,clock,schema_target=13) as store:
        IdentityService(store,authority);memory=MemoryService(store,authority);memory.entity('synthetic-sister','PERSON')
        _,result,_,lesson=learn_missing_locator(store,memory,authority)
    config=RuntimeConfig(schema_target=13,scopes=('synthetic-home',),entity_id='synthetic-sister',privacy_classes=('PERSONAL',),
        idle_recall_us=2*SECOND,review_interval_us=10*SECOND,cognition_cooldown_us=0)
    runtime=NanaRuntime(path,config,clock=clock)
    policy=ContextPolicy(policy_id='private-method-continuation',allowed_scopes=('synthetic-home',),readable_privacy=('PERSONAL',))
    cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CURIOSITY',topic_key='own-method-play',possible_behaviors=('WATCH',),valid_until_us=clock.utc_now_us()+SECOND)
    memory=MemoryService(runtime.store,runtime.authority)
    evidence=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.private-method',source_reference='initial-window',source_kind='DIRECT_OBSERVATION'),
        text=cue.model_dump_json(),privacy_class='PERSONAL',observed_time_us=clock.utc_now_us()))
    mid=memory.add(MemoryCandidate(entity_id='synthetic-sister',scope='synthetic-home',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',
        source_evidence_id=evidence,text=cue.model_dump_json(),predicate_key='concern.initial-method-window'))
    class Plan:
        descriptor='synthetic-original-c-qualifed-method-selection'
        def __init__(self,refs,revises=None):self.refs,self.revises=refs,revises
        def propose(self,request):
            value=json.loads(AnalyticalFixturePort().propose(request))
            value.update(lesson_refs=self.refs,proposed_operations=['DRAFT'],private_plan={
                'topic':'own-method-play','plan':'PRIVATE_METHOD_PLAN_CANARY' + (' revised without adopting a method' if self.revises else ''),
                'revises_record_id':self.revises})
            return json.dumps(value)
    source=SubjectInput(source_key='synthetic.private-method-plan',kind='WAKE',origin='SELF_WAKE',entity_id='synthetic-sister',scope='synthetic-home',
        privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,),task_class='reading_card')
    runtime.subject.cognize(source,model=Plan([lesson] if selected else []),authority=runtime.authority,policy=policy)
    rid,plan=private_intent.candidates(runtime.store,'synthetic-home',('PERSONAL',))[0]
    return runtime,policy,rid,plan,lesson,result,source,Plan


def bind(r,transport,policy):
    session=CognitionSession(r,transport,policy);budget=CognitionBudget(input_tokens=65536)
    def preview(event,frame):
        if frame is None:return
        return session.preview('subject-cognition.'+frame.subject_event_id,'SELF',frame.source_memory_ids,subject_frame=frame,budget=budget,
            **subject_focus_inputs(frame.subject_event_id,event.privacy_class,event.text or 'Assess current concerns; silence is allowed',event.task_class or 'subject_deliberation'))
    r.cognition.bind_provider(lambda event:session.subject_port(privacy_class=event.privacy_class,budget=budget),preview)
    return session


@pytest.mark.parametrize('condition',['active','unrelated-lesson','no-ref','suspended','withdrawn','reselected-without-ref','ablated'])
def test_normal_taskless_d_uses_only_current_explicit_private_method_selection(tmp_path,monkeypatch,condition):
    clock=VirtualClock();runtime,policy,rid,plan,lesson,result,source,Plan=prepared(tmp_path,clock,selected=condition!='no-ref');seen=[]
    def propose(request):
        context=json.loads(request.context_json);identity=context['manifest']
        refs=[json.loads(b['data_json'])['lesson_id'] for b in context['blocks'] if b['kind']=='LESSON'];seen.append(refs)
        assert request.media_input()['subject_cognition']['task_class']=='subject_deliberation'  # D did not assign a work goal.
        return StructuredProposal(interpretation='SYNTHETIC bounded method continuation',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='SYNTHETIC reflect on a method' if refs else 'SYNTHETIC wait',
            lesson_refs=tuple(refs),proposed_operations=('DRAFT',) if refs else ('WAIT',),
            private_question={'topic':'own-method-play','question':'PRIVATE_METHOD_QUESTION_CANARY: could this checked method support a different private activity?'} if refs else None))
    with provider_harness(proposer=propose) as (transport,state),runtime as r:
        from tests.world_loop.test_model_framing import bind as bind_counter
        bind_counter(transport)
        if condition=='unrelated-lesson':
            from tests.continuous_self.conftest import evidence
            from tests.continuous_self.test_memory import add
            memory=MemoryService(r.store,r.authority);learning=ExperienceService(r.store,r.authority)
            context=add(memory,evidence(memory,'unrelated-context','SYNTHETIC a different reading project'),'SYNTHETIC a different reading project')
            output=add(memory,evidence(memory,'unrelated-result','{"text":"SYNTHETIC another card"}'),'{"text":"SYNTHETIC another card"}')
            proof=learning.verify_reading_result(output,r.authority)
            experience=learning.record(ExperienceInput(context_memory_ids=(context,),scope='synthetic-home',task_class='reading_card',
                decision='SYNTHETIC different missing locator',result_memory_id=output,verification_memory_id=proof))
            other=learning.derive_lesson(experience);assert all(learning.test_lesson(other).values());learning.activate(other,r.authority)
            assert other!=lesson
        if condition=='suspended':ExperienceService(r.store,r.authority).suspend(lesson,r.authority)
        if condition=='withdrawn':MemoryService(r.store,r.authority).forget(result,r.authority)
        if condition=='reselected-without-ref':
            r.subject.cognize(source.model_copy(update={'source_key':'synthetic.drop-private-method'}),model=Plan([],rid),authority=r.authority,policy=policy)
            rid,plan=private_intent.candidates(r.store,'synthetic-home',('PERSONAL',))[0]
        if condition=='ablated':monkeypatch.setattr(private_intent,'deliberated_lesson_refs',lambda *args,**kwargs:())
        ordinary=ContextAssembler(r.store,r.authority).assemble(ContextRequest(entity_id='synthetic-sister',scopes=('synthetic-home',),
            task_class='ordinary',task='Ordinary permitted context',task_privacy_class='PERSONAL'),policy)
        assert 'PRIVATE_METHOD_PLAN_CANARY' not in ordinary.model_dump_json() and not any(b.kind=='LESSON' for b in ordinary.blocks)
        bind(r,transport,policy);clock.advance(3*SECOND);r.refresh_attention()
        for _ in range(4):r.step()
        # Original D first reviews the actual training failure; that activity
        # starts its normal quiet window. Wait for it, without disabling D.
        assert state['calls']==0
        clock.advance(2*SECOND);r.refresh_attention()
        for _ in range(4):r.step()
        expected=condition in {'active','unrelated-lesson'};values=private_intent.candidates(r.store,'synthetic-home',('PERSONAL',))
        assert any(v.category=='PRIVATE_QUESTION' for _,v in values)==expected, (condition,seen)
        assert seen==([] if condition=='withdrawn' else [[lesson] if expected else []])
        assert state['calls']==(0 if condition=='withdrawn' else 1)
        rows=[row for row in r.store.all('runtime_queue') if json.loads(row['metadata_json']).get('private_thought_ref')]
        if condition!='withdrawn':
            assert len(rows)==1 and rows[0]['state']=='DONE'
            assert json.loads(rows[0]['metadata_json'])['task_class'] is None
        for _ in range(3):r.refresh_attention();r.step()
        assert state['calls']==(0 if condition=='withdrawn' else 1) and not r.store.all('runtime_cognition_calls')
        assert not r.store.all('goals') and not r.store.all('actions') and not r.store.all('grants')
        if expected:
            question=next(v for _,v in values if v.category=='PRIVATE_QUESTION');path=r.store.path;identity=r.identity_id;config=r.config
    if condition in {'active','unrelated-lesson'}:
        with NanaRuntime(path,config,clock=clock) as r:
            assert r.identity_id==identity and any(v.intent_id==question.intent_id for _,v in private_intent.candidates(r.store,'synthetic-home',('PERSONAL',)))
            MemoryService(r.store,r.authority).forget(result,r.authority)
            assert not private_intent.candidates(r.store,'synthetic-home',('PERSONAL',))
            assert not r.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'PRIVATE_METHOD_QUESTION_CANARY')>0").fetchone()


def test_private_method_projection_is_read_only_deduplicated_and_qualified_by_original_g(tmp_path,monkeypatch):
    runtime,policy,rid,plan,lesson,_,source,_=prepared(tmp_path,VirtualClock())
    with runtime as r:
        from nana_core.continuity.subject.policy import appraise,motivate,decide,deliberation_frame
        from nana_core.continuity.subject.ingress import SubjectIngress
        event=source.model_copy(update={'source_key':'synthetic.private-method-owner-preview'})
        row=SubjectIngress(r.store).ingest(event);situation=r.subject.situation(event,row);appraisal=appraise(event,situation);motives=motivate(event,situation,appraisal)
        frame=deliberation_frame(row['subject_event_id'],situation,appraisal,motives,decide(event,situation,appraisal,motives)[0])
        request=ContextRequest(entity_id='synthetic-sister',scopes=('synthetic-home',),task_class='reading_card',task='Current own consideration',task_privacy_class='PERSONAL',max_input_tokens=65536)
        before=r.store.snapshot();writes=r.store.db.total_changes
        package=ContextAssembler(r.store,r.authority).assemble(request,policy,subject_frame=frame)
        assert [json.loads(b.data_json)['lesson_id'] for b in package.blocks if b.kind=='LESSON']==[lesson]
        assert r.store.snapshot()==before and r.store.db.total_changes==writes
        assert private_intent.deliberated_lesson_refs(r.store,({'record_id':rid},),scope='synthetic-home',privacy_classes=('PROJECT',))==()
        assert private_intent.deliberated_lesson_refs(r.store,({'record_id':rid},),scope='other-scope',privacy_classes=('PERSONAL',))==()
        # Explicit references use primary-key reads, never a second full history scan.
        old_all=r.store.all
        def no_history(table):
            if table in {'lessons','experiences'}:raise AssertionError('selected references must not scan histories')
            return old_all(table)
        monkeypatch.setattr(r.store,'all',no_history)
        blocks=ExperienceService(r.store,r.authority).context_blocks(request,('PERSONAL',),selected_lesson_ids=(lesson,lesson))
        assert len(blocks)==1 and r.store.db.total_changes==writes
        assert ExperienceService(r.store,r.authority).context_blocks(request,('PROJECT',),selected_lesson_ids=(lesson,))==[]
