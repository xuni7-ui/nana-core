from pathlib import Path
from types import SimpleNamespace
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.cognition import CognitionSession
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.context import ContextPolicy
from nana_core.life.config import update_config
from nana_core.life.application import LifeApplication
from tests.independent_life.conftest import initialize
from tools.nana_foundation_closure.live_once import chain,restrict_once


def test_one_dispatch_guard_rejects_second_before_transport():
    calls=[]
    port=SimpleNamespace(messages=lambda request:[],exchange=lambda request:calls.append(request))
    counter,_=restrict_once(port)
    request=SimpleNamespace(budget=SimpleNamespace(timeout_ms=15000,cost_ceiling_micro=50000))
    port.exchange(request)
    with pytest.raises(CoreError,match='ONE_NEW_DISPATCH_LIMIT'):port.exchange(request)
    assert len(calls)==counter['dispatches']==1


def test_original_life_subject_semantic_chain_loopback(tmp_path):
    home=tmp_path/'life';c=initialize(home,active=0)
    update_config(home,c.model_copy(update={'revision':c.revision+1,'provider_calls_per_day':20,'provider_cost_ceiling_micro':50000}),expected_revision=c.revision)
    root=tmp_path/'experiment';root.mkdir()
    with LifeApplication(home) as app,provider_harness() as (transport,metrics):
        app.pause();identity=app.runtime.identity_id
        policy=ContextPolicy(policy_id='one-loopback',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT'),remote_privacy=('PUBLIC','PROJECT'))
        s=CognitionSession(app.runtime,transport,policy);counter,_=restrict_once(transport)
        result={};chain(app,s,root,result)
        assert result['qualification']=='CONTROLLED_TEXT_SEMANTIC_CHAIN_PASS'
        assert result['identity_id']==identity and result['effect_counts_unchanged']
        assert counter['dispatches']==metrics['calls']==1
        assert result['semantic_source_kind']=='MODEL_DERIVATION' and result['after_intention']=='NO_ACTION'
