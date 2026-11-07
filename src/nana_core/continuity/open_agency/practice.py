"""Bounded practice competition, unable to inspect final evaluator or transfer."""

from ...contracts import CoreError
from ...storage import digest
from .world import transform


def compare_practice(problem, *, preferred, evaluator=None):
    from .learning import LearningProblem

    if type(problem) is not LearningProblem or preferred not in problem.hypotheses:
        raise CoreError("PRACTICE_PROBLEM_REQUIRED")
    trials = []
    for method in problem.hypotheses:
        cases = []
        if evaluator is not None:
            # Trusted application evaluator receives practice ONLY. Boundary,
            # timeout and source-change errors propagate as UNKNOWN, not failure.
            result = evaluator(method, problem.practice)
            for case, row in zip(problem.practice, result["cases"]):
                if row["input_digest"] != digest(case.data) or row["expected_digest"] != digest(case.expected):
                    raise CoreError("PRACTICE_EVALUATION_INVALID")
                cases.append(
                    {
                        "case_id": case.case_id,
                        "input_digest": digest(case.data),
                        "actual_digest": digest(row["actual"]),
                        "passed": digest(row["actual"]) == digest(case.expected),
                    }
                )
            if len(cases) != len(problem.practice):
                raise CoreError("PRACTICE_EVALUATION_INCOMPLETE")
        for case in () if evaluator is not None else problem.practice:
            try:
                actual = transform(method, case.data)
                cases.append(
                    {
                        "case_id": case.case_id,
                        "input_digest": digest(case.data),
                        "actual_digest": digest(actual),
                        "passed": digest(actual) == digest(case.expected),
                    }
                )
            except (CoreError, ValueError, TypeError) as exc:
                cases.append(
                    {
                        "case_id": case.case_id,
                        "input_digest": digest(case.data),
                        "passed": False,
                        "reason": exc.code if isinstance(exc, CoreError) else type(exc).__name__,
                    }
                )
        trials.append(
            {"method": method, "passed": sum(row["passed"] for row in cases), "checked": len(cases), "cases": cases}
        )
    selected = max(trials, key=lambda row: (row["passed"], row["method"] == preferred))["method"]
    return selected, trials
