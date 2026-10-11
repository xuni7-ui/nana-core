import pytest
from nana_core.storage import Store
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError
from nana_core.integration.contracts import RuntimeIntegrationContext
from nana_core.integration.shadow import ShadowBridge,ShadowDecision
from nana_core.integration.session import HostShadowSession,shadow_health
from test_host import event

def test_bounded_window_session_persists_limit_and_dedup(tmp_path):
    p=tmp_path/'s.db';clock=ManualClock();until=clock.utc_now_us()+1_000_000
    d=ShadowDecision(interpretation='one synthetic probe',rationale='no action')
    with Store(p,clock) as s:
        c=RuntimeIntegrationContext(host_instance='synthetic-host',expected_identity_id=s.identity['identity_id'])
        session=HostShadowSession(ShadowBridge(s,c),allowed_conversations=(('qq','synthetic-chat'),),expires_at_us=until)
        result=session.observe(event(),d);assert session.observe(event(),d)==result
        with pytest.raises(CoreError,match='LIMIT'):session.observe(event(event_id='m2'),d)
        with pytest.raises(CoreError,match='OUT_OF_SCOPE'):session.observe(event().model_copy(update={'platform':'bili'}),d)
        assert shadow_health(s)['action_count']==0
    with Store(p,clock) as s:
        session=HostShadowSession(ShadowBridge(s,c),allowed_conversations=(('qq','synthetic-chat'),),expires_at_us=until)
        assert session.observe(event(),d)==result
        clock.advance(2_000_000)
        with pytest.raises(CoreError,match='EXPIRED'):session.observe(event(),d)
