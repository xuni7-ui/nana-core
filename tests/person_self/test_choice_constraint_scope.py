"""A constraint on an unchosen alternative is not a ban on the chosen life option."""
import pytest

from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue,LearningValue,ShareAssessment
from nana_core.continuity.project_work.service import capture
from .conftest import initialize
from .test_inner_communication import seed


@pytest.mark.parametrize('options,share,value,load,expected',[
    (('CREATE','SOCIALIZE'),ShareAssessment(user_preference='DECLINED'),None,'LOW','CREATE'),
    (('CREATE','SOCIALIZE'),ShareAssessment(relational_relevance='LOW',affect_relevance='LOW'),None,'LOW','CREATE'),
    (('CREATE','LEARN'),None,LearningValue(goal_value='HIGH',future_reuse='HIGH',risk='HIGH'),'LOW','CREATE'),
    (('CREATE','LEARN'),None,LearningValue(goal_value='HIGH',future_reuse='HIGH',time_compute_cost='HEAVY'),'HIGH','CREATE'),
    (('SOCIALIZE','CREATE'),ShareAssessment(user_preference='DECLINED'),None,'LOW','STAY_SILENT'),
    (('LEARN','CREATE'),None,LearningValue(goal_value='HIGH',future_reuse='HIGH',risk='HIGH'),'LOW','REST'),
],ids=['creative-not-declined-contact','creative-not-low-social-value','creative-not-learning-risk',
       'light-creative-not-heavy-learning','chosen-contact-still-declined','chosen-learning-still-risk-reviewed'])
def test_unchosen_social_or_learning_constraints_do_not_veto_creation(tmp_path,options,share,value,load,expected):
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();seed(app);r=app.runtime
        cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CREATIVE_INTEREST',topic_key='own-curiosity',
            possible_behaviors=options,share_assessment=share,learning_value=value,cognitive_load=load)
        mid=capture(r,'scope-choice',cue.model_dump(mode='json'),predicate='concern.scope-choice')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.scope-choice',kind='WAKE',origin='SELF_WAKE',
            entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        cycle=r.subject.run(event)
        assert cycle.intention.behavior==expected
        if load=='HIGH':assert any(m.source=='REST' for m in cycle.motivations)
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')
