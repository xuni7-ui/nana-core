"""Invisible assessment headers cannot crowd out a checked visible G outcome."""
import json
import pytest

from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.subject import growth_life
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.world_loop.reference import context_policy
from nana_core.presence.runtime import NanaRuntime
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from .test_growth_inner_choice import grown
from .test_private_method_continuation import bind


@pytest.mark.parametrize('invisible_count',[0,32])
def test_checked_growth_still_reaches_original_c_after_private_review_population(tmp_path,invisible_count):
    clock=VirtualClock();seen=[];call_ids=[]
    def propose(request):
        package=json.loads(request.context_json);call_ids.append(request.request_id)
        assert 'PRIVATE_GROWTH_POPULATION_CANARY' not in request.context_json
        own=[json.loads(b['data_json']) for b in package['blocks'] if b['kind']=='GROWTH_CHANGE']
        seen.append(own)
        return StructuredProposal(interpretation='SYNTHETIC checked reuse may inspire another interest',
            subject_cognition=CognitiveProposal(identity_id=package['manifest']['identity_id'],
                identity_revision=package['manifest']['identity_revision'],
                interpretation='SYNTHETIC I choose an own question after this checked outcome',
                preferred_behavior='REFLECT',proposed_operations=('DRAFT',),
                private_question={'topic':'own-checked-growth','question':'SYNTHETIC Could this verified method help my own playful experiment?'}))
    with grown(tmp_path/'life',clock) as (r,view,origin,reuse,lesson):
        records=RecordService(r.store);memory=MemoryService(r.store)
        original=records.read(r.store.one('strategy_assessments',view.assessment_id)['record_id'])['payload']['episode']
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC','PERSONAL'))
        private_ids=[]
        for i in range(invisible_count):
            # Repeated private observations of the SAME actual checked use.
            # These are not 32 independent successes or new learning evidence.
            episode={**original,'episode_key':'private-repeated-observation-'+str(i)}
            body=json.dumps({'strategy_episode':episode,'private_note':'PRIVATE_GROWTH_POPULATION_CANARY'})
            eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.growth-population',
                source_reference=str(i),source_kind='SYSTEM_VERIFICATION'),text=body,privacy_class='PERSONAL',observed_time_us=clock.utc_now_us()))
            mid=memory.add(MemoryCandidate(entity_id=r.config.entity_id,scope='world',memory_type=MemoryType.EPISODIC,
                epistemic_kind='OBSERVATION',source_evidence_id=eid,text=body,derived_from=(reuse,)))
            assessment=review.assess(lesson,mid,authority=r.authority)
            assert r.store.one('strategy_assessments',assessment)['verdict']=='SUCCESS'
            assert growth_life.project(r.store,assessment,scope='world',privacy_classes=('PUBLIC',)) is None
            private_ids.append(mid)
        assert growth_life.project(r.store,view.assessment_id,scope='world',privacy_classes=('PUBLIC',))
        visible=growth_life.opportunities(r.store,scope='world',privacy_classes=('PUBLIC',))
        assert [v.assessment_id for v in visible]==[view.assessment_id]
        assert not growth_life.opportunities(r.store,scope='other-scope',privacy_classes=('PUBLIC',))
        assert not growth_life.opportunities(r.store,scope='world',privacy_classes=())
        path=r.store.path;identity=r.identity_id
        config=r.config.model_copy(update={'privacy_classes':('PUBLIC',)})
    # The producer was authorized to record private reviews. The reopened
    # original owner intentionally has a PUBLIC-only cognition policy.
    with NanaRuntime(path,config,clock=clock) as r,provider_harness(proposer=propose) as (transport,state):
        assert r.identity_id==identity and r.subject.privacy_classes==('PUBLIC',)
        policy=context_policy().model_copy(update={'readable_privacy':('PUBLIC',)})
        bind(r,transport,policy)
        before={t:len(r.store.all(t)) for t in ('actions','goals','grants')}
        clock.advance(3*SECOND);r.lease.heartbeat();r.refresh_attention()
        for _ in range(12):r.step()
        for _ in range(3):r.refresh_attention();r.step()
        own=[v for _,v in candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL'))
             if v.category=='PRIVATE_QUESTION' and v.topic=='own-checked-growth']
        assert len(own)==1 and state['calls']==1
        assert seen and seen[0][0]['assessment_id']==view.assessment_id
        assert before=={t:len(r.store.all(t)) for t in before}
        assert not set(private_ids)&set(own[0].source_memory_ids)
        measure=dict(r.store.one('cognitive_requests',call_ids[0]))
        memory=MemoryService(r.store,r.authority);memory.forget(reuse,r.authority)
        assert not growth_life.opportunities(r.store,scope='world',privacy_classes=('PUBLIC',))
        assert not any(v.topic=='own-checked-growth' for _,v in candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL')))
        print(json.dumps({'invisible_assessments':invisible_count,'original_runtime_self_calls':state['calls'],
            'new_own_question':len(own),'new_goal_action_grant':False,'real_provider_calls':0,
            'input_bytes':measure['input_bytes'],'reserved_bytes':measure['reserved_bytes'],
            'latency_us':measure['latency_us'],'measurement_semantics':'PROGRAM_BYTES_NOT_PROVIDER_TOKENS'}))
