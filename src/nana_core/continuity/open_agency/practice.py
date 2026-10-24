"""Bounded practice competition, unable to inspect final evaluator or transfer."""
from ...contracts import CoreError
from ...storage import digest
from .world import transform


def compare_practice(problem, *, preferred):
    from .learning import LearningProblem
    if type(problem) is not LearningProblem or preferred not in problem.hypotheses:
        raise CoreError('PRACTICE_PROBLEM_REQUIRED')
    trials = []
    for method in problem.hypotheses:
        cases = []
        for case in problem.practice:
            try:
                actual = transform(method, case.data)
                cases.append({'case_id':case.case_id,'input_digest':digest(case.data),'actual_digest':digest(actual),'passed':digest(actual)==digest(case.expected)})
            except (CoreError, ValueError, TypeError) as exc:
                cases.append({'case_id':case.case_id,'input_digest':digest(case.data),'passed':False,'reason':exc.code if isinstance(exc,CoreError) else type(exc).__name__})
        trials.append({'method':method,'passed':sum(row['passed'] for row in cases),'checked':len(cases),'cases':cases})
    selected = max(trials, key=lambda row:(row['passed'],row['method']==preferred))['method']
    return selected, trials
