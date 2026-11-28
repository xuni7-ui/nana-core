"""Repeated checks of a known practice case are not new independent attention."""
import json
import pytest
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.open_agency.fixtures import numeric_learning
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.subject import growth_life
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.reference import context_policy
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tools.nana_vision_first.demo import source
from .test_growth_inner_choice import grown
from .test_private_method_continuation import bind


@pytest.mark.parametrize('repeated,relabel',[(0,False),(32,False),(32,True)])
def test_repeated_training_context_does_not_erase_an_independently_verified_later_use(tmp_path,repeated,relabel):
    clock=VirtualClock();seen=[]
    def propose(request):
        package=json.loads(request.context_json)
        changes=[json.loads(b['data_json']) for b in package['blocks'] if b['kind']=='GROWTH_CHANGE']
        seen.append(changes)
        return StructuredProposal(interpretation='SYNTHETIC independently checked later use',
            subject_cognition=CognitiveProposal(identity_id=package['manifest']['identity_id'],
                identity_revision=package['manifest']['identity_revision'],interpretation='SYNTHETIC I may explore an own idea',
                preferred_behavior='REFLECT',proposed_operations=('DRAFT',),
                private_question={'topic':'own-unseen-growth','question':'SYNTHETIC Could this later verified use inspire an own experiment?'}))
    with grown(tmp_path/'life',clock) as (r,view,origin,reuse,lesson),provider_harness(proposer=propose) as (transport,state):
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
        for i in range(repeated):
            # Exact practice input, even when someone changes its case labels.
            case=numeric_learning().practice[0]
            if relabel:case=case.model_copy(update={'case_id':f'practice-{i}','context':f'other-label-{i}'})
            episode={'episode_key':'practice-check-'+str(i),'lesson_id':lesson,
                     'case':case.model_dump(mode='json')}
            mid=source(r,'practice-check-'+str(i),{'strategy_episode':episode},kind='SYSTEM_VERIFICATION')
            aid=review.assess(lesson,mid,authority=r.authority)
            assert r.store.one('strategy_assessments',aid)['verdict']=='SUCCESS'
            assert growth_life.project(r.store,aid,scope='world',privacy_classes=('PUBLIC',)) is None
        choices=growth_life.opportunities(r.store,scope='world',privacy_classes=('PUBLIC',))
        assert [v.assessment_id for v in choices]==[view.assessment_id]
        bind(r,transport,context_policy());before={t:len(r.store.all(t)) for t in ('actions','goals','grants')}
        clock.advance(3*SECOND);r.lease.heartbeat();r.refresh_attention()
        for _ in range(12):r.step()
        for _ in range(3):r.refresh_attention();r.step()
        own=[v for _,v in candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL'))
             if v.category=='PRIVATE_QUESTION' and v.topic=='own-unseen-growth']
        assert len(own)==1 and state['calls']==1 and seen[0][0]['assessment_id']==view.assessment_id
        assert before=={t:len(r.store.all(t)) for t in before}
        print(json.dumps({'repeated_practice_checks':repeated,'original_self_calls':state['calls'],
            'relabeled_practice':relabel,'independent_transfer_selected':True,'own_questions':len(own),'real_provider_calls':0}))
        if relabel:
            from nana_core.continuity.memory import MemoryService
            MemoryService(r.store,r.authority).forget(reuse,r.authority)
            assert not growth_life.opportunities(r.store,scope='world',privacy_classes=('PUBLIC',))


@pytest.mark.parametrize('schema_target',[7,12,13])
def test_growth_lookups_preserve_legacy_owner_open_and_reopen(tmp_path,schema_target):
    from nana_core.continuity import ContinuityStore
    path=tmp_path/'legacy'/'subject.db'
    for _ in range(2):
        with ContinuityStore(path,VirtualClock(),schema_target=schema_target) as store:
            names={row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
            assert ({'strategy_growth_context_lookup','strategy_growth_order_lookup'}<=names)==(schema_target>=13)
            assert store.schema_target==schema_target


@pytest.mark.parametrize('newer_qualified',[False,True])
def test_group_head_is_not_qualification_or_a_reason_to_prefer_an_older_outcome(tmp_path,newer_qualified):
    from nana_core.continuity.records import RecordService
    from nana_core.continuity.open_agency.learning import LearningCase
    clock=VirtualClock()
    with grown(tmp_path/'life',clock) as (r,view,origin,reuse,lesson):
        review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
        records=RecordService(r.store)
        original=records.read(r.store.one('strategy_assessments',view.assessment_id)['record_id'])['payload']['episode']
        expected=view.assessment_id
        if newer_qualified:
            clock.advance(SECOND);r.lease.heartbeat()
            # A trusted mathematical evaluation, not a new platform action.
            case=LearningCase(case_id='other-unseen-evaluation',context='other-mathematical-context',data=[7.25,1.5],expected=8.75)
            mid=source(r,'other-verified-context',{'strategy_episode':{'episode_key':'other-unseen-evaluation',
                'lesson_id':lesson,'case':case.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
            expected=review.assess(lesson,mid,authority=r.authority)
            assert growth_life.project(r.store,expected,scope='world',privacy_classes=('PUBLIC',))
        clock.advance(SECOND);r.lease.heartbeat()
        report=source(r,'later-unverified-report',{'strategy_episode':{**original,'episode_key':'later-unverified-report'}},kind='USER_STATEMENT')
        unqualified=review.assess(lesson,report,authority=r.authority)
        assert r.store.one('strategy_assessments',unqualified)['verdict']=='SUCCESS'
        assert growth_life.project(r.store,unqualified,scope='world',privacy_classes=('PUBLIC',)) is None
        writes=r.store.db.total_changes
        assert [v.assessment_id for v in growth_life.opportunities(r.store,scope='world',privacy_classes=('PUBLIC',))]==[expected]
        assert r.store.db.total_changes==writes
