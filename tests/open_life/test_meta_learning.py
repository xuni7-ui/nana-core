import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.open_life.meta_learning import propose,recent_transfer_counterexample,select
from nana_core.continuity.open_agency.learning import LearningService,LearningProblem,LearningCase
from nana_core.continuity.learning import ExperienceService
from nana_core.continuity.records import RecordService
from nana_core.continuity.memory import MemoryService
from tests.open_autonomy.test_learning import number_learning,start_learning
from tests.open_autonomy.helpers import capture,fresh,send

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


@pytest.mark.parametrize('reviewed', [False, True])
def test_runtime_owned_reflection_can_propose_a_strategy_for_independent_review(tmp_path, reviewed):
    from nana_core.presence.runtime import NanaRuntime

    path = tmp_path/'self.db'
    initial = number_learning()
    future = initial.model_copy(update={
        'learning_key': 'learn.after-reflection',
        'hypotheses': ('NAIVE_SUM', 'NUMERIC_SUM'),
        'practice': (LearningCase(case_id='novel-practice', context='recipe', data=[1.75, 0.625], expected=2.375),),
        'evaluation': (LearningCase(case_id='novel-heldout', context='recipe', data=[3.125, 1.5], expected=4.625),),
        'transfer': (LearningCase(case_id='novel-transfer', context='trail', data=[0.375, 1.125], expected=1.5),),
    })
    problem = LearningProblem.from_spec(future)
    with fresh(path, schema_target=13) as r:
        r.work.configure_open_learning((initial,))
        source = start_learning(r, initial)
        method = r.store.all('lessons')[0]
        experience_id = method['experience_id']
        send(r, 'learned-method-reflection', (source,), reflection_experience_id=experience_id)
        cycle = r.step()['cycle']
        assert cycle.intention.kind == 'REFLECTION'
        intention = r.store.one('subject_intentions', cycle.intention_id)
        assert intention['state'] == 'COMPLETED'
        reflection = r.store.db.execute('SELECT * FROM subject_reflections WHERE experience_id=?', (experience_id,)).fetchone()
        assert reflection and reflection['state'] == 'CANDIDATE'
        strategy = reflection['lesson_id']
        assert strategy and strategy != method['lesson_id']
        candidate = r.store.one('lessons', strategy)
        assert candidate['state'] == 'CANDIDATE'
        parents = {edge[0] for edge in r.store.db.execute(
            "SELECT parent_id FROM record_dependencies WHERE record_id=? AND parent_kind='RECORD' AND relation_kind='SUPPORT'",
            (candidate['record_id'],),
        )}
        assert {intention['record_id'], reflection['record_id']} <= parents
        assert select(r.store, problem, scope='lab', privacy=('PERSONAL',)) == (None, None)
        config, clock, identity = r.config, r.clock, r.identity_id

    with NanaRuntime(path, config, clock=clock) as r:
        assert r.identity_id == identity
        send(r, 'another-reflection', (source,), reflection_experience_id=experience_id)
        assert r.step()['cycle'].intention.kind == 'REFLECTION'
        assert len([row for row in r.store.all('lessons') if row['task_class']=='learning.strategy']) == 1
        expected_method = 'NAIVE_SUM'
        expected_strategy = None
        if reviewed:
            r.subject.reflect(experience_id, authority=r.authority, apply=True)
            expected_method = 'NUMERIC_SUM'
            expected_strategy = r.store.one('lessons', strategy)['record_id']
            assert select(r.store, problem, scope='lab', privacy=('PERSONAL',)) == (expected_method, expected_strategy)
        r.work.configure_open_learning((future,))
        start_learning(r, future, 'later-unseen-method')
        job = r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1").fetchone()
        learned = RecordService(r.store).read(job['record_id'])['payload']
        assert job['state'] == ('DONE' if reviewed else 'BLOCKED')
        assert learned['selected_method'] == expected_method
        assert learned.get('learning_strategy_record_id') == expected_strategy
        assert learned['results']['EVALUATE']['all_passed'] is reviewed
        assert learned['results']['TRANSFER']['all_passed'] is reviewed
        assert not r.store.all('actions') and not r.store.all('cognitive_requests')
        print(f'Original G after restart: reviewed={reviewed}, method={expected_method}, state={job["state"]}, real_model_calls=0')
        MemoryService(r.store, r.authority).forget(source, r.authority)
        assert select(r.store, problem, scope='lab', privacy=('PERSONAL',)) == (None, None)


