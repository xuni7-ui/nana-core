"""Metadata-only actual receipt accounting, not real provider qualification."""
import pytest
from nana_core.presence.resources import resource_state,_reported_usage_pair
from tests.independent_life.test_dialogue import relay
from nana_core.life.application import LifeApplication


@pytest.mark.parametrize('usage,expected',[
    ({'prompt_tokens':10,'completion_tokens':7,'total_tokens':17},(10,7)),
    ({'input_tokens':4,'output_tokens':0},(4,0)),
    ({'input_tokens':4,'prompt_tokens':4,'output_tokens':1,'completion_tokens':1},(4,1)),
    ({'input_tokens':4,'prompt_tokens':5,'output_tokens':1},None),
    ({'input_tokens':True,'output_tokens':1},None),
    ({'input_tokens':4,'output_tokens':1,'total_tokens':9},None),
    ({'prompt_tokens':8},None),(None,None),({},None),
])
def test_usage_aliases_missing_invalid_and_zero(usage,expected):
    assert _reported_usage_pair(usage)==expected


def test_original_receipts_report_fixture_separately_and_unknown_is_not_free(app,monkeypatch):
    home=app.home;clock=app.clock;app.close()
    with relay(home,'CHAT') as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as current:
            current.pause();answer=current.chat('SYNTHETIC usage sample',message_id='usage')
            assert answer['render_state']=='UNVERIFIED_MODEL_WORDING' and len(requests)==2
            state=resource_state(current.runtime.store,current.runtime.config)
            assert state.provider_reported_input_tokens is None and state.real_usage_reported_calls==0
            assert state.fixture_reported_input_tokens==20 and state.fixture_reported_output_tokens==20
            assert state.fixture_usage_reported_calls==2 and state.usage_missing_or_invalid_calls==0
            from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
            def timeout(*args):raise TimeoutError()
            monkeypatch.setattr(OpenAIJSONTransport,'exchange',timeout)
            current.chat('SYNTHETIC unresolved sample',message_id='usage-unknown')
            after=resource_state(current.runtime.store,current.runtime.config)
            assert after.usage_missing_or_invalid_calls==1 and after.unresolved_calls==1
            assert after.fixture_reported_input_tokens==20
            assert after.reserved_estimated_cost_micro>=state.reserved_estimated_cost_micro
