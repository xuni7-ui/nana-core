import json
import pytest
from nana_core.life.application import LifeApplication
from nana_core.life.inspector import inspect
from nana_core.continuity.autonomy.private_intent import candidates,metadata,eligible_content
from nana_core.continuity.autonomy.contracts import SocialExpectationSpec
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.project_work.service import capture
from nana_core.contracts import CoreError
from nana_core.presence.authority import VirtualClock
from tests.cloud_life.conftest import initialize


def choose(app,key='idea',*,topic='creative-project'):
    r=app.runtime
    cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key=topic,motivation_source='CREATIVE_INTEREST',possible_behaviors=('CREATE','REST'),resource_class='ORDINARY')
    mid=capture(r,key,cue.model_dump(mode='json'),predicate='concern.'+topic)
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
    result=r.subject.run(event)
    return mid,event,result


def test_original_c_creates_private_idea_no_command_or_model(tmp_path):
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        mid,event,result=choose(app)
        assert result.intention.behavior=='CREATE' and result.evaluation.normative=='ENDORSED'
        rows=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
        assert len(rows)==1
        rid,value=rows[0]
        assert value.intent_id==result.intention_id and value.owner_identity_id==app.runtime.identity_id
        assert value.disclosure_policy=='PRIVATE_FOR_NOW'
        with pytest.raises(CoreError,match='WITHHELD'):eligible_content(app.runtime.store,value.intent_id,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
        before=app.runtime.store.db.total_changes
        snapshot=inspect(home,scope='project-work',entity_id='project-user')
        assert snapshot.private_activity=='PRESENT_CONTENT_WITHHELD'
        assert value.content_summary not in snapshot.model_dump_json()
        assert app.runtime.store.db.total_changes==before
        app.runtime.subject.run(event)
        assert len(candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT')))==1
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        app.forget(mid)
        assert not candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
        assert value.content_summary not in inspect(home,scope='project-work',entity_id='project-user').model_dump_json()


@pytest.mark.parametrize('enabled,withdrawn,matching,expected',[
    (False,False,True,'IGNORE'),(True,False,True,'CREATE'),
    (True,True,True,'IGNORE'),(True,False,False,'IGNORE'),
])
def test_existing_private_idea_changes_later_choice_after_restart_without_disclosing_content(tmp_path,monkeypatch,enabled,withdrawn,matching,expected):
    from nana_core.continuity.autonomy import private_intent
    from nana_core.continuity.subject.opportunities import OpportunityAssessment
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        mid,_,first=choose(app)
        original=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0]
        identity=app.runtime.identity_id
        # The first consideration is over; the original private idea survives it.
        app.runtime.subject.transition_intention(first.intention_id,expected_revision=1,state='COMPLETED')
    with LifeApplication(home) as app:
        assert app.runtime.identity_id==identity
        if withdrawn:app.forget(mid)
        if not enabled:
            monkeypatch.setattr(private_intent,'decision_support',lambda *args,**kwargs:(),raising=False)
        topic='creative-project' if matching else 'unrelated-project'
        cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key=topic,motivation_source='CREATIVE_INTEREST',
            possible_behaviors=('CREATE','REST'),resource_class='ORDINARY',
            opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'))
        cause=capture(app.runtime,'later-internal-opportunity',cue.model_dump(mode='json'),predicate='concern.later-opportunity.'+topic)
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.later-private-choice',
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
            observed_at_us=app.runtime.clock.utc_now_us(),source_memory_ids=(cause,))
        cycle=app.runtime.subject.run(event)
        assert cycle.intention.behavior==expected
        assert cycle.appraisal.expected_value=='LOW' and cycle.appraisal.novelty=='LOW'
        support=[m for m in cycle.motivations if m.source=='PRIVATE_INTEREST']
        if enabled and not withdrawn and matching:
            assert support and original[0] in support[0].source_ids
            assert cycle.appraisal.interest_relevance=='HIGH'
            assert len(candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT')))==1
        else:assert not support
        assert original[1].content_summary not in inspect(home,scope='project-work',entity_id='project-user').model_dump_json()
        from nana_core.continuity.context import ContextAssembler,ContextRequest
        package=ContextAssembler(app.runtime.store,app.runtime.authority).assemble(
            ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='first-life',
                task='ordinary outward context',task_privacy_class='PROJECT'),app.policy)
        assert original[1].content_summary not in package.model_dump_json()
        assert not app.runtime.store.all('cognitive_requests')
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_private_decision_references_respect_owner_scope_privacy_and_nonretention(tmp_path,monkeypatch):
    from nana_core.continuity.autonomy import private_intent
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        _,_,_=choose(app);store=app.runtime.store
        row=candidates(store,'project-work',('PUBLIC','PROJECT'))[0]
        assert private_intent.decision_support(store,'project-work',('PUBLIC',),topic='creative-project')==()
        assert private_intent.decision_support(store,'other-scope',('PUBLIC','PROJECT'),topic='creative-project')==()
        assert private_intent.decision_support(store,'project-work',('PUBLIC','PROJECT'),topic=None)==()
        with monkeypatch.context() as patch:
            patch.setattr(private_intent,'candidates',lambda *args,**kwargs:((row[0],row[1].model_copy(update={'owner_identity_id':'other-subject'})),))
            assert private_intent.decision_support(store,'project-work',('PUBLIC','PROJECT'),topic='creative-project')==()
        before=len(candidates(store,'project-work',('PUBLIC','PROJECT')))
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.nonretained-private-review',
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic='creative-project',
            observed_at_us=app.runtime.clock.utc_now_us(),retention='DO_NOT_REMEMBER')
        cycle=app.runtime.subject.run(event)
        assert cycle.intention.kind=='NO_ACTION' and not any(m.source=='PRIVATE_INTEREST' for m in cycle.motivations)
        assert len(candidates(store,'project-work',('PUBLIC','PROJECT')))==before
        assert not store.all('cognitive_requests') and not store.all('actions') and not store.all('grants')


def private_choice(app,key,behavior,*,value='LOW',novelty='REPEATED',intent_id=None):
    from nana_core.continuity.subject.opportunities import OpportunityAssessment,PrivateIntentRef
    r=app.runtime
    rid,item=next((rid,item) for rid,item in candidates(r.store,'project-work',('PUBLIC','PROJECT'))
        if item.topic=='creative-project' and (intent_id is None or item.intent_id==intent_id))
    cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key='creative-project',motivation_source='CREATIVE_INTEREST',
        possible_behaviors=(behavior,),resource_class='ORDINARY',
        private_intent_ref=PrivateIntentRef(record_id=rid,intent_id=item.intent_id,revision=item.revision),
        opportunity_assessment=OpportunityAssessment(value=value,novelty=novelty))
    mid=capture(r,key,cue.model_dump(mode='json'),predicate='concern.private-choice.'+key)
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.'+key,
        kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
        observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
    cycle=r.subject.run(event)
    if cycle.intention_id:
        row=r.store.one('subject_intentions',cycle.intention_id)
        if row['state']=='PENDING':r.subject.transition_intention(cycle.intention_id,expected_revision=row['revision'],state='COMPLETED')
    return cycle,event


def test_private_idea_can_pause_resume_abandon_and_reconsider_in_original_c_across_restarts(tmp_path):
    from nana_core.continuity.autonomy.private_intent import PrivateActivity,decision_support
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        original_source,_,first=choose(app);identity=app.runtime.identity_id
        app.runtime.subject.transition_intention(first.intention_id,expected_revision=1,state='COMPLETED')
        original=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1]
        clock.advance(1_000_000)
        cycle,event=private_choice(app,'pause-private-idea','REST')
        assert cycle.intention.behavior=='REST'
        rid,paused=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0]
        assert isinstance(paused,PrivateActivity) and paused.activity_state=='PAUSED'
        assert paused.intent_id==original.intent_id and paused.revision==2
        assert paused.last_choice_cycle_id==cycle.cycle_id and paused.updated_at_us>paused.created_at_us
        before=app.runtime.store.db.total_changes
        app.runtime.subject.run(event)
        assert candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1].revision==2
        assert app.runtime.store.db.total_changes==before  # Original source replay, no repeated revision.
    with LifeApplication(home,clock=clock) as app:
        assert app.runtime.identity_id==identity
        assert candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1].activity_state=='PAUSED'
        # Rest did not erase an interest. Original C can choose it again even
        # when instrumental value remains LOW and the opportunity is repeated.
        clock.advance(1_000_000);resumed,_=private_choice(app,'resume-private-idea','CREATE')
        assert resumed.intention.behavior=='CREATE'
        value=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1]
        assert value.intent_id==original.intent_id and value.activity_state=='ACTIVE' and value.revision==3
        clock.advance(1_000_000);withdrawn,_=private_choice(app,'abandon-private-idea','WITHDRAW')
        assert withdrawn.intention.behavior=='WITHDRAW'
        value=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1]
        assert value.activity_state=='ABANDONED' and value.revision==4
        assert decision_support(app.runtime.store,'project-work',('PUBLIC','PROJECT'),topic='creative-project')==()
        from nana_core.continuity.context import ContextAssembler,ContextRequest
        package=ContextAssembler(app.runtime.store,app.runtime.authority).assemble(
            ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='first-life',
                task='ordinary outward context',task_privacy_class='PROJECT'),app.policy)
        assert not any(block.kind=='PRIVATE_INTENT_STATE' for block in package.blocks)
        ignored,_=private_choice(app,'old-idea-not-automatic','CREATE');assert ignored.intention.behavior=='IGNORE'
        assert candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1].revision==4
    with LifeApplication(home,clock=clock) as app:
        assert app.runtime.identity_id==identity
        clock.advance(1_000_000)
        renewed,_=private_choice(app,'new-ground-for-reconsidering','CREATE',value='HIGH',novelty='NEW')
        assert renewed.intention.behavior=='CREATE'
        values=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
        assert len(values)==1 and values[0][1].intent_id==original.intent_id
        assert values[0][1].activity_state=='ACTIVE' and values[0][1].revision==5
        assert values[0][1].epistemic_status=='OWN_TENDENCY_NOT_WORLD_FACT'
        assert values[0][1].execution_state=='NOT_INFERRED_FROM_ACTIVITY_STATE'
        assert not app.runtime.store.all('cognitive_requests') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
    # Simulate stopped time, then acquire the original fresh runtime lease.
    # Advancing a live lease by48h must remain fenced as RUNTIME_LEASE_LOST.
    clock.advance(48*60*60*1_000_000)
    with LifeApplication(home,clock=clock) as app:
        assert app.runtime.identity_id==identity
        for _ in range(3):app.runtime.step()
        assert candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1].revision==5
        assert not app.runtime.store.all('cognitive_requests') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        app.forget(original_source)
        assert not candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))


