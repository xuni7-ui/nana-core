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


def test_one_human_review_is_not_outvoted_by_many_fixture_reviews(app):
    from nana_core.continuity.lived_language import learnable
    record(app,1);record(app,2);record(app,3)
    record(app,4,provenance='USER_PROVIDED_REVIEW')
    result=learnable(app.runtime.store,'project-work',('PROJECT',))
    assert result['evidence_level']=='USER_PROVIDED_REVIEW' and not result['eligible']
