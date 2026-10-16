"""Small public synthetic reference data, no real content/subject bindings."""
from ...storage import digest
from .contracts import Objective,Operator
from .learning import LearningSpec,LearningCase

def numeric_learning():
    return LearningSpec(learning_key='learn.numbers',domain='numbers',baseline_method='NAIVE_SUM',hypotheses=('NUMERIC_SUM',),
        practice=(LearningCase(case_id='practice',context='inventory',data=[1.25,2],expected=3.25),),
        evaluation=(LearningCase(case_id='evaluation',context='inventory',data=[2.5,3.5],expected=6.),),
        transfer=(LearningCase(case_id='transfer',context='science',data=[.2,.3],expected=.5),))

def language_learning():
    return LearningSpec(learning_key='learn.language',domain='language',baseline_method='SPLIT_SPACE',hypotheses=('UNICODE_WORDS',),
        practice=(LearningCase(case_id='practice',context='captions',data='One\tTwo',expected=['One','Two']),),
        evaluation=(LearningCase(case_id='evaluation',context='captions',data='Hello\nworld',expected=['Hello','world']),),
        transfer=(LearningCase(case_id='transfer',context='notes',data='Ａ\u3000Ｂ',expected=['A','B']),))

def numeric_objective():
    return Objective(objective_id='project.inventory',scope='life',motivation_source='PROJECT_COMPLETION',task_domain='numbers',desired=('report',),operators=(
        Operator(operator_id='inspect',capability='world.observe',resource='synthetic://inventory/source',produces=('observed',),args={}),
        Operator(operator_id='total',capability='world.compute',resource='synthetic://inventory/total',requires=('observed',),produces=('totalled',),args={'method':'NAIVE_SUM','input_from':'inspect'},expected_digest=digest(3.5),strategy_selectable=True),
        Operator(operator_id='publish',capability='world.publish',resource='synthetic://inventory/report',requires=('totalled',),produces=('report',),args={'input_from':'total'},expected_digest=digest(3.5))))

def feed_objective():
    return Objective(objective_id='explore.feed',scope='life',motivation_source='CURIOSITY',task_domain='media',desired=('seen',),operators=(
        Operator(operator_id='browse',capability='world.observe',resource='synthetic://media/feed',produces=('seen',),args={}),))
