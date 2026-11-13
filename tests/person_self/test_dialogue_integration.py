import json
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_dialogue import relay
from .conftest import initialize


def test_commercial_chat_c_selects_private_interest_for_current_topic_without_disclosure_or_extra_calls(tmp_path):
    from tests.first_life_integration.test_private_intent import choose
    from nana_core.continuity.autonomy.private_intent import candidates
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with relay(home,'CHAT') as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();identity=app.runtime.identity_id
            root,_,formed=choose(app,topic='own-composition')
            rid,idea=candidates(app.runtime.store,'project-work',('PROJECT',))[0]
            app.runtime.subject.transition_intention(formed.intention_id,expected_revision=1,state='COMPLETED')
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();assert app.runtime.identity_id==identity
            for key,topic,privacy,relevant in [
                ('unrelated','another-topic','PROJECT',False),
                ('matching','own-composition','PROJECT',True),
                ('public','own-composition','PUBLIC',False),
                ('withdrawn','own-composition','PROJECT',False),
            ]:
                if key=='withdrawn':app.forget(root)
                result=app.chat('SYNTHETIC current-topic chat',topic=topic,privacy=privacy,message_id=key)
                assert result['render_state']=='UNVERIFIED_MODEL_WORDING',result
                cycle=app.runtime.subject.result(app.runtime.store.one('subject_cycles',result['cycle_id']))
                selected=tuple(ref for motive in cycle.motivations if motive.source=='PRIVATE_INTEREST' for ref in motive.source_ids)
                assert (rid in selected)==relevant
                assert cycle.appraisal.interest_relevance==('HIGH' if relevant else 'LOW')
            assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        assert len(requests)==8  # Existing INTERPRET/RENDER only; no inner model loop.
        # Only the matching, sufficiently private INTERPRET request may consider
        # this own state. Public/other topics/withdrawn sources and every RENDER
        # keep the original non-disclosure guarantee.
        assert all(idea.content_summary not in request['context_json']
            for index,request in enumerate(requests) if index!=2)
        assert requests[2]['cognitive_role']=='INTERPRET'


def test_original_transport_c_role_adoption_both_sides_and_restart(tmp_path):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    p={'kind':'RELATIONSHIP_ROLE','operation':'PROPOSE','value':'sibling','quote':'sibling'}
    with relay(home,'CHAT',conversation_proposal=p) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();identity=app.runtime.identity_id
            a=app.chat('Please use sibling as our relationship label',privacy='PROJECT',retain_shared_life=True,message_id='adopt')
            assert a['render_state']=='UNVERIFIED_MODEL_WORDING',a
            assert a['conversation_decision']['choice']=='ADOPT'
            assert a['raw_body_persisted'] and a['exchange_record_id']
            assert requests[-1]['role_input']['dialogue']['conversation_decision']['choice']=='ADOPT'
        with LifeApplication(home,clock=clock,router=router) as app:
            # A different surface/topic may retrieve the enduring relationship;
            # it is not dependent on remembering the last six user messages.
            p.clear()
            result=app.chat('What role do we use?',topic='later',privacy='PROJECT',retain_shared_life=True,message_id='recall')
            assert result['render_state']=='UNVERIFIED_MODEL_WORDING',result
            context=json.loads(requests[-1]['context_json'])
            person=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='PERSON_SELF')
            assert person['adopted_conventions'][0]['value']=='sibling'
            assert app.runtime.identity_id==identity
            assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')


def test_default_transient_history_has_assistant_side_but_not_store(tmp_path):
    home=tmp_path/'home';initialize(home)
    with relay(home,'CHAT') as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();app.chat('PROJECT_TRANSIENT_CANARY',privacy='PROJECT',message_id='first')
        result=app.chat('Please continue',privacy='PROJECT',message_id='second')
        assert result['render_state']=='UNVERIFIED_MODEL_WORDING',result
        turns=requests[-1]['role_input']['dialogue']['recent_turns']
        assert any(t['speaker']=='ASSISTANT' for t in turns)
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'PROJECT_TRANSIENT_CANARY')>0 OR instr(CAST(payload AS TEXT),'A deliberately synthetic language response')>0").fetchone()


