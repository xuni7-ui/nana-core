"""Whole-subject qualification; actual codecs/HTTP/isolated skills, no live model."""
import pytest
from nana_core.presence.world_demo import run_world


@pytest.mark.parametrize('variant',[0,1])
def test_integrated_world_life_and_distinct_contrast(tmp_path,variant):
    result=run_world(tmp_path,variant=variant)
    assert result['virtual_hours']>=24
    not_applicable={'learning_reused','world_replanned_after_learning'} if variant else set()
    for gate,value in result['checks'].items():
        if gate in not_applicable:assert value.startswith('NOT_APPLICABLE_')
        else:assert value is True,(gate,value)
    assert result['counts']['goals']>=3
    assert len(result['details']['decoded_world_beliefs'])==3
    assert result['details']['extension']['task']==('TOKEN_ANALYSIS' if variant else 'TEXT_CLEAN')
    domains={g['domain'] for g in result['goal_states']}
    assert ('sorting' if variant else 'numbers') in domains
    assert result['real_model_calls']==result['real_external_actions']==result['real_social_deliveries']==0
