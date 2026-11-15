"""Explicit original-C lifecycle choices reuse existing private records/states."""
import json
import pytest
from nana_core.continuity.autonomy.private_intent import candidates,PrivateThoughtEdit
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_private_tendency import form


@pytest.mark.parametrize('wanted',['PAUSED','ABANDONED'])
@pytest.mark.parametrize('declared',[True,False])
def test_normal_provider_c_can_explicitly_set_one_existing_thought_lifecycle(tmp_path,wanted,declared):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    private='PRIVATE_LIFECYCLE_CANARY: an own question I may keep, pause, or leave without declaring any external effect.'
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app,text=private,topic='own-lifecycle')
        old_rid,old=candidates(app.runtime.store,'project-work',('PROJECT',))[0]
        identity=app.runtime.identity_id;source=old.source_memory_ids[0]
    cfg=load_config(home)
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'provider_background_cognition':True,'provider_context_tokens':32768}),expected_revision=cfg.revision)
    def inner(request):
        package=json.loads(request['context_json']);manifest=package['manifest']
        values=[json.loads(b['data_json']) for b in package['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE']
        value=next(v for v in values if v['record_id']==old_rid);assert value['activity_state']=='ACTIVE'
        offered='activity_state' in request['expected_schema']['$defs']['PrivateTendencyProposal']['properties']
        seen.append(request)
        return {'interpretation':'SYNTHETIC choose the lifespan of only this own idea',
            'subject_cognition':{'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],
                'interpretation':'SYNTHETIC pause or end attention without claiming an action or erasing history',
                'preferred_behavior':'REFLECT','proposed_operations':['DRAFT'],
                'private_tendency':{'topic':'own-lifecycle','tendency':private,'revises_record_id':old_rid,
                    **({'activity_state':wanted} if offered and declared else {})}}}
    with relay(home,subject_builder=inner,context_limit=65536) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity
            app.pause(False);clock.advance(2*SECOND);app.runtime.refresh_attention()
            for _ in range(8):app.tick()
            rid,item=next((r,v) for r,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')) if v.intent_id==old.intent_id)
            measure=app.runtime.store.one('cognitive_requests',seen[0]['request_id']) if seen else None
            print(json.dumps({'measurement':'synthetic_private_lifecycle_choice','wanted':wanted,'declared':declared,'state':item.activity_state,
                'self_calls':len(seen),'input_bytes':measure['input_bytes'] if measure else None,'reserved_bytes':measure['reserved_bytes'] if measure else None},sort_keys=True))
            assert len(seen)==1 and item.activity_state==(wanted if declared else 'ACTIVE')
            if declared:
                assert rid!=old_rid and item.revision==old.revision+1
                assert app.runtime.store.one('continuity_records',rid)['privacy_class']=='PERSONAL'
            else:assert rid==old_rid and item.revision==old.revision
            assert item.intent_id==old.intent_id and item.created_at_us==old.created_at_us and item.content_summary==private
            assert not app.runtime.store.all('goals') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
            assert not app.runtime.store.db.execute('SELECT 1 FROM events WHERE instr(data_json,?)>0',(private,)).fetchone()
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity
            assert next(v for _,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')) if v.intent_id==old.intent_id).activity_state==(wanted if declared else 'ACTIVE')
            clock.advance(3*SECOND);app.runtime.refresh_attention()
            for _ in range(8):app.tick()
            assert len(seen)==1
            # Ending attention keeps the actual private history until its source
            # is withdrawn; withdrawal still clears its dependent contents.
            app.forget(source)
            assert not any(v.intent_id==old.intent_id for _,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')))
            assert not app.runtime.store.db.execute('SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),?)>0',(private,)).fetchone()


@pytest.mark.parametrize('kind,field,category',[('private_question','question','PRIVATE_QUESTION'),('private_plan','plan','PRIVATE_PLAN'),('private_tendency','tendency','PRIVATE_TENDENCY')])
def test_same_c_can_pause_reactivate_and_end_one_idea_while_other_interest_remains(tmp_path,kind,field,category):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app,'other','SYNTHETIC another independent own interest.',topic='lifecycle-target')
        other_rid,other=candidates(app.runtime.store,'project-work',('PROJECT',))[0]
        formation=form(app,'target','SYNTHETIC my own optional idea.',topic='lifecycle-target',kind=kind,related=(other_rid,))
        rid,item=next((r,v) for r,v in candidates(app.runtime.store,'project-work',('PROJECT',)) if v.intent_id==formation.intention_id)
        initial=item;r=app.runtime
        for index,state in enumerate(('PAUSED','PAUSED','ACTIVE','ABANDONED')):
            before_count=r.store.db.execute("SELECT count(*) FROM continuity_records WHERE target_id='private-intent.v1'").fetchone()[0]
            old_rid,old=rid,item
            class Edit:
                descriptor='synthetic-private-lifecycle-only'
                def propose(self,request):
                    value=json.loads(AnalyticalFixturePort().propose(request));value['proposed_operations']=['DRAFT']
                    value[kind]={'topic':old.topic,field:old.content_summary,'revises_record_id':old_rid,
                        **({'activity_state':state} if 'activity_state' in PrivateThoughtEdit.model_fields else {})}
                    return json.dumps(value)
            clock.advance(SECOND)
            result=r.subject.cognize(SubjectInput(source_key='synthetic.lifecycle.'+str(index),kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
                privacy_class='PROJECT',topic=old.topic,observed_at_us=clock.utc_now_us()),model=Edit(),authority=r.authority,policy=app.policy)
            rid,item=next((rr,v) for rr,v in candidates(r.store,'project-work',('PROJECT',)) if v.intent_id==initial.intent_id)
            assert item.activity_state==state and item.category==category
            assert item.intent_id==initial.intent_id and item.created_at_us==initial.created_at_us and item.content_summary==initial.content_summary
            assert result.intention.behavior=='REFLECT' and not result.goal_candidate_id
            if index==1:
                assert rid==old_rid and item.revision==old.revision
                assert r.store.db.execute("SELECT count(*) FROM continuity_records WHERE target_id='private-intent.v1'").fetchone()[0]==before_count
            assert next((rr,v) for rr,v in candidates(r.store,'project-work',('PROJECT',)) if v.intent_id==other.intent_id)==(other_rid,other)
            clock.advance(2*SECOND)
            opportunities=r.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=0,quiet_window_us=SECOND)
            assert any(v.private_thought_ref and v.private_thought_ref.record_id==rid for v in opportunities)==(state=='ACTIVE')
        assert not r.store.all('goals') and not r.store.all('actions') and not r.store.all('grants')


def test_lifecycle_omission_preserves_legacy_wire_and_invalid_edits_hide_private_input():
    from nana_core.continuity.autonomy.private_intent import PrivateTendencyProposal
    private='PRIVATE_INVALID_LIFECYCLE_CANARY'
    proposal=PrivateTendencyProposal(topic='own-test',tendency=private)
    assert 'activity_state' not in proposal.model_dump() and 'activity_state' not in proposal.model_dump_json()
    for value in ({'activity_state':'PAUSED'},{'activity_state':'INVENTED','revises_record_id':'known-private-record'}):
        with pytest.raises(ValueError) as error:
            PrivateTendencyProposal(topic='own-test',tendency=private,**value)
        assert private not in str(error.value)


def test_lifecycle_choice_cannot_edit_an_unselected_private_record(tmp_path):
    from nana_core.contracts import CoreError
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app,topic='only-this-topic')
        rid,idea=candidates(app.runtime.store,'project-work',('PROJECT',))[0]
        class Outside:
            descriptor='synthetic-lifecycle-unselected-reference'
            def propose(self,request):
                value=json.loads(AnalyticalFixturePort().propose(request));value['proposed_operations']=['DRAFT']
                value['private_tendency']={'topic':idea.topic,'tendency':idea.content_summary,'revises_record_id':rid,
                    **({'activity_state':'PAUSED'} if 'activity_state' in PrivateThoughtEdit.model_fields else {})}
                return json.dumps(value)
        r=app.runtime
        with pytest.raises(CoreError,match='UNSUPPORTED_PRIVATE_TENDENCY_REVISION'):
            r.subject.cognize(SubjectInput(source_key='synthetic.lifecycle.unselected',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
                privacy_class='PROJECT',topic='unrelated-context',observed_at_us=clock.utc_now_us()),model=Outside(),authority=r.authority,policy=app.policy)
        assert next((rr,v) for rr,v in candidates(r.store,'project-work',('PROJECT',)) if v.intent_id==idea.intent_id)==(rid,idea)
        assert not r.store.all('goals') and not r.store.all('actions') and not r.store.all('grants')


def test_editing_paused_contents_does_not_silently_reactivate_background_attention(tmp_path):
    from .test_private_tendency import change
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app)
        change(app,'REST','pause-before-edit')
        rid,idea=candidates(app.runtime.store,'project-work',('PROJECT',))[0]
        assert idea.activity_state=='PAUSED'
        form(app,'edit-while-paused','SYNTHETIC the same private interest, now expressed more clearly.',revision=rid)
        revised_rid,revised=next((rr,v) for rr,v in candidates(app.runtime.store,'project-work',('PROJECT',)) if v.intent_id==idea.intent_id)
        clock.advance(2*SECOND);r=app.runtime
        offered=r.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=0,quiet_window_us=SECOND)
        offered_target=any(v.private_thought_ref and v.private_thought_ref.record_id==revised_rid for v in offered)
        print(json.dumps({'measurement':'synthetic_paused_edit_attention','state':revised.activity_state,'offered_target':offered_target,'model_calls':0},sort_keys=True))
        assert revised.activity_state=='PAUSED' and not offered_target
        assert revised.intent_id==idea.intent_id and revised.created_at_us==idea.created_at_us and revised.revision==idea.revision+1
        assert not r.store.all('goals') and not r.store.all('actions') and not r.store.all('grants')
