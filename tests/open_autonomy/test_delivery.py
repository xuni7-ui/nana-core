import pytest
from nana_core.continuity.open_agency.delivery import DeliveryAdmission,DeliveryPolicy,RecipientState
from nana_core.continuity.autonomy.contracts import RealizationTarget
from nana_core.continuity.relational.projections import social_appetite
from nana_core.continuity.subject.opportunities import ConcernCue
from .helpers import *

def test_busy_recipient_defers_delivery_not_internal_desire_or_grants(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        resource='synthetic://contact/friend'
        c=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='RELATIONSHIP',topic_key='connection',possible_behaviors=('SOCIALIZE',),resource_ref=resource,resource_class='ORDINARY',availability='BUSY')
        mid=capture(r,'connection',c.model_dump_json(),predicate='concern.connection')
        recipient=RecipientState(resource=resource,entity_id='synthetic-person',availability='BUSY',observed_at_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+HOUR,permitted_privacy=('PERSONAL',))
        capture(r,'busy',recipient.model_dump_json(),predicate='recipient.'+digest(resource)[:32])
        gate=DeliveryAdmission(r.store,DeliveryPolicy(recipients=(resource,),privacy_classes=('PERSONAL',),quiet_start_utc_hour=0,quiet_end_utc_hour=0),scopes=('lab',),privacy_classes=('PERSONAL',))
        qid=send(r,'want-contact',(mid,),realization_target=RealizationTarget(capability='world.contact',operation='CONTACT',resource=resource,resource_class='ORDINARY'))
        cycle=r.step()['cycle']
        assert cycle.evaluation.normative=='ENDORSED' and cycle.intention.kind=='SOCIAL_INTERACTION'
        decision=gate.assess(cycle,resource)
        assert decision['result']=='DEFER_BUSY'
        assert gate.assess(cycle,resource)['record_id']==decision['record_id']
        assert social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',)).state=='OPEN'
        assert not r.store.all('grants') and not r.store.all('actions')

def test_available_recipient_actual_fixture_contact_is_kernel_verified_and_admission_bound(tmp_path):
    import pytest,json
    from nana_core.contracts import CoreError,Invocation
    from nana_core.continuity.open_agency.contracts import Objective,Operator
    from nana_core.continuity.records import RecordService
    with fresh(tmp_path/'s'/'self.db') as r:
        resource='synthetic://contact/friend'
        obj=Objective(objective_id='project.contact',scope='lab',motivation_source='PROJECT_COMPLETION',task_domain='contact',desired=('contacted',),operators=(Operator(operator_id='contact',capability='world.contact',resource=resource,produces=('contacted',),args={'data':'synthetic greeting'},expected_digest=digest('synthetic greeting')),))
        port=configure(r,tmp_path/'w'/'world.fixture.json',(obj,));port.seed_observation(resource,{'availability':'AVAILABLE','reaction':'NO_RESPONSE'},privacy_class='PERSONAL')
        state=RecipientState(resource=resource,entity_id='synthetic-person',availability='AVAILABLE',observed_at_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+HOUR,permitted_privacy=('PERSONAL',))
        capture(r,'available',state.model_dump_json(),predicate='recipient.'+digest(resource)[:32])
        delivery=DeliveryAdmission(r.store,DeliveryPolicy(recipients=(resource,),privacy_classes=('PERSONAL',),quiet_start_utc_hour=0,quiet_end_utc_hour=0),scopes=('lab',),privacy_classes=('PERSONAL',))
        port.delivery=delivery;r.work.agency.delivery=delivery
        mid=cue(r,obj);send(r,'contact',(mid,));r.drain(8)
        action=r.store.all('actions')[0];assert action['state']=='SUCCEEDED'
        result=json.loads(r.work.agency.realization.kernel.payload(action,'result_json'))
        assert result['delivered']=='SYNTHETIC_ONLY' and result['reaction']=='NO_RESPONSE'
        admission=r.store.db.execute("SELECT * FROM continuity_records WHERE record_kind='DELIVERY_DECISION'").fetchone()
        forged=Invocation(action_id='different-action',attempt_id='different',capability='world.contact',resource=resource,args={'data':'different greeting'},args_hash='different',idempotency_key='different')
        with pytest.raises(CoreError,match='INTENTION_OR_PAYLOAD_MISMATCH'):delivery.require(admission['record_id'],resource,invocation=forged)
        send(r,'same-contact-cause',(mid,));r.drain(8)
        assert len(json.loads(port.path.read_text())['effects'])==1 and len(r.store.all('actions'))==1


