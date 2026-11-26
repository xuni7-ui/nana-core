import pytest,json
from nana_core.contracts import CoreError
from nana_core.continuity.open_agency.learning import LearningService,LearningSpec,LearningCase
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.records import RecordService
from nana_core.continuity.learning import ExperienceService
from nana_core.continuity.world_loop.learning import EpisodeLearning
from .helpers import *

def number_learning():
    return LearningSpec(learning_key='learn.numbers',domain='numbers',baseline_method='NAIVE_SUM',hypotheses=('NUMERIC_SUM',),
        practice=(LearningCase(case_id='practice',context='warehouse',data=[1.25,2],expected=3.25),),
        evaluation=(LearningCase(case_id='evaluation',context='warehouse',data=[2.5,3.5],expected=6.),),
        transfer=(LearningCase(case_id='transfer',context='science',data=[.2,.3],expected=.5),))

def language_learning():
    return LearningSpec(learning_key='learn.words',domain='language',baseline_method='SPLIT_SPACE',hypotheses=('UNICODE_WORDS',),
        practice=(LearningCase(case_id='words-practice',context='captions',data='One\tTwo',expected=['One','Two']),),
        evaluation=(LearningCase(case_id='words-eval',context='captions',data='Hello\nworld',expected=['Hello','world']),),
        transfer=(LearningCase(case_id='words-transfer',context='notes',data='Ａ\u3000Ｂ',expected=['A','B']),))

def start_learning(r,spec,key='learn'):
    c=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CAPABILITY_GAP',topic_key=key,program_id=spec.learning_key,possible_behaviors=('LEARN',))
    mid=capture(r,key,c.model_dump_json(),predicate='concern.'+key)
    send(r,key,(mid,));r.drain(24)
    return mid

