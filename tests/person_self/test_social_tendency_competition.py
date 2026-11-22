"""Longer quiet tendencies need not veto a present source-backed own wish."""
import json
import pytest
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput,PreferenceSignal
from nana_core.continuity.subject.opportunities import ConcernCue,ShareAssessment,OpportunityAssessment
from nana_core.continuity.relational.projections import social_appetite
from nana_core.continuity.project_work.service import capture
from .test_private_tendency import form,current


@pytest.mark.parametrize('hidden_constraint',[False,True])
def test_hidden_cues_do_not_consume_allowed_subject_attention(app,hidden_constraint):
    from nana_core.continuity.contracts import EvidenceInput,MemoryCandidate,MemoryType,Provenance
    from nana_core.continuity.memory import MemoryService
    from nana_core.presence.contracts import SECOND

    r=app.runtime
    visible=ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key='visible-cue')
    visible_mid=capture(r,'visible-cue',visible.model_dump(mode='json'),predicate='concern.visible-cue')
    assert social_appetite(r.store,scope='project-work',privacy_classes=('PROJECT',)).state=='OPEN'
    assert 'SECRET' not in r.subject.privacy_classes
    memory=MemoryService(r.store)
    r.clock.source.advance(SECOND)
    now=r.clock.utc_now_us()
    hidden=ConcernCue(cue_kind='CONSTRAINT' if hidden_constraint else 'DISCOVERY',
        motivation_source='RELATIONSHIP',topic_key='unavailable-cue',prohibited_behaviors=('SOCIALIZE',))
    for index in range(65):
        text=hidden.model_copy(update={'topic_key':f'private-cue-{index}'}).model_dump_json()
        evidence=memory.capture(EvidenceInput(
            provenance=Provenance(source_namespace='synthetic.private-attention',source_reference=str(index),
                source_kind='DIRECT_OBSERVATION'),text=text,privacy_class='SECRET',observed_time_us=now))
        memory.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.EPISODIC,
            epistemic_kind='OBSERVATION',source_evidence_id=evidence,text=text,
            predicate_key=f'concern.{"constraint." if hidden_constraint else ""}private-cue-{index}'))
    result=r.subject.run(SubjectInput(source_key='synthetic.visible-social-consideration',kind='INTERACTION',origin='USER',
        entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=now,
        text='SYNTHETIC consider whether to continue the current ordinary conversation.'))
    view=social_appetite(r.store,scope='project-work',privacy_classes=('PROJECT',))
    assert view.state=='OPEN' and view.source_memory_ids==(visible_mid,)
    connection=next(m for m in result.motivations if m.source=='SOCIAL_CONNECTION')
    assert visible_mid in connection.source_ids
    assert not r.store.all('actions') and not r.store.all('grants')


