import pytest
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from tools.nana_first_life_integration.dev import initialize,preflight


def test_preflight_read_only_offline_and_fail_closed_live_or_active(tmp_path,approved_dev_branch):
    home=tmp_path/'life';initialize(home)
    result=preflight(home)
    assert result['state']=='PREFLIGHT_PASS' and result['checks']['manager_path']
    with LifeApplication(home) as app:
        before=app.runtime.store.db.total_changes
        assert preflight(home)['state']=='FIRST_LIFE_START_BLOCKED'
        assert app.runtime.store.db.total_changes==before
    assert preflight(home,live=True)['state']=='FIRST_LIFE_START_BLOCKED'
    cfg=load_config(home)
    update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'remote_privacy':('PERSONAL',)}),expected_revision=cfg.revision)
    assert not preflight(home)['checks']['privacy']


def test_branch_mismatch_stays_blocked_without_default_policy_change(tmp_path,monkeypatch):
    import subprocess
    from tools.nana_first_life_integration import dev
    assert dev.BRANCH=='dev/nana-core-cloud-first-life-launch-v1-codex'
    home=tmp_path/'life';initialize(home)
    actual=subprocess.check_output(['git','branch','--show-current'],cwd=dev.REPO,text=True).strip()
    monkeypatch.setattr(dev,'BRANCH',actual+'.not-the-approved-branch')
    result=preflight(home)
    assert result['state']=='FIRST_LIFE_START_BLOCKED'
    assert not result['checks']['branch']
    assert all(value for key,value in result['checks'].items() if key!='branch')
    assert result['read_only'] and not result['production']


@pytest.mark.parametrize('text,kind',[('这个先别聊了','DECLINE_DELIVERY'),('禁止再处理这个信息','DECLINE_DEPTH'),('他说“先别聊”是什么意思','UNCLEAR')])
def test_explicit_boundary_wording(text,kind):
    from nana_core.continuity.dialogue_shadow.bridge import LiteralSpanInterpreter
    assert LiteralSpanInterpreter().interpret(text).kind==kind