def test_withdrawal_removes_retained_exchange_from_restart_context(tmp_path):
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with relay(home,'CHAT') as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();first=app.chat('RETAINED_CANARY',privacy='PROJECT',retain_shared_life=True)
            assert first['exchange_record_id']
            app.forget(first['message_memory_id'])
        with LifeApplication(home,clock=clock,router=router) as app:
            later=app.chat('Continue',privacy='PROJECT')
            assert later['render_state']=='UNVERIFIED_MODEL_WORDING',later
            assert 'RETAINED_CANARY' not in requests[-1]['context_json']


def test_unknown_retained_turn_is_not_replayed_but_new_turn_can_continue(tmp_path,monkeypatch):
    from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
    home=tmp_path/'home';initialize(home);calls=[];clock=VirtualClock()
    def timeout(self,request):calls.append(request.request_id);raise TimeoutError()
    monkeypatch.setattr(OpenAIJSONTransport,'exchange',timeout)
    with relay(home,'CHAT') as (router,_):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();app.chat('first',message_id='first',privacy='PROJECT',retain_shared_life=True)
            original=dict(app.runtime.store.all('cognitive_requests')[0])
            assert original['state']=='UNKNOWN' and len(calls)==1
        with LifeApplication(home,clock=clock,router=router) as app:
            app.chat('first',message_id='first',privacy='PROJECT',retain_shared_life=True)
            assert len(calls)==1
            app.chat('different',message_id='different',privacy='PROJECT',retain_shared_life=True)
            assert len(calls)==2 and len(set(calls))==2
            # New independent dialogue does not refund or rewrite the old UNKNOWN.
            assert dict(app.runtime.store.one('cognitive_requests',original['request_id']))==original


def test_learned_policy_changes_later_unrelated_render_after_restart(tmp_path):
    from .test_learning import record,activate
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    def render(request):
        context=json.loads(request['context_json'])
        active=any(b['kind']=='LIVED_LANGUAGE' and json.loads(b['data_json'])['policy']['state']=='ACTIVE_BOUNDED_HYPOTHESIS' for b in context['blocks'])
        return 'SYNTHETIC: concise contextual wording' if active else 'SYNTHETIC: First, I will summarize your requirements and propose a trial period.'
    with relay(home,'CHAT',renderer=render) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();before=app.chat('casual synthetic case',privacy='PROJECT')
            assert before['render_state']=='UNVERIFIED_MODEL_WORDING',before
            record(app,1);_,eid=record(app,2);activate(app,eid)
        with LifeApplication(home,clock=clock,router=router) as app:
            after=app.chat('unrelated later case',topic='another',privacy='PROJECT')
            assert after['render_state']=='UNVERIFIED_MODEL_WORDING',after
            assert 'concise contextual' in after['text']
            assert before['text']!=after['text']
            assert len(requests)==4  # loopback only, never a real provider