def test_revising_one_private_idea_does_not_hide_another_current_interest(tmp_path):
    """Historical header fixture, not 70 fabricated experiences/model thoughts."""
    from nana_core.continuity.records import RecordService
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        for key,topic in [('stable-private','stable-project'),('revised-private','creative-project')]:
            _,_,cycle=choose(app,key,topic=topic)
            app.runtime.subject.transition_intention(cycle.intention_id,expected_revision=1,state='COMPLETED')
        records=RecordService(app.runtime.store)
        rid,value=next((rid,item) for rid,item in candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT')) if item.topic=='creative-project')
        for _ in range(70):
            value=value.model_copy(update={'revision':value.revision+1})
            with app.runtime.store.transaction('fixture.private_header_history') as tx:
                rid=records.create(tx,kind='INTENTION',scope='project-work',target_id='private-intent.v1',
                    payload=value.model_dump(mode='json'),records=(rid,),supersedes=rid)
        queries=[];app.runtime.store.db.set_trace_callback(queries.append)
        try:values=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
        finally:app.runtime.store.db.set_trace_callback(None)
        assert {v.topic for _,v in values}=={'stable-project','creative-project'}
        actual=next(sql for sql in queries if 'FROM continuity_records' in sql and "'private-intent.v1'" in sql and 'ORDER BY' in sql)
        plan=app.runtime.store.db.execute('EXPLAIN QUERY PLAN '+actual).fetchall()
        assert any('private_intent_live_lookup' in str(tuple(row)) for row in plan)
        assert not app.runtime.store.all('cognitive_requests') and not app.runtime.store.all('actions')


def test_private_lifecycle_requires_exact_current_target_and_preserves_other_ideas(tmp_path):
    from nana_core.continuity.subject.opportunities import PrivateIntentRef
    from nana_core.continuity.records import RecordService
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        _,_,first=choose(app)
        app.runtime.subject.transition_intention(first.intention_id,expected_revision=1,state='COMPLETED')
        original_rid,original=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0]
        # A second valid stored idea at the same topic is a historical fixture,
        # not a claim that this C policy invents two different creative contents.
        other=original.model_copy(update={'intent_id':'synthetic.other-private-idea','content_summary':'SYNTHETIC second independent idea'})
        with app.runtime.store.transaction('fixture.second_private_idea') as tx:
            other_rid=RecordService(app.runtime.store).create(tx,kind='INTENTION',scope='project-work',
                payload=other.model_dump(mode='json'),records=(first.record_id,),target_id='private-intent.v1')
        reference=PrivateIntentRef(record_id=original_rid,intent_id=original.intent_id,revision=original.revision)
        def review(key,ref):
            cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='creative-project',motivation_source='CREATIVE_INTEREST',
                possible_behaviors=('REST',),private_intent_ref=ref)
            mid=capture(app.runtime,key,cue.model_dump(mode='json'),predicate='concern.review.'+key)
            return SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.'+key,
                kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
                observed_at_us=app.runtime.clock.utc_now_us(),source_memory_ids=(mid,))
        app.runtime.subject.run(review('bound-private-rest',reference))
        values={v.intent_id:(rid,v) for rid,v in candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))}
        assert values[original.intent_id][1].activity_state=='PAUSED' and values[original.intent_id][1].revision==2
        assert values[other.intent_id][0]==other_rid and values[other.intent_id][1].revision==1
        assert getattr(values[other.intent_id][1],'activity_state','ACTIVE')=='ACTIVE'
        with pytest.raises(CoreError,match='PRIVATE_INTENT_REVIEW_UNAVAILABLE'):
            app.runtime.subject.run(review('stale-private-rest',reference))
        assert {v.intent_id:v.revision for _,v in candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))}=={
            original.intent_id:2,other.intent_id:1}
        assert not app.runtime.store.all('cognitive_requests') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_private_activity_in_registered_inactive_backup_follows_original_withdrawal(tmp_path):
    import sqlite3
    from nana_core.life.inspector import _ReadView
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        mid,_,cycle=choose(app)
        app.runtime.subject.transition_intention(cycle.intention_id,expected_revision=1,state='COMPLETED')
        private_choice(app,'private-before-backup','REST')
        rid,value=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0]
        assert value.activity_state=='PAUSED'
        backup=tmp_path/'inactive'/'private.db';app.runtime.store.backup(backup)
        def read_copy():
            with sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True) as db:
                db.row_factory=sqlite3.Row
                return candidates(_ReadView(db,backup,'project-work',('PUBLIC','PROJECT')),'project-work',('PUBLIC','PROJECT'))
        assert read_copy()[0][1].activity_state=='PAUSED'
        app.forget(mid)
        assert not read_copy()
        with sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True) as db:
            assert db.execute('SELECT a.payload FROM continuity_records r JOIN artifacts a ON a.artifact_id=r.payload_artifact_id WHERE r.record_id=?',(rid,)).fetchone()==(None,)
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('cognitive_requests')


