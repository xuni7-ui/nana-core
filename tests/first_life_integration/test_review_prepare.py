from tools.nana_first_life_integration.dev import initialize
from tools.nana_first_life_integration.review_prepare import prepare


def test_high_primary_significance_preserves_independent_framing_and_no_authority(tmp_path):
    home=tmp_path/'life';initial=initialize(home)
    from nana_core.life.config import load_config,update_config
    cfg=load_config(home);update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'current_project_state':None}),expected_revision=cfg.revision)
    first=prepare(home)
    assert first['current_state_projection']['attribution']=='EXTERNAL_PROJECT_STATUS_NOT_SUBJECT_EXPERIENCE'
    assert load_config(home).current_project_state is not None
    assert first['identity_id']==initial['identity_id'] and first['primary_user_salience']=='HIGH'
    assert first['framing']['judgment']=='ALTERNATIVE' and not first['framing']['suggestion_auto_adopted']
    assert first['counts_unchanged']['grants']==first['counts_unchanged']['actions']==first['provider_calls']==0
    again=prepare(home)
    assert again['framing']['cycle_id']==first['framing']['cycle_id']
    assert again['counts_unchanged']==first['counts_unchanged']
