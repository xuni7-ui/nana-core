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


def choose(app,key='idea'):
    r=app.runtime
    cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='creative-project',motivation_source='CREATIVE_INTEREST',possible_behaviors=('CREATE','REST'),resource_class='ORDINARY')
    mid=capture(r,key,cue.model_dump(mode='json'),predicate='concern.creative-project')
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
