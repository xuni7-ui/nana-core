"""Own retained tendencies use original private activity, C, context and delivery."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.cognition import AnalyticalFixturePort,CognitiveProposal
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue,PrivateIntentRef
from nana_core.continuity.autonomy.private_intent import candidates,internal_projection,eligible_content
from nana_core.continuity.project_work.service import capture
from tests.independent_life.test_dialogue import relay
from .conftest import initialize

PRIVATE='PRIVATE_TENDENCY_CANARY: I feel a tentative concern and wish to listen gently, without claiming to know the other person\'s mood.'


def form(app,key='concern',text=PRIVATE,*,topic='own-concern',revision=None,kind='private_tendency',related=()):
    class Own:
        descriptor='synthetic-own-retained-tendency'
        def propose(self,request):
            value=json.loads(AnalyticalFixturePort().propose(request))
            if kind in CognitiveProposal.model_fields:
                field={'private_tendency':'tendency','private_question':'question','private_plan':'plan'}[kind]
                value[kind]={'topic':topic,field:text,'related_private_record_ids':related}
                if revision:value[kind]['revises_record_id']=revision
            return json.dumps(value)
    r=app.runtime
    return r.subject.cognize(SubjectInput(source_key='synthetic.private-tendency.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',topic=topic,observed_at_us=r.clock.utc_now_us()),model=Own(),authority=r.authority,policy=app.policy)


def current(app,category='PRIVATE_TENDENCY'):
    return [(rid,item) for rid,item in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')) if item.category==category]


def change(app,behavior,key):
    rid,item=current(app)[0];r=app.runtime
    cue=ConcernCue(cue_kind='OPPORTUNITY',topic_key=item.topic,motivation_source='CREATIVE_INTEREST',possible_behaviors=(behavior,),private_intent_ref=PrivateIntentRef(record_id=rid,intent_id=item.intent_id,revision=item.revision))
    mid=capture(r,key,cue.model_dump(mode='json'),predicate='concern.tendency.'+key)
    return r.subject.run(SubjectInput(source_key='synthetic.tendency-choice.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',source_memory_ids=(mid,),observed_at_us=r.clock.utc_now_us()))


def meaning(request):
    own=[json.loads(b['data_json']) for b in json.loads(request['context_json'])['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY']
    return {'communication_proposal':{'approach':'LISTEN' if own else 'CHAT','detail':'BRIEF','follow_up':'NONE','basis_private_record_ids':[v['record_id'] for v in own]}}


def render(request):
    choice=request['role_input']['dialogue']['communication_purpose'].get('choice')
    return 'SYNTHETIC: stay with the topic without pressing for details.' if choice and choice['approach']=='LISTEN' else 'SYNTHETIC: ordinary brief chat.'


def test_own_tendency_changes_next_original_dialogue_choice_before_render_without_public_inner_text(tmp_path,monkeypatch):
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=65536) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();formed=form(app);identity=app.runtime.identity_id
        with monkeypatch.context() as off:
            off.setattr(app.runtime.subject,'dialogue_private_refs',lambda **kw:())
            baseline=app.chat('SYNTHETIC ordinary followup',topic='own-concern',privacy='PROJECT',message_id='off')
        later=app.chat('SYNTHETIC ordinary followup',topic='own-concern',privacy='PROJECT',message_id='on')
        assert baseline['text']=='SYNTHETIC: ordinary brief chat.'
        assert later['text']=='SYNTHETIC: stay with the topic without pressing for details.'
        rid,item=current(app)[0]
        assert formed.intention.kind=='REFLECTION' and item.epistemic_status=='OWN_TENDENCY_NOT_WORLD_FACT'
        assert item.activity_state=='ACTIVE' and item.disclosure_policy=='PRIVATE_FOR_NOW'
        assert app.runtime.store.one('subject_intentions',formed.intention_id)['state']=='COMPLETED'
        assert PRIVATE in requests[-2]['context_json'] and PRIVATE not in requests[-1]['context_json'] and PRIVATE not in later['text']
        assert requests[-1]['role_input']['dialogue']['communication_purpose']['choice']=={'approach':'LISTEN','detail':'BRIEF','follow_up':'NONE'}
        assert app.runtime.identity_id==identity and len(requests)==4
        assert not app.runtime.store.all('goals') and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        assert PRIVATE not in formed.deliberation.raw_proposal_json
        assert not app.runtime.store.db.execute("SELECT 1 FROM events WHERE instr(data_json,?)>0",(PRIVATE,)).fetchone()
        with pytest.raises(CoreError,match='WITHHELD'):eligible_content(app.runtime.store,item.intent_id,scope='project-work',privacy_classes=('PROJECT',))


def test_tendency_restarts_revises_and_withdraws_without_turning_into_a_plan_or_world_fact(tmp_path):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app);rid,item=current(app)[0];identity=app.runtime.identity_id;root=item.source_memory_ids[0]
        assert app.runtime.store.one('memories',root)['source_evidence_id']
    with LifeApplication(home,clock=clock) as app:
        app.pause();assert app.runtime.identity_id==identity and current(app)[0][1].content_summary==PRIVATE
        form(app,'reconsider','SYNTHETIC I still care, but prefer giving space now.',revision=rid)
        revised,value=current(app)[0]
        assert revised!=rid and value.revision==item.revision+1 and 'giving space' in value.content_summary
        assert value.intent_id==item.intent_id and value.contract=='PRIVATE_TENDENCY_V4'
        assert not app.runtime.store.all('goals') and not app.runtime.store.all('world_beliefs')
        app.forget(root)
        assert not current(app) and internal_projection(app.runtime.store,(revised,),scope='project-work',privacy_classes=('PROJECT',))==()


@pytest.mark.parametrize('behavior,state',[('REST','PAUSED'),('WITHDRAW','ABANDONED')])
def test_original_c_can_pause_or_end_a_tendency_without_overwriting_its_contents(tmp_path,behavior,state):
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();form(app);rid,item=current(app)[0]
        cycle=change(app,behavior,'choose-'+behavior.lower())
        assert cycle.intention.behavior==behavior
        now,value=current(app)[0] if state!='ABANDONED' else next((r,v) for r,v in candidates(app.runtime.store,'project-work',('PROJECT',)) if v.category=='PRIVATE_TENDENCY')
        assert now!=rid and value.contract=='PRIVATE_TENDENCY_V4' and value.activity_state==state and value.content_summary==PRIVATE
        if state=='PAUSED':
            change(app,'CREATE','reawaken');assert current(app)[0][1].activity_state=='ACTIVE' and current(app)[0][1].content_summary==PRIVATE
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_question_plan_and_tendency_coexist_and_links_are_tentative_not_fact_causation(tmp_path):
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();form(app,'question','SYNTHETIC Could color change a composition?',topic='own-color',kind='private_question')
        form(app,'plan','SYNTHETIC A private sketch I might make.',topic='own-sketch',kind='private_plan')
        question=next(r for r,v in candidates(app.runtime.store,'project-work',('PROJECT',)) if v.category=='PRIVATE_QUESTION')
        # The existing association projection must actually select the source,
        # rather than accepting a model-named arbitrary private record.
        form(app,'curiosity','SYNTHETIC I feel drawn to this unresolved color question.',topic='own-color',related=(question,))
        assert {v.category for _,v in candidates(app.runtime.store,'project-work',('PROJECT',))}=={'PRIVATE_QUESTION','PRIVATE_PLAN','PRIVATE_TENDENCY'}
        rid,value=current(app)[0];projection=internal_projection(app.runtime.store,(rid,),scope='project-work',privacy_classes=('PROJECT',))
        assert projection[0]['related_private_record_ids']==(question,)
        assert projection[0]['association_semantics']=='OWN_ASSOCIATION_NOT_WORLD_CAUSATION_OR_PRIORITY'
        assert not app.runtime.store.all('goals') and not app.runtime.store.all('actions')


@pytest.mark.parametrize('state',['ACTIVE','PAUSED','ABANDONED'])
def test_tendency_uses_normal_background_provider_to_form_a_new_question_once_without_new_user_input(tmp_path,state):
    from nana_core.life.config import load_config,update_config
    from nana_core.presence.contracts import SECOND
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app);identity=app.runtime.identity_id
        if state!='ACTIVE':change(app,'REST' if state=='PAUSED' else 'WITHDRAW','before-background-'+state.lower())
    config=load_config(home)
    update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_background_cognition':True,'provider_context_tokens':32768}),expected_revision=config.revision)
    def inner(request):
        context=json.loads(request['context_json']);manifest=context['manifest']
        own=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['category']=='PRIVATE_TENDENCY']
        return {'interpretation':'SYNTHETIC current tendency reconsideration','subject_cognition':{'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],'interpretation':'SYNTHETIC an own question, not a claim of the other person\'s mood','proposed_operations':['DRAFT'] if own else ['WAIT'],**({'private_question':{'topic':'own-concern','question':'SYNTHETIC Could giving space be more suitable than asking another question?'}} if own else {})}}
    with relay(home,subject_builder=inner,context_limit=65536) as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
        assert app.runtime.identity_id==identity and not requests
        app.pause(False);clock.advance(2*SECOND);app.runtime.refresh_attention()
        for _ in range(5):app.tick()
        if state!='ACTIVE':
            assert not requests and not app.runtime.store.all('cognitive_requests')
            return
        assert len(requests)==1 and requests[0]['cognitive_role']=='SELF'
        assert current(app) and any(v.category=='PRIVATE_QUESTION' and 'giving space' in v.content_summary for _,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')))
        assert len(app.runtime.store.all('cognitive_requests'))==1 and not app.runtime.store.all('runtime_cognition_calls')
        for _ in range(8):app.tick()
        assert len(requests)==1 and not app.runtime.store.all('goals') and not app.runtime.store.all('actions')


def test_boundary_and_unrelated_topic_do_not_disclose_or_erase_a_private_tendency(tmp_path):
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT',meaning_builder=meaning,renderer=render,context_limit=65536) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();form(app)
        other=app.chat('SYNTHETIC separate topic',topic='unrelated',privacy='PROJECT',message_id='unrelated')
        assert other['text']=='SYNTHETIC: ordinary brief chat.' and PRIVATE not in requests[0]['context_json']
        before=len(requests)
        stopped=app.chat('先别分析这个话题',topic='own-concern',privacy='PROJECT',message_id='explicit-boundary')
        assert len(requests)==before and stopped['text'] and current(app)[0][1].content_summary==PRIVATE
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_nonretention_and_role_schema_do_not_turn_every_thought_into_a_retained_tendency(tmp_path):
    from nana_core.continuity.world_loop.cognition import proposal_schema
    home=tmp_path/'home';initialize(home);calls=[]
    class NoRetention:
        descriptor='synthetic-nonretention-tendency'
        def propose(self,request):calls.append(request);return AnalyticalFixturePort().propose(request)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime
        r.subject.cognize(SubjectInput(source_key='synthetic.nonretained-tendency',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),retention='DO_NOT_REMEMBER'),model=NoRetention(),authority=r.authority,policy=app.policy)
        assert not current(app) and not calls and not r.store.all('actions')
    ordinary=proposal_schema();own=proposal_schema(internal=True)
    assert 'PrivateTendencyProposal' not in ordinary.get('$defs',{})
    assert 'PrivateTendencyProposal' in own['$defs']
    value=CognitiveProposal(identity_id='synthetic',identity_revision=1,interpretation='SYNTHETIC',proposed_operations=('WAIT',))
    assert 'private_tendency' not in value.model_dump(mode='json')
    with pytest.raises(ValueError):CognitiveProposal(**value.model_dump(),private_tendency={'topic':'own-test','tendency':'SYNTHETIC'},private_plan={'topic':'own-test','plan':'SYNTHETIC'})


def test_disjoint_legacy_and_tendency_indexes_preserve_old_predicate_and_wrong_binding_falls_back_read_only(tmp_path):
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();form(app,'question','SYNTHETIC An unresolved related question.',topic='own-concern',kind='private_question');form(app)
        store=app.runtime.store
        sql=dict(store.db.execute("SELECT name,sql FROM sqlite_master WHERE type='index' AND name LIKE 'private_intent_%'"))
        assert 'PRIVATE_TENDENCY_V4' not in sql['private_intent_topic_lookup_v1']
        assert 'PRIVATE_TENDENCY_V4' in sql['private_intent_tendency_topic_v4']
        args=dict(topic='own-concern',owner_identity_id=app.runtime.identity_id)
        expected={v.category for _,v in candidates(store,'project-work',('PROJECT',),**args)}
        assert expected=={'PRIVATE_QUESTION','PRIVATE_TENDENCY'}
        store.db.execute('DROP INDEX private_intent_topic_lookup_v1')
        store.db.execute('CREATE INDEX private_intent_topic_lookup_v1 ON artifacts(artifact_id) WHERE 0')
        snapshot=store.snapshot();writes=store.db.total_changes
        assert {v.category for _,v in candidates(store,'project-work',('PROJECT',),**args)}==expected
        assert store.snapshot()==snapshot and store.db.total_changes==writes


def test_tendency_revision_cannot_retype_a_plan_and_private_validation_does_not_echo_content(tmp_path):
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();form(app,'plan','SYNTHETIC independently retained private plan.',topic='own-concern',kind='private_plan')
        rid,item=next((r,v) for r,v in candidates(app.runtime.store,'project-work',('PROJECT',)) if v.category=='PRIVATE_PLAN')
        with pytest.raises(CoreError,match='UNSUPPORTED_PRIVATE_TENDENCY_REVISION'):form(app,'bad-retyping',revision=rid)
        assert not current(app) and any(v.category=='PRIVATE_PLAN' and v.content_summary==item.content_summary for _,v in candidates(app.runtime.store,'project-work',('PROJECT',)))
        form(app,'own-valid');tendency_id,value=current(app)[0]
        assert internal_projection(app.runtime.store,(tendency_id,),scope='other',privacy_classes=('PROJECT',))==()
        assert internal_projection(app.runtime.store,(tendency_id,),scope='project-work',privacy_classes=('PUBLIC',))==()
        invalid={'identity_id':app.runtime.identity_id,'identity_revision':1,'interpretation':'SYNTHETIC','proposed_operations':['DRAFT'],'private_tendency':{'topic':'own-test','tendency':PRIVATE,'execution_authority':True}}
        with pytest.raises(ValueError) as error:CognitiveProposal.model_validate_json(json.dumps(invalid))
        assert PRIVATE not in str(error.value) and not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