@pytest.mark.parametrize('expectation',['EXPLICITLY_PRIVATE','EXPLICITLY_FORBIDDEN','CONTEXT_SENSITIVE'])
@pytest.mark.parametrize('behavior',['CREATE','SOCIALIZE'])
def test_reception_boundary_restrains_expression_without_banning_unbound_private_creativity(tmp_path,expectation,behavior):
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        spec=SocialExpectationSpec(topic='creative-project',expectation=expectation)
        capture(app.runtime,'private-reception',spec.model_dump(mode='json'),kind='USER_STATEMENT',
            predicate='social.expectation.creative-project')
        cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='creative-project',motivation_source='CREATIVE_INTEREST',
            possible_behaviors=(behavior,),resource_class='ORDINARY',availability='AVAILABLE')
        mid=capture(app.runtime,'private-creative-choice',cue.model_dump(mode='json'),predicate='concern.creative-project')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.private-creative-choice',
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
            observed_at_us=app.runtime.clock.utc_now_us(),source_memory_ids=(mid,))
        cycle=app.runtime.subject.run(event)
        if behavior=='CREATE':
            assert cycle.intention.behavior=='CREATE' and cycle.evaluation.normative=='ENDORSED'
            values=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
            assert len(values)==1
            assert values[0][1].disclosure_policy==('MANAGER_AUDIT_ONLY' if expectation=='EXPLICITLY_FORBIDDEN' else 'PRIVATE_FOR_NOW')
            if expectation!='CONTEXT_SENSITIVE':
                with pytest.raises(CoreError,match='PRIVATE_INTENT_WITHHELD'):
                    eligible_content(app.runtime.store,values[0][1].intent_id,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
        else:
            assert cycle.intention.behavior!='SOCIALIZE' and not candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
            assert cycle.evaluation.normative==('UNDECIDED' if expectation=='CONTEXT_SENSITIVE' else 'RESTRAINED')
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants') and not app.runtime.store.all('cognitive_requests')


@pytest.mark.parametrize('expectation',['EXPLICITLY_PRIVATE','EXPLICITLY_FORBIDDEN','CONTEXT_SENSITIVE'])
def test_private_rest_review_respects_reception_boundary_without_erasing_own_choice(tmp_path,expectation):
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        _,_,first=choose(app)
        app.runtime.subject.transition_intention(first.intention_id,expected_revision=1,state='COMPLETED')
        before=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1]
        spec=SocialExpectationSpec(topic='creative-project',expectation=expectation)
        capture(app.runtime,'later-private-boundary',spec.model_dump(mode='json'),kind='USER_STATEMENT',
            predicate='social.expectation.creative-project')
        cycle,_=private_choice(app,'private-rest-with-boundary','REST')
        assert cycle.intention.behavior=='REST' and cycle.evaluation.normative=='UNDECIDED'
        after=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1]
        assert after.intent_id==before.intent_id and after.activity_state=='PAUSED' and after.revision==2
        with pytest.raises(CoreError,match='PRIVATE_INTENT_WITHHELD'):
            eligible_content(app.runtime.store,after.intent_id,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants') and not app.runtime.store.all('cognitive_requests')


def test_unbound_creative_choice_still_respects_separate_sourced_norm(tmp_path):
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        norm=ConcernCue(cue_kind='CONSTRAINT',topic_key='creative-project',motivation_source='NORM',prohibited_behaviors=('CREATE',))
        capture(app.runtime,'creative-norm',norm.model_dump(mode='json'),kind='USER_STATEMENT',predicate='concern.constraint.creative-project')
        spec=SocialExpectationSpec(topic='creative-project',expectation='EXPLICITLY_PRIVATE')
        capture(app.runtime,'creative-boundary',spec.model_dump(mode='json'),kind='USER_STATEMENT',predicate='social.expectation.creative-project')
        _,_,cycle=choose(app)
        assert cycle.intention.behavior!='CREATE' and not candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants') and not app.runtime.store.all('cognitive_requests')


@pytest.mark.parametrize('condition,expected',[
    ('active','WAIT'),('paused','WAIT'),('abandoned','GOAL_CANDIDATE'),
    ('unrelated','GOAL_CANDIDATE'),('withdrawn','GOAL_CANDIDATE'),('disabled','GOAL_CANDIDATE'),
])
def test_internal_thought_projection_changes_existing_c_deliberation_after_restart(tmp_path,monkeypatch,condition,expected):
    from nana_core.continuity.autonomy import private_intent
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextAssembler,ContextPolicy,ContextRequest
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        original,_,created=choose(app)
        app.runtime.subject.transition_intention(created.intention_id,expected_revision=1,state='COMPLETED')
        summary=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1].content_summary
        if condition in {'paused','abandoned'}:private_choice(app,'before-deliberation','REST' if condition=='paused' else 'WITHDRAW')
        if condition=='withdrawn':app.forget(original)
        identity=app.runtime.identity_id
    with LifeApplication(home) as app:
        r=app.runtime;assert r.identity_id==identity
        if condition=='disabled':monkeypatch.setattr(private_intent,'internal_projection',lambda *args,**kwargs:())
        topic='other-project' if condition=='unrelated' else 'creative-project'
        cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key=topic,motivation_source='CREATIVE_INTEREST',possible_behaviors=('CREATE',),resource_class='ORDINARY')
        mid=capture(r,'internal-reconsideration',cue.model_dump(mode='json'),predicate='concern.internal-reconsideration')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.internal-reconsideration',
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        policy=ContextPolicy(policy_id='private-internal-fixture',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'))
        calls=[]
        class ExistingDeliberationFixture:
            descriptor='offline-private-thought-deliberation-fixture'
            def propose(self,request):
                data=json.loads(request.context_json);calls.append(data)
                own=[json.loads(b['data_json']) for b in data['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE']
                assert all(v['epistemic_status']=='OWN_TENDENCY_NOT_WORLD_FACT' and not v['recipient_disclosure'] and not v['execution_authority'] for v in own)
                base=json.loads(AnalyticalFixturePort().propose(request))
                # Frozen fixture rule, not a claim of LLM quality: only actually
                # supplied own content can request further clarification.
                base['proposed_operations']=['ASK'] if any(v['content_summary']==summary for v in own) else ['DRAFT']
                return json.dumps(base)
        result=r.subject.cognize(event,model=ExistingDeliberationFixture(),authority=r.authority,policy=policy)
        assert result.intention.kind==expected and len(calls)==1
        print('PRIVATE_INTERNAL_MEASURE',condition,'fixture_calls',len(calls),'context_counter',calls[0]['manifest']['counter'],
            'context_units',calls[0]['manifest']['input_tokens'],'input_limit',calls[0]['manifest']['input_limit'])
        assert calls[0]['manifest']['input_limit']==61440
        assert calls[0]['manifest']['input_tokens']<=61440
        ordinary=ContextAssembler(r.store,r.authority).assemble(ContextRequest(entity_id='project-user',scopes=('project-work',),
            task_class='dialogue',task='SYNTHETIC ordinary response',task_privacy_class='PROJECT',max_input_tokens=65536),policy)
        assert not any(b.kind=='PRIVATE_INTERNAL_STATE' for b in ordinary.blocks)
        assert summary not in ordinary.model_dump_json()
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


def test_internal_projection_uses_original_complete_budget_and_invalidates_on_withdrawal(tmp_path,monkeypatch):
    from nana_core.continuity.autonomy import private_intent
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextAssembler,ContextPolicy,ContextRequest
    from nana_core.continuity.subject.contracts import DeliberationFrame
    from nana_core.continuity.subject.policy import appraise,motivate,decide
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        original,_,created=choose(app)
        r=app.runtime;r.subject.transition_intention(created.intention_id,expected_revision=1,state='COMPLETED')
        cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='creative-project',motivation_source='CREATIVE_INTEREST',possible_behaviors=('CREATE',))
        mid=capture(r,'private-budget',cue.model_dump(mode='json'),predicate='concern.private-budget')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.private-budget',
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        source=r.subject.ingress.ingest(event);situation=r.subject.situation(event,source);appraisal=appraise(event,situation);motives=motivate(event,situation,appraisal)
        frame=DeliberationFrame(subject_event_id=source['subject_event_id'],scope=event.scope,appraisal=appraisal,motivations=motives,
            attention=decide(event,situation,appraisal,motives)[0],source_memory_ids=situation.memory_ids,source_record_ids=situation.support_record_ids)
        policy=ContextPolicy(policy_id='internal-budget-fixture',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'))
        request=ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='subject_deliberation',task='SYNTHETIC private reconsideration',
            task_privacy_class='PROJECT',max_input_tokens=65536,output_reserve_tokens=4096)
        assembler=ContextAssembler(r.store,r.authority)
        enabled=assembler.assemble(request,policy,subject_frame=frame)
        with monkeypatch.context() as patch:
            patch.setattr(private_intent,'internal_projection',lambda *args,**kwargs:())
            disabled=assembler.assemble(request,policy,subject_frame=frame)
        assert any(b.kind=='PRIVATE_INTERNAL_STATE' for b in enabled.blocks)
        assert not any(b.kind=='PRIVATE_INTERNAL_STATE' for b in disabled.blocks)
        assert enabled.manifest.input_limit==disabled.manifest.input_limit==61440
        assert enabled.manifest.input_tokens>disabled.manifest.input_tokens
        # Find the minimum valid original package budget, without changing its
        # mandatory rules or counting bytes as actual model tokens.
        low,high=4096+256,65536
        while low<high:
            bound=(low+high)//2
            try:assembler.assemble(request.model_copy(update={'max_input_tokens':bound}),policy,subject_frame=frame)
            except CoreError as exc:
                assert exc.code=='INSUFFICIENT_CONTEXT_BUDGET';low=bound+1
            else:high=bound
        compact_request=request.model_copy(update={'max_input_tokens':low})
        compact=assembler.assemble(compact_request,policy,subject_frame=frame)
        assert compact.manifest.input_tokens<=compact.manifest.input_limit
        assert not any(b.kind=='PRIVATE_INTERNAL_STATE' for b in compact.blocks)
        assert any(x.startswith('private-internal:') for x in compact.manifest.omitted_ids)
        calls=[]
        class WithdrawalDuringInference:
            descriptor='offline-withdrawal-during-existing-inference'
            def propose(self,request):
                calls.append(request);reply=AnalyticalFixturePort().propose(request)
                app.forget(original)
                return reply
        with pytest.raises(CoreError,match='STALE_CONTEXT'):
            r.subject.cognize(event,model=WithdrawalDuringInference(),authority=r.authority,policy=policy)
        assert len(calls)==1
        assert not r.store.db.execute('SELECT 1 FROM subject_cycles WHERE subject_event_id=?',(source['subject_event_id'],)).fetchone()
        assert not private_intent.internal_projection(r.store,frame.source_record_ids,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')
        print('PRIVATE_INTERNAL_SAME_STATE_BUDGET',enabled.manifest.counter,'enabled',enabled.manifest.input_tokens,
            'disabled',disabled.manifest.input_tokens,'limit',enabled.manifest.input_limit,'minimum_package_limit',compact.manifest.input_limit)


@pytest.mark.parametrize('next_behavior',['EXPLORE','LEARN','SEEK_CAPABILITY'])
def test_own_new_question_without_user_message_survives_restart_and_changes_future_choice(tmp_path,monkeypatch,next_behavior):
    from nana_core.continuity.autonomy import private_intent
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.records import RecordService
    from nana_core.continuity.context import ContextPolicy,ContextAssembler,ContextRequest
    from nana_core.continuity.subject.opportunities import OpportunityAssessment,LearningValue
    import sqlite3
    from nana_core.life.inspector import _ReadView
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    question='SYNTHETIC-PRIVATE-NEW-QUESTION: Could this creative project become an interactive story?'
    calls=[]
    with LifeApplication(home) as app:
        original,_,created=choose(app)
        r=app.runtime;r.subject.transition_intention(created.intention_id,expected_revision=1,state='COMPLETED')
        own_rid=candidates(r.store,'project-work',('PUBLIC','PROJECT'))[0][0]
        identity=r.identity_id
        # The wake contains no new user text, source memory or external event.
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.own-question',
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic='creative-project',observed_at_us=r.clock.utc_now_us())
        policy=ContextPolicy(policy_id='own-question-fixture',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'))
        class OwnQuestionFixture:
            descriptor='offline-own-question-fixture-not-quality-evidence'
            def propose(self,request):
                calls.append(request)
                base=json.loads(AnalyticalFixturePort().propose(request))
                base.update(interpretation=question,private_question={'topic':'creative-project','question':question,'related_private_record_ids':[own_rid]})
                return json.dumps(base)
        result=r.subject.cognize(event,model=OwnQuestionFixture(),authority=r.authority,policy=policy)
        assert result.judgment.stance=='REFLECT' and result.intention.behavior=='REFLECT' and len(calls)==1
        assert question not in result.model_dump_json()
        values=[(rid,v) for rid,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if v.category=='PRIVATE_QUESTION']
        assert len(values)==1
        qrid,q=values[0]
        assert q.content_summary==question and q.epistemic_status=='OWN_QUESTION_NOT_WORLD_FACT'
        assert q.disclosure_policy=='PRIVATE_FOR_NOW' and not q.execution_authority
        assert not event.source_memory_ids and event.text is None
        assert r.store.db.execute("SELECT 1 FROM record_dependencies WHERE record_id=? AND parent_kind='RECORD' AND parent_id=? AND relation_kind='SUPPORT'",(qrid,own_rid)).fetchone()
        assert r.store.one('subject_intentions',result.intention_id)['state']=='COMPLETED'
        changes=r.store.db.total_changes
        assert r.subject.cognize(event,model=OwnQuestionFixture(),authority=r.authority,policy=policy).replayed
        assert len(calls)==1 and r.store.db.total_changes==changes
        private_choice(app,'abandon-seed-after-question','WITHDRAW',intent_id=created.intention_id)
        backup=tmp_path/'inactive'/'question.db';r.store.backup(backup)
        def backup_questions():
            with sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True) as db:
                db.row_factory=sqlite3.Row
                return [v for _,v in candidates(_ReadView(db,backup,'project-work',('PUBLIC','PROJECT')),'project-work',('PUBLIC','PROJECT')) if v.category=='PRIVATE_QUESTION']
        assert backup_questions()[0].content_summary==question
    with LifeApplication(home) as app:
        r=app.runtime;assert r.identity_id==identity
        assert any(v.content_summary==question for _,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')))
        private_choice(app,'pause-own-question','REST',intent_id=q.intent_id)
        paused=next(v for _,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if v.intent_id==q.intent_id)
        assert paused.contract=='PRIVATE_QUESTION_V3' and paused.activity_state=='PAUSED' and paused.content_summary==question
        private_choice(app,'resume-own-question','CREATE',intent_id=q.intent_id)
        qrid,resumed=next((rid,v) for rid,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if v.intent_id==q.intent_id)
        assert resumed.contract=='PRIVATE_QUESTION_V3' and resumed.activity_state=='ACTIVE' and resumed.content_summary==question
        cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key='creative-project',motivation_source='CURIOSITY',possible_behaviors=(next_behavior,),
            resource_class='ORDINARY',opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'),
            learning_value=LearningValue(goal_value='LOW',future_reuse='LOW',interest='LOW',relationship_relevance='LOW',alternative='AVAILABLE')
                if next_behavior in {'LEARN','SEEK_CAPABILITY'} else None)
        def next_event(key):
            mid=capture(r,key,cue.model_dump(mode='json'),predicate='concern.'+key)
            return SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.'+key,
                kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        with monkeypatch.context() as patch:
            patch.setattr(private_intent,'decision_support',lambda *args,**kwargs:())
            before=r.subject.run(next_event('without-inner-interest'))
        after=r.subject.run(next_event('with-inner-interest'))
        assert before.intention.behavior=='IGNORE' and after.intention.behavior==next_behavior
        assert next(m for m in after.motivations if m.source=='PRIVATE_INTEREST').source_ids==(qrid,)
        ordinary=ContextAssembler(r.store,r.authority).assemble(ContextRequest(entity_id='project-user',scopes=('project-work',),
            task_class='dialogue',task='SYNTHETIC ordinary response',task_privacy_class='PROJECT',max_input_tokens=65536),policy)
        assert question not in ordinary.model_dump_json() and question not in inspect(home,scope='project-work',entity_id='project-user').model_dump_json()
        with pytest.raises(CoreError,match='WITHHELD'):eligible_content(r.store,q.intent_id,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
        app.forget(original)
        assert not any(v.category=='PRIVATE_QUESTION' for _,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')))
        assert not backup_questions()
        withdrawn=r.subject.run(next_event('after-interest-withdrawal'))
        assert withdrawn.intention.behavior=='IGNORE' and not any(m.source=='PRIVATE_INTEREST' for m in withdrawn.motivations)
        assert len(calls)==1 and not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


@pytest.mark.parametrize('condition',['user','norm','resource','rest','nonretained','unsupported-reference'])
def test_model_question_is_a_candidate_and_c_keeps_original_boundaries(tmp_path,condition):
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextPolicy
    from nana_core.continuity.records import RecordService
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        r=app.runtime;calls=[]
        if condition=='norm':
            norm=ConcernCue(cue_kind='CONSTRAINT',topic_key='creative-project',motivation_source='NORM',prohibited_behaviors=('REFLECT',))
            capture(r,'question-norm',norm.model_dump(mode='json'),kind='USER_STATEMENT',predicate='concern.constraint.question')
        cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='creative-project',motivation_source='CURIOSITY',
            possible_behaviors=('REST',) if condition=='rest' else ('REFLECT',),
            resource_ref='synthetic://private/resource' if condition=='resource' else None,resource_class='ORDINARY')
        mid=capture(r,'question-admission',cue.model_dump(mode='json'),predicate='concern.question-admission')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.question-admission',
            kind='WAKE' if condition!='user' else 'INTERACTION',origin='USER' if condition=='user' else 'SELF_WAKE',
            entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),source_memory_ids=() if condition=='nonretained' else (mid,),
            retention='DO_NOT_REMEMBER' if condition=='nonretained' else 'MAY_REMEMBER')
        class CandidateFixture:
            descriptor='offline-question-candidate-admission'
            def propose(self,request):
                calls.append(request);base=json.loads(AnalyticalFixturePort().propose(request))
                base['private_question']={'topic':'creative-project','question':'SYNTHETIC private question never a command',
                    'related_private_record_ids':['forged-private-record'] if condition=='unsupported-reference' else []}
                return json.dumps(base)
        policy=ContextPolicy(policy_id='question-admission',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'))
        if condition=='unsupported-reference':
            with pytest.raises(CoreError,match='UNSUPPORTED_PRIVATE_QUESTION_REFERENCE'):
                r.subject.cognize(event,model=CandidateFixture(),authority=r.authority,policy=policy)
        else:r.subject.cognize(event,model=CandidateFixture(),authority=r.authority,policy=policy)
        assert not any(v.category=='PRIVATE_QUESTION' for _,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')))
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


def test_existing_runtime_self_queue_drives_one_question_without_periodic_inference(tmp_path,monkeypatch):
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.presence.contracts import RuntimeEvent,Cause
    # An isolated nominal fixture reservation, never a real-provider budget.
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0,provider_cost_ceiling_micro=1000)
    with LifeApplication(home) as app:
        _,_,created=choose(app)
        r=app.runtime;r.subject.transition_intention(created.intention_id,expected_revision=1,state='COMPLETED')
        r.cognition.set_model('analytical');calls=[]
        class RuntimeQuestionFixture:
            descriptor='offline-existing-runtime-private-question-fixture'
            def propose(self,request):
                calls.append(request);data=json.loads(request.context_json)
                private=next(b for b in data['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE')
                base=json.loads(AnalyticalFixturePort().propose(request))
                base['private_question']={'topic':'creative-project','question':'SYNTHETIC: What alternative form could this project take?',
                    'related_private_record_ids':private['source_record_ids']}
                return json.dumps(base)
        monkeypatch.setattr(r.cognition,'port',lambda call:RuntimeQuestionFixture())
        now=r.clock.utc_now_us()
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.queued-own-question',
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic='creative-project',
            observed_at_us=now,significance='HIGH',uncertainty='HIGH')
        qid=r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=event,
            causes=(Cause(kind='CANONICAL_SELF',reference_id=r.identity_id),
                Cause(kind='INTENTION',reference_id=created.intention_id,revision=2)),due_at_us=now,priority=0))
        result=r.step()
        assert result['queue_id']==qid and result['mode']=='FULL_COGNITION' and result['cycle'].intention.behavior=='REFLECT',result['reason']
        assert r.store.one('runtime_queue',qid)['state']=='DONE'
        assert len(calls)==1 and len(r.store.all('runtime_cognition_calls'))==1
        assert r.store.all('runtime_cognition_calls')[0]['state']=='SUCCEEDED'
        assert len([v for _,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if v.category=='PRIVATE_QUESTION'])==1
        assert r.store.one('subject_intentions',result['cycle'].intention_id)['state']=='COMPLETED'
        for _ in range(3):r.step()
        assert len(calls)==1 and len(r.store.all('runtime_cognition_calls'))==1
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


