import pytest
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.learning import ExperienceService,ExperienceInput,InteractionOutcome
from nana_core.continuity.subject.reflection import ReflectionService
from nana_core.continuity.subject.contracts import StandingDelegation
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import HOUR
from nana_core.presence.fixtures import concern,memory,familiar_relationship,advance
from nana_core.presence.adapters import FilePerceptionPort
from nana_core.contracts import CoreError
from .test_coordinator import prepared


def config():return RuntimeConfig(scopes=('life',),entity_id='synthetic-person',lease_us=3*HOUR,heartbeat_us=HOUR,idle_recall_us=HOUR)


def test_one_loop_open_motive_constraint_rest_and_social_learning(tmp_path):
    clock=VirtualClock();path=tmp_path/'self.db';prepared(path,clock)
    with NanaRuntime(path,config(),clock=clock) as rt:
        familiar_relationship(rt)
        root=concern(rt,'discovery',ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key='unexpected_finding',possible_behaviors=('SOCIALIZE',),availability='AVAILABLE'))
        results=advance(rt,clock,2*HOUR)
        cycle=next(x['cycle'] for x in results if x['cycle'] and x['cycle'].social_proposal)
        assert cycle.social_proposal.act=='TEASE' and cycle.social_proposal.utterance is None
        result=memory(rt,'reaction',InteractionOutcome(proposal_intention_id=cycle.intention_id,reaction='POSITIVE_PLAYFUL').model_dump_json())
        learning=ExperienceService(rt.store,rt.authority)
        proof=learning.verify_interaction_result(result,rt.authority)
        experience=learning.record(ExperienceInput(context_memory_ids=(root,),scope='life',task_class='interaction.shared_discovery',
            decision=cycle.intention.purpose,result_memory_id=result,verification_memory_id=proof))
        # Reflection opportunity passes through D -> the same C loop.
        rt.refresh_attention();later=advance(rt,clock,2*HOUR)
        assert any(x['cycle'] and x['cycle'].judgment.stance=='REFLECT' for x in later)
        reflection=rt.store.all('subject_reflections')[0]
        lesson=ReflectionService(rt.store,rt.authority).apply(reflection['reflection_id'],expected_revision=1,authority=rt.authority)
        assert rt.store.one('lessons',lesson)['state']=='ACTIVE'
        concern(rt,'next-discovery',ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key='another_finding',possible_behaviors=('SOCIALIZE',),availability='AVAILABLE'))
        changed=advance(rt,clock,2*HOUR)
        proposal=next(x['cycle'].social_proposal for x in changed if x['cycle'] and x['cycle'].social_proposal)
        assert proposal.act=='SHARE_THOUGHT' and proposal.lesson_ids==(lesson,)
        learning.suspend(lesson,rt.authority)
        concern(rt,'ablation-discovery',ConcernCue(cue_kind='DISCOVERY',motivation_source='RELATIONSHIP',topic_key='third_finding',possible_behaviors=('SOCIALIZE',),availability='AVAILABLE'))
        control=advance(rt,clock,2*HOUR)
        assert next(x['cycle'].social_proposal.act for x in control if x['cycle'] and x['cycle'].social_proposal)=='TEASE'
        assert not any(rt.store.all(t) for t in ('actions','attempts','grants','budgets'))


def test_synthetic_read_scope_and_c_nonaction(tmp_path):
    clock=VirtualClock();path=tmp_path/'self.db';prepared(path,clock)
    with NanaRuntime(path,config(),clock=clock) as rt:
        resource='synthetic://ordinary/resource-1'
        concern(rt,'interest',ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CURIOSITY',topic_key='open_question',possible_behaviors=('EXPLORE',),resource_ref=resource,resource_class='ORDINARY'))
        outputs=advance(rt,clock,2*HOUR)
        cycle=next(x['cycle'] for x in outputs if x['cycle'] and x['cycle'].action_proposal)
        assert cycle.goal_candidate_id and cycle.action_proposal.execution_authority is False
        delegation=StandingDelegation(delegation_id='synthetic-only',subject=rt.store.identity['identity_id'],capability='synthetic.resource.read',
            resource_scope=(resource,),operations=('READ',),risk_ceiling='READ_ONLY',privacy_scope=('PERSONAL',),
            issued_at_us=clock.utc_now_us(),expires_at_us=clock.utc_now_us()+HOUR,provenance='synthetic-reviewed-snapshot')
        port=FilePerceptionPort(rt.store.identity['identity_id'],'synthetic-person','life',{resource:('ORDINARY','A synthetic observation')})
        observed=port.simulate_read(cycle.action_proposal,delegation,clock,intention_id=cycle.intention_id)
        rt.submit(observed);rt.drain()
        with pytest.raises(CoreError,match='SYNTHETIC_DELEGATION_SCOPE_BLOCKED'):
            port.simulate_read(cycle.action_proposal,delegation.model_copy(update={'resource_scope':('synthetic://other',)}),clock,intention_id=cycle.intention_id)
        for unsafe in ('PASSWORD','CREDENTIAL','PAYMENT','OTHER_PERSON_SECRET','UNKNOWN'):
            with pytest.raises(CoreError,match='SYNTHETIC_DELEGATION_SCOPE_BLOCKED'):
                port.simulate_read(cycle.action_proposal.model_copy(update={'resource_class':unsafe}),delegation,clock,intention_id=cycle.intention_id)
        assert not any(rt.store.all(t) for t in ('actions','attempts','grants','budgets'))
