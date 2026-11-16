import math
import pytest
from tools.nana_next_experience.experiments.video_segment_windows import windows


def test_long_plan_has_bounded_overlapping_windows_and_no_claim_of_observation():
    result=windows('source.fixture',601,window_seconds=600,overlap_seconds=1)
    assert [(x['start_seconds'],x['end_seconds']) for x in result['windows']]==[(0,600),(599,601)]
    assert not result['truncated'] and result['unplanned_intervals']==[]
    assert result['status']=='REQUESTS_ONLY_NOT_OBSERVED' and result['model_calls']==0


def test_exhausted_plan_reports_exact_unplanned_tail():
    result=windows('source.fixture',100,window_seconds=10,overlap_seconds=2,max_windows=3)
    assert [(x['start_seconds'],x['end_seconds']) for x in result['windows']]==[(0,10),(8,18),(16,26)]
    assert result['truncated'] and result['unplanned_intervals']==[(26,100)]


@pytest.mark.parametrize('kwargs',[{'duration':0},{'duration':math.nan},{'duration':100,'overlap_seconds':600},
                                   {'duration':100,'window_seconds':601},{'duration':100,'max_windows':0}])
def test_invalid_bounds_do_not_become_a_plan(kwargs):
    with pytest.raises(ValueError):windows('source.fixture',**kwargs)
