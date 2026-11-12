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
            patch.setattr(private_intent,'candidates',lambda *args:((row[0],row[1].model_copy(update={'owner_identity_id':'other-subject'})),))
            assert private_intent.decision_support(store,'project-work',('PUBLIC','PROJECT'),topic='creative-project')==()
        before=len(candidates(store,'project-work',('PUBLIC','PROJECT')))
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',privacy_class='PROJECT',source_key='development.nonretained-private-review',
            kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',topic='creative-project',
            observed_at_us=app.runtime.clock.utc_now_us(),retention='DO_NOT_REMEMBER')
        cycle=app.runtime.subject.run(event)
        assert cycle.intention.kind=='NO_ACTION' and not any(m.source=='PRIVATE_INTEREST' for m in cycle.motivations)
        assert len(candidates(store,'project-work',('PUBLIC','PROJECT')))==before
        assert not store.all('cognitive_requests') and not store.all('actions') and not store.all('grants')


def private_choice(app,key,behavior,*,value='LOW',novelty='REPEATED'):
    from nana_core.continuity.subject.opportunities import OpportunityAssessment,PrivateIntentRef
    r=app.runtime
    rid,item=next((rid,item) for rid,item in candidates(r.store,'project-work',('PUBLIC','PROJECT')) if item.topic=='creative-project')
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
