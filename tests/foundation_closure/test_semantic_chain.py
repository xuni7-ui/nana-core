import json
import pytest
from tools.nana_foundation_closure.semantic_chain import run
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.contracts import CoreError


def test_current_lineage_owned_source_semantic_world_concern_c_withdrawal_restart(tmp_path,record_property):
    with provider_harness() as (transport,metrics):
        result=run(tmp_path/'chain',transport)
        assert metrics['calls']==1
        assert result['source_kind']=='MODEL_DERIVATION'
        assert result['intention_before']=='EXPLORE' and result['intention_after']=='NO_ACTION'
        assert result['no_duplicate_dispatch']
        record_property('semantic_chain',json.dumps(result))


def test_live_transport_needs_new_explicit_authorization_before_creating_source(tmp_path):
    class Remote:remote=True
    with pytest.raises(CoreError,match='NEW_PAID'):run(tmp_path/'denied',Remote())
    assert not (tmp_path/'denied').exists()
