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
