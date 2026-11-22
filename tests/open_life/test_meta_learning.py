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


def test_other_domains_do_not_displace_a_verified_learning_strategy_before_later_g(tmp_path):
    """The original learning-policy lesson must reach its existing G consumer."""
    from nana_core.presence.runtime import NanaRuntime
    path=tmp_path/'populated'/'self.db'
    with fresh(path) as r:
        spec=number_learning();service=LearningService(r.store,r.authority,(spec,),privacy_classes=('PERSONAL',),scopes=('lab',))
        r.work.open_learning=service;exp=ExperienceService(r.store,r.authority)
        def qualified(current,key):
            service.specs[current.learning_key]=current;start_learning(r,current,key)
            method=r.store.db.execute('SELECT * FROM lessons WHERE task_class=? ORDER BY rowid DESC LIMIT 1',(current.domain,)).fetchone()
            assert method and method['state']=='ACTIVE'
            lid=propose(r.store,method['lesson_id'],authority=r.authority)
            assert all(exp.test_lesson(lid).values());exp.activate(lid,r.authority)
            return lid
        lid=qualified(spec,'original-policy')
        from nana_core.continuity.open_agency.learning import LearningCase
        later=spec.model_copy(update={'learning_key':'learn.future','hypotheses':('NAIVE_SUM','NUMERIC_SUM'),
            'practice':(LearningCase(case_id='future-practice',context='garden',data=[7.25,1.5],expected=8.75),),
            'evaluation':(LearningCase(case_id='future-evaluation',context='garden',data=[4.125,2.5],expected=6.625),),
            'transfer':(LearningCase(case_id='future-transfer',context='music',data=[.4,.35],expected=.75),)})
        assert select(r.store,LearningProblem.from_spec(later),scope='lab',privacy=('PERSONAL',))[0]=='NUMERIC_SUM'
        # Genuine original G trials and qualified meta-lessons, not fabricated
        # ACTIVE rows. These unrelated domains merely fill the old global cap.
        for i in range(8):qualified(spec.model_copy(update={'learning_key':'learn.unrelated'+str(i),'domain':'unrelated'+str(i)}),'unrelated-'+str(i))
        config,clock,identity=r.config,r.clock,r.identity_id
    with NanaRuntime(path,config,clock=clock) as r:
        assert r.identity_id==identity
        service=LearningService(r.store,r.authority,(later,),privacy_classes=('PERSONAL',),scopes=('lab',));r.work.open_learning=service
        import time
        problem=LearningProblem.from_spec(later)
        assert select(r.store,problem,scope='other-scope',privacy=('PERSONAL',))==(None,None)
        assert select(r.store,problem,scope='lab',privacy=('PUBLIC',))==(None,None)
        assert select(r.store,problem,scope='lab',privacy=())==(None,None)
        before=r.store.db.total_changes;started=time.perf_counter();cpu=time.process_time()
        method,record=select(r.store,problem,scope='lab',privacy=('PERSONAL',))
        selection_seconds=time.perf_counter()-started;selection_cpu=time.process_time()-cpu
        assert r.store.db.total_changes==before
        start_learning(r,later,'future-policy-use')
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1").fetchone()
        body=RecordService(r.store).read(job['record_id'])['payload']
        import json
        model_calls=sum(r.store.db.execute('SELECT count(*) FROM '+table).fetchone()[0]
            for table in ('cognitive_requests','runtime_cognition_calls')
            if r.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone())
        print(json.dumps({'measurement':'original_meta_policy_after8_other_domains','selected_by_policy':method,
            'later_job_state':job['state'],'later_g_hypothesis':body.get('selected_method'),
            'original_policy_record_consumed':body.get('learning_strategy_record_id')==r.store.one('lessons',lid)['record_id'],
            'independent_evaluation':body.get('results',{}).get('EVALUATE',{}).get('all_passed'),
            'independent_transfer':body.get('results',{}).get('TRANSFER',{}).get('all_passed'),
            'model_calls':model_calls,'selector_seconds':selection_seconds,'selector_cpu_seconds':selection_cpu,'selector_write_rows':0}))
        assert method=='NUMERIC_SUM' and record==r.store.one('lessons',lid)['record_id']
        assert job['state']=='DONE' and body['selected_method']=='NUMERIC_SUM'
        assert body['learning_strategy_record_id']==record
        assert body['results']['EVALUATE']['all_passed'] and body['results']['TRANSFER']['all_passed']
        assert model_calls==0 and not r.store.all('actions')
        source=RecordService(r.store).support(record)[0];MemoryService(r.store,r.authority).forget(source,r.authority)
        assert select(r.store,LearningProblem.from_spec(later),scope='lab',privacy=('PERSONAL',))==(None,None)
        assert not RecordService(r.store).current_support(r.store.one('lessons',body['lesson_id'])['record_id'])