@pytest.mark.parametrize('tendency,state',[('social_recovery_needed','RECOVERING'),('social_quiet_preference','QUIET')])
@pytest.mark.parametrize('choice,guard,expected',[('SOCIALIZE','none','SOCIALIZE'),('REST','none','REST'),(None,'none','IGNORE'),('SOCIALIZE','declined','STAY_SILENT'),('SOCIALIZE','norm','REST'),('SOCIALIZE','withdrawn','SOCIALIZE'),('EXPLORE','research','EXPLORE'),('SOCIALIZE','repeated-delivery','STAY_SILENT')])
def test_current_c_can_compare_a_private_connection_wish_with_its_quiet_tendency(app,tendency,state,choice,guard,expected):
    r=app.runtime;seen=[];topic='own-connection'
    for i in range(2):
        r.subject.run(SubjectInput(source_key='synthetic.quiet-tendency.'+str(i),kind='PLAY',origin='ENVIRONMENT',
            entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
            text='SYNTHETIC independent observed preference for a quieter interval '+str(i),
            preference_signal=PreferenceSignal(topic=tendency,direction='SUPPORT',interpretation='SYNTHETIC a sourced quieter tendency, not permanent incapacity')))
    before=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))
    assert before.state==state and before.source_record_ids
    form(app,'connection','SYNTHETIC I currently wish to share a small ordinary moment while still valuing quiet.',topic=topic)
    thought=current(app)[0][1]
    cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key=topic,resource_class='ORDINARY',
        possible_behaviors=('EXPLORE','REST') if guard=='research' else ('SOCIALIZE','REST'),availability='BUSY',
        opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'),share_assessment=ShareAssessment(user_preference='DECLINED' if guard=='declined' else 'ALLOW',novelty='REPEATED' if guard=='repeated-delivery' else 'NEW',recent_delivery_frequency='HIGH' if guard=='repeated-delivery' else 'LOW'))
    mid=capture(r,'quiet-and-connection',cue.model_dump(mode='json'),predicate='concern.quiet-and-connection')
    if guard=='norm':
        norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key=topic,prohibited_behaviors=('SOCIALIZE',))
        capture(r,'quiet-social-norm',norm.model_dump(mode='json'),predicate='concern.constraint.quiet-social')
    if guard=='withdrawn':app.forget(thought.source_memory_ids[0])
    # Existing support can be shared: erasing a root may retire both the thought
    # and its old quiet tendency. C must not resurrect either from stale state.
    retained=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))
    if guard=='withdrawn':assert retained.state not in {'RECOVERING','QUIET','SATURATED'}
    class Choosing:
        descriptor='synthetic-own-current-choice-among-conflicting-tendencies'
        def propose(self,request):
            seen.append(request)
            value=json.loads(AnalyticalFixturePort().propose(request));value.update(preferred_behavior=choice,proposed_operations=['DRAFT'])
            return json.dumps(value)
    event=SubjectInput(source_key='synthetic.private-connection-current-choice',kind='WAKE',origin='SELF_WAKE',
        entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
    result=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy)
    assert len(seen)==1 and result.intention.behavior==expected
    assert any(m.source=='PRIVATE_INTEREST' for m in result.motivations)==(guard!='withdrawn')
    frame=next(json.loads(b['data_json']) for b in json.loads(seen[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
    quiet=[m for m in frame['motivations'] if m['source']=='SOCIAL_QUIET']
    quiet_expected=guard!='research' and retained.state in {'RECOVERING','QUIET','SATURATED'} and bool(retained.source_record_ids)
    assert len(quiet)==int(quiet_expected)
    if quiet:assert quiet[0]['source_ids'] and quiet[0]['strength']=='RELEVANT'
    assert any(m.source=='SOCIAL_QUIET' for m in result.motivations)==quiet_expected
    assert social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',)).state==retained.state
    if guard!='withdrawn':assert retained.state==state
    assert (not current(app)) if guard=='withdrawn' else current(app)[0][1]==thought
    if guard=='withdrawn':
        # Old content stays withdrawn. A newly considered wish can arise from
        # this independent, still-current cue without resurrecting that content.
        assert thought.content_summary not in seen[0].context_json
        assert thought.source_memory_ids[0] not in frame['source_memory_ids']
        assert mid in frame['source_memory_ids']
        assert r.store.one('memories',thought.source_memory_ids[0])['lifecycle']=='DELETED'
    assert not r.store.all('actions') and not r.store.all('grants')


def test_structured_self_retains_old_quiet_and_current_wish_after_49h_restart_without_sending(tmp_path):
    from .conftest import initialize
    from nana_core.life.application import LifeApplication
    from nana_core.presence.authority import VirtualClock
    from nana_core.presence.contracts import SECOND
    from nana_core.continuity.cognition import CognitiveProposal
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    with LifeApplication(home,clock=clock) as original:
        original.pause();r=original.runtime;identity=r.identity_id
        for i in range(2):
            r.subject.run(SubjectInput(source_key='synthetic.old-quiet.'+str(i),kind='PLAY',origin='ENVIRONMENT',
                entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
                text='SYNTHETIC independent earlier recovery preference '+str(i),preference_signal=PreferenceSignal(
                    topic='social_recovery_needed',direction='SUPPORT',interpretation='SYNTHETIC a quieter tendency')))
        old=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',));assert old.state=='RECOVERING'
    clock.advance(49*3600*SECOND)
    def choose(request):
        context=json.loads(request.context_json);manifest=context['manifest']
        frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        seen.append((request,frame))
        return StructuredProposal(interpretation='SYNTHETIC consider two sourced directions without sending',
            subject_cognition=CognitiveProposal(identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],
                interpretation='SYNTHETIC quiet still matters, and I currently choose to consider ordinary contact',
                preferred_behavior='SOCIALIZE',proposed_operations=('DRAFT',)))
    with provider_harness(proposer=choose) as (transport,state),LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime;assert r.identity_id==identity
        assert social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',)).state=='RECOVERING'
        form(app,'fresh-connection','SYNTHETIC a current own connection wish, alongside earlier quiet.',topic='current-connection')
        own=current(app)[0][1]
        cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key='current-connection',resource_class='ORDINARY',
            possible_behaviors=('SOCIALIZE','REST'),availability='BUSY',opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'))
        mid=capture(r,'fresh-connection-opportunity',cue.model_dump(mode='json'),predicate='concern.fresh-connection')
        event=SubjectInput(source_key='synthetic.structured-current-social-choice',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
            scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        port=CognitionSession(r,transport,app.policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=32768))
        result=r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
        measured=r.store.all('cognitive_requests');assert len(measured)==1 and state['calls']==1
        print(json.dumps({'measurement':'synthetic_cross_time_social_choice','behavior':result.intention.behavior,
            'self_calls':state['calls'],'input_bytes':measured[0]['input_bytes'],'reserved_bytes':measured[0]['reserved_bytes'],
            'quiet_motive_before_model':any(m['source']=='SOCIAL_QUIET' for m in seen[0][1]['motivations']),
            'virtual_hours':49,'real_social_sends':0,'real_provider_calls':0}))
        assert result.intention.behavior=='SOCIALIZE' and result.evaluation.wanted
        assert any(m['source']=='SOCIAL_QUIET' for m in seen[0][1]['motivations'])
        assert any(m['source']=='PRIVATE_INTEREST' for m in seen[0][1]['motivations'])
        assert seen[0][0].budget.timeout_ms==120000 and seen[0][0].cognitive_role=='SELF'
        assert r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy).cycle_id==result.cycle_id and state['calls']==1
        assert social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',)).state=='RECOVERING'
        assert current(app)[0][1]==own
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('runtime_cognition_calls')


@pytest.mark.parametrize('quiet_topic,quiet_state',[('social_recovery_needed','RECOVERING'),('social_quiet_preference','QUIET')])
@pytest.mark.parametrize('choice,guard,expected',[('SOCIALIZE','none','SOCIALIZE'),('REST','none','REST'),(None,'none','IGNORE'),('SOCIALIZE','declined','STAY_SILENT'),('SOCIALIZE','norm','REST'),('SOCIALIZE','repeated','STAY_SILENT')])
def test_retained_connection_and_quiet_can_compete_without_a_new_private_thought(app,quiet_topic,quiet_state,choice,guard,expected):
    r=app.runtime;seen=[]
    for topic in ('social_connection',quiet_topic):
        for i in range(2):
            r.subject.run(SubjectInput(source_key=f'synthetic.retained.{topic}.{i}',kind='PLAY',origin='ENVIRONMENT',
                entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
                text=f'SYNTHETIC independent lived preference {topic} occurrence {i}',preference_signal=PreferenceSignal(
                    topic=topic,direction='SUPPORT',interpretation='SYNTHETIC a revisable supported preference')))
    before=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))
    assert before.state==quiet_state and not current(app)
    by_state={t.state:t.source_record_ids for t in before.retained_tendencies}
    assert set(by_state)=={'SEEKING',quiet_state} and not set(by_state['SEEKING'])&set(by_state[quiet_state])
    cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key='ordinary-small-share',
        resource_class='ORDINARY',possible_behaviors=('SOCIALIZE','REST'),availability='BUSY',
        opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'),share_assessment=ShareAssessment(user_preference='DECLINED' if guard=='declined' else 'ALLOW',novelty='REPEATED' if guard=='repeated' else 'NEW',recent_delivery_frequency='HIGH' if guard=='repeated' else 'LOW'))
    if guard=='norm':
        norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key='ordinary-small-share',prohibited_behaviors=('SOCIALIZE',))
        capture(r,'coexisting-social-norm',norm.model_dump(mode='json'),predicate='concern.constraint.coexisting-social')
    mid=capture(r,'coexisting-social-opportunity',cue.model_dump(mode='json'),predicate='concern.coexisting-social')
    class Choosing:
        descriptor='synthetic-independent-retained-tendencies'
        def propose(self,request):
            seen.append(request);value=json.loads(AnalyticalFixturePort().propose(request))
            value.update(preferred_behavior=choice,proposed_operations=['DRAFT']);return json.dumps(value)
    event=SubjectInput(source_key='synthetic.coexisting-social-choice',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
        scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
    result=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy)
    assert result.intention.behavior==expected
    frame=next(json.loads(b['data_json']) for b in json.loads(seen[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
    motives={m['source']:tuple(m['source_ids']) for m in frame['motivations']}
    assert motives['SOCIAL_CONNECTION']==by_state['SEEKING'] and motives['SOCIAL_QUIET']==by_state[quiet_state]
    assert len(seen)==1 and not current(app) and not r.store.all('actions') and not r.store.all('grants')
    assert social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',)).state==quiet_state


def retain_social_tendencies(app):
    r=app.runtime
    for topic in ('social_connection','social_quiet_preference','social_recovery_needed','social_satiation'):
        for i in range(2):
            r.subject.run(SubjectInput(source_key=f'synthetic.coexisting.{topic}.{i}',kind='PLAY',origin='ENVIRONMENT',
                entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
                text=f'SYNTHETIC separate experience {topic} {i}',preference_signal=PreferenceSignal(topic=topic,
                    direction='SUPPORT',interpretation='SYNTHETIC revisable social tendency')))


@pytest.mark.parametrize('withdraw',['SEEKING','QUIET'])
def test_coexisting_projection_is_readonly_private_and_retires_only_withdrawn_support(app,withdraw):
    from nana_core.continuity.records import RecordService
    from nana_core.continuity.relational.contracts import SocialAppetiteView
    r=app.runtime;retain_social_tendencies(app)
    before=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))
    states={t.state:t.source_record_ids for t in before.retained_tendencies}
    assert set(states)=={'SEEKING','QUIET','RECOVERING','SATURATED'}
    changes=r.store.db.total_changes
    assert social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))==before
    assert r.store.db.total_changes==changes and not r.store.all('cognitive_requests')
    assert SocialAppetiteView.model_validate_json(before.model_dump_json())==before
    for scope,privacy in [('project-work',('PUBLIC',)),('another-scope',('PERSONAL',))]:
        hidden=social_appetite(r.store,scope=scope,privacy_classes=privacy)
        assert hidden.state=='UNKNOWN' and not hidden.source_record_ids and 'retained_tendencies' not in hidden.model_dump(mode='json')
    # A genuine source withdrawal leaves independently sourced tendencies intact.
    support=RecordService(r.store).support(states[withdraw][0]);assert support
    app.forget(support[0])
    after=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))
    remaining={t.state:t.source_record_ids for t in after.retained_tendencies}
    assert set(remaining)==set(states)-{withdraw}
    assert all(remaining[k]==v for k,v in states.items() if k!=withdraw)
    assert not after.sources_for(withdraw)
    assert not current(app) and not r.store.all('actions') and not r.store.all('grants')