@pytest.mark.parametrize('condition,expected',[('risk','REST'),('norm','IGNORE'),('withdrawn','IGNORE')])
def test_private_learning_interest_keeps_original_risk_norm_and_source_constraints(tmp_path,condition,expected):
    from nana_core.continuity.subject.opportunities import LearningValue,OpportunityAssessment
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        mid,_,created=choose(app);r=app.runtime
        r.subject.transition_intention(created.intention_id,expected_revision=1,state='COMPLETED')
        if condition=='withdrawn':app.forget(mid)
        if condition=='norm':
            norm=ConcernCue(cue_kind='CONSTRAINT',topic_key='creative-project',motivation_source='NORM',prohibited_behaviors=('LEARN',))
            capture(r,'learning-norm',norm.model_dump(mode='json'),kind='USER_STATEMENT',predicate='concern.constraint.private-learning')
        cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key='creative-project',motivation_source='CURIOSITY',possible_behaviors=('LEARN',),
            resource_class='ORDINARY',opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'),
            learning_value=LearningValue(goal_value='LOW',future_reuse='LOW',interest='LOW',alternative='AVAILABLE',risk='HIGH' if condition=='risk' else 'LOW'))
        source=capture(r,'private-learning-boundary',cue.model_dump(mode='json'),predicate='concern.private-learning-boundary')
        result=r.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.private-learning-boundary',
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(source,)))
        assert result.intention.behavior==expected
        assert cue.learning_value.interest=='LOW' and cue.learning_value.alternative=='AVAILABLE'
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


