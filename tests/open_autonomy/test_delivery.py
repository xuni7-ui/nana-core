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
