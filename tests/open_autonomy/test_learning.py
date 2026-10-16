import pytest,json
from nana_core.continuity.open_agency.learning import LearningService,LearningSpec,LearningCase
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.records import RecordService
from nana_core.continuity.learning import ExperienceService
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