def test_private_question_revision_keeps_own_lineage_and_rejects_wrong_or_stale_target(tmp_path):
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextPolicy
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    old_text='SYNTHETIC private question before new evidence'
    new_text='SYNTHETIC revised private question after reconsideration'
    with LifeApplication(home) as app:
        original,_,seed=choose(app);r=app.runtime
        r.subject.transition_intention(seed.intention_id,expected_revision=1,state='COMPLETED')
        seed_rid=candidates(r.store,'project-work',('PUBLIC','PROJECT'))[0][0];calls=[]
        policy=ContextPolicy(policy_id='private-question-revision',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'))
        def think(key,text,revision_of=None):
            event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.'+key,
                kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic='creative-project',observed_at_us=r.clock.utc_now_us())
            class QuestionFixture:
                descriptor='offline-private-question-revision-fixture'
                def propose(self,request):
                    calls.append(request);base=json.loads(AnalyticalFixturePort().propose(request))
                    base['private_question']={'topic':'creative-project','question':text,'revises_record_id':revision_of}
                    base['interpretation']=text
                    return json.dumps(base)
            return r.subject.cognize(event,model=QuestionFixture(),authority=r.authority,policy=policy)
        created=think('question-created',old_text)
        assert r.store.one('subject_intentions',created.intention_id)['state']=='COMPLETED'
        old_rid,old=next((rid,v) for rid,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if v.category=='PRIVATE_QUESTION')
        with pytest.raises(CoreError,match='UNSUPPORTED_PRIVATE_QUESTION_REVISION'):think('cannot-revise-creative-idea',new_text,seed_rid)
        changed=think('question-revised',new_text,old_rid)
        assert changed.intention.behavior=='REFLECT' and new_text not in changed.model_dump_json()
        current_rid,current=next((rid,v) for rid,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if v.category=='PRIVATE_QUESTION')
        assert current.intent_id==old.intent_id and current.revision==2 and current.content_summary==new_text
        assert current.created_at_us==old.created_at_us and current.updated_at_us>=old.updated_at_us
        assert r.store.one('continuity_records',old_rid)['lifecycle']=='SUPERSEDED'
        assert r.store.db.execute("SELECT 1 FROM record_dependencies WHERE record_id=? AND parent_id=? AND relation_kind='SUPPORT'",(current_rid,old_rid)).fetchone()
        assert r.store.one('subject_intentions',changed.intention_id)['state']=='COMPLETED'
        with pytest.raises(CoreError,match='UNSUPPORTED_PRIVATE_QUESTION_REVISION'):think('stale-question-version',old_text,old_rid)
        same=think('unchanged-question',new_text,current_rid)
        assert next(rid for rid,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if v.category=='PRIVATE_QUESTION')==current_rid
        assert next(v.revision for _,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if v.category=='PRIVATE_QUESTION')==2
        assert new_text not in same.model_dump_json()
        app.forget(original)
        assert not candidates(r.store,'project-work',('PUBLIC','PROJECT'))
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


def test_original_c_can_retain_more_than_32_distinct_private_creative_interests(tmp_path):
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        for i in range(40):
            _,_,result=choose(app,'own-interest-'+str(i),topic='own-interest-'+str(i))
            assert result.intention.behavior=='CREATE' and result.evaluation.normative=='ENDORSED'
            app.runtime.subject.transition_intention(result.intention_id,expected_revision=1,state='COMPLETED')
        values=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
        assert len(values)==40 and len({v.intent_id for _,v in values})==40
        # The optional artifact lookup must ignore binary and unrelated JSON;
        # the shared artifact store is not restricted to private JSON objects.
        with app.runtime.store.transaction('fixture.nonprivate_artifacts') as tx:
            raw=b'\x00\xff\x89SYNTHETIC_BINARY'
            binary=tx.artifact(raw);tx.artifact(b'[1,2]');tx.artifact(b'"SYNTHETIC plain JSON"')
        assert app.runtime.store.artifact(binary)==raw
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants') and not app.runtime.store.all('cognitive_requests')


