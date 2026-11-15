"""Original C can consider an original consolidation candidate before committing it."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.cognition import AnalyticalFixturePort,CognitiveProposal
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.memory import MemoryService
from .test_dream_recall import source


def offered(app,*,pending=0,prohibited=()):
    r=app.runtime
    for n in range(pending):
        cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key='memory.pending-'+str(n),motivation_source='CURIOSITY',possible_behaviors=('EXPLORE',))
        mid=source(app,'pending-'+str(n),cue.model_dump_json(),predicate_key='concern.memory.pending-'+str(n))
        r.subject.run(SubjectInput(source_key='synthetic.memory-pending.'+str(n),kind='WAKE',origin='SELF_WAKE',
            entity_id='project-user',scope='project-work',privacy_class='PROJECT',source_memory_ids=(mid,),observed_at_us=r.clock.utc_now_us()))
    assert len(r.subject.pending('project-work'))==pending
    mid=source(app,'bounded-review-source','SYNTHETIC stored observation worth considering, not a command.',importance=.9)
    maintenance=r.work.maintenance
    rid=maintenance._offer((MemoryService(r.store).read(mid),),'project-work','INCREMENTAL')
    head,body=maintenance.candidate(rid);mids=[mid]
    if prohibited:
        cue=ConcernCue(cue_kind='CONSTRAINT',topic_key='memory-review',motivation_source='NORM',prohibited_behaviors=prohibited)
        mids.append(source(app,'review-norm',cue.model_dump_json(),predicate_key='concern.memory.norm'))
    event=SubjectInput(source_key='synthetic.current-memory-review.'+rid,kind='WAKE',origin='SELF_WAKE',
        entity_id='project-user',scope='project-work',privacy_class='PROJECT',source_memory_ids=tuple(mids),
        observed_at_us=head['created_at_us'],memory_review_id=rid)
    return event,rid,mid


@pytest.mark.parametrize('preference,pending,prohibited,expected',[
    ('MAINTAIN',6,(),'MEMORY_CANDIDATE'),('REST',0,(),'NO_ACTION'),
    (None,6,(),'NO_ACTION'),(None,0,(),'MEMORY_CANDIDATE'),
    ('MAINTAIN',0,('MAINTAIN',),'NO_ACTION'),
])
def test_actual_candidate_is_offered_before_c_and_can_be_adopted_or_declined(app,preference,pending,prohibited,expected):
    event,rid,mid=offered(app,pending=pending,prohibited=prohibited);seen=[]
    class Choosing:
        descriptor='synthetic-memory-choice'
        def propose(self,request):
            seen.append(request);value=json.loads(AnalyticalFixturePort().propose(request))
            if preference:value['preferred_behavior']=preference
            return json.dumps(value)
    r=app.runtime
    original=r.subject.ingress.ingest(event);writes=r.store.db.total_changes
    preview=r.subject.situation(event,original)
    assert preview.memory_review_id==rid and rid in preview.support_record_ids
    assert r.store.db.total_changes==writes
    result=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy)
    assert result.intention.kind==expected
    frame=next(json.loads(b['data_json']) for b in json.loads(seen[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
    assert set(frame.get('behavior_options',()))=={'MAINTAIN','REST'}
    assert rid in frame['source_record_ids']
    assert any(m['source']=='MAINTENANCE' for m in frame['motivations'])
    if pending:assert any(m['source']=='REST' for m in frame['motivations'])
    summary=r.work.maintenance.adopt(rid,result)
    if expected=='MEMORY_CANDIDATE':
        assert summary
        row=MemoryService(r.store).read(summary)
        assert row['authority']=='INFERRED' and row['epistemic_kind']=='SUMMARY'
        assert mid in {d['parent_id'] for d in r.store.all('memory_dependencies') if d['memory_id']==summary}
    else:
        assert summary is None and result.intention.behavior=='REST'
    app.forget(mid)
    if summary:assert r.store.one('memories',summary)['lifecycle']=='DELETED'
    trigger=source(app,'fresh-review-trigger','SYNTHETIC unrelated current trigger, not the withdrawn evidence.')
    stale=event.model_copy(update={'source_key':'synthetic.stale-memory-review.'+rid,'source_memory_ids':(trigger,)})
    with pytest.raises(CoreError,match='MAINTENANCE_SOURCE_UNAVAILABLE'):
        r.subject.cognize(stale,model=Choosing(),authority=r.authority,policy=app.policy)
    assert len(seen)==1 and not r.store.all('actions') and not r.store.all('goals')


def test_normal_self_resource_can_choose_rest_for_a_memory_candidate_without_an_extra_model_phase(app):
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.context import ContextPolicy
    event,rid,_=offered(app);seen=[];r=app.runtime
    def propose(request):
        seen.append(request);manifest=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC defer optional consolidation',
            subject_cognition=CognitiveProposal(identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],
                interpretation='SYNTHETIC choose rest while retaining the original sources',preferred_behavior='REST',proposed_operations=('DRAFT',)))
    policy=ContextPolicy(policy_id='synthetic.memory-choice',allowed_scopes=('project-work',),readable_privacy=('PROJECT',))
    with provider_harness(proposer=propose) as (transport,metrics):
        port=CognitionSession(r,transport,policy).subject_port(privacy_class='PROJECT',budget=CognitionBudget(input_tokens=65536))
        try:
            result=r.subject.cognize(event,model=port,authority=r.authority,policy=policy)
        finally:
            print(json.dumps({'measurement':'memory-review-resource-attempt','http_calls':metrics['calls'],
                'request_json_bytes':len(seen[0].model_dump_json().encode()) if seen else None,
                'budget':seen[0].budget.model_dump() if seen else None,'real_model_calls':0}))
        print(json.dumps({'measurement':'memory-review-self','kind':result.intention.kind,'behavior':result.intention.behavior,
            'http_calls':metrics['calls'],'request_json_bytes':len(seen[0].model_dump_json().encode()),'real_model_calls':0}))
        assert result.intention.kind=='NO_ACTION' and result.intention.behavior=='REST'
        assert r.work.maintenance.adopt(rid,result) is None
        assert metrics['calls']==1 and not r.store.all('actions')


def test_normal_runtime_step_receives_the_same_candidate_and_defers_without_polling(app):
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal,subject_focus_inputs
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.context import ContextPolicy
    from nana_core.presence.contracts import RuntimeEvent,Cause
    event,rid,mid=offered(app);r=app.runtime
    event=event.model_copy(update={'source_key':'synthetic.living.review.'+rid,'significance':'HIGH','uncertainty':'HIGH'})
    app.pause(False)  # Explicit DEV resume through the original owner control.
    def propose(request):
        manifest=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC normal D considers a real consolidation candidate',
            subject_cognition=CognitiveProposal(identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],
                interpretation='SYNTHETIC keep sources and rest for now',preferred_behavior='REST',proposed_operations=('DRAFT',)))
    with provider_harness(proposer=propose) as (transport,metrics):
        policy=ContextPolicy(policy_id='synthetic.memory-normal-d',allowed_scopes=('project-work',),readable_privacy=('PROJECT',))
        session=CognitionSession(r,transport,policy);budget=CognitionBudget(input_tokens=32768)
        def preview(event,frame):
            return session.preview('subject-cognition.'+frame.subject_event_id,'SELF',frame.source_memory_ids,
                subject_frame=frame,**subject_focus_inputs(frame.subject_event_id,event.privacy_class,
                    event.text or 'Assess current concerns; silence is allowed',event.task_class or 'subject_deliberation'),budget=budget)
        r.cognition.bind_provider(lambda event:session.subject_port(privacy_class=event.privacy_class,budget=budget),preview)
        value=RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=event,
                           causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=r.clock.utc_now_us())
        qid=r.submit(value);result=r.step()
        assert result['queue_id']==qid and result['cycle'].intention.behavior=='REST'
        assert r.store.one('runtime_queue',qid)['state']=='DONE'
        job=r.store.db.execute("SELECT * FROM jobs WHERE occurrence_key=?",('maintenance-review:'+rid,)).fetchone()
        assert job and job['state']=='PAUSED'
        assert len(r.store.all('cognitive_requests'))==1 and not r.store.all('runtime_cognition_calls')
        assert metrics['calls']==1 and not r.store.all('actions')
        assert r.submit(value)==qid
        for _ in range(2):r.step()
        assert metrics['calls']==1
        assert not [m for m in r.store.all('memories') if m['epistemic_kind']=='SUMMARY']


def test_nonretention_review_rejects_persistent_derivation_before_a_model(app):
    event,rid,_=offered(app);called=[]
    class MustNotRun:
        descriptor='synthetic-nonretention-review'
        def propose(self,request):called.append(request);raise AssertionError('NONRETENTION_MODEL_CALL')
    event=event.model_copy(update={'retention':'DO_NOT_REMEMBER'})
    r=app.runtime
    writes=r.store.db.total_changes
    with pytest.raises(CoreError,match='NONRETENTION_INPUT_CANNOT_PERSIST_DERIVATION'):
        r.subject.cognize(event,model=MustNotRun(),authority=r.authority,policy=app.policy)
    assert called==[] and r.store.db.total_changes==writes
    assert not [m for m in r.store.all('memories') if m['epistemic_kind']=='SUMMARY']
    assert not r.store.all('cognitive_requests') and not r.store.all('actions')
