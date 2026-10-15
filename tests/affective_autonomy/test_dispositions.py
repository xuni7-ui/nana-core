import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.autonomy.contracts import DisclosureRequest,SocialExpectationSpec
from nana_core.continuity.autonomy.disclosure import eligible_assertion
from nana_core.continuity.autonomy.history import dispositions
from nana_core.continuity.subject.opportunities import ConcernCue
from .conftest import event,memory,concern


def test_endorse_restraint_and_empty_wake_differ(subject):
 r=subject
 m=concern(r,'interest',ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CURIOSITY',topic_key='topic',possible_behaviors=('EXPLORE',)))
 c=r.subject.run(event(r,'first',source_memory_ids=(m,)))
 assert c.evaluation.normative=='ENDORSED' and c.intention_id
 r.subject.transition_intention(c.intention_id,expected_revision=1,state='DROPPED')
 n=concern(r,'norm',ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key='topic',prohibited_behaviors=('EXPLORE',)))
 restrained=r.subject.run(event(r,'restrained',source_memory_ids=(m,n)))
 assert restrained.evaluation.normative=='RESTRAINED' and restrained.evaluation.wanted
 assert dispositions(r.store,scope='lab',intention_id=restrained.intention_id)[0].code=='SUBJECT_RESTRAINED'
 quiet=r.subject.run(event(r,'quiet',kind='WAKE',origin='SELF_WAKE',text=None))
 assert quiet.evaluation.normative=='UNDECIDED' and not quiet.evaluation.considered
 assert not r.store.all('actions') and not r.store.all('grants')


def test_disclosure_withhold_cannot_negate_known_fact(subject):
 r=subject
 spec=SocialExpectationSpec(topic='planned-work',expectation='CONTEXT_SENSITIVE',timing='DEFER_UNTIL',reveal_at_us=r.clock.utc_now_us()+1000000)
 mid=memory(r,'expectation',spec.model_dump_json(),predicate='social.expectation.planned-work',source_kind='USER_STATEMENT')
 result=r.subject.run(event(r,'asked',disclosure_request=DisclosureRequest(topic='planned-work',asked=True)))
 assert result.disclosure.mode=='WITHHOLD_UNTIL_REVEAL' and result.disclosure.phase=='PLANNED'
 assert not result.disclosure.assertions and result.disclosure.delivery_authority is False
 fact=memory(r,'known', '{"value":true}',source_kind='SYSTEM_VERIFICATION')
 assert eligible_assertion(r.store,fact,True,scope='lab',privacy_classes=('PERSONAL',))
 with pytest.raises(CoreError,match='KNOWING_FALSEHOOD'):
  eligible_assertion(r.store,fact,False,scope='lab',privacy_classes=('PERSONAL',))