def test_feedback_on_later_learned_reply_binds_current_report_and_erases_copied_wording(tmp_path,monkeypatch):
    from .test_learning import record,activate
    from nana_core.continuity.lived_language import LanguageSample,LanguageService
    from nana_core.continuity.records import RecordService
    from nana_core.life.control import dispatch
    from nana_core.contracts import CoreError
    import pytest
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with relay(home,'CHAT') as (router,_),LifeApplication(home,clock=clock,router=router) as app:
        app.pause();record(app,1);_,eid=record(app,2);activate(app,eid)
        turn=app.chat('FEEDBACK_SOURCE_CANARY',privacy='PROJECT',retain_shared_life=True)
        assert turn['render_state']=='UNVERIFIED_MODEL_WORDING',turn
        sample=LanguageSample(sample_id='later-human',review_target=turn['exchange_record_id'],mode='CASUAL',context='FEEDBACK_SOURCE_CANARY',candidate_response=turn['text'],human_judgment='REJECTED',reason_tags=('TOO_TERSE',),provenance='USER_PROVIDED_REVIEW',observed_at_us=clock.utc_now_us())
        response=dispatch(app,{'operation':'language-feedback','exchange_record_id':turn['exchange_record_id'],'sample':sample.model_dump(mode='json')})
        experience=app.runtime.store.one('experiences',response['experience_id'])
        result=RecordService(app.runtime.store).memory.read(experience['result_memory_id'])
        assert result['source_provenance']['source_reference']=='later-human'
        from nana_core.continuity.memory import MemoryService
        original=MemoryService.add
        def interrupted(memory,candidate):
            if memory.evidence(candidate.source_evidence_id)['source_reference']=='interrupted-review':raise CoreError('INJECTED_BEFORE_SAMPLE_LINK')
            return original(memory,candidate)
        monkeypatch.setattr(MemoryService,'add',interrupted)
        service=LanguageService(app.runtime.store,app.runtime.authority)
        with pytest.raises(CoreError,match='INJECTED_BEFORE_SAMPLE_LINK'):
            service.record(sample.model_copy(update={'sample_id':'interrupted-review'}),scope='project-work',entity_id='project-user',privacy='PUBLIC',authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
        orphan=app.runtime.store.db.execute("SELECT * FROM continuity_evidence WHERE source_namespace='recorded.conversation.feedback' AND source_reference='interrupted-review'").fetchone()
        assert orphan['privacy_class']=='PROJECT'
        assert b'FEEDBACK_SOURCE_CANARY' not in app.runtime.store.artifact(orphan['payload_artifact_id'])
        app.forget(turn['message_memory_id'])
        with pytest.raises(CoreError):RecordService(app.runtime.store).memory.read(experience['result_memory_id'])
        assert not app.runtime.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'FEEDBACK_SOURCE_CANARY')>0").fetchone()


def test_distinct_bound_reviews_survive_synthetic_counter_and_change_later_context(tmp_path):
    """Synthetic local feedback types; no human/naturalness qualification."""
    from .test_learning import record,activate
    from nana_core.continuity.lived_language import LanguageSample,LanguageService
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    def render(request):
        context=json.loads(request['context_json'])
        active=any(b['kind']=='LIVED_LANGUAGE' and json.loads(b['data_json'])['policy']['state']=='ACTIVE_BOUNDED_HYPOTHESIS' for b in context['blocks'])
        return 'SYNTHETIC later concise' if active else 'SYNTHETIC earlier procedural'
    with relay(home,'CHAT',renderer=render) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();service=LanguageService(app.runtime.store,app.runtime.authority)
            for i in range(2):
                turn=app.chat('SYNTHETIC human-like input '+str(i),privacy='PROJECT',retain_shared_life=True,message_id='review-turn-'+str(i))
                sample=LanguageSample(sample_id='bound-review-'+str(i),review_target=turn['exchange_record_id'],
                    mode='CASUAL',context='SYNTHETIC human-like input '+str(i),candidate_response=turn['text'],
                    human_judgment='REJECTED',reason_tags=('TOO_VERBOSE',),provenance='USER_PROVIDED_REVIEW',observed_at_us=clock.utc_now_us())
                rid=service.record(sample,scope='project-work',entity_id='project-user',privacy='PROJECT',
                    authority=app.runtime.authority,exchange_record_id=turn['exchange_record_id'])
                eid=service.experience(rid,app.runtime.authority)
            record(app,9,tags=('TOO_TERSE',),provenance='PROJECT_SYNTHETIC')
            lesson=activate(app,eid)
            identity=app.runtime.identity_id
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause()
            after=app.chat('SYNTHETIC distinct later turn',privacy='PROJECT',message_id='review-later')
            assert app.runtime.identity_id==identity and after['text']=='SYNTHETIC later concise'
            context=json.loads(requests[-1]['context_json'])
            assert any(b['kind']=='LIVED_LANGUAGE' and json.loads(b['data_json'])['policy'].get('lesson_id')==lesson for b in context['blocks'])
