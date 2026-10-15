from nana_core.continuity.autonomy.experience import ExperienceCandidateService,ConsequenceObservation
from nana_core.continuity.autonomy.history import dispositions
from nana_core.continuity.autonomy.governance import GovernanceController,ManagerConstraintGate,snapshot
from nana_core.continuity.learning import ExperienceService,ExperienceInput
from nana_core.continuity.memory import MemoryService
from .conftest import event,memory
from .test_governance import proposed,constraint


def test_block_is_fact_not_automatic_experience_or_personality(subject):
 r=subject;ctrl=GovernanceController(r.store,r.authority);ctrl.install(constraint(r),r.authority)
 c=proposed(r);gate=ManagerConstraintGate(r.store);gate.gate(c.intention_id,expected_revision=1)
 disp=dispositions(r.store,scope='lab',intention_id=c.intention_id)[0]
 assert disp.code=='MANAGER_BLOCKED'
 candidates=ExperienceCandidateService(r.store,r.authority)
 assert candidates.consider(disp.record_id) is None
 assert not r.store.all('experiences')
 observation=ConsequenceObservation(disposition_record_id=disp.record_id,kind='PROJECT_OUTCOME',assessment='HARMFUL',description='A fictional deadline was missed; this does not invalidate governance')
 consequence=memory(r,'consequence',observation.model_dump_json())
 candidate=candidates.consider(disp.record_id,consequence_memory_id=consequence)
 assert candidates.consider(disp.record_id,consequence_memory_id=consequence)==candidate
 result,proof=candidates.verify(candidate,r.authority)
 assert candidates.verify(candidate,r.authority)==(result,proof)
 service=ExperienceService(r.store,r.authority)
 data=ExperienceInput(context_memory_ids=(consequence,),scope='lab',task_class='disposition.review',decision='A veto occurred; later consequences warrant review',result_memory_id=result,verification_memory_id=proof)
 eid=service.record(data);assert service.record(data)==eid
 assert service.get(eid).outcome=='NON_EXECUTION'
 before=r.store.identity.copy();reflection=r.subject.reflect(eid,authority=r.authority,apply=True)
 learned=r.subject.run(event(r,'later',task_class='disposition.review'))
 assert learned.judgment.selected_method=='ask_for_review_without_bypass'
 lesson=r.store.one('subject_reflections',reflection)['lesson_id'];service.suspend(lesson,r.authority)
 control=r.subject.run(event(r,'without',task_class='disposition.review'))
 assert control.judgment.selected_method is None
 assert r.store.identity==before and not r.store.all('grants') and not r.store.all('actions')
 MemoryService(r.store,r.authority).forget(consequence,r.authority)
 assert r.store.one('continuity_records',candidate)['lifecycle']=='DELETED'
 assert snapshot(r.store)[1][0][1].constraint_id=='constraint-a'


def test_subject_reflection_selects_existing_disposition_without_inventing_history(subject):
 r=subject;c=proposed(r)
 disp=dispositions(r.store,scope='lab',intention_id=c.intention_id)[0]
 selected=r.subject.run(event(r,'select',kind='WAKE',origin='SELF_WAKE',text=None,disposition_reflection_id=disp.record_id))
 assert selected.judgment.stance=='REFLECT'
 candidates=ExperienceCandidateService(r.store,r.authority)
 cid=candidates.consider(disp.record_id,selection_cycle_id=selected.cycle_id)
 result,proof=candidates.verify(cid,r.authority)
 assert 'NOT_ESTABLISHED_BY_DISPOSITION' in r.store.artifact(r.store.one('memories',result)['payload_artifact_id']).decode()
 assert not r.store.all('self_assertions') and not r.store.all('experiences')
