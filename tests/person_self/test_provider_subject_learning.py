"""Qualified original lessons remain available through the same SELF resource."""
import json
import pytest
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.learning import ExperienceService
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.records import RecordService
from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.presence import NanaRuntime
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import RuntimeConfig
from tests.continuous_self.test_learning import learn_missing_locator


@pytest.mark.parametrize('condition',['active','suspended','wrong-task'])
def test_original_qualified_lesson_changes_a_later_self_choice_and_withdrawal_removes_its_influence(tmp_path,condition):
    path=tmp_path/'original'/'self.db';clock=VirtualClock();authority=OperatorAuthority()
    with ContinuityStore(path,clock,schema_target=13) as store:
        IdentityService(store,authority);memory=MemoryService(store,authority);memory.entity('synthetic-sister','PERSON')
        original,result,experience,lesson=learn_missing_locator(store,memory,authority)
        if condition=='suspended':ExperienceService(store,authority).suspend(lesson,authority)
        cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CURIOSITY',topic_key='own-source-method',possible_behaviors=('EXPLORE','REST'))
        evidence=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.later-self-learning',source_reference='reflection',source_kind='DIRECT_OBSERVATION'),
            text=cue.model_dump_json(),privacy_class='PERSONAL',observed_time_us=clock.utc_now_us()))
        cue_memory=memory.add(MemoryCandidate(entity_id='synthetic-sister',scope='synthetic-home',memory_type=MemoryType.EPISODIC,
            epistemic_kind='OBSERVATION',source_evidence_id=evidence,text=cue.model_dump_json(),predicate_key='concern.later-learning'))
    config=RuntimeConfig(schema_target=13,scopes=('synthetic-home',),entity_id='synthetic-sister',privacy_classes=('PERSONAL',))
    policy=ContextPolicy(policy_id='self-qualified-lesson',allowed_scopes=('synthetic-home',),readable_privacy=('PERSONAL',))
    seen=[]
    def propose(request):
        context=json.loads(request.context_json);identity=context['manifest']
        available=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='LESSON']
        lessons=[v['lesson_id'] for v in available if v['rule'].get('kind')=='ADD_READ_STEP' and v['rule'].get('capability')=='reading.source.locate'];seen.append(lessons)
        return StructuredProposal(interpretation='SYNTHETIC sourced learning reconsideration',subject_cognition=CognitiveProposal(
            identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],lesson_refs=tuple(lessons),
            interpretation='SYNTHETIC explore using a checked method' if lessons else 'SYNTHETIC rest without claiming a learned method',
            preferred_behavior='EXPLORE' if lessons else 'REST',
            proposed_operations=('READ_SOURCE','LOCATE_SOURCE','DRAFT') if lessons else ('WAIT',)))
    with provider_harness(proposer=propose) as (transport,state):
        with NanaRuntime(path,config,clock=clock) as r:
            source=SubjectInput(source_key='synthetic.later-learning-choice',kind='WAKE',origin='SELF_WAKE',entity_id='synthetic-sister',scope='synthetic-home',
                task_class='unrelated-domain' if condition=='wrong-task' else 'reading_card',privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=(cue_memory,))
            cycle=r.subject.cognize(source,model=CognitionSession(r,transport,policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=65536)),authority=r.authority,policy=policy)
            expected=condition=='active'
            assert cycle.intention.behavior==('EXPLORE' if expected else 'REST'), {'seen':seen,'stance':cycle.judgment.stance,'calls':state['calls']}
            assert seen==[[lesson] if expected else []] and state['calls']==1
            assert cycle.judgment.stance==('THINK_MORE' if expected else 'DEFER')
            assert not r.store.all('goals')
            assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('runtime_cognition_calls')
            identity=r.identity_id
        with NanaRuntime(path,config,clock=clock) as r:
            assert r.identity_id==identity
            replay=r.subject.result(r.store.one('subject_cycles',cycle.cycle_id))
            assert replay.intention.behavior==('EXPLORE' if expected else 'REST')
            if expected:
                MemoryService(r.store,r.authority).forget(result,r.authority)
                assert not RecordService(r.store).current_support(cycle.record_id)
                with pytest.raises(CoreError,match='SUBJECT_RATIONALE_RETIRED'):r.subject.run(source)
            assert state['calls']==1


def test_original_lesson_category_cannot_be_applied_without_the_bound_self_frame(tmp_path):
    from nana_core.continuity.context import ContextAssembler,ContextRequest
    from .test_provider_subject_seedless import bare
    with bare(tmp_path,VirtualClock()) as r:
        policy=ContextPolicy(policy_id='no-second-category-authority',allowed_scopes=('own-scope',),readable_privacy=('PROJECT',))
        request=ContextRequest(entity_id='counterparty',scopes=('own-scope',),task_class='world.self',task='Bounded candidate',task_privacy_class='PROJECT')
        with pytest.raises(CoreError,match='SUBJECT_TASK_CLASS_BINDING_REQUIRED'):
            ContextAssembler(r.store,r.authority).assemble(request,policy,subject_task_class='reading_card')
