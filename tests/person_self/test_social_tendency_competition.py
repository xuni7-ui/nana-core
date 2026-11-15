"""Longer quiet tendencies need not veto a present source-backed own wish."""
import json
import pytest
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput,PreferenceSignal
from nana_core.continuity.subject.opportunities import ConcernCue,ShareAssessment,OpportunityAssessment
from nana_core.continuity.relational.projections import social_appetite
from nana_core.continuity.project_work.service import capture
from .test_private_tendency import form,current


@pytest.mark.parametrize('tendency,state',[('social_recovery_needed','RECOVERING'),('social_quiet_preference','QUIET')])
@pytest.mark.parametrize('choice,guard,expected',[('SOCIALIZE','none','SOCIALIZE'),('REST','none','REST'),(None,'none','IGNORE'),('SOCIALIZE','declined','STAY_SILENT'),('SOCIALIZE','norm','REST'),('SOCIALIZE','withdrawn','IGNORE'),('EXPLORE','research','EXPLORE'),('SOCIALIZE','repeated-delivery','STAY_SILENT')])
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