@pytest.mark.parametrize('same_method', [False, True])
def test_later_meta_strategy_has_its_own_provenance_after_real_proposer_use(tmp_path, same_method):
    import json

    from nana_core.continuity.context import ContextPolicy
    from nana_core.continuity.open_agency.learning import LearningCase
    from nana_core.continuity.world_loop.cognition import CognitionSession
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.world_loop.ports import CognitionLearningProposer
    from tests.open_autonomy.helpers import capture
    from tests.open_autonomy.test_learning import language_learning

    with fresh(tmp_path / 'self.db', schema_target=13) as runtime, provider_harness() as (transport, calls):
        original = number_learning()
        service = LearningService(runtime.store, runtime.authority, (original,), privacy_classes=('PERSONAL',), scopes=('lab',))
        runtime.work.open_learning = service
        start_learning(runtime, original, 'first-numeric')
        records = RecordService(runtime.store)
        method = runtime.store.all('lessons')[0]
        strategy_id = propose(runtime.store, method['lesson_id'], authority=runtime.authority)
        experience = ExperienceService(runtime.store, runtime.authority)
        assert all(experience.test_lesson(strategy_id).values())
        experience.activate(strategy_id, runtime.authority)
        strategy_record = runtime.store.one('lessons', strategy_id)['record_id']

        prior = (original.model_copy(update={'learning_key': 'learn.unrelated-numbers', 'domain': 'inventory'})
                 if same_method else language_learning())
        prior_provider_source = capture(runtime, 'prior-provider-only', 'Synthetic context exclusive to the previous proposal', privacy='PUBLIC')
        policy = ContextPolicy(policy_id='meta-provenance', allowed_scopes=('lab',), readable_privacy=('PUBLIC', 'PERSONAL'))
        proposer = CognitionLearningProposer(CognitionSession(runtime, transport, policy), (prior_provider_source,))
        service.proposer = proposer
        service.specs[prior.learning_key] = prior
        start_learning(runtime, prior, 'prior-proposer-job')
        prior_job = runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1").fetchone()
        assert prior_job['state'] == 'DONE' and calls['calls'] == 1
        prior_proposal = proposer.last_record_id
        assert records.read(prior_job['record_id'])['payload']['hypothesis_source'] == prior_proposal

        future = original.model_copy(update={'learning_key': 'learn.new-recipe', 'hypotheses': ('NAIVE_SUM', 'NUMERIC_SUM'),
            'practice': (LearningCase(case_id='recipe-practice', context='recipe', data=[1.75, .625], expected=2.375),),
            'evaluation': (LearningCase(case_id='recipe-heldout', context='recipe', data=[3.125, 1.5], expected=4.625),),
            'transfer': (LearningCase(case_id='trail-transfer', context='trail distances', data=[.375, 1.125], expected=1.5),)})
        service.specs[future.learning_key] = future
        start_learning(runtime, future, 'future-meta-job')
        new_job = runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1").fetchone()
        body = records.read(new_job['record_id'])['payload']
        print(json.dumps({'same_method': same_method, 'future_state': new_job['state'], 'future_stage': body['stage'],
            'attached_previous_proposal': body.get('hypothesis_source') == prior_proposal, 'loopback_calls_total': calls['calls']}))
        assert new_job['state'] == 'DONE' and body['selected_method'] == 'NUMERIC_SUM'
        assert body['learning_strategy_record_id'] == strategy_record and not body.get('hypothesis_source')
        assert body['results']['EVALUATE']['all_passed'] and body['results']['TRANSFER']['all_passed']
        assert calls['calls'] == 1 and not runtime.store.all('actions')
        MemoryService(runtime.store, runtime.authority).forget(prior_provider_source, runtime.authority)
        assert not records.current_support(prior_proposal)
        assert records.current_support(runtime.store.one('lessons', body['lesson_id'])['record_id'])
