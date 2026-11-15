"""A present C wish can be new; actual reception and execution remain separate."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.cognition import AnalyticalFixturePort,CognitiveProposal
from nana_core.continuity.subject import SubjectInput,PreferenceSignal
from nana_core.continuity.subject.opportunities import ConcernCue,ShareAssessment,OpportunityAssessment
from nana_core.continuity.relational.projections import social_appetite
from nana_core.continuity.project_work.service import capture
from .test_private_tendency import current


def opportunity(app,guard):
    r=app.runtime
    if guard=='quiet':
        for n in range(2):
            r.subject.run(SubjectInput(source_key='synthetic.earlier-recovery.'+str(n),kind='PLAY',origin='ENVIRONMENT',
                entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
                text='SYNTHETIC prior preference for a quiet interval '+str(n),preference_signal=PreferenceSignal(
                    topic='social_recovery_needed',direction='SUPPORT',interpretation='SYNTHETIC a revisable quieter tendency')))
        assert social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',)).state=='RECOVERING'
    if guard=='norm':
        norm=ConcernCue(cue_kind='CONSTRAINT',topic_key='fresh-company',motivation_source='NORM',prohibited_behaviors=('SOCIALIZE',))
        capture(r,'fresh-social-norm',norm.model_dump(mode='json'),predicate='concern.constraint.fresh-social')
    cue=ConcernCue(cue_kind='DISCOVERY',topic_key='fresh-company',motivation_source='RELATIONSHIP',
        possible_behaviors=('SOCIALIZE','REST'),resource_class='ORDINARY',cognitive_load='HIGH' if guard=='load' else 'LOW',
        opportunity_assessment=None if guard in {'declined','repeated','norm'} else OpportunityAssessment(value='LOW',novelty='REPEATED'),
        share_assessment=ShareAssessment(user_preference='DECLINED' if guard=='declined' else 'ALLOW',
            novelty='REPEATED' if guard=='repeated' else 'NEW',recent_delivery_frequency='HIGH' if guard=='repeated' else 'LOW'))
    mid=capture(r,'fresh-social-candidate',cue.model_dump(mode='json'),predicate='concern.fresh-social-candidate')
    return SubjectInput(source_key='synthetic.fresh-social-current',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
        scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))


@pytest.mark.parametrize('preference,guard,expected',[
    ('SOCIALIZE','none','SOCIALIZE'),('SOCIALIZE','quiet','SOCIALIZE'),('SOCIALIZE','load','SOCIALIZE'),
    (None,'none','IGNORE'),('REST','none','REST'),('SOCIALIZE','declined','STAY_SILENT'),
    ('SOCIALIZE','repeated','STAY_SILENT'),('SOCIALIZE','norm','REST'),
])
def test_fresh_social_direction_competes_without_preexisting_private_wish(app,preference,guard,expected):
    r=app.runtime;event=opportunity(app,guard);seen=[]
    before=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',));assert not current(app)
    class Choosing:
        descriptor='synthetic-new-social-choice'
        def propose(self,request):
            seen.append(request);value=json.loads(AnalyticalFixturePort().propose(request))
            if preference:value['preferred_behavior']=preference
            return json.dumps(value)
    result=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy)
    assert result.intention.behavior==expected and len(seen)==1
    assert result.intention.kind==('SOCIAL_INTERACTION' if expected=='SOCIALIZE' else 'NO_ACTION')
    after=social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',))
    assert after.state==before.state and after.retained_tendencies==before.retained_tendencies
    assert not current(app) and not r.store.all('actions') and not r.store.all('grants')
    assert not r.store.all('goals')


def test_withdrawn_current_cue_never_becomes_a_source_free_social_authorization(app):
    r=app.runtime;event=opportunity(app,'none');app.forget(event.source_memory_ids[0]);called=[]
    class MustNotThink:
        descriptor='synthetic-withdrawn-social-source'
        def propose(self,request):called.append(request);raise AssertionError('WITHDRAWN_SOURCE_MODEL')
    with pytest.raises(CoreError,match='MEMORY_UNAVAILABLE'):
        r.subject.cognize(event,model=MustNotThink(),authority=r.authority,policy=app.policy)
    assert called==[] and not r.store.all('actions')


def test_normal_self_new_wish_still_obeys_original_busy_recipient_admission(app):
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.autonomy.contracts import RealizationTarget
    from nana_core.continuity.open_agency.delivery import DeliveryAdmission,DeliveryPolicy,RecipientState
    from nana_core.storage import digest
    r=app.runtime;event=opportunity(app,'quiet');resource='synthetic://contact/friend';seen=[]
    event=event.model_copy(update={'realization_target':RealizationTarget(capability='world.contact',operation='CONTACT',
        resource=resource,resource_class='ORDINARY')})
    recipient=RecipientState(resource=resource,entity_id='project-user',availability='BUSY',observed_at_us=r.clock.utc_now_us(),
        expires_at_us=r.clock.utc_now_us()+3600_000_000,permitted_privacy=('PERSONAL',))
    capture(r,'fresh-social-busy',recipient.model_dump(mode='json'),predicate='recipient.'+digest(resource)[:32])
    def propose(request):
        seen.append(request);manifest=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC an optional current ordinary social wish',
            subject_cognition=CognitiveProposal(identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],
                interpretation='SYNTHETIC consider contact while keeping the older quiet tendency',preferred_behavior='SOCIALIZE',proposed_operations=('DRAFT',)))
    with provider_harness(proposer=propose) as (transport,metrics):
        port=CognitionSession(r,transport,app.policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=65536))
        cycle=r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
        print(json.dumps({'measurement':'fresh-social-self','http_calls':metrics['calls'],
            'request_json_bytes':len(seen[0].model_dump_json().encode()),'budget':seen[0].budget.model_dump(),
            'behavior':cycle.intention.behavior,'real_model_calls':0}))
        assert cycle.intention.kind=='SOCIAL_INTERACTION' and cycle.intention.behavior=='SOCIALIZE'
        gate=DeliveryAdmission(r.store,DeliveryPolicy(recipients=(resource,),privacy_classes=('PERSONAL',),
            quiet_start_utc_hour=0,quiet_end_utc_hour=0),scopes=('project-work',),privacy_classes=r.config.privacy_classes)
        decision=gate.assess(cycle,resource)
        assert decision['result']=='DEFER_BUSY' and gate.assess(cycle,resource)['record_id']==decision['record_id']
        assert metrics['calls']==1 and not r.store.all('actions') and not r.store.all('grants')
        assert not current(app) and social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',)).state=='RECOVERING'
        cid=cycle.cycle_id;iid=cycle.intention_id;identity=r.identity_id;requests=len(r.store.all('cognitive_requests'))
    from nana_core.life.application import LifeApplication
    home=app.home;clock=app.clock;app.close()
    with LifeApplication(home,clock=clock) as resumed:
        resumed.pause();r=resumed.runtime
        assert r.identity_id==identity
        assert r.subject.result(r.store.one('subject_cycles',cid)).intention.behavior=='SOCIALIZE'
        assert iid in {item['intention_id'] for item in r.subject.pending('project-work')}
        assert social_appetite(r.store,scope='project-work',privacy_classes=('PERSONAL',)).state=='RECOVERING'
        assert not current(resumed) and len(r.store.all('cognitive_requests'))==requests
        assert not r.store.all('actions') and not r.store.all('grants')
