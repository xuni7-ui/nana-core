from nana_core.continuity.open_agency.learning import LearningService,LearningProblem
from nana_core.continuity.open_agency.practice import compare_practice
from nana_core.continuity.records import RecordService
from nana_core.contracts import CoreError
from tests.open_autonomy.helpers import fresh,objective,configure,cue,send,advance
from tests.open_autonomy.test_learning import number_learning,start_learning
import pytest


def test_practice_competition_improves_wrong_nominee_then_independent_transfer_and_use(tmp_path):
    base=number_learning().model_copy(update={'hypotheses':('NAIVE_SUM','NUMERIC_SUM')})
    for selection in ('PROPOSER_ONLY','PRACTICE_COMPARE'):
        spec=base.model_copy(update={'hypothesis_policy':selection})
        with fresh(tmp_path/selection/'self.db') as r:
            service=LearningService(r.store,r.authority,(spec,),privacy_classes=('PERSONAL',),scopes=('lab',));r.work.open_learning=service
            start_learning(r,spec)
            job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone();body=RecordService(r.store).read(job['record_id'])['payload']
            if selection=='PROPOSER_ONLY':
                assert job['state']=='BLOCKED' and not r.store.all('lessons')
                assert body['selected_method']=='NAIVE_SUM'
                continue
            assert job['state']=='DONE' and body['results']['BASELINE']['passed']==0
            assert body['results']['EVALUATE']['all_passed'] and body['results']['TRANSFER']['all_passed']
            assert body['selected_method']=='NUMERIC_SUM' and body['practice_competition']['nominee']=='NAIVE_SUM'
            assert service.strategy('numbers','lab')[1]=='NUMERIC_SUM'
            obj=objective('precision.transfer',method='NAIVE_SUM',expected=10.75)
            port=configure(r,tmp_path/selection/'w'/'transfer.fixture.json',(obj,));r.work.agency.learning=service
            port.seed_observation(obj.operators[0].resource,[4.25,6.5]);send(r,'independent-transfer',(cue(r,obj),));r.step();advance(r,5)
            assert r.store.all('goals')[0]['state']=='COMPLETED'
            assert port._load()['resources'][obj.operators[-1].resource]['data']==10.75


def test_practice_port_has_no_heldout_answers_and_cannot_self_qualify(tmp_path):
    spec=number_learning().model_copy(update={'hypotheses':('NAIVE_SUM','NUMERIC_SUM'),'hypothesis_policy':'PRACTICE_COMPARE'})
    problem=LearningProblem.from_spec(spec)
    assert not hasattr(problem,'evaluation') and not hasattr(problem,'transfer')
    with pytest.raises(CoreError):compare_practice(spec,preferred='NAIVE_SUM')
    # Passing practice alone must not admit a method that fails new contexts.
    broken=spec.model_copy(update={'hypotheses':('NAIVE_SUM',),'practice':tuple(c.model_copy(update={'data':[1,2],'expected':3}) for c in spec.practice)})
    with fresh(tmp_path/'self.db') as r:
        service=LearningService(r.store,r.authority,(broken,),privacy_classes=('PERSONAL',),scopes=('lab',));r.work.open_learning=service
        start_learning(r,broken)
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone();body=RecordService(r.store).read(job['record_id'])['payload']
        assert body['practice_competition']['trials'][0]['passed']==1
        assert job['state']=='BLOCKED' and not r.store.all('lessons')