def test_learning_heldout_transfer_changes_actual_later_plan_and_judgment(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        spec=number_learning();ls=LearningService(r.store,r.authority,(spec,),privacy_classes=('PERSONAL',),scopes=('lab',));r.work.open_learning=ls
        start_learning(r,spec)
        assert ls.strategy('numbers','lab')[1]=='NUMERIC_SUM'
        obj=objective(method='NAIVE_SUM');p=configure(r,tmp_path/'w'/'world.fixture.json',(obj,));r.work.agency.learning=ls
        p.seed_observation(obj.operators[0].resource,[1.2,2.3]);mid=cue(r,obj)
        send(r,'after-learning',(mid,),task_class='numbers');result=r.step()
        assert result['cycle'].judgment.selected_method=='NUMERIC_SUM'
        advance(r,6);assert r.store.all('goals')[0]['state']=='COMPLETED'
        work=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone()
        data=RecordService(r.store).read(work['record_id'])['payload']
        assert data['results']['BASELINE']['passed']==0 and data['results']['TRANSFER']['all_passed']
        assert ls.monitor(data['lesson_id'],(LearningCase(case_id='regression',context='negative',data=[1,2],expected=99),),authority=r.authority)['all_passed'] is False
        assert ls.strategy('numbers','lab') is None


@pytest.mark.parametrize('evidence', ['qualification_corpus', 'relabeled_input'])
def test_strategy_revalidation_requires_unseen_distinct_inputs(tmp_path, evidence):
    spec = number_learning()
    with fresh(tmp_path/'s'/'self.db', schema_target=13) as r:
        r.work.configure_open_learning((spec,))
        start_learning(r, spec)
        lesson_id = r.store.all('lessons')[0]['lesson_id']
        assert r.work.open_learning.strategy('numbers', 'lab')[1] == 'NUMERIC_SUM'
        review = EpisodeLearning(r.store, r.authority, scopes=('lab',), privacy_classes=('PERSONAL',))

        def assess(key, data, expected):
            case = LearningCase(case_id=key, context=key, data=data, expected=expected)
            body = {'strategy_episode': {
                'episode_key': key, 'lesson_id': lesson_id, 'case': case.model_dump(mode='json'),
            }}
            source = capture(r, key, json.dumps(body))
            return source, review.assess(lesson_id, source, authority=r.authority)

        counter, _ = assess('counterexample', [0.1, 0.2], 0.3)
        MemoryService(r.store, r.authority).set_lifecycle(counter, 'SUPPRESSED', r.authority)
        if evidence == 'qualification_corpus':
            for case in (*spec.practice, *spec.evaluation, *spec.transfer):
                assess(f'replay-{case.case_id}', case.data, case.expected)
        else:
            assess('novel-a', [12.5, 13], 25.5)
            _, first = assess('renamed-novel-a', [12.5, 13], 25.5)
        writes = r.store.db.total_changes
        with pytest.raises(CoreError, match='INDEPENDENT_REVALIDATION_REQUIRED'):
            review.revalidate(lesson_id, authority=r.authority)
        assert r.store.db.total_changes == writes
        assert r.work.open_learning.strategy('numbers', 'lab') is None

        if evidence == 'qualification_corpus':
            _, first = assess('novel-a', [12.5, 13], 25.5)
        _, second = assess('novel-b', [18, 23.5], 41.5)
        assert review.revalidate(lesson_id, authority=r.authority)['state'] == 'ACTIVE'
        event = r.store.db.execute(
            "SELECT data_json FROM events WHERE kind='world.strategy_revalidated' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        assert set(json.loads(event[0])['data']['support_records']) == {
            r.store.one('strategy_assessments', assessment)['record_id'] for assessment in (first, second)
        }
        assert r.work.open_learning.strategy('numbers', 'lab')[1] == 'NUMERIC_SUM'
        assert not r.store.all('cognitive_requests')

def test_private_lessons_do_not_hide_an_earlier_project_strategy(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        original=number_learning()

        def qualify(spec,key,privacy):
            r.work.configure_open_learning((spec,))
            concern=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CAPABILITY_GAP',
                topic_key=key,program_id=spec.learning_key,possible_behaviors=('LEARN',))
            mid=capture(r,key,concern.model_dump_json(),predicate='concern.'+key,privacy=privacy)
            send(r,key,(mid,),privacy_class=privacy);r.drain(24)
            lesson=r.store.db.execute("SELECT record_id FROM lessons ORDER BY rowid DESC LIMIT 1").fetchone()
            assert lesson and RecordService(r.store).read(lesson[0])['privacy_class']==privacy
            return lesson[0]

        visible=qualify(original,'original-visible-method','PROJECT')
        reader=LearningService(r.store,r.authority,(),privacy_classes=('PROJECT',),scopes=('lab',))
        assert reader.strategy('numbers','lab')==(visible,'NUMERIC_SUM')
        for index in range(16):
            key=f'personal-method-{index}'
            qualify(original.model_copy(update={'learning_key':f'learn.{key}'}),key,'PERSONAL')
        assert len(r.store.all('lessons'))==17
        assert reader.strategy('numbers','lab')==(visible,'NUMERIC_SUM')
        source=RecordService(r.store).support(visible)[0]
        MemoryService(r.store,r.authority).forget(source,r.authority)
        assert reader.strategy('numbers','lab') is None
        assert not r.store.all('actions') and not r.store.all('grants')


def test_different_domain_and_timeout_does_not_advance_learning_cursor(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        spec=language_learning();ls=LearningService(r.store,r.authority,(spec,),privacy_classes=('PERSONAL',),scopes=('lab',));r.work.open_learning=ls
        start_learning(r,spec,'words')
        assert ls.strategy('language','lab')[1]=='UNICODE_WORDS'
        work=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone()
        assert work['state']=='DONE'
        lesson=r.store.all('lessons')[0]
        MemoryService(r.store,r.authority).forget(RecordService(r.store).support(lesson['record_id'])[0],r.authority)
        assert ls.strategy('language','lab') is None
    with fresh(tmp_path/'s2'/'self.db') as r:
        spec=number_learning()
        class Broken:
            def evaluate(self,*a):raise TimeoutError()
        ls=LearningService(r.store,r.authority,(spec,),privacy_classes=('PERSONAL',),scopes=('lab',),evaluator=Broken());r.work.open_learning=ls
        start_learning(r,spec)
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone()
        assert job['cursor']==3 and job['state']=='UNKNOWN' and not r.store.all('lessons')

def test_verified_failure_selects_learning_then_runtime_replans_same_goal(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        obj=objective(method='NAIVE_SUM');p=configure(r,tmp_path/'w'/'world.fixture.json',(obj,))
        p.seed_observation(obj.operators[0].resource,[1.2,2.3]);r.work.configure_open_learning((number_learning(),))
        mid=cue(r,obj);send(r,'failure-cause',(mid,));r.step();advance(r,4)
        goal=r.store.all('goals')[0];assert goal['state']=='FAILED'
        exp=r.store.all('experiences')[0]
        send(r,'reflect-failure',(mid,),reflection_experience_id=exp['experience_id'],task_class='numbers')
        r.drain(24);advance(r,12)
        goals=r.store.all('goals');assert len(goals)==1 and goals[0]['state']=='COMPLETED'
        assert any(e['kind']=='open.goal_replanned' for e in r.store.all('events'))
        # Old failure is retained even though a reviewed revision now succeeds.
        assert r.store.one('experiences',exp['experience_id'])['outcome']=='FAILURE'

def test_monitored_strategy_suspension_fences_already_compiled_plan_before_action(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        r.work.configure_open_learning((number_learning(),));start_learning(r,number_learning())
        obj=objective(method='NAIVE_SUM');port=configure(r,tmp_path/'w'/'world.fixture.json',(obj,));r.work.agency.learning=r.work.open_learning
        port.seed_observation(obj.operators[0].resource,[1.2,2.3]);mid=cue(r,obj);send(r,'compiled-before-regression',(mid,));r.step()
        lesson=r.store.all('lessons')[0]
        r.work.open_learning.monitor(lesson['lesson_id'],(LearningCase(case_id='changed-context',context='new-constraint',data=[1,2],expected=999),),authority=r.authority)
        advance(r,2)
        assert r.store.all('goals')[0]['state']=='BLOCKED' and not r.store.all('actions')


def test_subject_reads_lessons_only_for_current_task(tmp_path):
    with fresh(tmp_path / "self.db") as runtime:
        spec = number_learning()
        service = LearningService(
            runtime.store, runtime.authority, (spec,), privacy_classes=("PERSONAL",), scopes=("lab",)
        )
        runtime.work.open_learning = service
        start_learning(runtime, spec, "current-task-study")
        lesson, _ = service.strategy("numbers", "lab")
        everyday = SubjectInput(
            source_key="synthetic.open.everyday",
            kind="WAKE",
            origin="SELF_WAKE",
            entity_id="synthetic-person",
            scope="lab",
            observed_at_us=runtime.clock.utc_now_us(),
        )
        source = runtime.subject.ingress.ingest(everyday)
        statements = []
        runtime.store.db.set_trace_callback(statements.append)
        try:
            situation = runtime.subject.situation(everyday, source)
        finally:
            runtime.store.db.set_trace_callback(None)
        assert lesson not in situation.support_record_ids
        assert not any("FROM lessons" in sql for sql in statements)

        task = everyday.model_copy(update={"source_key": "synthetic.open.numbers", "task_class": "numbers"})
        task_source = runtime.subject.ingress.ingest(task)
        assert lesson in runtime.subject.situation(task, task_source).support_record_ids