def test_own_question_can_open_and_reframe_a_new_topic_without_changing_scope_or_disclosing_it(tmp_path,monkeypatch):
    from nana_core.continuity.autonomy import private_intent
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextPolicy
    from nana_core.continuity.records import RecordService
    from nana_core.continuity.subject.opportunities import OpportunityAssessment
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        _,_,seed=choose(app);r=app.runtime
        r.subject.transition_intention(seed.intention_id,expected_revision=1,state='COMPLETED')
        calls=[];policy=ContextPolicy(policy_id='own-new-topic',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'))
        def think(key,context_topic,new_topic,text,revision=None):
            class QuestionFixture:
                descriptor='offline-own-topic-transition-fixture'
                def propose(self,request):
                    calls.append(request);base=json.loads(AnalyticalFixturePort().propose(request))
                    base['private_question']={'topic':new_topic,'question':text,'revises_record_id':revision}
                    return json.dumps(base)
            return r.subject.cognize(SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.'+key,
                kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic=context_topic,observed_at_us=r.clock.utc_now_us()),
                model=QuestionFixture(),authority=r.authority,policy=policy)
        created=think('new-direction','creative-project','story-research','SYNTHETIC private question about a newly imagined story direction')
        assert created.intention.behavior=='REFLECT'
        assert r.store.one('subject_intentions',created.intention_id)['state']=='COMPLETED'
        rid,old=next((rid,q) for rid,q in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if q.category=='PRIVATE_QUESTION')
        assert old.topic=='story-research'
        # A historical eligibility fixture does NOT claim an actual send.
        with r.store.transaction('fixture.old_question_public_eligibility') as tx:
            eligible=old.model_copy(update={'disclosure_policy':'PUBLIC','status':'DISCLOSURE_ELIGIBLE','revision':old.revision+1})
            rid=RecordService(r.store).create(tx,kind='INTENTION',scope='project-work',payload=eligible.model_dump(mode='json'),
                records=(rid,),supersedes=rid,target_id='private-intent.v1')
        assert not eligible_content(r.store,eligible.intent_id,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))['delivery_authority']
        changed=think('reframe-direction','story-research','interactive-story-research','SYNTHETIC private question reframed toward interactive stories',rid)
        assert changed.intention.behavior=='REFLECT' and len(calls)==2
        new_rid,new=next((rid,q) for rid,q in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if q.category=='PRIVATE_QUESTION')
        assert new.intent_id==old.intent_id and new.topic=='interactive-story-research' and new.revision==eligible.revision+1
        assert new.disclosure_policy=='PRIVATE_FOR_NOW' and new.status=='CONSIDERED' and new.trigger_at_us is None
        assert r.store.one('continuity_records',new_rid)['scope']=='project-work'
        assert not private_intent.decision_support(r.store,'project-work',('PUBLIC','PROJECT'),topic='story-research')
        assert private_intent.decision_support(r.store,'project-work',('PUBLIC','PROJECT'),topic=new.topic)==(new_rid,)
        assert not private_intent.decision_support(r.store,'other-scope',('PUBLIC','PROJECT'),topic=new.topic)
        with pytest.raises(CoreError,match='WITHHELD'):eligible_content(r.store,new.intent_id,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
        assert r.store.one('subject_intentions',changed.intention_id)['state']=='COMPLETED'
        cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key=new.topic,motivation_source='CURIOSITY',possible_behaviors=('EXPLORE',),resource_class='ORDINARY',
            opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'))
        mid=capture(r,'new-focus-opportunity',cue.model_dump(mode='json'),predicate='concern.new-focus-opportunity')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.follow-new-focus',kind='WAKE',origin='SELF_WAKE',
            entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        with monkeypatch.context() as patch:
            patch.setattr(private_intent,'decision_support',lambda *args,**kwargs:())
            before=r.subject.run(event.model_copy(update={'source_key':'development.without-new-focus'}))
        after=r.subject.run(event)
        assert before.intention.behavior=='IGNORE' and after.intention.behavior=='EXPLORE'
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


@pytest.mark.parametrize('other_pending',[False,True])
def test_recorded_private_questions_do_not_accumulate_as_pending_external_work(tmp_path,other_pending):
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextPolicy
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        _,_,seed=choose(app);r=app.runtime
        r.subject.transition_intention(seed.intention_id,expected_revision=1,state='COMPLETED')
        pending=[]
        if other_pending:
            for i in range(8):
                cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key='pending-work-'+str(i),motivation_source='CURIOSITY',
                    possible_behaviors=('EXPLORE',),resource_class='ORDINARY',urgency='HIGH')
                mid=capture(r,'pending-work-'+str(i),cue.model_dump(mode='json'),predicate='concern.pending-work-'+str(i))
                cycle=r.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.pending-work-'+str(i),
                    kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,)))
                assert cycle.intention.kind=='EXPLORE'
                pending.append(dict(r.store.one('subject_intentions',cycle.intention_id)))
        counts={table:len(r.store.all(table)) for table in ('experiences','lessons','relationship_events')};calls=[]
        policy=ContextPolicy(policy_id='private-formation',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'))
        for i in range(10):
            class QuestionFixture:
                descriptor='offline-private-question-formation-fixture'
                def propose(self,request):
                    calls.append(request);base=json.loads(AnalyticalFixturePort().propose(request))
                    base['private_question']={'topic':'creative-project','question':'SYNTHETIC distinct private question '+str(i)}
                    return json.dumps(base)
            result=r.subject.cognize(SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.form-private-question-'+str(i),
                kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic='creative-project',observed_at_us=r.clock.utc_now_us()),
                model=QuestionFixture(),authority=r.authority,policy=policy)
            assert result.intention.behavior=='REFLECT'
            assert r.store.one('subject_intentions',result.intention_id)['state']=='COMPLETED'
        questions=[v for _,v in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if v.category=='PRIVATE_QUESTION']
        assert len(questions)==10 and all(v.activity_state=='ACTIVE' and v.execution_state=='NOT_INFERRED_FROM_ACTIVITY_STATE' for v in questions)
        assert len(r.subject.pending('project-work'))==len(pending)
        assert all(r.store.one('subject_intentions',row['intention_id'])==row for row in pending)
        if other_pending:
            resting,_=private_choice(app,'quiet-review-with-full-work-queue','REST',intent_id=questions[0].intent_id)
            assert resting.intention.behavior=='REST'
            assert next(q.activity_state for _,q in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if q.intent_id==questions[0].intent_id)=='PAUSED'
            assert len(r.subject.pending('project-work'))==8
            assert all(r.store.one('subject_intentions',row['intention_id'])==row for row in pending)
        assert all(len(r.store.all(table))==before for table,before in counts.items())
        assert len(calls)==10 and not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')
        identity=r.identity_id
    with LifeApplication(home) as app:
        assert app.runtime.identity_id==identity and len(app.runtime.subject.pending('project-work'))==len(pending)
        if not other_pending:
            foreground=app.chat('只是吐槽：SYNTHETIC foreground conversation still has room.',topic='ordinary',privacy='PROJECT',message_id='foreground-after-thoughts')
            assert foreground['mode']=='VENT' and foreground['intention']=='SOCIAL_INTERACTION'
        assert len(calls)==10


@pytest.mark.parametrize('schema_target',[8,12])
def test_old_store_does_not_claim_or_queue_an_unsupported_private_question(tmp_path,schema_target):
    from nana_core.actions import OperatorAuthority
    from nana_core.continuity import ContinuityStore,IdentityService
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
    from nana_core.continuity.subject import SubjectLoop
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextPolicy
    clock=VirtualClock();authority=OperatorAuthority()
    with ContinuityStore(tmp_path/'old'/'self.db',clock,schema_target=schema_target) as store:
        IdentityService(store,authority);memory=MemoryService(store);memory.entity('old-person','PERSON')
        text='SYNTHETIC old-store context'
        eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.private.old',source_reference='seed',source_kind='USER_STATEMENT'),
            text=text,privacy_class='PROJECT',observed_time_us=clock.utc_now_us()))
        mid=memory.add(MemoryCandidate(entity_id='old-person',scope='old-scope',memory_type=MemoryType.EPISODIC,epistemic_kind='STATEMENT',source_evidence_id=eid,text=text))
        class UnsupportedQuestionFixture:
            descriptor='offline-old-store-question-fixture'
            def propose(self,request):
                base=json.loads(AnalyticalFixturePort().propose(request))
                base['private_question']={'topic':'new-direction','question':'SYNTHETIC unsupported private-state contract'}
                return json.dumps(base)
        loop=SubjectLoop(store,scopes=('old-scope',))
        result=loop.cognize(SubjectInput(source_key='synthetic.private.old-question',kind='WAKE',origin='SELF_WAKE',entity_id='old-person',scope='old-scope',
            privacy_class='PROJECT',topic='old-topic',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,)),model=UnsupportedQuestionFixture(),
            authority=authority,policy=ContextPolicy(policy_id='old-private-profile',allowed_scopes=('old-scope',),readable_privacy=('PROJECT',)))
        assert result.intention.kind=='NO_ACTION' and result.intention_id is None and not loop.pending('old-scope')
        assert 'SYNTHETIC unsupported private-state contract' not in result.model_dump_json()
        assert not store.all('actions') and not store.all('grants')