def test_single_state_legacy_wire_and_unadopted_conflict_are_unchanged(app):
    from nana_core.continuity.relational.contracts import SocialAppetiteView
    r=app.runtime
    for topic in ('social_connection','social_quiet_preference'):
        for i in range(2 if topic=='social_connection' else 1):
            r.subject.run(SubjectInput(source_key=f'synthetic.unadopted.{topic}.{i}',kind='PLAY',origin='ENVIRONMENT',
                entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
                text=f'SYNTHETIC independent experience {topic} {i}',preference_signal=PreferenceSignal(topic=topic,
                    direction='SUPPORT',interpretation='SYNTHETIC not every thought is a stable tendency')))
    view=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))
    assert view.state=='SEEKING' and not view.retained_tendencies and not view.sources_for('QUIET')
    wire=view.model_dump(mode='json');assert 'retained_tendencies' not in wire
    assert SocialAppetiteView.model_validate_json(json.dumps(wire))==view


def test_relational_consideration_keeps_desire_while_quiet_is_also_retained(app):
    from nana_core.continuity.relational.contracts import RelationalRequest,DAY
    r=app.runtime;retain_social_tendencies(app)
    before=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))
    assert before.sources_for('SEEKING') and before.sources_for('QUIET')
    result=r.subject.run(SubjectInput(source_key='synthetic.coexisting.bounded-request',kind='INTERACTION',origin='USER',
        entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
        text='SYNTHETIC consider a bounded social accommodation, not indefinite obedience',relational_request=RelationalRequest(
            request_id='coexisting-bounded',requesting_entity='project-user',operation='REFRAIN',behavior_domain='SOCIAL_NEW_CONTACTS',duration_us=DAY)))
    assert result.relational_decision.response.retained_preference=='SOCIALIZE'
    assert 'RETAINED_SOCIAL_DESIRE' in result.relational_decision.deference.counterconsiderations
    assert not r.store.all('grants') and not r.store.all('actions') and not r.store.all('commitments')
    assert social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',)).retained_tendencies==before.retained_tendencies