@pytest.mark.parametrize('state, change', [
    ('CANDIDATE', 'reason'), ('ACTIVE', 'reason'), ('ACTIVE', 'interrupted'),
    ('ACTIVE', 'experiment'), ('SUSPENDED', 'reason'), ('RETIRED', 'reason'),
])
def test_new_reflection_can_renew_a_strategy_after_only_its_reason_is_withdrawn(tmp_path, monkeypatch, state, change):
    from nana_core.presence.runtime import NanaRuntime

    path=tmp_path/'self.db'
    initial=number_learning()
    later=initial.model_copy(update={
        'learning_key':'learn.after-renewal',
        'hypotheses':('NAIVE_SUM','NUMERIC_SUM'),
        'practice':(LearningCase(case_id='new-practice', context='recipe', data=[1.75,.625], expected=2.375),),
        'evaluation':(LearningCase(case_id='new-heldout', context='recipe', data=[3.125,1.5], expected=4.625),),
        'transfer':(LearningCase(case_id='new-transfer', context='trail', data=[.375,1.125], expected=1.5),),
    })
    problem=LearningProblem.from_spec(later)
    interrupted=change=='interrupted'
    with fresh(path, schema_target=13) as runtime:
        runtime.work.configure_open_learning((initial,))
        start_learning(runtime,initial)
        method=runtime.store.all('lessons')[0]
        old_reason=capture(runtime,'old-reflection-reason','SYNTHETIC first experience prompting reflection')
        send(runtime,'first-reflection-only-source',(old_reason,),reflection_experience_id=method['experience_id'])
        assert runtime.step()['cycle'].intention.kind=='REFLECTION'
        reflection=runtime.store.all('subject_reflections')[0]
        strategy_id=reflection['lesson_id']
        if state!='CANDIDATE':
            runtime.subject.reflect(method['experience_id'], authority=runtime.authority,apply=True)
        if state in {'SUSPENDED','RETIRED'}:
            ExperienceService(runtime.store,runtime.authority).suspend(strategy_id,runtime.authority,retire=state=='RETIRED')
        prior=runtime.store.one('lessons',strategy_id)
        assert prior['state']==state
        assert old_reason in RecordService(runtime.store).support(prior['record_id'])
        removed=old_reason
        if change=='experiment':
            removed=runtime.store.one('experiences',prior['experience_id'])['result_memory_id']
        MemoryService(runtime.store,runtime.authority).forget(removed,runtime.authority)
        assert runtime.store.one('continuity_records',prior['record_id'])['lifecycle']=='DELETED'
        assert RecordService(runtime.store).current_support(method['record_id'])
        assert select(runtime.store,problem,scope='lab',privacy=('PERSONAL',))==(None,None)
        config,clock,identity=runtime.config,runtime.clock,runtime.identity_id

    with NanaRuntime(path,config,clock=clock) as runtime:
        assert runtime.identity_id==identity
        new_reason=capture(runtime,'new-reflection-reason','SYNTHETIC later observation prompting reflection')
        queue_id=send(runtime,'new-reflection-only-source',(new_reason,),reflection_experience_id=method['experience_id'])
        if interrupted:
            transaction=runtime.store.transaction
            def stop_after_candidate(kind, *args, **kwargs):
                if kind=='subject.reflection_intention_completed':
                    raise RuntimeError('synthetic stop before reflection follow-up')
                return transaction(kind,*args,**kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(runtime.store,'transaction',stop_after_candidate)
                with pytest.raises(RuntimeError,match='synthetic stop before reflection follow-up'):
                    runtime.step()
            assert runtime.store.one('lessons',strategy_id)['state']=='CANDIDATE'
            assert runtime.store.one('subject_reflections',reflection['reflection_id'])['state']=='APPLIED'
        else:
            cycle=runtime.step()['cycle']
            assert cycle.intention.kind=='REFLECTION'
            assert runtime.store.one('subject_intentions',cycle.intention_id)['state']=='COMPLETED'

    with NanaRuntime(path,config,clock=clock) as runtime:
        assert runtime.identity_id==identity
        if interrupted:
            recovery=runtime.step()
            assert recovery['queue_id']==queue_id and recovery['reason']=='RECOVERED_SUBJECT_FOLLOWUP'
        current=runtime.store.one('lessons',strategy_id)
        if state in {'SUSPENDED','RETIRED'} or change=='experiment':
            assert current==prior and select(runtime.store,problem,scope='lab',privacy=('PERSONAL',))==(None,None)
            return
        assert runtime.store.one('subject_reflections',reflection['reflection_id'])['state']=='CANDIDATE'
        assert current['record_id']!=prior['record_id'] and current['state']=='CANDIDATE'
        assert current['experience_id']==prior['experience_id']
        assert current['tested_rule_hash'] is None and current['test_event_id'] is None
        records=RecordService(runtime.store)
        assert new_reason in records.support(current['record_id']) and old_reason not in records.support(current['record_id'])
        assert runtime.store.one('continuity_records',prior['record_id'])['lifecycle']=='DELETED'
        assert select(runtime.store,problem,scope='lab',privacy=('PERSONAL',))==(None,None)
        runtime.subject.reflect(method['experience_id'],authority=runtime.authority,apply=True)
        runtime.work.configure_open_learning((later,))
        start_learning(runtime,later,'new-task-after-reviewed-renewal')
        job=runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1").fetchone()
        result=records.read(job['record_id'])['payload']
        assert job['state']=='DONE' and result['selected_method']=='NUMERIC_SUM'
        assert result['learning_strategy_record_id']==current['record_id']
        assert result['results']['EVALUATE']['all_passed'] and result['results']['TRANSFER']['all_passed']
        assert not runtime.store.all('cognitive_requests') and not runtime.store.all('actions')
        MemoryService(runtime.store,runtime.authority).forget(new_reason,runtime.authority)
        assert not records.current_support(job['record_id'])
        assert select(runtime.store,problem,scope='lab',privacy=('PERSONAL',))==(None,None)
        print(f'prior={state}, interrupted={interrupted}, renewed after restart and independently reviewed, real_model_calls=0')


def test_meta_lesson_requires_transfer_of_its_own_practice_selection(tmp_path):
    from nana_core.continuity.open_agency.learning import LearningSpec

    with fresh(tmp_path/'self.db', schema_target=13) as runtime:
        spec=LearningSpec(learning_key='learn.normalize',domain='labels',baseline_method='IDENTITY',
            hypotheses=('CASEFOLD','NFKC_CASEFOLD'),
            practice=(LearningCase(case_id='practice',context='labels',data='ALPHA',expected='alpha'),),
            evaluation=(LearningCase(case_id='heldout',context='labels',data='BETA',expected='beta'),),
            transfer=(LearningCase(case_id='transfer',context='catalog',data='ＧＡＭＭＡ',expected='gamma'),))

        class Proposer:
            def propose_method(self,problem):
                assert not hasattr(problem,'transfer')
                return 'NFKC_CASEFOLD'

        service=LearningService(runtime.store,runtime.authority,(spec,),privacy_classes=('PERSONAL',),scopes=('lab',),
            proposer=Proposer())
        runtime.work.open_learning=service
        source=start_learning(runtime,spec,'normalize-labels')
        method=runtime.store.all('lessons')[0]
        assert method['state']=='ACTIVE' and service.strategy('labels','lab')[1]=='NFKC_CASEFOLD'
        before=len(runtime.store.all('experiences'))
        with pytest.raises(CoreError,match='META_SELECTION_NOT_TRANSFERRED'):
            propose(runtime.store,method['lesson_id'],authority=runtime.authority)
        assert len(runtime.store.all('experiences'))==before
        assert len(runtime.store.all('lessons'))==1
        send(runtime, 'reflect-failed-meta-transfer', (source,), reflection_experience_id=method['experience_id'])
        cycle=runtime.step()['cycle']
        assert cycle.intention.kind=='REFLECTION'
        assert runtime.store.one('subject_intentions',cycle.intention_id)['state']=='COMPLETED'
        reflection=runtime.store.db.execute('SELECT lesson_id FROM subject_reflections WHERE experience_id=?',(method['experience_id'],)).fetchone()
        assert reflection and not reflection['lesson_id'] and len(runtime.store.all('lessons'))==1
        assert select(runtime.store,LearningProblem.from_spec(spec),scope='lab',privacy=('PERSONAL',))==(None,None)
        assert service.strategy('labels','lab')[1]=='NFKC_CASEFOLD'
        assert not runtime.store.all('actions')


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


@pytest.mark.parametrize('compatible_available',[True,False])
def test_verified_meta_strategy_can_handle_a_changed_candidate_population(tmp_path,compatible_available):
    import json
    from nana_core.continuity.open_agency.learning import LearningCase

    with fresh(tmp_path/'self.db') as runtime:
        original=number_learning()
        service=LearningService(runtime.store,runtime.authority,(original,),privacy_classes=('PERSONAL',),scopes=('lab',))
        runtime.work.open_learning=service
        start_learning(runtime,original,'meta-training')
        original_lesson=runtime.store.all('lessons')[0]
        strategy=propose(runtime.store,original_lesson['lesson_id'],authority=runtime.authority)
        experience=ExperienceService(runtime.store,runtime.authority)
        assert all(experience.test_lesson(strategy).values())
        experience.activate(strategy,runtime.authority)
        record=runtime.store.one('lessons',strategy)['record_id']
        future=original.model_copy(update={
            'learning_key':'learn.changed-methods',
            'hypotheses':('CASEFOLD','NUMERIC_SUM') if compatible_available else ('NUMERIC_SUM',),
            'practice':(LearningCase(case_id='changed-practice',context='meal',data=[1.75,1.25],expected=3.0 if compatible_available else [1.25,1.75]),),
            'evaluation':(LearningCase(case_id='changed-heldout',context='meal',data=[2.5,2.25],expected=4.75 if compatible_available else [2.25,2.5]),),
            'transfer':(LearningCase(case_id='changed-transfer',context='drawing',data=[3.5,.625],expected=4.125 if compatible_available else [.625,3.5]),),
        })
        seen=[]
        class CurrentProposer:
            def propose_method(self,problem):
                assert isinstance(problem,LearningProblem)
                assert not hasattr(problem,'evaluation') and not hasattr(problem,'transfer')
                seen.append(problem.learning_key)
                return 'NUMERIC_SUM'
        service.proposer=CurrentProposer()
        service.specs[future.learning_key]=future
        start_learning(runtime,future,'new-strategy-conditions')
        job=runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1").fetchone()
        body=RecordService(runtime.store).read(job['record_id'])['payload']
        print(json.dumps({'compatible_available':compatible_available,'state':job['state'],'stage':body['stage'],
            'used_original_strategy':body.get('learning_strategy_record_id')==record,'proposer_calls':len(seen)}))
        if compatible_available:
            assert job['state']=='DONE' and body['learning_strategy_record_id']==record
            assert seen==[] and body['results']['EVALUATE']['all_passed'] and body['results']['TRANSFER']['all_passed']
        else:
            assert job['state']=='BLOCKED'
            event=runtime.store.db.execute("SELECT data_json FROM events WHERE kind='open.learning_parked' AND json_extract(data_json,'$.data.work_id')=?",(job['job_id'],)).fetchone()
            assert json.loads(event[0])['data']['reason']=='LEARNING_NOT_TRANSFERRED_OR_NO_IMPROVEMENT'
            assert 'learning_strategy_record_id' not in body and seen==[future.learning_key]
            assert not body['results']['EVALUATE']['all_passed'] and not body['results']['TRANSFER']['all_passed']
        assert runtime.store.one('lessons',strategy)['state']=='ACTIVE' and not runtime.store.all('actions')


def test_meta_strategy_inapplicable_on_new_transfer_is_a_known_learning_failure(tmp_path):
    import json

    from nana_core.continuity.open_agency.learning import LearningCase
    from nana_core.presence.runtime import NanaRuntime

    path = tmp_path / "self.db"
    with fresh(path) as runtime:
        original = number_learning()
        service = LearningService(
            runtime.store, runtime.authority, (original,), privacy_classes=("PERSONAL",), scopes=("lab",)
        )
        runtime.work.open_learning = service
        start_learning(runtime, original, "known-transfer-training")
        lesson = runtime.store.all("lessons")[0]
        strategy = propose(runtime.store, lesson["lesson_id"], authority=runtime.authority)
        experience = ExperienceService(runtime.store, runtime.authority)
        assert all(experience.test_lesson(strategy).values())
        experience.activate(strategy, runtime.authority)
        strategy_record = runtime.store.one("lessons", strategy)["record_id"]

        future = original.model_copy(update={
            "learning_key": "learn.mixed-source-totals",
            "baseline_method": "IDENTITY",
            "practice": (LearningCase(case_id="totals-practice", context="recipe", data=[2.5, .75], expected=3.25),),
            "evaluation": (LearningCase(case_id="totals-heldout", context="recipe", data=[3.25, 1.25], expected=4.5),),
            "transfer": (LearningCase(case_id="totals-transfer", context="receipts", data="3.25 + 2.5", expected=5.75),),
        })
        service.specs[future.learning_key] = future
        start_learning(runtime, future, "later-source-format")
        job = runtime.store.db.execute(
            "SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        body = RecordService(runtime.store).read(job["record_id"])["payload"]
        assert body["learning_strategy_record_id"] == strategy_record
        assert body["results"]["EVALUATE"]["all_passed"]
        assert body["stage"] == "TRANSFER" and job["state"] == "BLOCKED"
        event = runtime.store.db.execute(
            "SELECT data_json FROM events WHERE kind='open.learning_parked' AND json_extract(data_json,'$.data.work_id')=?",
            (job["job_id"],),
        ).fetchone()
        assert json.loads(event[0])["data"]["reason"] == "LEARNING_METHOD_INPUT_INAPPLICABLE"
        assert len(runtime.store.all("lessons")) == 2
        config, clock, identity = runtime.config, runtime.clock, runtime.identity_id

    with NanaRuntime(path, config, clock=clock) as runtime:
        assert runtime.identity_id == identity
        assert runtime.store.one("jobs", job["job_id"])["state"] == "BLOCKED"
        assert runtime.store.one("lessons", strategy)["state"] == "ACTIVE"
        problem = LearningProblem.from_spec(future)
        assert recent_transfer_counterexample(runtime.store, problem, 'NUMERIC_SUM', scope='lab',
            privacy=('PERSONAL',)) == job['record_id']
        assert recent_transfer_counterexample(runtime.store, problem, 'NUMERIC_SUM', scope='lab',
            privacy=('PUBLIC',)) is None


@pytest.mark.parametrize('hypothesis_policy', ['PROPOSER_ONLY', 'PRACTICE_COMPARE'])
def test_reviewed_transfer_counterexample_redirects_matching_future_job_after_restart(tmp_path, hypothesis_policy):
    from nana_core.continuity.open_agency.learning import LearningSpec
    from nana_core.continuity.subject.opportunities import ConcernCue
    from nana_core.presence.runtime import NanaRuntime

    path = tmp_path / 'self.db'
    training = LearningSpec(learning_key='learn.normalize', domain='labels', baseline_method='IDENTITY',
        hypotheses=('CASEFOLD', 'NFKC_CASEFOLD'),
        practice=(LearningCase(case_id='practice', context='labels', data='ALPHA', expected='alpha'),),
        evaluation=(LearningCase(case_id='heldout', context='labels', data='BETA', expected='beta'),),
        transfer=(LearningCase(case_id='transfer', context='catalog', data='GAMMA', expected='gamma'),))
    failing = training.model_copy(update={
        'learning_key':'learn.first-new-labels',
        'hypothesis_policy':hypothesis_policy,
        'practice':(LearningCase(case_id='new-practice', context='gardening', data='DELTA', expected='delta'),),
        'evaluation':(LearningCase(case_id='new-heldout', context='gardening', data='EPSILON', expected='epsilon'),),
        'transfer':(LearningCase(case_id='new-transfer', context='suppliers', data='ＺＥＴＡ', expected='zeta'),),
    })
    later = failing.model_copy(update={
        'learning_key':'learn.later-new-labels',
        'practice':(failing.practice[0].model_copy(update={'case_id':'later-practice','context':'relabeled'}),),
        'evaluation':(LearningCase(case_id='later-heldout', context='gardening', data='ETA', expected='eta'),),
        'transfer':(LearningCase(case_id='later-transfer', context='labels', data='ＴＨＥＴＡ', expected='theta'),),
    })
    dissimilar = later.model_copy(update={'learning_key':'learn.different-labels',
        'practice':(LearningCase(case_id='other-practice', context='studying', data='IOTA', expected='iota'),),
        'transfer':(LearningCase(case_id='other-transfer', context='labels', data='KAPPA', expected='kappa'),)})

    def latest(runtime):
        job = runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1").fetchone()
        return job, RecordService(runtime.store).read(job['record_id'])['payload']

    with fresh(path, schema_target=13) as runtime:
        runtime.work.configure_open_learning((training,failing))
        start_learning(runtime,training)
        method = runtime.store.all('lessons')[0]
        strategy = propose(runtime.store,method['lesson_id'],authority=runtime.authority)
        experience = ExperienceService(runtime.store,runtime.authority)
        assert all(experience.test_lesson(strategy).values())
        experience.activate(strategy,runtime.authority)
        failure_source = start_learning(runtime,failing,'new-case-absence')
        blocked, body = latest(runtime)
        assert blocked['state']=='BLOCKED' and body['selected_method']=='CASEFOLD'
        assert body['results']['EVALUATE']['all_passed'] and not body['results']['TRANSFER']['all_passed']
        config, clock, identity = runtime.config, runtime.clock, runtime.identity_id

    proposer_calls=[]
    class CurrentProposer:
        def propose_method(self, problem):
            assert isinstance(problem, LearningProblem)
            assert not hasattr(problem,'evaluation') and not hasattr(problem,'transfer')
            proposer_calls.append(problem.learning_key)
            return 'NFKC_CASEFOLD'

    with NanaRuntime(path,config,clock=clock) as runtime:
        assert runtime.identity_id==identity
        runtime.work.configure_open_learning((later,dissimilar),proposer=CurrentProposer())
        start_learning(runtime,dissimilar,'different-context')
        unrelated, body = latest(runtime)
        assert unrelated['state']=='DONE' and body['selected_method']=='CASEFOLD'
        start_learning(runtime,later,'matching-context')
        redirected, body = latest(runtime)
        assert redirected['state']=='DONE' and body['selected_method']=='NFKC_CASEFOLD'
        assert proposer_calls==[], f'The verified strategy returned to the proposer: {proposer_calls}'
        assert body['learning_strategy_record_id']==runtime.store.one('lessons',strategy)['record_id']
        if hypothesis_policy=='PRACTICE_COMPARE':
            assert [trial['method'] for trial in body['practice_competition']['trials']]==['NFKC_CASEFOLD']
        assert body['results']['EVALUATE']['all_passed'] and body['results']['TRANSFER']['all_passed']
        assert blocked['record_id'] in {edge[0] for edge in runtime.store.db.execute(
            "SELECT parent_id FROM record_dependencies WHERE record_id=? AND parent_kind='RECORD'",
            (redirected['record_id'],))}
        assert not runtime.store.all('cognitive_requests')
        assert runtime.store.one('lessons',strategy)['state']=='ACTIVE'
        MemoryService(runtime.store,runtime.authority).forget(failure_source,runtime.authority)
        assert not RecordService(runtime.store).current_support(redirected['record_id'])
        next_spec = later.model_copy(update={'learning_key':'learn.withdrawn-example'})
        runtime.work.configure_open_learning((next_spec,),proposer=CurrentProposer())
        start_learning(runtime,next_spec,'after-withdrawal')
        after, body = latest(runtime)
        assert after['state']=='BLOCKED' and body['selected_method']=='CASEFOLD'
        print(f'S10 transfer comparison: policy={hypothesis_policy}, first=BLOCKED, other_practice=CASEFOLD, '
              'matching_practice=NFKC_CASEFOLD, redirected=DONE, withdrawn=BLOCKED, proposer_calls=0, real_model_calls=0')
