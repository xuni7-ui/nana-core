import pytest
from nana_core.continuity.lived_language import LanguageService,LanguageSample,expression_policy,context
from nana_core.continuity.learning import ExperienceService
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication


def sample(app,n,*,tags=('TOO_VERBOSE',),provenance='PROJECT_SYNTHETIC',target=None):
    return LanguageSample(sample_id='review-'+str(n),review_target=target or 'synthetic-turn-'+str(n),mode='CASUAL',context='A project-owned casual contrast case',candidate_response='First, I will summarize your requirements and propose a trial period.',human_judgment='REJECTED',exact_feedback='Project fixture: too much procedural meta-talk.',reason_tags=tags,provenance=provenance,observed_at_us=app.clock.utc_now_us())


def record(app,n,**kw):
    r=app.runtime
    service=LanguageService(r.store,r.authority)
    rid=service.record(sample(app,n,**kw),scope='project-work',entity_id='project-user',privacy='PROJECT',authority=r.authority)
    return rid,service.experience(rid,r.authority)


def activate(app,eid):
    r=app.runtime;s=ExperienceService(r.store,r.authority)
    lid=s.derive_lesson(eid)
    assert all(s.test_lesson(lid).values())
    s.activate(lid,r.authority)
    return lid


def test_one_feedback_is_candidate_not_personality_overwrite(app):
    rid,eid=record(app,1)
    s=ExperienceService(app.runtime.store,app.runtime.authority)
    lid=s.derive_lesson(eid)
    assert app.runtime.store.one('lessons',lid)['state']=='CANDIDATE'
    assert expression_policy(app.runtime.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')['rule'] is None
    assert not all(s.test_lesson(lid).values())
    assert not app.runtime.store.all('self_assertions')


def test_recipient_bound_fixture_counter_does_not_override_independent_human_corpus(app):
    record(app,1,provenance='USER_PROVIDED_REVIEW')
    _,eid=record(app,2,provenance='USER_PROVIDED_REVIEW')
    learned=activate(app,eid)
    turn=app.chat('SYNTHETIC earlier local conversation',privacy='PROJECT',retain_shared_life=True,message_id='fixture-local-counter')
    r=app.runtime;service=LanguageService(r.store,r.authority)
    counter=sample(app,3,tags=('TOO_TERSE',),target=turn['exchange_record_id']).model_copy(
        update={'candidate_response':turn['text']})
    service.record(counter,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=r.authority,
        exchange_record_id=turn['exchange_record_id'])
    view=expression_policy(r.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL',
        audience=('project-user',None))
    assert view['lesson_id']==learned and view['evidence_level']=='USER_PROVIDED_REVIEW'


def test_feedback_experience_learning_restart_context_and_counterexample(app):
    record(app,1);rid,eid=record(app,2);lid=activate(app,eid)
    home=app.home;clock=app.clock;identity=app.runtime.identity_id
    app.close()
    with LifeApplication(home,clock=clock) as later:
        assert later.runtime.identity_id==identity
        view=context(later.runtime.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')
        assert view['policy']['lesson_id']==lid
        assert view['examples_are_not_autobiography'] and not view['human_naturalness_qualified']
        assert expression_policy(later.runtime.store,scope='project-work',privacy=('PROJECT',),mode='TECHNICAL')['rule'] is None
        record(later,3,tags=('TOO_TERSE',))
        assert expression_policy(later.runtime.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')['rule'] is None
        s=ExperienceService(later.runtime.store,later.runtime.authority);s.suspend(lid,later.runtime.authority)
        assert later.runtime.store.one('lessons',lid)['state']=='SUSPENDED'


def test_duplicate_review_and_derived_same_target_do_not_inflate(app):
    rid,eid=record(app,1,target='same')
    assert record(app,1,target='same')==(rid,eid)
    record(app,2,target='same')
    from nana_core.continuity.lived_language import learnable
    assert not learnable(app.runtime.store,'project-work',('PROJECT',))['eligible']
    assert len(app.runtime.store.all('experiences'))==2


def test_synthetic_cannot_pad_human_threshold_or_bypass_privacy(app):
    record(app,1,provenance='USER_PROVIDED_REVIEW');record(app,2)
    from nana_core.continuity.lived_language import learnable
    assert not learnable(app.runtime.store,'project-work',('PROJECT',))['eligible']
    assert not context(app.runtime.store,scope='project-work',privacy=('PUBLIC',),mode='CASUAL')['examples']


def test_delete_feedback_invalidates_derived_lesson(app):
    rid,eid=record(app,1);record(app,2);lid=activate(app,eid)
    from nana_core.continuity.records import RecordService
    root=RecordService(app.runtime.store).support(rid)[0]
    app.forget(root)
    assert expression_policy(app.runtime.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')['rule'] is None


def test_synthetic_counterexample_cannot_overrule_human_feedback(app):
    from nana_core.continuity.lived_language import learnable
    record(app,1,provenance='USER_PROVIDED_REVIEW')
    record(app,2,provenance='USER_PROVIDED_REVIEW')
    record(app,3,tags=('TOO_TERSE',),provenance='PROJECT_SYNTHETIC')
    result=learnable(app.runtime.store,'project-work',('PROJECT',))
    assert result['eligible'] and result['evidence_level']=='USER_PROVIDED_REVIEW'
    record(app,4,tags=('TOO_TERSE',),provenance='USER_PROVIDED_REVIEW')
    assert not learnable(app.runtime.store,'project-work',('PROJECT',))['eligible']


def test_human_counterexample_still_blocks_synthetic_hypothesis(app):
    from nana_core.continuity.lived_language import learnable
    record(app,1);record(app,2)
    assert learnable(app.runtime.store,'project-work',('PROJECT',))['eligible']
    record(app,3,tags=('TOO_TERSE',),provenance='USER_PROVIDED_REVIEW')
    assert not learnable(app.runtime.store,'project-work',('PROJECT',))['eligible']


def test_human_review_cannot_requalify_a_synthetic_lesson(app):
    record(app,1);_,synthetic_experience=record(app,2);synthetic_lesson=activate(app,synthetic_experience)
    record(app,3,provenance='USER_PROVIDED_REVIEW')
    _,human_experience=record(app,4,provenance='USER_PROVIDED_REVIEW')
    before=expression_policy(app.runtime.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')
    assert before['rule'] is None
    human_lesson=activate(app,human_experience)
    after=expression_policy(app.runtime.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')
    assert after['lesson_id']==human_lesson and after['lesson_id']!=synthetic_lesson


def test_unreviewed_example_is_not_a_human_counterexample(app):
    from nana_core.continuity.lived_language import learnable
    record(app,1,provenance='USER_PROVIDED_REVIEW')
    record(app,2,provenance='USER_PROVIDED_REVIEW')
    draft=sample(app,3,tags=('TOO_TERSE',),provenance='USER_PROVIDED_REVIEW').model_copy(update={'human_judgment':'UNREVIEWED'})
    r=app.runtime
    LanguageService(r.store,r.authority).record(draft,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=r.authority)
    assert learnable(r.store,'project-work',('PROJECT',))['eligible']


@pytest.mark.parametrize('later_fixtures',[0,40])
def test_one_human_review_is_not_outvoted_by_many_fixture_reviews(app,later_fixtures):
    from nana_core.continuity.lived_language import learnable
    record(app,1);record(app,2);record(app,3)
    record(app,4,provenance='USER_PROVIDED_REVIEW')
    for n in range(later_fixtures):record(app,100+n)
    import time,json
    writes=app.runtime.store.db.total_changes;wall=time.perf_counter();cpu=time.process_time()
    result=learnable(app.runtime.store,'project-work',('PROJECT',))
    print(json.dumps({'measurement':'synthetic_language_population_window','newer_fixture_reviews':later_fixtures,
        'evidence_level':result['evidence_level'],'eligible':result['eligible'],'wall_seconds':time.perf_counter()-wall,
        'cpu_seconds':time.process_time()-cpu,'writes':app.runtime.store.db.total_changes-writes,'provider_requests':len(app.runtime.store.all('cognitive_requests'))}))
    assert app.runtime.store.db.total_changes==writes
    assert result['evidence_level']=='USER_PROVIDED_REVIEW' and not result['eligible']


@pytest.mark.parametrize('human_case',['counter','qualified'])
def test_fixture_volume_cannot_erase_a_human_counterexample_or_overrule_human_qualification(app,human_case):
    from nana_core.continuity.lived_language import learnable
    if human_case=='counter':
        record(app,1,tags=('TOO_TERSE',),provenance='USER_PROVIDED_REVIEW')
    else:
        record(app,1,provenance='USER_PROVIDED_REVIEW');record(app,2,provenance='USER_PROVIDED_REVIEW')
    for n in range(40):record(app,100+n,tags=('TOO_VERBOSE',) if human_case=='counter' else ('TOO_TERSE',))
    result=learnable(app.runtime.store,'project-work',('PROJECT',))
    assert result['evidence_level']=='USER_PROVIDED_REVIEW'
    assert result['eligible']==(human_case=='qualified')


@pytest.mark.parametrize('crowding',['scope','privacy'])
def test_unrelated_active_expression_lessons_do_not_hide_an_eligible_local_lesson(app,crowding):
    record(app,1);_,eid=record(app,2);local=activate(app,eid)
    r=app.runtime;language=LanguageService(r.store,r.authority)
    for n in range(17):
        review=language.record(sample(app,100+n),scope='another-project' if crowding=='scope' else 'project-work',
            entity_id='project-user',privacy='PERSONAL' if crowding=='privacy' else 'PROJECT',authority=r.authority)
        experience=language.experience(review,r.authority)
        if n>=1:activate(app,experience)
    before=r.store.snapshot();writes=r.store.db.total_changes
    policy=expression_policy(r.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')
    assert policy['lesson_id']==local
    assert all(r.store.one('continuity_records',rid)['scope']=='project-work' and r.store.one('continuity_records',rid)['privacy_class']=='PROJECT' for rid in policy['source_record_ids'])
    assert r.store.snapshot()==before and r.store.db.total_changes==writes


def test_unreviewed_volume_does_not_hide_prior_reviewed_human_counterexample(app):
    from nana_core.continuity.lived_language import learnable
    record(app,1,tags=('TOO_TERSE',),provenance='USER_PROVIDED_REVIEW')
    service=LanguageService(app.runtime.store,app.runtime.authority)
    for n in range(40):
        draft=sample(app,100+n,provenance='USER_PROVIDED_REVIEW').model_copy(update={'human_judgment':'UNREVIEWED'})
        service.record(draft,scope='project-work',entity_id='project-user',privacy='PROJECT',authority=app.runtime.authority)
        record(app,200+n)
    result=learnable(app.runtime.store,'project-work',('PROJECT',))
    assert result['evidence_level']=='USER_PROVIDED_REVIEW' and not result['eligible']


def test_active_human_expression_policy_projects_only_its_own_evidence_population(app):
    record(app,1,provenance='USER_PROVIDED_REVIEW');_,eid=record(app,2,provenance='USER_PROVIDED_REVIEW')
    lid=activate(app,eid)
    for n in range(40):record(app,100+n,tags=('TOO_TERSE',))
    view=context(app.runtime.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')
    assert view['policy']['lesson_id']==lid and view['policy']['evidence_level']=='USER_PROVIDED_REVIEW'
    assert view['examples'] and all(e['provenance']=='USER_PROVIDED_REVIEW' for e in view['examples'])
    assert not view['human_naturalness_qualified']


def test_normal_dialogue_retains_human_policy_after_dense_synthetic_feedback(tmp_path):
    import json
    from .conftest import initialize
    from tests.independent_life.test_dialogue import relay
    from nana_core.presence.authority import VirtualClock
    home=tmp_path/'home';initialize(home);seen=[]
    def render(request):
        blocks=json.loads(request['context_json'])['blocks']
        policies=[json.loads(b['data_json'])['policy'] for b in blocks if b['kind']=='LIVED_LANGUAGE']
        examples=[e for b in blocks if b['kind']=='LANGUAGE_EXAMPLES' for e in json.loads(b['data_json'])['examples']]
        seen.append((policies,examples))
        correct=bool(policies and policies[0].get('evidence_level')=='USER_PROVIDED_REVIEW')
        if correct:assert all(e['provenance']=='USER_PROVIDED_REVIEW' for e in examples)
        return 'SYNTHETIC original human-reviewed method' if correct else 'SYNTHETIC lost human-reviewed method'
    with relay(home,'CHAT',renderer=render,context_limit=65536) as (router,requests),LifeApplication(home,clock=VirtualClock(),router=router) as app:
        app.pause();record(app,1,provenance='USER_PROVIDED_REVIEW');_,eid=record(app,2,provenance='USER_PROVIDED_REVIEW');lid=activate(app,eid)
        for n in range(40):record(app,100+n,tags=('TOO_TERSE',))
        answer=app.chat('SYNTHETIC a different casual conversation',privacy='PROJECT',message_id='human-policy-after-fixtures')
        assert answer['text']=='SYNTHETIC original human-reviewed method'
        assert answer['mode']=='CHAT' and len(requests)==2 and [r['cognitive_role'] for r in requests]==['INTERPRET','SOCIAL']
        assert seen and seen[0][0][0]['lesson_id']==lid
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        print(json.dumps({'measurement':'synthetic_original_dialogue_population','roles':[r['cognitive_role'] for r in requests],
            'policy_evidence_level':seen[0][0][0]['evidence_level'],'projected_example_count':len(seen[0][1]),'human_naturalness':'NOT_RUN','real_provider_calls':0}))
