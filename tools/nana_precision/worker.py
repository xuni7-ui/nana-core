"""Data-only planner subprocess. No evaluator, answers, Store or tool handles."""
import json
import sys
import time


def main():
    # Explicit source selector is for equal-condition baseline/candidate runs.
    sys.path.insert(0, sys.argv[1] + '/src')
    from nana_core.continuity.open_agency.contracts import PlannerInput
    from nana_core.continuity.open_agency.planning import BoundedPlanner, validate_plan
    from nana_core.continuity.open_agency.world import LocalWorldRegistry
    from nana_core.contracts import CoreError
    request = json.loads(sys.stdin.read(262145))
    start = time.perf_counter()
    try:
        planner = BoundedPlanner()
        typed = PlannerInput.model_validate_json(json.dumps(request))
        result = planner.plan(typed)
        out = {'state': 'PROPOSED', 'proposal': result.model_dump(mode='json'), 'validator_accepted': False}
        try:
            validate_plan(typed, result, LocalWorldRegistry())
            out['validator_accepted'] = True
        except CoreError as exc:
            out['validation_reason'] = exc.code
        if hasattr(planner, 'last_search'):
            out['search'] = planner.last_search
    except CoreError as exc:
        out = {'state': 'UNAVAILABLE', 'reason': exc.code}
    except Exception as exc:
        out = {'state': 'INVALID', 'reason': type(exc).__name__}
    out['planner_seconds'] = time.perf_counter() - start
    print(json.dumps(out))


if __name__ == '__main__':
    main()