def test_question_record_and_formation_completion_roll_back_in_one_original_transaction(tmp_path,monkeypatch):
    from nana_core.continuity.autonomy import private_intent
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextPolicy
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        _,_,seed=choose(app);r=app.runtime
        r.subject.transition_intention(seed.intention_id,expected_revision=1,state='COMPLETED')
        counts={table:len(r.store.all(table)) for table in ('subject_cycles','subject_intentions')};revision=r.subject.revision;calls=[]
        class QuestionFixture:
            descriptor='offline-atomic-question-formation-fixture'
            def propose(self,request):
                calls.append(request);base=json.loads(AnalyticalFixturePort().propose(request))
                base['private_question']={'topic':'creative-project','question':'SYNTHETIC this aborted private question must not become recorded'}
                return json.dumps(base)
        def stop_after_private_write(*args):raise RuntimeError('CONTROLLED_BEFORE_QUESTION_FORMATION_COMPLETION')
        monkeypatch.setattr(private_intent,'_complete_question_formation',stop_after_private_write)
        with pytest.raises(RuntimeError,match='CONTROLLED_BEFORE_QUESTION_FORMATION_COMPLETION'):
            r.subject.cognize(SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.aborted-question-formation',
                kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic='creative-project',observed_at_us=r.clock.utc_now_us()),
                model=QuestionFixture(),authority=r.authority,policy=ContextPolicy(policy_id='atomic-private-question',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT')))
        assert r.subject.revision==revision and all(len(r.store.all(table))==n for table,n in counts.items())
        assert not any(q.category=='PRIVATE_QUESTION' for _,q in candidates(r.store,'project-work',('PUBLIC','PROJECT')))
        assert len(calls)==1 and not r.store.all('actions') and not r.store.all('grants')


@pytest.mark.parametrize('privacy',['PUBLIC','PROJECT','PERSONAL'])
def test_identity_only_cognition_can_form_a_persistent_question_with_own_occurrence_provenance(tmp_path,privacy):
    from nana_core.actions import OperatorAuthority
    from nana_core.continuity import ContinuityStore,IdentityService
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.subject import SubjectLoop
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextPolicy
    clock=VirtualClock();authority=OperatorAuthority();path=tmp_path/'own'/'self.db';calls=[]
    text='SYNTHETIC entirely new question without prior world observations or memories'
    with ContinuityStore(path,clock,schema_target=13) as store:
        IdentityService(store,authority);MemoryService(store).entity('counterparty','PERSON')
        assert not store.all('memories') and not store.all('projects')
        class InitialQuestionFixture:
            descriptor='offline-identity-only-question-fixture'
            def propose(self,request):
                calls.append(request);data=json.loads(request.context_json)
                assert not any(b['source_memory_ids'] for b in data['blocks'])
                base=json.loads(AnalyticalFixturePort().propose(request));assert not base['memory_refs']
                base.update(private_question={'topic':'own-new-question','question':text},interpretation=text)
                return json.dumps(base)
        loop=SubjectLoop(store,scopes=('own-scope',),privacy_classes=(privacy,))
        event=SubjectInput(source_key='synthetic.identity-only-question',kind='WAKE',origin='SELF_WAKE',entity_id='counterparty',scope='own-scope',
            privacy_class=privacy,observed_at_us=clock.utc_now_us())
        policy=ContextPolicy(policy_id='identity-only-cognition',allowed_scopes=('own-scope',),readable_privacy=(privacy,))
        result=loop.cognize(event,model=InitialQuestionFixture(),authority=authority,policy=policy)
        private=candidates(store,'own-scope',(privacy,));assert len(private)==1
        rid,question=private[0]
        assert question.content_summary==text and question.epistemic_status=='OWN_QUESTION_NOT_WORLD_FACT'
        assert store.one('continuity_records',rid)['privacy_class']==privacy and text not in result.model_dump_json()
        assert store.one('subject_intentions',result.intention_id)['state']=='COMPLETED'
        assert len(question.source_memory_ids)==1
        source=MemoryService(store).read(question.source_memory_ids[0])
        assert source['entity_id']==store.identity['identity_id'] and source['epistemic_kind']=='OBSERVATION'
        assert source['source_provenance']['domain']=='SELF_COGNITION' and source['source_provenance']['source_kind']=='SYSTEM_VERIFICATION'
        assert text not in source['text'] and 'candidate' in source['text'].lower()
        assert not store.all('world_beliefs') and not store.all('experiences') and not store.all('lessons') and not store.all('actions')
        identity=store.identity['identity_id'];memory_id=source['memory_id']
        before=store.db.total_changes;assert loop.cognize(event,model=InitialQuestionFixture(),authority=authority,policy=policy).replayed
        assert len(calls)==1 and store.db.total_changes==before
    with ContinuityStore(path,clock,schema_target=13) as store:
        assert store.identity['identity_id']==identity and candidates(store,'own-scope',(privacy,))[0][1].content_summary==text
        MemoryService(store,authority).forget(memory_id,authority)
        assert not candidates(store,'own-scope',(privacy,)) and store.identity['identity_id']==identity
        assert len(calls)==1


@pytest.mark.parametrize('crowding',['unrelated','withdrawn'])
def test_old_relevant_private_interest_survives_many_unrelated_current_ideas(tmp_path,crowding):
    from nana_core.continuity.autonomy.private_intent import decision_support
    from nana_core.continuity.records import RecordService
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        source,_,created=choose(app,'stable-own-interest',topic='stable-project')
        r=app.runtime;r.subject.transition_intention(created.intention_id,expected_revision=1,state='COMPLETED')
        own_rid,own=candidates(r.store,'project-work',('PUBLIC','PROJECT'))[0]
        # Typed synthetic records measure retrieval crowding, not 100 lived
        # experiences or 100 model-generated thoughts.
        with r.store.transaction('fixture.unrelated_private_ideas') as tx:
            records=RecordService(r.store)
            for i in range(100):
                clock.advance(1)
                value=own.model_copy(update={'intent_id':'synthetic.other-interest-'+str(i),
                    'topic':'other-topic-'+str(i) if crowding=='unrelated' else own.topic,
                    'status':'CONSIDERED' if crowding=='unrelated' else 'WITHDRAWN'})
                records.create(tx,kind='INTENTION',scope='project-work',target_id='private-intent.v1',
                    payload=value.model_dump(mode='json'),records=(created.record_id,))
        queries=[];r.store.db.set_trace_callback(queries.append)
        try:assert decision_support(r.store,'project-work',('PUBLIC','PROJECT'),topic='stable-project')==(own_rid,)
        finally:r.store.db.set_trace_callback(None)
        sql=next(q for q in queries if 'FROM artifacts a INDEXED BY private_intent_topic_lookup_v1' in q)
        plan=[tuple(row) for row in r.store.db.execute('EXPLAIN QUERY PLAN '+sql)]
        assert any('private_intent_topic_lookup_v1' in str(row) for row in plan)
        assert any('private_intent_payload_lookup' in str(row) for row in plan)
        assert decision_support(r.store,'project-work',('PUBLIC',),topic='stable-project')==()
        assert decision_support(r.store,'other-scope',('PUBLIC','PROJECT'),topic='stable-project')==()
        before=r.store.db.execute("SELECT count(*) FROM continuity_records WHERE target_id='private-intent.v1'").fetchone()[0]
        _,_,revisited=choose(app,'revisit-stable-project',topic='stable-project')
        assert revisited.intention.behavior=='CREATE'
        assert r.store.db.execute("SELECT count(*) FROM continuity_records WHERE target_id='private-intent.v1'").fetchone()[0]==before
        # A registered inactive copy without the optional new caches is a
        # read-only compatibility probe, not a second runtime/Store authority.
        import sqlite3
        from nana_core.life.inspector import _ReadView
        backup=tmp_path/'inactive'/'legacy-private.db';r.store.backup(backup)
        with sqlite3.connect(backup) as db:
            db.execute('DROP INDEX private_intent_topic_lookup_v1');db.execute('DROP INDEX private_intent_payload_lookup')
        with sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row;readonly=_ReadView(db,backup,'project-work',('PUBLIC','PROJECT'))
            assert decision_support(readonly,'project-work',('PUBLIC','PROJECT'),topic='stable-project')==(own_rid,)
            assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='private_intent_topic_lookup_v1'").fetchone()
        app.forget(source)
        assert not decision_support(r.store,'project-work',('PUBLIC','PROJECT'),topic='stable-project')
        from nana_core.continuity.store import PRIVATE_INTENT_JSON_FILTER
        assert r.store.db.execute('SELECT count(*) FROM artifacts WHERE '+PRIVATE_INTENT_JSON_FILTER).fetchone()[0]==0


def test_sourced_surprise_trigger_reconsiders_in_c_not_timer_delivery(tmp_path):
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        spec=SocialExpectationSpec(topic='creative-project',expectation='OPEN',timing='DEFER_UNTIL',reveal_at_us=clock.utc_now_us()+1_000_000)
        capture(app.runtime,'expectation',spec.model_dump(mode='json'),kind='USER_STATEMENT',predicate='social.expectation.creative-project')
        mid,event,result=choose(app)
        value=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1]
        assert value.disclosure_policy=='SURPRISE'
        identity=app.runtime.identity_id
    clock.advance(2_000_000)
    with LifeApplication(home,clock=clock) as app:
        assert app.runtime.identity_id==identity
        assert candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1].disclosure_policy=='SURPRISE'
        # Merely inspecting/clock passing did not reveal; ordinary original C did.
        app.runtime.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.review',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=clock.utc_now_us()))
        revised=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1]
        assert revised.disclosure_policy=='DISCLOSED' and revised.revision==2
        content=eligible_content(app.runtime.store,revised.intent_id,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
        assert not content['delivery_authority'] and content['effect_phase']=='PLANNED'
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_private_content_absent_from_chat_board_and_context(tmp_path):
    from nana_core.continuity.context import ContextAssembler,ContextRequest
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        mid,event,result=choose(app)
        value=candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))[0][1]
        reply=app.chat('先别聊这个了',topic='creative-project',privacy='PROJECT')
        assert reply['mode']=='RESPECT_BOUNDARY'
        assert value.content_summary not in json.dumps(reply,ensure_ascii=False)
        assert value.content_summary not in json.dumps(app.board(),ensure_ascii=False)
        package=ContextAssembler(app.runtime.store,app.runtime.authority).assemble(ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='first-life',task='public source review',task_privacy_class='PROJECT'),app.policy)
        assert value.content_summary not in package.model_dump_json()
        assert any(b.kind=='PRIVATE_INTENT_STATE' for b in package.blocks)
        from nana_core.life.control import dispatch
        with pytest.raises(CoreError,match='OPERATION_DENIED'):dispatch(app,{'operation':'private-upsert','content':'roleplay','grant':True})
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_private_timing_source_withdrawal_cannot_reveal_after_restart(tmp_path):
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        spec=SocialExpectationSpec(topic='creative-project',expectation='OPEN',timing='DEFER_UNTIL',reveal_at_us=clock.utc_now_us()+1_000_000)
        timing=capture(app.runtime,'timing-source',spec.model_dump(mode='json'),kind='USER_STATEMENT',predicate='social.expectation.creative-project')
        choose(app)
        assert candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
        app.forget(timing)
    clock.advance(2_000_000)
    with LifeApplication(home,clock=clock) as app:
        assert not candidates(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
        assert not metadata(app.runtime.store,'project-work',('PUBLIC','PROJECT'))
        assert inspect(home,scope='project-work',entity_id='project-user').private_activity!='PRESENT_CONTENT_WITHHELD'


def test_cross_topic_private_association_changes_later_c_choice_without_public_disclosure(tmp_path,monkeypatch):
    from nana_core.continuity.autonomy import private_intent
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextAssembler,ContextPolicy,ContextRequest
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    parent_text='SYNTHETIC question: Could quiet observation reveal a different creative method?'
    child_text='SYNTHETIC question: Could I explore the associated new story direction?'
    policy=ContextPolicy(policy_id='cross-topic-association',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'))
    calls=[]
    def think(app,key,focus,model):
        r=app.runtime
        return r.subject.cognize(SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.'+key,
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic=focus,observed_at_us=r.clock.utc_now_us()),
            model=model,authority=r.authority,policy=policy)
    class QuestionFixture:
        descriptor='offline-associated-question-fixture'
        def __init__(self,topic,text,related=(),revises=None):self.topic,self.text,self.related,self.revises=topic,text,related,revises
        def propose(self,request):
            calls.append(json.loads(request.context_json));base=json.loads(AnalyticalFixturePort().propose(request))
            base['private_question']={'topic':self.topic,'question':self.text,'related_private_record_ids':self.related,'revises_record_id':self.revises}
            return json.dumps(base)
    with LifeApplication(home) as app:
        _,_,seed=choose(app);r=app.runtime
        r.subject.transition_intention(seed.intention_id,expected_revision=1,state='COMPLETED')
        think(app,'association-parent','creative-project',QuestionFixture('old-question',parent_text))
        parent_rid,parent=next((rid,v) for rid,v in candidates(r.store,'project-work',('PROJECT',)) if v.topic=='old-question')
        think(app,'association-child','old-question',QuestionFixture('new-direction',child_text,(parent_rid,)))
        child_rid,child=next((rid,v) for rid,v in candidates(r.store,'project-work',('PROJECT',)) if v.topic=='new-direction')
        assert r.store.db.execute("SELECT 1 FROM record_dependencies WHERE record_id=? AND parent_id=? AND relation_kind='SUPPORT'",(child_rid,parent_rid)).fetchone()
        identity=r.identity_id
    with LifeApplication(home) as app:
        r=app.runtime;assert r.identity_id==identity
        projected=private_intent.internal_projection(r.store,(child_rid,),scope='project-work',privacy_classes=('PROJECT',))
        assert {p['record_id'] for p in projected}=={child_rid,parent_rid}
        child_view=next(p for p in projected if p['record_id']==child_rid)
        assert child_view['related_private_record_ids']==(parent_rid,)
        assert child_view['association_semantics']=='OWN_ASSOCIATION_NOT_WORLD_CAUSATION_OR_PRIORITY'
        class AssociationSensitiveFixture:
            descriptor='offline-association-choice-fixture'
            def propose(self,request):
                data=json.loads(request.context_json);calls.append(data)
                own=[json.loads(b['data_json']) for b in data['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE']
                base=json.loads(AnalyticalFixturePort().propose(request))
                linked=any(p['record_id']==child_rid and parent_rid in p.get('related_private_record_ids',()) for p in own)
                if linked and any(p['content_summary']==parent_text for p in own):base['proposed_operations']=['WAIT']
                return json.dumps(base)
        real_projection=private_intent.internal_projection
        with monkeypatch.context() as patch:
            def flat(*args,**kwargs):return real_projection(*args,**{**kwargs,'include_associations':False})
            patch.setattr(private_intent,'internal_projection',flat)
            before=think(app,'association-off','new-direction',AssociationSensitiveFixture())
        after=think(app,'association-on','new-direction',AssociationSensitiveFixture())
        assert before.intention.kind!='WAIT' and after.intention.kind=='WAIT'
        assert len(calls)==4 and {v['manifest']['input_limit'] for v in calls[-2:]}=={61440}
        assert calls[-1]['manifest']['input_tokens']<=61440
        assert parent_text not in after.model_dump_json() and child_text not in after.model_dump_json()
        assert parent_text not in json.dumps(app.board(),ensure_ascii=False)
        ordinary=ContextAssembler(r.store,r.authority).assemble(ContextRequest(entity_id='project-user',scopes=('project-work',),
            task_class='public-review',task='Review actual public source',task_privacy_class='PROJECT'),policy)
        assert parent_text not in ordinary.model_dump_json() and child_text not in ordinary.model_dump_json()
        assert not private_intent.internal_projection(r.store,(child_rid,),scope='another-scope',privacy_classes=('PROJECT',))
        assert not private_intent.internal_projection(r.store,(child_rid,),scope='project-work',privacy_classes=('PUBLIC',))
        assert not r.store.all('actions') and not r.store.all('grants')
        print('PRIVATE_ASSOCIATION_ABLATION',json.dumps({'before_kind':before.intention.kind,'after_kind':after.intention.kind,
            'input_limit':[v['manifest']['input_limit'] for v in calls[-2:]],'input_units':[v['manifest']['input_tokens'] for v in calls[-2:]],
            'counter':calls[-1]['manifest']['counter'],'fixture_calls_per_choice':1,'real_provider_calls':0}))
        revised=think(app,'revise-associated-question','new-direction',QuestionFixture('new-direction',child_text+' Reconsidered.',revises=child_rid))
        assert revised.intention.behavior=='REFLECT'
        child_rid,child=next((rid,v) for rid,v in candidates(r.store,'project-work',('PROJECT',)) if v.intent_id==child.intent_id)
        assert child.revision==2
        assert {p['record_id'] for p in private_intent.internal_projection(r.store,(child_rid,),scope='project-work',privacy_classes=('PROJECT',))}=={child_rid,parent_rid}
        from nana_core.continuity.subject.opportunities import PrivateIntentRef
        def review(rid,item,behavior,key):
            cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key=item.topic,motivation_source='CREATIVE_INTEREST',possible_behaviors=(behavior,),
                private_intent_ref=PrivateIntentRef(record_id=rid,intent_id=item.intent_id,revision=item.revision),resource_class='ORDINARY')
            mid=capture(r,key,cue.model_dump(mode='json'),predicate='concern.'+key)
            return r.subject.run(SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.'+key,
                kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,)))
        review(child_rid,child,'REST','pause-associated-question')
        paused_rid,paused=next((rid,v) for rid,v in candidates(r.store,'project-work',('PROJECT',)) if v.intent_id==child.intent_id)
        assert paused.activity_state=='PAUSED'
        assert {p['record_id'] for p in private_intent.internal_projection(r.store,(paused_rid,),scope='project-work',privacy_classes=('PROJECT',))}=={paused_rid,parent_rid}
        review(parent_rid,parent,'WITHDRAW','abandon-related-question')
        projection=private_intent.internal_projection(r.store,(paused_rid,),scope='project-work',privacy_classes=('PROJECT',))
        assert {p['record_id'] for p in projection}=={paused_rid}
        assert parent_text not in json.dumps(projection,ensure_ascii=False)
        app.forget(parent.source_memory_ids[0])
        assert not private_intent.internal_projection(r.store,(paused_rid,),scope='project-work',privacy_classes=('PROJECT',))
        assert len(calls)==5