@pytest.mark.parametrize('owned,value,novelty,preference,frequency,load,availability,expected', [
    (True,'LOW','NEW','UNKNOWN','LOW','LOW','BUSY','SOCIALIZE'),
    (True,'RELEVANT','REPEATED','UNKNOWN','LOW','LOW','UNKNOWN','SOCIALIZE'),
    (True,'RELEVANT','NEW','ALLOW','LOW','LOW','AVAILABLE','SOCIALIZE'),
    (True,'RELEVANT','NEW','DECLINED','LOW','LOW','AVAILABLE','STAY_SILENT'),
    (True,'RELEVANT','REPEATED','ALLOW','HIGH','LOW','AVAILABLE','STAY_SILENT'),
    (False,'LOW','NEW','UNKNOWN','LOW','LOW','AVAILABLE','IGNORE'),
    (False,'RELEVANT','NEW','UNKNOWN','LOW','LOW','AVAILABLE','STAY_SILENT'),
    (True,'RELEVANT','NEW','ALLOW','LOW','HIGH','AVAILABLE','SOCIALIZE'),
    (True,'RELEVANT','NEW','ALLOW','LOW','HIGH','BUSY','SOCIALIZE'),
    (True,'RELEVANT','NEW','ALLOW','LOW','HIGH','UNKNOWN','SOCIALIZE'),
    (True,'RELEVANT','NEW','DECLINED','LOW','HIGH','AVAILABLE','STAY_SILENT'),
    (True,'RELEVANT','REPEATED','ALLOW','HIGH','HIGH','AVAILABLE','STAY_SILENT'),
])
def test_owned_connection_interest_can_compete_with_generic_share_relevance(
        tmp_path,owned,value,novelty,preference,frequency,load,availability,expected):
    from nana_core.continuity.subject import PreferenceSignal
    from nana_core.continuity.subject.opportunities import ShareAssessment,OpportunityAssessment
    with fresh(tmp_path/'s'/'self.db') as r:
        if owned:
            for index in range(2):
                r.subject.run(SubjectInput(source_key='synthetic.social-interest.'+str(index),kind='PLAY',origin='ENVIRONMENT',
                    entity_id='synthetic-person',scope='lab',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
                    text='SYNTHETIC independent enjoyable connection '+str(index),
                    preference_signal=PreferenceSignal(topic='social_connection',direction='SUPPORT',
                        interpretation='SYNTHETIC personally values ordinary company')))
            desire=social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',))
            assert desire.state=='SEEKING' and desire.source_record_ids
        resource='synthetic://contact/friend'
        cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key='small-share',
            possible_behaviors=('SOCIALIZE','STAY_SILENT'),resource_class='ORDINARY',availability=availability,cognitive_load=load,
            share_assessment=ShareAssessment(user_preference=preference,recent_delivery_frequency=frequency,novelty=novelty),
            opportunity_assessment=OpportunityAssessment(value=value,novelty=novelty))
        mid=capture(r,'small-share',cue.model_dump_json(),predicate='concern.small-share')
        recipient=RecipientState(resource=resource,entity_id='synthetic-person',availability=availability,
            observed_at_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+HOUR,permitted_privacy=('PERSONAL',))
        capture(r,'small-share-recipient',recipient.model_dump_json(),predicate='recipient.'+digest(resource)[:32])
        send(r,'small-share-choice',(mid,),realization_target=RealizationTarget(capability='world.contact',operation='CONTACT',resource=resource,resource_class='ORDINARY'))
        cycle=r.step()['cycle']
        assert cycle.intention.behavior==expected
        if load=='HIGH':
            rest=[m for m in cycle.motivations if m.source=='REST']
            assert len(rest)==1 and rest[0].strength=='RELEVANT' and rest[0].source_ids
        assert cycle.evaluation.wanted
        if expected=='SOCIALIZE':
            assert cycle.intention.kind=='SOCIAL_INTERACTION' and cycle.evaluation.normative=='ENDORSED'
            gate=DeliveryAdmission(r.store,DeliveryPolicy(recipients=(resource,),privacy_classes=('PERSONAL',),
                quiet_start_utc_hour=0,quiet_end_utc_hour=0),scopes=('lab',),privacy_classes=('PERSONAL',))
            result=gate.assess(cycle,resource)
            assert result['result']=={'BUSY':'DEFER_BUSY','UNKNOWN':'UNKNOWN_AVAILABILITY','AVAILABLE':'ELIGIBLE'}[availability]
            assert result['authority_granted'] is False
        assert not r.store.all('grants') and not r.store.all('actions')
        assert not r.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cognitive_requests'").fetchone()


def test_connection_interest_restart_and_source_withdrawal_remove_its_exception(tmp_path):
    from nana_core.continuity.subject import PreferenceSignal
    from nana_core.continuity.subject.opportunities import ShareAssessment,OpportunityAssessment
    with fresh(tmp_path/'s'/'self.db') as r:
        roots=[]
        for index in range(2):
            c=r.subject.run(SubjectInput(source_key='synthetic.connection-root.'+str(index),kind='PLAY',origin='ENVIRONMENT',
                entity_id='synthetic-person',scope='lab',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),
                text='SYNTHETIC independent social preference '+str(index),preference_signal=PreferenceSignal(
                    topic='social_connection',direction='SUPPORT',interpretation='SYNTHETIC enjoys ordinary company')))
            roots.append(r.store.one('subject_events',c.event_id)['memory_id'])
        identity,path,clock=r.identity_id,r.store.path,r.clock.source;r.stop()
        with fresh(path,clock) as current:
            assert current.identity_id==identity
            cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key='unimportant-company',
                possible_behaviors=('SOCIALIZE','STAY_SILENT'),resource_class='ORDINARY',availability='BUSY',
                share_assessment=ShareAssessment(),opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'))
            mid=capture(current,'unimportant-company',cue.model_dump_json(),predicate='concern.unimportant-company')
            def choose(key):return current.subject.run(SubjectInput(source_key='synthetic.connection-choice.'+key,
                kind='WAKE',origin='SELF_WAKE',entity_id='synthetic-person',scope='lab',privacy_class='PERSONAL',
                observed_at_us=current.clock.utc_now_us(),source_memory_ids=(mid,)))
            assert choose('before').intention.behavior=='SOCIALIZE'
            MemoryService(current.store,current.authority).forget(roots[0],current.authority)
            appetite=social_appetite(current.store,scope='lab',privacy_classes=('PERSONAL',))
            assert appetite.state=='OPEN' and not appetite.source_record_ids
            assert choose('withdrawn').intention.behavior=='IGNORE'
            assert not current.store.all('grants') and not current.store.all('actions')