def test_restarted_coexisting_tendencies_reach_structured_self_once_without_private_recreation(tmp_path,monkeypatch):
    from .conftest import initialize
    from nana_core.life.application import LifeApplication
    from nana_core.presence.authority import VirtualClock
    from nana_core.presence.contracts import SECOND
    from nana_core.continuity.cognition import CognitiveProposal
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    import itertools,uuid
    # Stable synthetic ids make the old/new budget comparison use the same
    # tie ordering for equally ranked source memories, not random UUID order.
    ids=itertools.count(100000)
    monkeypatch.setattr('nana_core.storage.sqlite_store.uuid.uuid4',lambda:uuid.UUID(int=next(ids)))
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    with LifeApplication(home,clock=clock) as prior:
        prior.pause();r=prior.runtime;identity=r.identity_id;retain_social_tendencies(prior)
        prior_view=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))
        source_ids=prior_view.source_record_ids
        assert prior_view.state in {'QUIET','RECOVERING','SATURATED'} and not current(prior)
    clock.advance(49*3600*SECOND)
    def choose(request):
        context=json.loads(request.context_json);manifest=context['manifest']
        seen.append(next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL'))
        return StructuredProposal(interpretation='SYNTHETIC compare coexisting retained preferences',subject_cognition=CognitiveProposal(
            identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],interpretation='SYNTHETIC consider a small share while retaining quieter tendencies',
            preferred_behavior='SOCIALIZE',proposed_operations=('DRAFT',)))
    with provider_harness(proposer=choose) as (transport,state),LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime;assert r.identity_id==identity and not current(app)
        cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key='small-new-share',resource_class='ORDINARY',
            possible_behaviors=('SOCIALIZE','REST'),availability='BUSY',opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'))
        mid=capture(r,'retained-social-new-share',cue.model_dump(mode='json'),predicate='concern.retained-social-new-share')
        event=SubjectInput(source_key='synthetic.coexisting.structured-restart',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
            scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        port=CognitionSession(r,transport,app.policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=32768))
        result=r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
        measured=r.store.all('cognitive_requests');assert len(measured)==1 and state['calls']==1
        print(json.dumps({'measurement':'synthetic_coexisting_social_restart','behavior':result.intention.behavior,'self_calls':state['calls'],
            'input_bytes':measured[0]['input_bytes'],'reserved_bytes':measured[0]['reserved_bytes'],
            'pre_model_motive_sources':[m['source'] for m in seen[0]['motivations']],
            'virtual_hours':49,'private_thoughts':len(current(app)),'real_social_sends':0,'real_provider_calls':0}))
        assert result.intention.behavior=='SOCIALIZE'
        assert {'SOCIAL_CONNECTION','SOCIAL_QUIET'}<={m['source'] for m in seen[0]['motivations']}
        assert social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',)).source_record_ids==source_ids
        assert not current(app) and not r.store.all('actions') and not r.store.all('grants') and not r.store.all('runtime_cognition_calls')
        assert r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy).cycle_id==result.cycle_id and state['calls']==1
