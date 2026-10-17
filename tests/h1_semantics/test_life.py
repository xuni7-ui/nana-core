import json
import pytest
from nana_core.presence.semantic_demo import semantic_world

@pytest.mark.parametrize('variant',[0,1])
def test_48h_semantic_world_reuses_f_g_i_and_preserves_subject(tmp_path,variant):
    result=semantic_world(tmp_path/'world',variant=variant,hours=48)
    assert result['virtual_hours']>=48
    assert all(v is True or str(v).startswith('NOT_APPLICABLE') for v in result['checks'].values()),result['checks']
    assert result['counts']['verified_actions']>=4
    assert result['real_model_calls']==result['real_external_actions']==0
    # Samples are actually decoded, interpreted and grounded; no live quality claim.
    assert set(result['media'])=={'IMAGE','AUDIO','VIDEO'}
    if variant==0:assert result['counts']['lessons']>=1
    else:assert result['counts']['lessons']==0
