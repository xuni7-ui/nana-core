import pytest
from tools.nana_next_experience.experiments.video_coverage import Candidate, plan


def test_coverage_reserves_space_before_change_peaks_and_reports_budget_limit():
    candidates=[Candidate(float(i),cut=100 if i < 5 else 0) for i in range(100)]
    result=plan(100,candidates,4,max_gap=10)
    assert result['timestamps']==(12.,37.,62.,87.)
    assert not result['coverage_target_met'] and result['gaps']
    assert len(result['timestamps'])==4


def test_sparse_timeline_does_not_claim_unseen_coverage():
    result=plan(100,[Candidate(1),Candidate(2),Candidate(90)],8,max_gap=15)
    assert (2,90) in result['gaps'] and not result['coverage_target_met']
    assert set(result['timestamps'])=={1,2,90}


def test_remaining_budget_selects_change_without_losing_coverage():
    candidates=[Candidate(float(i),cut=10 if i==6 else 0) for i in range(11)]
    result=plan(10,candidates,5,max_gap=5)
    assert 6 in result['timestamps'] and len(result['timestamps'])==5
    assert result['coverage_target_met']


def test_exact_duration_is_not_lost_to_floating_window_endpoint():
    duration=23167.081846406618
    assert duration*235/235<duration
    result=plan(duration,[Candidate(duration)],235,max_gap=duration/234.5)
    assert result['timestamps']==(duration,)


def test_midpoint_tie_keeps_earlier_frame_and_duration_endpoint():
    result=plan(10,[Candidate(2),Candidate(3),Candidate(10)],2,max_gap=5)
    assert result['timestamps']==(2,10)


@pytest.mark.parametrize('candidates',[[Candidate(float('nan'))],[Candidate(1),Candidate(1)],[Candidate(11)],[Candidate(1,motion=-1)]])
def test_invalid_measurements_are_rejected(candidates):
    with pytest.raises(ValueError):plan(10,candidates,3,max_gap=2)
