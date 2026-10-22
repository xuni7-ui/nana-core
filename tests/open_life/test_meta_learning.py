import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.open_life.meta_learning import propose,select
from nana_core.continuity.open_agency.learning import LearningService,LearningProblem
from nana_core.continuity.learning import ExperienceService
from nana_core.continuity.records import RecordService
from nana_core.continuity.memory import MemoryService
from tests.open_autonomy.test_learning import number_learning,start_learning
from tests.open_autonomy.helpers import fresh

def test_actual_trial_meta_lesson_changes_later_hypothesis_not_grader(tmp_path):
    with fresh(tmp_path/'s.db') as r:
        spec=number_learning();service=LearningService(r.store,r.authority,(spec,),privacy_classes=('PERSONAL',),scopes=('lab',));r.work.open_learning=service
        start_learning(r,spec)
        method=r.store.all('lessons')[0];lid=propose(r.store,method['lesson_id'],authority=r.authority);exp=ExperienceService(r.store,r.authority)
        later=spec.model_copy(update={'learning_key':'learn.later','hypotheses':('NAIVE_SUM','NUMERIC_SUM')})
        p=LearningProblem.from_spec(later)
        assert select(r.store,p,scope='lab',privacy=('PERSONAL',))==(None,None)
        assert all(exp.test_lesson(lid).values());exp.activate(lid,r.authority)
        assert select(r.store,p,scope='lab',privacy=('PERSONAL',))[0]=='NUMERIC_SUM'
        # A new original G job actually consumes the strategy. Its independent
        # heldout and transfer still run; no expected answers enter proposer.
        service.specs[later.learning_key]=later
        start_learning(r,later,'later')
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1").fetchone()
        body=RecordService(r.store).read(job['record_id'])['payload']
        assert body['selected_method']=='NUMERIC_SUM' and body['learning_strategy_record_id']
        assert body['results']['EVALUATE']['all_passed'] and body['results']['TRANSFER']['all_passed']
        assert not r.store.all('grants') and not r.store.all('actions')
        exp.suspend(lid,r.authority)
        assert select(r.store,p,scope='lab',privacy=('PERSONAL',))==(None,None)
        source=RecordService(r.store).support(method['record_id'])[0]
        MemoryService(r.store,r.authority).forget(source,r.authority)
        with pytest.raises(CoreError):propose(r.store,method['lesson_id'],authority=r.authority)