def test_c_can_reconsider_association_without_inventing_a_changed_question(tmp_path):
    from nana_core.continuity.autonomy.private_intent import internal_projection
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.context import ContextPolicy
    home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
    with LifeApplication(home) as app:
        r=app.runtime;_,_,seed=choose(app);r.subject.transition_intention(seed.intention_id,expected_revision=1,state='COMPLETED')
        def propose(key,text,related=(),revises=None):
            class AssociationRevisionFixture:
                descriptor='offline-association-revision-fixture'
                def propose(self,request):
                    base=json.loads(AnalyticalFixturePort().propose(request))
                    base['private_question']={'topic':'creative-project','question':text,'related_private_record_ids':related,'revises_record_id':revises}
                    return json.dumps(base)
            r.subject.cognize(SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.'+key,
                kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic='creative-project',observed_at_us=r.clock.utc_now_us()),
                model=AssociationRevisionFixture(),authority=r.authority,policy=ContextPolicy(policy_id='association-revision',allowed_scopes=('project-work',),readable_privacy=('PROJECT',)))
            return next((rid,v) for rid,v in candidates(r.store,'project-work',('PROJECT',)) if v.content_summary==text)
        a,qa=propose('first-question','SYNTHETIC own question about one possible explanation')
        b,qb=propose('second-question','SYNTHETIC own question about a different explanation')
        old,original=propose('linked-question','SYNTHETIC same question whose association changes',(a,))
        rid,updated=propose('reconsider-link',original.content_summary,(b,),old)
        assert updated.intent_id==original.intent_id and updated.revision==original.revision+1
        projection=internal_projection(r.store,(rid,),scope='project-work',privacy_classes=('PROJECT',))
        assert {v['record_id'] for v in projection}=={rid,b}
        assert next(v for v in projection if v['record_id']==rid)['related_private_record_ids']==(b,)
        same,unchanged=propose('same-association',updated.content_summary,(b,),rid)
        assert same==rid and unchanged.revision==updated.revision
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('lessons')
